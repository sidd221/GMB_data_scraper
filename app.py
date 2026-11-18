import os
import re
import sys
import uuid
import threading
from datetime import datetime
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
import data_scrap
import db_memory

try:
    if hasattr(sys.stdout, 'reconfigure'):
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        getattr(sys.stderr, 'reconfigure')(encoding='utf-8', errors='replace')
except Exception:
    pass

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Active scrape jobs storage
jobs = {}

def background_scraper(job_id, keyword, city, target_count=100, source="all", skip_memory=True):
    stop_event = threading.Event()
    jobs[job_id]["stop_event"] = stop_event
    jobs[job_id]["status"] = "running"
    src_label = "Multi-Engine (Google + Bing Maps)" if source == "all" else ("Bing Maps" if source == "bing" else "Google Maps")
    auth = data_scrap.check_auth_status()
    auth_tag = f" [Account: {auth['email']}]" if auth.get("logged_in") and auth.get("email") else " [Persistent Profile]"
    cities = data_scrap.parse_cities(city, max_cities=4)
    city_label = ", ".join(cities) if cities else city
    per_city_target = target_count
    total_target = per_city_target * len(cities)
    loc_phrase = f"across {city_label} ({per_city_target} leads/city, up to {total_target} total)" if len(cities) > 1 else f"in '{city_label}' ({per_city_target} leads)"

    known_phones, known_names, _ = db_memory.get_known_identifiers() if skip_memory else (set(), set(), set())
    mem_tag = f" [Memory: {len(known_phones)} leads cached]" if skip_memory and known_phones else ""

    jobs[job_id]["message"] = f"Initializing Chrome{auth_tag}{mem_tag} for {src_label} searching '{keyword}' {loc_phrase}..."
    jobs[job_id]["count"] = 0
    jobs[job_id]["total"] = total_target
    jobs[job_id]["percent"] = 0
    jobs[job_id]["leads"] = []

    clean_kw = re.sub(r'[^a-zA-Z0-9]', '_', keyword.strip()).lower()
    clean_ct = "_".join([re.sub(r'[^a-zA-Z0-9]', '', c).lower() for c in cities]) if cities else re.sub(r'[^a-zA-Z0-9]', '_', city.strip()).lower()
    prefix = "leads" if source == "all" else f"leads_{source}"
    date_str = datetime.now().strftime("%Y-%m-%d")
    base_output = f"{prefix}_{clean_kw}_{clean_ct}_{date_str}"
    output_filename = f"{base_output}.csv"
    if os.path.exists(os.path.join(BASE_DIR, output_filename)):
        time_str = datetime.now().strftime("%H%M%S")
        output_filename = f"{base_output}_{time_str}.csv"
    file_path = os.path.join(BASE_DIR, output_filename)

    seen_names = set(known_names)
    seen_phones = set(known_phones)

    def on_progress(count, total, latest_lead, query_info=""):
        q_label = f" (Searching: '{query_info}')" if query_info else ""
        if latest_lead:
            name = latest_lead.get("Business Name", "")
            phone = latest_lead.get("Phone Number", "")
            canon_p = data_scrap.canonical_phone(phone)
            norm_n = data_scrap.normalize_for_dedup(name)
            if canon_p and norm_n and canon_p not in seen_phones and norm_n not in seen_names:
                seen_phones.add(canon_p)
                seen_names.add(norm_n)
                if "Website" not in latest_lead or not latest_lead["Website"]:
                    latest_lead["Website"] = "NA"
                jobs[job_id]["leads"].append(latest_lead)

        current_count = len(jobs[job_id]["leads"])
        progress_total = total if total > 0 else total_target
        pct = min(100, int((current_count / progress_total) * 100)) if progress_total > 0 else 0
        jobs[job_id]["count"] = current_count
        jobs[job_id]["total"] = progress_total
        jobs[job_id]["percent"] = pct
        jobs[job_id]["message"] = f"Found {current_count} of up to {progress_total} leads ({per_city_target}/city){q_label}..."

    try:
        leads = data_scrap.scrape_leads(
            keyword=keyword,
            city=city,
            target_count=per_city_target,
            source=source,
            progress_callback=on_progress,
            stop_event=stop_event,
            headless=False,
            skip_memory=skip_memory
        )

        final_leads = data_scrap.deduplicate_leads(leads if leads else jobs[job_id]["leads"])

        if final_leads:
            col_order = ["Business Name", "Phone Number", "Website", "City"]
            df = pd.DataFrame(final_leads)
            ordered_cols = [c for c in col_order if c in df.columns] + [c for c in df.columns if c not in col_order]
            df = df[ordered_cols]
            df.to_csv(file_path, index=False, encoding="utf-8-sig")

            # Guarantee all leads are stored into persistent memory database
            db_memory.save_leads_batch(final_leads, keyword=keyword, city=city_label, source=source)

            was_stopped = stop_event.is_set()
            lead_count = len(final_leads)
            if was_stopped:
                status_text = "stopped"
                msg = f"Stopped: Successfully saved all {lead_count} unique leads collected across {city_label} to {output_filename}."
            elif lead_count >= total_target:
                status_text = "completed"
                msg = f"Completed: Successfully collected and saved all {lead_count} target leads across {city_label} to {output_filename}!"
            else:
                status_text = "completed"
                msg = f"Completed: Collected {lead_count} unique leads across {city_label} (Target: {per_city_target} leads/city, up to {total_target}) and saved to {output_filename}!"

            jobs[job_id]["status"] = status_text
            jobs[job_id]["message"] = msg
            jobs[job_id]["count"] = lead_count
            jobs[job_id]["total"] = total_target
            jobs[job_id]["percent"] = 100 if lead_count >= total_target or not was_stopped else min(100, int((lead_count / total_target) * 100))
            jobs[job_id]["filename"] = output_filename
            jobs[job_id]["leads"] = final_leads
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["message"] = f"No new leads found for '{keyword}' {loc_phrase}. Note: If previously scraped leads are stored in memory, all available leads in this area may already have been collected!"

    except Exception as e:
        collected = jobs[job_id].get("leads", [])
        if collected:
            saved_leads = data_scrap.deduplicate_leads(collected)
            if saved_leads:
                try:
                    col_order = ["Business Name", "Phone Number", "Website", "City"]
                    df = pd.DataFrame(saved_leads)
                    ordered_cols = [c for c in col_order if c in df.columns] + [c for c in df.columns if c not in col_order]
                    df = df[ordered_cols]
                    df.to_csv(file_path, index=False, encoding="utf-8-sig")
                    db_memory.save_leads_batch(saved_leads, keyword=keyword, city=city_label, source=source)
                    count = len(saved_leads)
                    jobs[job_id]["status"] = "stopped"
                    jobs[job_id]["message"] = f"Notice: Halted ({str(e)}). Preserved and saved all {count} unique leads to {output_filename}!"
                    jobs[job_id]["filename"] = output_filename
                    jobs[job_id]["count"] = count
                    jobs[job_id]["leads"] = saved_leads
                    jobs[job_id]["percent"] = min(100, int((count / total_target) * 100)) if total_target > 0 else 100
                    return
                except Exception:
                    pass
        jobs[job_id]["status"] = "error"
        jobs[job_id]["message"] = f"An error occurred: {str(e)}"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    data = request.get_json(force=True) or {}
    keyword = data.get("keyword", "").strip()
    city = data.get("city", "").strip()
    source = data.get("source", "all").strip().lower()
    skip_memory = bool(data.get("skip_memory", True))
    if source not in ["all", "google", "bing"]:
        source = "all"

    try:
        target_count = int(data.get("target_count", 100))
        target_count = max(1, min(500, target_count))
    except (ValueError, TypeError):
        target_count = 100

    if not keyword or not city:
        return jsonify({"error": "Both Keyword and City are required."}), 400

    raw_cities = [c.strip() for c in city.split(",") if c.strip()]
    if len(raw_cities) > 4:
        return jsonify({"error": f"Maximum of 4 cities allowed at a time (you provided {len(raw_cities)}). Please reduce your city list to at most 4 cities."}), 400
    if not raw_cities:
        return jsonify({"error": "Please enter at least one valid target city."}), 400

    parsed_cities = data_scrap.parse_cities(city, max_cities=4)
    city_formatted = ", ".join(parsed_cities)
    per_city_target = target_count
    total_target = per_city_target * len(parsed_cities)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "keyword": keyword,
        "city": city_formatted,
        "cities": parsed_cities,
        "source": source,
        "skip_memory": skip_memory,
        "per_city_target": per_city_target,
        "target_count": total_target,
        "total": total_target,
        "count": 0,
        "leads": [],
        "filename": None,
        "message": f"Queued scraper for {city_formatted} ({per_city_target} leads/city, up to {total_target} total)..."
    }

    t = threading.Thread(target=background_scraper, args=(job_id, keyword, city_formatted, per_city_target, source, skip_memory), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})

