import sys
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from flask import Flask, render_template, request, jsonify
import data_scrap
import ai_recommender
import bihar_directory_scraper
import indiamart_scraper
import ai_engine
import pandas as pd
import threading
import uuid
import time

app = Flask(__name__)

# To prevent the browser from timing out while we scrape leads,
# we will run the scraper in a background thread and let the frontend check its status.
jobs = {}

def format_eta(seconds):
    """Format ETA seconds into human-readable string like ~2m 30s left."""
    if seconds is None:
        return "Calculating ETA..."
    if seconds <= 0:
        return "Finishing up..."
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"~{h}h {m}m left"
    elif m > 0:
        return f"~{m}m {s}s left"
    else:
        return f"~{s}s left"

def format_duration(seconds):
    """Format duration in seconds into Xm Ys or Xs."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    elif m > 0:
        return f"{m}m {s}s"
    else:
        return f"{s}s"

def background_scraper(job_id, keyword, city, target_count=400, require_website=False, mode="general", directory_source="all"):
    start_time = time.time()

    if mode == "bihar_directory":
        jobs[job_id] = {
            "status": "running",
            "message": f"Scanning bot-friendly Bihar Local Directories for '{keyword}' in {city}...",
            "count": 0,
            "total": target_count,
            "percent": 0,
            "start_time": start_time,
            "elapsed_seconds": 0,
            "elapsed_text": "0s",
            "eta_seconds": None,
            "eta_text": "Connecting to directory...",
            "speed": "--"
        }
        
        def on_dir_progress(count, total):
            elapsed = max(1.0, time.time() - start_time)
            rate = count / elapsed
            remaining = max(0, total - count)
            eta_seconds = int(remaining / rate) if rate > 0 and count >= 2 else None
            eta_text = format_eta(eta_seconds) if eta_seconds is not None else "Estimating pace..."
            speed_text = f"{rate * 60:.1f} leads/min" if count >= 2 else "--"
            pct = min(100, int((count / total) * 100)) if total > 0 else 0

            jobs[job_id].update({
                "count": count,
                "total": total,
                "percent": pct,
                "elapsed_seconds": int(elapsed),
                "elapsed_text": format_duration(elapsed),
                "eta_seconds": eta_seconds,
                "eta_text": eta_text,
                "speed": speed_text,
                "message": f"Extracting Bihar Directory leads... Found {count}/{total} verified listings."
            })

        try:
            scraped_data = bihar_directory_scraper.scrape_bihar_directory(
                keyword=keyword,
                city=city,
                target_count=target_count,
                directory_source=directory_source,
                progress_callback=on_dir_progress
            )
            elapsed_final = int(time.time() - start_time)
            if scraped_data:
                df = pd.DataFrame(scraped_data)
                clean_keyword = keyword.replace(" ", "_").lower()
                clean_city = city.replace(" ", "_").lower()
                output_file = f"leads_bihardir_{clean_keyword}_{clean_city}.csv"
                df.to_csv(output_file, index=False, encoding="utf-8-sig")

                final_speed = f"{(len(scraped_data) / max(1.0, elapsed_final)) * 60:.1f} leads/min"
                jobs[job_id] = {
                    "status": "completed",
                    "message": f"Successfully extracted {len(scraped_data)} verified local leads to {output_file} from Bihar Directories!",
                    "count": len(scraped_data),
                    "total": target_count,
                    "percent": 100,
                    "elapsed_seconds": elapsed_final,
                    "elapsed_text": format_duration(elapsed_final),
                    "eta_seconds": 0,
                    "eta_text": "Completed",
                    "speed": final_speed,
                    "filename": output_file
                }
            else:
                jobs[job_id] = {
                    "status": "error",
                    "message": f"No listings found in Bihar Directories for '{keyword}' in {city}. Try broader categories like 'Real Estate', 'Coaching', or 'Contractors'."
                }
        except Exception as e:
            jobs[job_id] = {
                "status": "error",
                "message": f"An error occurred while scraping Bihar Directory: {str(e)}"
            }
        return

    if mode == "indiamart":
        jobs[job_id] = {
            "status": "running",
            "message": f"Launching Playwright Chromium & scanning IndiaMART directory for '{keyword}' in {city}...",
            "count": 0,
            "total": target_count,
            "percent": 0,
            "start_time": start_time,
            "elapsed_seconds": 0,
            "elapsed_text": "0s",
            "eta_seconds": None,
            "eta_text": "Launching Playwright...",
            "speed": "--"
        }

        def on_indiamart_progress(count, processed, total):
            elapsed = max(1.0, time.time() - start_time)
            rate = count / elapsed
            remaining = max(0, total - count)
            eta_seconds = int(remaining / rate) if rate > 0 and count >= 2 else None
            eta_text = format_eta(eta_seconds) if eta_seconds is not None else "Estimating pace..."
            speed_text = f"{rate * 60:.1f} leads/min" if count >= 2 else "--"
            pct = min(100, int((count / total) * 100)) if total > 0 else 0

            jobs[job_id].update({
                "count": count,
                "total": total,
                "percent": pct,
                "elapsed_seconds": int(elapsed),
                "elapsed_text": format_duration(elapsed),
                "eta_seconds": eta_seconds,
                "eta_text": eta_text,
                "speed": speed_text,
                "message": f"Extracting IndiaMART B2B leads... Found {count}/{total} verified suppliers ({processed} processed)."
            })

        try:
            scraped_data = indiamart_scraper.scrape_indiamart(
                keyword=keyword,
                city=city,
                target_count=target_count,
                progress_callback=on_indiamart_progress
            )
            elapsed_final = int(time.time() - start_time)
            if scraped_data:
                df = pd.DataFrame(scraped_data)
                columns = ["company_name", "phone", "city", "address", "profile_url"]
                for col in columns:
                    if col not in df.columns:
                        df[col] = "N/A"
                df = df[columns]

                clean_keyword = keyword.replace(" ", "_").lower()
                clean_city = city.replace(" ", "_").lower()
                output_file = f"leads_indiamart_{clean_keyword}_{clean_city}.csv"
                df.to_csv(output_file, index=False, encoding="utf-8-sig")

                final_speed = f"{(len(scraped_data) / max(1.0, elapsed_final)) * 60:.1f} leads/min"
                jobs[job_id] = {
                    "status": "completed",
                    "message": f"Successfully extracted {len(scraped_data)} verified B2B leads to {output_file} from IndiaMART!",
                    "count": len(scraped_data),
                    "total": target_count,
                    "percent": 100,
                    "elapsed_seconds": elapsed_final,
                    "elapsed_text": format_duration(elapsed_final),
                    "eta_seconds": 0,
                    "eta_text": "Completed",
                    "speed": final_speed,
                    "filename": output_file
                }
            else:
                jobs[job_id] = {
                    "status": "error",
                    "message": f"No suppliers found on IndiaMART for '{keyword}' in {city}. Try broader terms like 'pharmaceutical-distributors', 'chemicals', or 'machinery'."
                }
        except Exception as e:
            jobs[job_id] = {
                "status": "error",
                "message": f"An error occurred while scraping IndiaMART: {str(e)}"
            }
        return

    # Google Maps Scraper (General & Coaching modes)
    status_suffix = " (Website & Phone Verified)" if require_website else ""
    jobs[job_id] = {
        "status": "running", 
        "message": f"Initializing browser and scanning Google Maps{status_suffix}...", 
        "count": 0,
        "total": target_count,
        "percent": 0,
        "start_time": start_time,
        "elapsed_seconds": 0,
        "elapsed_text": "0s",
        "eta_seconds": None,
        "eta_text": "Launching Chrome & Maps...",
        "speed": "--"
    }
    
    def on_progress(count, total):
        elapsed = max(1.0, time.time() - start_time)
        rate = count / elapsed
        remaining = max(0, total - count)
        eta_seconds = int(remaining / rate) if rate > 0 and count >= 2 else None
        eta_text = format_eta(eta_seconds) if eta_seconds is not None else "Estimating pace..."
        speed_text = f"{rate * 60:.1f} leads/min" if count >= 2 else "--"
        pct = min(100, int((count / total) * 100)) if total > 0 else 0

        jobs[job_id].update({
            "count": count,
            "total": total,
            "percent": pct,
            "elapsed_seconds": int(elapsed),
            "elapsed_text": format_duration(elapsed),
            "eta_seconds": eta_seconds,
            "eta_text": eta_text,
            "speed": speed_text,
            "message": f"Scraping Google Maps{status_suffix}... Found {count}/{total} verified leads."
        })

    try:
        scraped_data = data_scrap.scrape_google_maps(
            keyword, city, target_count=target_count, 
            progress_callback=on_progress, require_website=require_website
        )
        elapsed_final = int(time.time() - start_time)
        if scraped_data:
            df = pd.DataFrame(scraped_data)
            clean_keyword = keyword.replace(" ", "_").lower()
            clean_city = city.replace(" ", "_").lower()
            prefix = "leads_coaching" if require_website else "leads"
            output_file = f"{prefix}_google_{clean_keyword}_{clean_city}.csv"
            df.to_csv(output_file, index=False, encoding="utf-8-sig")
            
            final_speed = f"{(len(scraped_data) / max(1.0, elapsed_final)) * 60:.1f} leads/min"
            jobs[job_id] = {
                "status": "completed",
                "message": f"Successfully exported {len(scraped_data)} records to {output_file} via Google Maps!",
                "count": len(scraped_data),
                "total": target_count,
                "percent": 100,
                "elapsed_seconds": elapsed_final,
                "elapsed_text": format_duration(elapsed_final),
                "eta_seconds": 0,
                "eta_text": "Completed",
                "speed": final_speed,
                "filename": output_file
            }
        else:
            jobs[job_id] = {
                "status": "error",
                "message": "No data was extracted from Google Maps. Please try a different search or location."
            }
    except Exception as e:
        jobs[job_id] = {
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/scrape", methods=["POST"])
def start_scrape():
    data = request.json or {}
    keyword = data.get("keyword")
    city = data.get("city")
    default_count = 400
    target_count = int(data.get("target_count", default_count))
    mode = data.get("mode", "general")
    require_website = bool(data.get("require_website", mode == "coaching"))
    directory_source = data.get("directory_source", "all")
    
    if not keyword or not city:
        return jsonify({"error": "Keyword and City are required"}), 400
        
    job_id = str(uuid.uuid4())
    
    # Start the scraper in a separate thread
    thread = threading.Thread(
        target=background_scraper, 
        args=(job_id, keyword, city, target_count, require_website, mode, directory_source)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def check_status(job_id):
    if job_id not in jobs:
        return jsonify({"status": "unknown"}), 404
    job = dict(jobs[job_id])
    if job.get("status") == "running" and "start_time" in job:
        elapsed = max(1.0, time.time() - job["start_time"])
        count = job.get("count", 0)
        total = job.get("total", 400)
        job["elapsed_seconds"] = int(elapsed)
        job["elapsed_text"] = format_duration(elapsed)
        if count >= 2:
            rate = count / elapsed
            remaining = max(0, total - count)
            eta_seconds = int(remaining / rate)
            job["eta_seconds"] = eta_seconds
            job["eta_text"] = format_eta(eta_seconds)
            job["speed"] = f"{rate * 60:.1f} leads/min"
        else:
            job["eta_seconds"] = None
            if elapsed < 15:
                job["eta_text"] = "Launching Chrome & scanning zones..."
            else:
                job["eta_text"] = "Reading first batch of listings..."
            job["speed"] = "--"
        job["percent"] = min(100, int((count / total) * 100)) if total > 0 else 0
    return jsonify(job)

@app.route("/api/bihar_directory/presets")
def get_bihar_directory_presets():
    return jsonify(bihar_directory_scraper.get_bihar_presets())

@app.route("/api/ai/categories")
def get_ai_categories():
    return jsonify({
        "categories": ai_recommender.get_categories(),
        "regions": ai_recommender.get_regions(),
        "google_sync": ai_recommender.get_google_sync_status()
    })

@app.route("/api/ai/sync_google", methods=["GET", "POST"])
def sync_google():
    sync_result = ai_recommender.sync_google_keywords(force=True)
    return jsonify({
        "success": True,
        "message": f"Successfully synced {sync_result.get('count', 0)} real-time trending keywords from Google India!",
        "google_sync": ai_recommender.get_google_sync_status()
    })

@app.route("/api/ai/recommend", methods=["GET", "POST"])
def get_ai_recommendations():
    if request.method == "POST":
        data = request.json or {}
    else:
        data = request.args
    
    state = data.get("state", "all")
    category = data.get("category", "all")
    sub_category = data.get("sub_category", "all")
    query = data.get("query", "")
    city = data.get("city", "")
    try:
        limit = int(data.get("limit", 24))
    except (ValueError, TypeError):
        limit = 24
    
    recs = ai_recommender.recommend_keywords(
        state=state,
        category=category,
        sub_category=sub_category,
        query=query,
        city=city,
        limit=limit
    )
    return jsonify({
        "recommendations": recs,
        "google_sync": ai_recommender.get_google_sync_status()
    })

# --- Live AI Research & Daily Recommendations Endpoints ---
@app.route("/api/ai/config", methods=["GET", "POST"])
def ai_config_route():
    if request.method == "POST":
        data = request.json or {}
        provider = data.get("provider", "gemini")
        api_key = data.get("api_key", "")
        model = data.get("model", "")
        saved_cfg = ai_engine.save_config(provider, api_key, model)
        return jsonify({
            "success": True,
            "message": "AI configuration updated successfully!",
            "config": ai_engine.get_public_config()
        })
    return jsonify(ai_engine.get_public_config())

@app.route("/api/ai/test_key", methods=["POST"])
def ai_test_key_route():
    data = request.json or {}
    provider = data.get("provider", "gemini")
    api_key = data.get("api_key", "")
    model = data.get("model", "")
    success, msg = ai_engine.test_api_connection(provider, api_key, model)
    return jsonify({
        "success": success,
        "message": msg
    })

@app.route("/api/ai/daily", methods=["GET", "POST"])
def ai_daily_route():
    force = False
    if request.method == "POST":
        data = request.json or {}
        force = bool(data.get("force", False))
    else:
        force = request.args.get("force", "false").lower() == "true"
        
    result = ai_engine.get_daily_ai_recommendations(force_refresh=force)
    return jsonify(result)

@app.route("/api/ai/deep_research", methods=["POST"])
def ai_deep_research_route():
    data = request.json or {}
    topic = data.get("topic", "").strip()
    if not topic:
        return jsonify({"success": False, "error": "Research topic or query is required"}), 400
        
    sector = data.get("sector", "all")
    region = data.get("region", "all")
    focus = data.get("focus", "all")
    
    result = ai_engine.conduct_deep_research(
        topic=topic,
        sector=sector,
        region=region,
        focus=focus
    )
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
