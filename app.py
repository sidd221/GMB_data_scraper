from flask import Flask, render_template, request, jsonify
import data_scrap
import pandas as pd
import threading
import uuid

app = Flask(__name__)

# To prevent the browser from timing out while we scrape 200 leads,
# we will run the scraper in a background thread and let the frontend check its status.
jobs = {}

def background_scraper(job_id, keyword, city, source="google", target_count=200):
    source_label = "Bing Maps" if source == "bing" else "Google Maps"
    jobs[job_id] = {"status": "running", "message": f"Initializing browser and scraping {source_label}...", "count": 0}
    try:
        # Run selected scraper logic
        if source == "bing":
            scraped_data = data_scrap.scrape_bing_maps(keyword, city, target_count=target_count)
        else:
            scraped_data = data_scrap.scrape_google_maps(keyword, city, target_count=target_count)
        
        if scraped_data:
            df = pd.DataFrame(scraped_data)
            clean_keyword = keyword.replace(" ", "_").lower()
            clean_city = city.replace(" ", "_").lower()
            output_file = f"leads_{source}_{clean_keyword}_{clean_city}.csv"
            df.to_csv(output_file, index=False, encoding="utf-8-sig")
            
            jobs[job_id] = {
                "status": "completed",
                "message": f"Successfully exported {len(scraped_data)} records to {output_file} via {source_label}!",
                "count": len(scraped_data),
                "filename": output_file
            }
        else:
            jobs[job_id] = {
                "status": "error",
                "message": f"No data was extracted from {source_label}. Please try a different search or location."
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
    source = data.get("source", "google").lower()
    if source not in ["google", "bing"]:
        source = "google"
    default_count = 100 if source == "bing" else 200
    target_count = int(data.get("target_count", default_count))
    
    if not keyword or not city:
        return jsonify({"error": "Keyword and City are required"}), 400
        
    job_id = str(uuid.uuid4())
    
    # Start the scraper in a separate thread so Flask can respond immediately
    thread = threading.Thread(target=background_scraper, args=(job_id, keyword, city, source, target_count))
    thread.daemon = True
    thread.start()
    
    return jsonify({"job_id": job_id})

@app.route("/api/status/<job_id>")
def check_status(job_id):
    if job_id in jobs:
        return jsonify(jobs[job_id])
    return jsonify({"status": "unknown"}), 404

if __name__ == "__main__":
    app.run(debug=True, port=5000)