@app.route("/api/memory/stats")
def memory_stats():
    stats = db_memory.get_memory_stats()
    return jsonify(stats)

@app.route("/api/memory/clear", methods=["POST"])
def memory_clear():
    db_memory.clear_memory()
    return jsonify({"status": "cleared", "message": "Lead memory cleared successfully."})

@app.route("/api/memory/export")
def memory_export():
    leads = db_memory.export_all_leads()
    if not leads:
        return jsonify({"error": "No leads currently saved in memory."}), 404
    export_df = pd.DataFrame(leads)
    date_str = datetime.now().strftime("%Y-%m-%d")
    master_name = f"all_scraped_leads_master_{date_str}.csv"
    export_path = os.path.join(BASE_DIR, master_name)
    export_df.to_csv(export_path, index=False, encoding="utf-8-sig")
    return send_file(export_path, as_attachment=True, download_name=master_name)

@app.route("/api/auth/status")
def auth_status():
    status = data_scrap.check_auth_status()
    return jsonify(status)

@app.route("/api/auth/open_login", methods=["POST"])
def open_login():
    try:
        data_scrap.open_google_login_browser()
        return jsonify({
            "status": "opened",
            "message": "Google Chrome opened! Sign in to your Google account in that window, then click 'Refresh Status'."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/auth/close_login", methods=["POST"])
def close_login():
    data_scrap.cleanup_lingering_scraper_chrome()
    return jsonify({"status": "closed"})

@app.route("/api/status/<job_id>")
def get_status(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job = jobs[job_id]
    return jsonify({
        "status": job.get("status"),
        "message": job.get("message"),
        "count": job.get("count", 0),
        "total": job.get("total", 0),
        "percent": job.get("percent", 0),
        "filename": job.get("filename"),
        "leads": job.get("leads", [])
    })

@app.route("/api/stop/<job_id>", methods=["POST"])
def stop_scrape(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    job = jobs[job_id]
    if "stop_event" in job and job["stop_event"]:
        job["stop_event"].set()
        job["message"] = "Stopping scraper and finalizing results..."
        return jsonify({"status": "stopping"})
    return jsonify({"status": "not_running"})

@app.route("/download/<path:filename>")
def download_file(filename):
    # Sanitize filename
    safe_name = os.path.basename(filename)
    file_path = os.path.join(BASE_DIR, safe_name)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    print("\nStarting Google Maps Lead Scraper Web UI at http://localhost:5000\n")
    app.run(debug=True, port=5000, host="127.0.0.1")
