import os
import re
import sys
import uuid
import threading
import pandas as pd
from flask import Flask, render_template, request, jsonify, send_file
import data_scrap

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Active scrape jobs storage
jobs = {}

def background_scraper(job_id, keyword, city, target_count=100):
    stop_event = threading.Event()
    jobs[job_id]["stop_event"] = stop_event
    jobs[job_id]["status"] = "running"
    jobs[job_id]["message"] = f"Initializing Chrome and searching Google Maps for '{keyword}' in '{city}'..."
    jobs[job_id]["count"] = 0
    jobs[job_id]["total"] = target_count
    jobs[job_id]["percent"] = 0
    jobs[job_id]["leads"] = []

    def on_progress(count, total, latest_lead, query_info=""):
        pct = min(100, int((count / total) * 100)) if total > 0 else 0
        jobs[job_id]["count"] = count
        jobs[job_id]["total"] = total
        jobs[job_id]["percent"] = pct
        q_label = f" (Searching: '{query_info}')" if query_info else ""
        jobs[job_id]["message"] = f"Found {count} of {total} leads{q_label}..."
        if latest_lead:
            jobs[job_id]["leads"].append(latest_lead)

    try:
        leads = data_scrap.scrape_google_maps(
            keyword=keyword,
            city=city,
            target_count=target_count,
            progress_callback=on_progress,
            stop_event=stop_event,
            headless=False
        )

        clean_kw = re.sub(r'[^a-zA-Z0-9]', '_', keyword.strip()).lower()
        clean_ct = re.sub(r'[^a-zA-Z0-9]', '_', city.strip()).lower()
        output_filename = f"leads_{clean_kw}_{clean_ct}.csv"
        file_path = os.path.join(BASE_DIR, output_filename)

        if leads:
            df = pd.DataFrame(leads)
            df.to_csv(file_path, index=False, encoding="utf-8-sig")

            was_stopped = stop_event.is_set()
            status_text = "stopped" if was_stopped else "completed"
            msg = f"Saved {len(leads)} leads to {output_filename}!" if not was_stopped else f"Stopped: Saved {len(leads)} leads collected so far."

            jobs[job_id]["status"] = status_text
            jobs[job_id]["message"] = msg
            jobs[job_id]["count"] = len(leads)
            jobs[job_id]["filename"] = output_filename
            jobs[job_id]["leads"] = leads
        else:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["message"] = "No leads found. Please try a different business keyword or city."

    except Exception as e:
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
    try:
        target_count = int(data.get("target_count", 100))
        target_count = max(1, min(500, target_count))
    except (ValueError, TypeError):
        target_count = 100

    if not keyword or not city:
        return jsonify({"error": "Both Keyword and City are required."}), 400

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "pending",
        "keyword": keyword,
        "city": city,
        "target_count": target_count,
        "count": 0,
        "leads": [],
        "filename": None,
        "message": "Queued scraper..."
    }

    t = threading.Thread(target=background_scraper, args=(job_id, keyword, city, target_count), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})

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
