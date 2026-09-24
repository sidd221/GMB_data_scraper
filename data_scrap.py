import sys
import time
import re
import json
import random
import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import urllib3
import requests
from urllib.parse import urlparse, parse_qs, urljoin
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def safe_print(*args, **kwargs):
    """Safely print strings avoiding UnicodeEncodeError crashes on Windows."""
    kwargs.setdefault('flush', True)
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        try:
            enc = sys.stdout.encoding or 'utf-8'
            cleaned = [str(a).encode(enc, errors='replace').decode(enc, errors='replace') for a in args]
            print(*cleaned, **kwargs)
        except Exception:
            pass
    except Exception:
        pass

def get_chrome_major_version():
    """Detect the installed Google Chrome major version."""
    try:
        if sys.platform.startswith("win"):
            import winreg
            paths = [
                r"Software\Google\Chrome\BLBeacon",
                r"Software\Wow6432Node\Google\Chrome\BLBeacon"
            ]
            for p in paths:
                for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                    try:
                        with winreg.OpenKey(root, p) as key:
                            v, _ = winreg.QueryValueEx(key, "version")
                            if v:
                                return int(v.split(".")[0])
                    except Exception:
                        pass
        elif sys.platform.startswith("darwin"):
            import subprocess
            res = subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"], capture_output=True, text=True)
            match = re.search(r"(\d+)\.", res.stdout)
            if match:
                return int(match.group(1))
        elif sys.platform.startswith("linux"):
            import subprocess
            res = subprocess.run(["google-chrome", "--version"], capture_output=True, text=True)
            match = re.search(r"(\d+)\.", res.stdout)
            if match:
                return int(match.group(1))
    except Exception:
        pass
    return None

def extract_website_from_gmaps(soup):
    """Extract official website link from Google Maps place details HTML."""
    website = ""
    # Method 1: data-item-id="authority"
    web_tag = soup.find("a", {"data-item-id": "authority"})
    if web_tag and web_tag.get("href"):
        website = web_tag["href"].strip()
        
    # Method 2: data-tooltip="Open website"
    if not website:
        web_tag = soup.find("a", {"data-tooltip": re.compile(r"website", re.I)})
        if web_tag and web_tag.get("href"):
            website = web_tag["href"].strip()

    # Method 3: aria-label starting with Website:
    if not website:
        web_tag = soup.find("a", {"aria-label": re.compile(r"Website:", re.I)})
        if web_tag and web_tag.get("href"):
            website = web_tag["href"].strip()

    # Method 4: any link with aria-label or text containing website
    if not website:
        for a in soup.find_all("a", href=True):
            aria = a.get("aria-label", "").lower()
            text = a.get_text(strip=True).lower()
            href = a["href"].strip()
            if ("website" in aria or text == "website") and href.startswith("http"):
                if not any(d in href for d in ["google.com", "gstatic.com", "goo.gl"]):
                    website = href
                    break

    # Clean Google redirect URL if wrapped
    if website and "google.com/url" in website:
        try:
            parsed = parse_qs(urlparse(website).query)
            if "q" in parsed:
                website = parsed["q"][0]
        except Exception:
            pass
            
    return website

def extract_website_from_bing_card(card, ent_dict=None):
    """Extract official website link from Bing Maps listing card."""
    if ent_dict:
        for key in ["website", "url", "officialWebsite", "webUrl"]:
            val = ent_dict.get(key)
            if val and isinstance(val, str) and val.startswith("http"):
                if not any(d in val for d in ["bing.com", "microsoft.com", "msn.com"]):
                    return val.strip()

    # Check <a> tags with Website in text, title, or aria-label
    for a in card.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True).lower()
        title = a.get("title", "").lower()
        aria = a.get("aria-label", "").lower()
        if (text == "website" or "website" in title or "website" in aria) and href.startswith("http"):
            if not any(d in href for d in ["bing.com", "microsoft.com", "msn.com"]):
                return href

    # Check any external href
    for a in card.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("http") and not any(d in href for d in ["bing.com", "microsoft.com", "msn.com", "google.com"]):
            return href

    return ""

def extract_details_from_website(website_url):
    """
    Visits the website (and optionally /contact) to extract verified phone numbers
    and institute/company name mentioned on the website.
    """
    if not website_url or not website_url.startswith("http"):
        return {"phone": "", "site_name": ""}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    found_phone = ""
    site_name = ""

    def scan_html(html_text):
        nonlocal found_phone, site_name
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            
            # Title / site name
            if not site_name:
                meta_site = soup.find("meta", property="og:site_name")
                if meta_site and meta_site.get("content"):
                    site_name = meta_site["content"].strip()
                elif soup.title and soup.title.string:
                    site_name = soup.title.string.split("|")[0].split("-")[0].strip()

            # Method 1: Check tel: links (most accurate)
            tel_links = soup.find_all("a", href=re.compile(r"^tel:", re.I))
            for tl in tel_links:
                raw_tel = re.sub(r"^tel:", "", tl.get("href", ""), flags=re.I).strip()
                clean = re.sub(r"[^\d+]", "", raw_tel)
                if len(clean) >= 8:
                    found_phone = raw_tel
                    return True
            
            # Method 2: Check phone regex in contact blocks / header / footer
            contact_elements = soup.find_all(class_=re.compile(r"contact|phone|header|footer|top-bar|helpline|support", re.I))
            for elem in contact_elements:
                text = elem.get_text()
                match = re.search(r'(?:\+?91[\s-]?)?[6-9]\d{9}', text)
                if match:
                    found_phone = match.group(0).strip()
                    return True
                match_gen = re.search(r'(\+?\d[\d \-\(\)]{8,14}\d)', text)
                if match_gen:
                    found_phone = match_gen.group(0).strip()
                    return True

            # Method 3: Entire page regex
            page_text = soup.get_text()
            match = re.search(r'(?:\+?91[\s-]?)?[6-9]\d{9}', page_text)
            if match:
                found_phone = match.group(0).strip()
                return True
            match_gen = re.search(r'(\+?\d[\d \-\(\)]{8,14}\d)', page_text)
            if match_gen:
                found_phone = match_gen.group(0).strip()
                return True
        except Exception:
            pass
        return False

    try:
        resp = requests.get(website_url, headers=headers, timeout=3, verify=False)
        if resp.status_code == 200:
            if scan_html(resp.text):
                return {"phone": found_phone, "site_name": site_name}
            
            # Fallback: check contact page
            soup = BeautifulSoup(resp.text, "html.parser")
            contact_a = soup.find("a", href=re.compile(r"contact", re.I))
            if contact_a and contact_a.get("href"):
                contact_url = urljoin(website_url, contact_a["href"])
                try:
                    c_resp = requests.get(contact_url, headers=headers, timeout=3, verify=False)
                    if c_resp.status_code == 200:
                        scan_html(c_resp.text)
                except Exception:
                    pass
    except Exception:
        pass

    return {"phone": found_phone, "site_name": site_name}

def get_user_input():
    print("\n==============================")
    print("BUSINESS LEADS SCRAPER (NAME, PHONE & WEBSITE)")
    print("==============================\n")
    print("Select Platform:")
    print("  1. Google Maps")
    print("  2. Bing Maps")
    choice = input("Enter choice (1 or 2, default 1): ").strip()
    source = "bing" if choice == "2" else "google"
    keyword = input("Enter Business Keyword (e.g., IIT JEE Coaching): ").strip()
    city = input("Enter City (e.g., Patna): ").strip()
    req_web = input("Require official website & verify website details? (y/n, default n): ").strip().lower()
    require_website = req_web == "y"
    return keyword, city, source, require_website

# City hubs and adjoining commercial corridors for deep multi-zone scanning
CITY_LOCALITY_HUBS = {
    "hajipur": ["Sonpur", "Paswan Chowk", "Bagmali", "Konhara Ghat", "Yadav Chowk", "Lalganj Road", "Industrial Area", "Vaishali"],
    "patna": ["Boring Road", "Kankarbagh", "Bailey Road", "Danapur", "Saguna More", "Bihta", "Rajendra Nagar", "Exhibition Road", "Anisabad", "Patliputra", "Ashiana Nagar", "Fraser Road"],
    "muzaffarpur": ["Bhagwanpur", "Mithanpura", "Sutapatti", "Gobarsahi", "Bypass Road", "Brahmpura", "Ramdayalu Nagar", "Zero Mile"],
    "gaya": ["Bodh Gaya", "Civil Lines", "Dobhi Highway", "GB Road", "Medical College Road"],
    "bhagalpur": ["Adampur", "Zero Mile", "Tilkamanjhi", "Bypass Road", "Mirjanhat"],
    "darbhanga": ["Laheriasarai", "Airport Road", "Tower Chowk", "Benta"],
    "purnia": ["Line Bazar", "Bhatta Bazar", "Gulabbagh", "Rambagh"],
    "begusarai": ["Barauni", "Traffic Chowk", "NH-31 Corridor", "Har Har Mahadev Chowk"],
    "ara": ["Gopali Chowk", "Arrah-Patna 4 Lane Road", "Dharahara", "Nawada"],
    "bihar sharif": ["Ranchi Road", "Hospital More", "NH-20", "Ramchandrapur"],
    "ranchi": ["Lalpur", "Main Road", "Harmu", "Doranda", "Bariatu", "Ratu Road", "Hinoo", "Morabadi", "Namkum", "Tupudana", "Kathal More", "Ring Road"],
    "jamshedpur": ["Bistupur", "Sakchi", "Dimna Road", "Mango", "Gamharia", "Adityapur Industrial Area", "Telco", "Kadma", "Sonari"],
    "dhanbad": ["Bank More", "Govindpur GT Road", "Saraidhela", "Barwadda Bypass", "Hirapur", "Jharia", "Katras"],
    "bokaro": ["Sector 4", "Chas Highway Corridor", "Sector 1", "Sector 6", "Bokaro Steel City"],
    "deoghar": ["AIIMS Road", "Tower Chowk", "Castairs Town", "Jasidih", "Baidyanath Dham"],
    "hazaribagh": ["Malviya Marg", "Korrah", "NH-33 Bypass", "Matwari"],
    "delhi": ["Connaught Place", "South Extension", "Lajpat Nagar", "Dwarka", "Rohini", "Karol Bagh", "Janakpuri", "Laxmi Nagar", "Saket", "Pitampura"],
    "mumbai": ["Andheri", "Bandra", "Borivali", "Thane", "Navi Mumbai", "Dadar", "Powai", "Goregaon", "Malad", "Worli"],
    "kolkata": ["Salt Lake", "Park Street", "New Town", "Gariahat", "Behala", "Howrah", "Dum Dum", "Rajarhat"],
    "bangalore": ["Indiranagar", "Koramangala", "Whitefield", "HSR Layout", "Jayanagar", "Electronic City", "Marathahalli", "BTM Layout"],
    "hyderabad": ["Hitech City", "Madhapur", "Gachibowli", "Banjara Hills", "Jubilee Hills", "Kukatpally", "Secunderabad", "Ameerpet"]
}

def generate_google_maps_queries(keyword, city):
    """
    Generates intelligent multi-locality and synonym search queries for Google Maps
    so that searches can easily break past the ~30-60 listing single-search limit
    and harvest between 100 and 400+ unique verified leads per city.
    """
    clean_kw = keyword.strip()
    clean_city = city.strip()
    city_lower = clean_city.lower()
    kw_lower = clean_kw.lower()

    queries = []
    
    # 1. Primary Query
    queries.append(f"{clean_kw} in {clean_city}")

    # 2. Semantic & Synonym Variations
    synonyms = []
    if any(w in kw_lower for w in ["gym", "jym", "fitness", "workout"]):
        synonyms = [
            f"gyms in {clean_city}",
            f"fitness center in {clean_city}",
            f"unisex gym in {clean_city}",
            f"crossfit workout gym in {clean_city}",
            f"health club and gym in {clean_city}",
            f"ladies gym in {clean_city}"
        ]
    elif any(w in kw_lower for w in ["bone", "ortho", "orthopedic", "joint", "knee"]):
        synonyms = [
            f"orthopedic doctor in {clean_city}",
            f"bone specialist clinic in {clean_city}",
            f"orthopedic hospital in {clean_city}",
            f"bone and joint doctor in {clean_city}",
            f"knee specialist doctor in {clean_city}",
            f"fracture clinic in {clean_city}"
        ]
    elif any(w in kw_lower for w in ["doctor", "clinic", "hospital"]):
        synonyms = [
            f"top {clean_kw} in {clean_city}",
            f"{clean_kw} clinic in {clean_city}",
            f"{clean_kw} specialist in {clean_city}",
            f"private hospital in {clean_city}"
        ]
    elif any(w in kw_lower for w in ["plot", "land", "real estate", "property"]):
        synonyms = [
            f"real estate property dealers in {clean_city}",
            f"plots for sale in {clean_city}",
            f"residential plots in {clean_city}",
            f"land colonizers and developers in {clean_city}"
        ]
    elif any(w in kw_lower for w in ["coaching", "classes", "tuition", "institute"]):
        synonyms = [
            f"coaching institute in {clean_city}",
            f"tuition center in {clean_city}",
            f"academy in {clean_city}"
        ]
    else:
        synonyms = [
            f"top {clean_kw} in {clean_city}",
            f"{clean_kw} center in {clean_city}",
            f"{clean_kw} services in {clean_city}"
        ]

    for syn in synonyms:
        if syn not in queries:
            queries.append(syn)

    # 3. Known Locality / Hub Variations
    hubs = CITY_LOCALITY_HUBS.get(city_lower, [])
    if not hubs:
        for k, v in CITY_LOCALITY_HUBS.items():
            if k in city_lower:
                hubs = v
                break

    for hub in hubs:
        hub_query = f"{clean_kw} in {hub}, {clean_city}"
        if hub_query not in queries:
            queries.append(hub_query)

    # 4. Directional / Generic Market Corridors
    generic_areas = ["Main Road", "Station Road", "Market", "Bypass Road", "near"]
    for area in generic_areas:
        if area == "near":
            g_query = f"{clean_kw} near {clean_city}"
        else:
            g_query = f"{clean_kw} in {area}, {clean_city}"
        if g_query not in queries:
            queries.append(g_query)

    return queries

def extract_gmaps_place_details(soup, link=""):
    """
    Extracts all rich business details from Google Maps place HTML:
    - Business Name
    - Phone Number
    - Full Address
    - Rating & Total Reviews
    - Primary Category / Niche
    - Official Website
    - Direct Google Maps Link
    """
    data = {
        "Business Name": "",
        "Phone Number": "",
        "Address": "",
        "Rating": "",
        "Reviews": "",
        "Category": "",
        "Website": "N/A",
        "Google Maps Link": link
    }
    
    # 1. Business Name
    h1 = soup.find("h1")
    if h1:
        data["Business Name"] = h1.get_text(strip=True)
    if not data["Business Name"]:
        name_div = soup.find("div", class_=re.compile(r"fontHeadlineLarge|header-title", re.I))
        if name_div:
            data["Business Name"] = name_div.get_text(strip=True)

    # 2. Rating & Reviews Count
    rating_el = soup.find("span", class_="MW4etd")
    if rating_el:
        data["Rating"] = rating_el.get_text(strip=True)
    if not data["Rating"]:
        aria_rating = soup.find(attrs={"aria-label": re.compile(r"(\d+(\.\d+)?)\s*stars?", re.I)})
        if aria_rating:
            m = re.search(r"(\d+(\.\d+)?)", aria_rating.get("aria-label", ""))
            if m:
                data["Rating"] = m.group(1)

    reviews_el = soup.find("span", class_="UY7F9")
    if reviews_el:
        rev_txt = reviews_el.get_text(strip=True).replace("(", "").replace(")", "").replace(",", "").strip()
        data["Reviews"] = rev_txt
    if not data["Reviews"]:
        rev_aria = soup.find(attrs={"aria-label": re.compile(r"(\d[\d,]*)\s*reviews?", re.I)})
        if rev_aria:
            m = re.search(r"(\d[\d,]*)", rev_aria.get("aria-label", ""))
            if m:
                data["Reviews"] = m.group(1).replace(",", "")

    # 3. Category / Business Type
    cat_btn = soup.find("button", class_="DkEaL")
    if cat_btn:
        data["Category"] = cat_btn.get_text(strip=True)
    if not data["Category"]:
        cat_btn = soup.find(attrs={"jsaction": re.compile(r"category", re.I)})
        if cat_btn:
            data["Category"] = cat_btn.get_text(strip=True)

    # 4. Address
    addr_btn = soup.find("button", {"data-item-id": "address"})
    if addr_btn:
        data["Address"] = addr_btn.get("aria-label", "").replace("Address:", "").strip()
        if not data["Address"]:
            data["Address"] = addr_btn.get_text(strip=True)
    if not data["Address"]:
        addr_btn = soup.find("button", {"data-tooltip": "Copy address"})
        if addr_btn:
            data["Address"] = addr_btn.get("aria-label", "").replace("Address:", "").strip()
            if not data["Address"]:
                data["Address"] = addr_btn.get_text(strip=True)

    # 5. Website
    data["Website"] = extract_website_from_gmaps(soup) or "N/A"

    # 6. Phone Number
    phone = ""
    phone_btn = soup.find("button", {"data-tooltip": "Copy phone number"})
    if phone_btn:
        phone = phone_btn.get("aria-label", "").replace("Phone:", "").strip()
        if not phone:
            phone = phone_btn.get_text(strip=True)

    if not phone:
        phone_item = soup.find(lambda e: e.name in ["button", "div", "a"] and e.get("data-item-id", "").startswith("phone:"))
        if phone_item:
            p_raw = phone_item.get("data-item-id", "").replace("phone:tel:", "").replace("phone:", "").strip()
            if p_raw:
                phone = p_raw
            elif phone_item.get("aria-label"):
                phone = phone_item.get("aria-label").replace("Phone:", "").strip()

    if not phone:
        tel_a = soup.find("a", href=re.compile(r"^tel:", re.I))
        if tel_a:
            phone = tel_a["href"].replace("tel:", "").strip()

    if not phone:
        for el in soup.find_all(["button", "a", "div"], attrs={"aria-label": re.compile(r"Phone:|Call", re.I)}):
            aria = el.get("aria-label", "")
            m = re.search(r'(?:\+?91[\d \-\(\)]{10,13}|0?\d{2,5}[\d \-\(\)]{6,10})', aria)
            if m:
                phone = m.group(0).strip()
                break

    if not phone:
        for btn in soup.find_all(["button", "span", "div"]):
            text = btn.get_text(strip=True)
            if re.match(r'^(?:\+?91[\s\-]?)?[6789]\d{9}$', text) or re.match(r'^0\d{2,4}[\s\-]?\d{6,8}$', text):
                phone = text
                break

    data["Phone Number"] = phone
    return data

def human_like_scroll_feed(driver, feed_element, target_candidates=50, max_seconds=45):
    """
    Scrolls Google Maps results feed naturally like a human operator:
    - Incremental variable pixel scrolls (220-420px) with micro-pauses.
    - Settle pauses so lazy-loaded cards render completely.
    - Up-down micro-jiggles when lazy loading pauses to trigger scroll boundary listeners.
    - Detects end of feed.
    """
    start_time = time.time()
    seen_links = set()
    consecutive_no_new = 0

    while time.time() - start_time < max_seconds:
        # Check current links
        soup = BeautifulSoup(driver.page_source, "html.parser")
        cards = soup.find_all("a", href=re.compile(r"/maps/place/"))
        current_links = set(c.get("href") for c in cards if c.get("href"))
        
        new_found = len(current_links - seen_links)
        seen_links.update(current_links)

        if len(seen_links) >= target_candidates:
            break

        if new_found == 0:
            consecutive_no_new += 1
            if consecutive_no_new >= 3:
                # Human micro-jiggle: scroll up slightly and back down
                driver.execute_script("arguments[0].scrollTop -= 200;", feed_element)
                time.sleep(random.uniform(0.5, 0.8))
                driver.execute_script("arguments[0].scrollTop += 350;", feed_element)
                time.sleep(random.uniform(1.2, 1.8))
                
                # Check for "You've reached the end of the list"
                src_lower = driver.page_source.lower()
                if "reached the end of the list" in src_lower or "end of results" in src_lower:
                    safe_print("   -> Reached the natural end of listings in this zone.")
                    break
                if consecutive_no_new >= 5:
                    break
        else:
            consecutive_no_new = 0

        # Incremental smooth scroll (3 to 5 micro steps)
        steps = random.randint(3, 5)
        for _ in range(steps):
            step_px = random.randint(220, 420)
            driver.execute_script("arguments[0].scrollTop += arguments[1];", feed_element, step_px)
            time.sleep(random.uniform(0.18, 0.35))

        # Settle pause for network chunk download and rendering
        time.sleep(random.uniform(1.4, 2.2))

    return list(seen_links)

def scrape_google_maps(keyword, city, target_count=400, progress_callback=None, require_website=False):
    queries_to_try = generate_google_maps_queries(keyword, city)
    safe_print(f"\n[Multi-Hub Human GMB Engine] Target: {target_count} leads. Generated {len(queries_to_try)} targeted zones and queries for {city}.")
    if require_website:
        safe_print("[Mode] Requiring active official website and verifying website phone numbers!")
    safe_print("Initializing browser... please wait.")
    
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US")
    
    major_version = get_chrome_major_version()
    if major_version:
        safe_print(f"Detected Chrome version: {major_version}")
        driver = uc.Chrome(options=options, version_main=major_version)
    else:
        driver = uc.Chrome(options=options)

    results = []
    seen_names = set()
    seen_phones = set()
    feed_xpath = "//div[@role='feed']"
    
    try:
        for q_idx, current_query in enumerate(queries_to_try, 1):
            if len(results) >= target_count:
                safe_print(f"Reached desired target limit of {target_count} leads!")
                break

            query_encoded = current_query.replace(" ", "+")
            url = f"https://www.google.com/maps/search/{query_encoded}"
            safe_print(f"\n[{q_idx}/{len(queries_to_try)}] Searching Google Maps: \"{current_query}\" (Verified Leads: {len(results)}/{target_count})")
            
            try:
                driver.get(url)
                time.sleep(random.uniform(3.5, 4.5))
            except Exception as e:
                safe_print(f"Error loading {current_query}: {e}")
                continue

            # Check if feed element exists
            try:
                feed_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, feed_xpath))
                )
            except Exception:
                safe_print("No listing feed found for this query, checking next zone...")
                continue

            # Human-like scrolling to gather cards
            needed_in_this_zone = min(60, target_count - len(results) + 15)
            safe_print("Scrolling feed naturally like a human operator...")
            found_urls = human_like_scroll_feed(driver, feed_element, target_candidates=needed_in_this_zone, max_seconds=40)
            
            # Map URLs to card names
            listing_urls = {}
            soup = BeautifulSoup(driver.page_source, "html.parser")
            for a in soup.find_all("a", href=re.compile(r"/maps/place/")):
                link = a.get("href")
                name = a.get("aria-label")
                if link and name and link not in listing_urls:
                    norm_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
                    if norm_name not in seen_names:
                        listing_urls[link] = name

            safe_print(f"Found {len(listing_urls)} new listings in this zone. Extracting comprehensive details...")

            # Extract full rich details for each listing
            for link, name in listing_urls.items():
                if len(results) >= target_count:
                    safe_print(f"Reached target limit of {target_count} verified leads!")
                    break

                norm_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
                if norm_name in seen_names:
                    continue

                try:
                    driver.get(link)
                    # Explicit wait for details pane
                    try:
                        WebDriverWait(driver, 6).until(
                            EC.presence_of_element_located((By.XPATH, "//h1 | //div[@role='main'] | //button[contains(@data-tooltip, 'phone')]"))
                        )
                    except Exception:
                        pass

                    # Human-like settle time for dynamic phone, address, rating, website elements
                    time.sleep(random.uniform(2.2, 3.2))
                    
                    html = driver.page_source
                    soup = BeautifulSoup(html, "html.parser")
                    
                    details = extract_gmaps_place_details(soup, link=link)
                    b_name = details["Business Name"] or name
                    phone = details["Phone Number"]
                    website = details["Website"]
                    address = details["Address"]
                    rating = details["Rating"]
                    reviews = details["Reviews"]
                    category = details["Category"]

                    if require_website and (not website or website == "N/A"):
                        seen_names.add(norm_name)
                        safe_print(f"   -> [SKIPPED] {b_name} has no official website.")
                        continue

                    # If phone missing on Google Maps, check official website
                    if not phone and website and website != "N/A":
                        safe_print(f"   -> Checking official website ({website}) for contact details...")
                        site_details = extract_details_from_website(website)
                        phone = site_details.get("phone", "")
                        if phone:
                            details["Phone Number"] = phone
                            safe_print(f"   -> [FOUND ON WEBSITE] Phone: {phone}")

                    seen_names.add(norm_name)
                    norm_phone = re.sub(r'\D', '', phone) if phone else ""

                    if phone and (not norm_phone or norm_phone not in seen_phones):
                        if norm_phone:
                            seen_phones.add(norm_phone)
                        rating_str = f"⭐ {rating} ({reviews} revs)" if rating else "Unrated"
                        safe_print(f"[{len(results)+1}] [SAVED] {b_name} | 📞 {phone} | {rating_str} | 📍 {address or 'N/A'}")
                        results.append({
                            "Business Name": b_name,
                            "Phone Number": phone,
                            "Address": address if address else "N/A",
                            "Rating": rating if rating else "N/A",
                            "Reviews": reviews if reviews else "0",
                            "Category": category if category else "N/A",
                            "Website": website if website else "N/A",
                            "Google Maps Link": link
                        })
                        if progress_callback:
                            progress_callback(len(results), target_count)
                    else:
                        if phone:
                            safe_print(f"   -> [DUPLICATE PHONE] {b_name} ({phone})")
                        else:
                            safe_print(f"   -> [SKIPPED] No phone number for {b_name}.")
                        
                except Exception as e:
                    safe_print(f"Failed to extract details for {name}: {e}")
                    continue

        safe_print(f"\n[Scraping Complete] Successfully extracted {len(results)} verified leads across multi-zone Google Maps search!")
                    
    except Exception as e:
        safe_print(f"\nAn error occurred during scraping: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        
    return results[:target_count]

def scrape_bing_maps(keyword, city, target_count=400, progress_callback=None, require_website=False):
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US")
    
    major_version = get_chrome_major_version()
    if major_version:
        safe_print(f"Detected Chrome version: {major_version}")
        driver = uc.Chrome(options=options, version_main=major_version)
    else:
        driver = uc.Chrome(options=options)

    results = []
    seen_names = set()
    
    # Radius / query variations to expand if local area has limited results:
    queries_to_try = [
        f"{keyword} in {city}",
        f"{keyword} near {city}",
        f"{keyword} around {city}",
        f"{keyword} in {city} area"
    ]
    
    try:
        def extract_cards_from_page():
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.find_all("div", class_="b_maglistcard")
            if not cards:
                cards = soup.find_all(attrs={"data-entity": True})
            if not cards:
                cards = soup.find_all("div", class_=re.compile(r"listingsCard|entity-list-item", re.I))

            extracted = 0
            for card in cards:
                try:
                    name = ""
                    phone = ""
                    website = ""
                    
                    # Method 1: Check embedded data-entity JSON
                    ent = {}
                    data_attr = card.get("data-entity")
                    if data_attr:
                        try:
                            data_obj = json.loads(data_attr)
                            ent = data_obj.get("entity", {})
                            name = ent.get("title", "").strip()
                            phone = ent.get("phone", "").strip()
                        except Exception:
                            pass
                    
                    # Method 2: Fallback title from DOM
                    if not name:
                        title_elem = card.find(class_=re.compile(r"title|name|header|cnm|bm_ib_title", re.I))
                        if title_elem:
                            name = title_elem.get_text(strip=True)

                    name = name.strip()
                    if not name or name in seen_names:
                        continue

                    # Extract Website from Bing card / entity
                    website = extract_website_from_bing_card(card, ent)

                    # If website is required, skip if no website found
                    if require_website and not website:
                        seen_names.add(name)
                        safe_print(f"   -> [SKIPPED] {name} has no website.")
                        continue
                    
                    # Method 3: tel: link in card
                    if not phone:
                        tel_link = card.find("a", href=re.compile(r"^tel:", re.I))
                        if tel_link:
                            phone = re.sub(r"^tel:", "", tel_link.get("href", ""), flags=re.I).strip()

                    # Method 4: Fallback phone from DOM span
                    if not phone:
                        phone_elem = card.find("span", class_="nowrap")
                        if phone_elem:
                            phone = phone_elem.get_text(strip=True)
                            
                    # Method 5: Fallback phone from text regex
                    if not phone:
                        m = re.search(r'(\+?\d[\d \-\(\)]{8,14}\d)', card.get_text())
                        if m:
                            phone = m.group(1).strip()

                    # If phone not found on card, but website exists, scrape website for phone!
                    if not phone and website:
                        safe_print(f"   -> Visiting website ({website}) to extract contact details...")
                        site_details = extract_details_from_website(website)
                        phone = site_details.get("phone", "")
                        if phone:
                            safe_print(f"   -> [FOUND ON WEBSITE] Extracted phone: {phone}")
                            
                    # Only keep leads with a valid phone number
                    seen_names.add(name)
                    if phone:
                        safe_print(f"[{len(results)+1}] [SAVED] Found: {name} | Phone: {phone} | Website: {website or 'N/A'}")
                        results.append({
                            "Business Name": name,
                            "Phone Number": phone,
                            "Website": website if website else "N/A"
                        })
                        extracted += 1
                        if progress_callback:
                            progress_callback(len(results), target_count)
                        if len(results) >= target_count:
                            break
                    else:
                        safe_print(f"   -> [SKIPPED] {name} (No phone number)")
                except Exception:
                    continue
            return extracted

        for q_idx, current_query in enumerate(queries_to_try, 1):
            if len(results) >= target_count:
                break
                
            url = f"https://www.bing.com/maps?q={current_query.replace(' ', '+')}"
            safe_print(f"\n[Bing Maps] ({q_idx}/{len(queries_to_try)}) Searching: {current_query}")
            try:
                driver.get(url)
                time.sleep(6)
            except Exception:
                continue

            extract_cards_from_page()
            safe_print(f"Leads extracted so far: {len(results)}/{target_count}")

            if len(results) >= target_count:
                break

            # Scroll .b_lstcards container and interact to load more results
            retries = 0
            scroll_attempts = 0
            max_scroll_attempts = 15

            while len(results) < target_count and scroll_attempts < max_scroll_attempts and retries < 4:
                scroll_attempts += 1
                
                # Scroll container and scroll last card into view
                driver.execute_script("""
                    var lst = document.querySelector('.b_lstcards') ||
                              document.getElementById('contentPane') || 
                              document.getElementById('localSearchContent') || 
                              document.querySelector('[class*="listingsCard"]');
                    if (lst) {
                        lst.scrollTop = lst.scrollHeight;
                    }
                    var cards = document.querySelectorAll('.b_maglistcard, [data-entity]');
                    if (cards.length > 0) {
                        cards[cards.length - 1].scrollIntoView({behavior: 'instant', block: 'end'});
                    }
                    window.scrollTo(0, document.body.scrollHeight);
                """)
                time.sleep(2.5)
                
                new_count = extract_cards_from_page()
                if new_count > 0:
                    retries = 0
                else:
                    retries += 1
                    
                    # Check for Next Page / Pagination buttons in Bing
                    next_found = False
                    try:
                        next_selectors = [
                            "//a[contains(@class, 'sb_pagN') or contains(@class, 'c_pagNext')]",
                            "//a[contains(@title, 'Next') or contains(@aria-label, 'Next page') or contains(@aria-label, 'Next')]",
                            "//button[contains(@title, 'Next') or contains(@aria-label, 'Next')]",
                            "//a[contains(@class, 'b_widePag') and contains(text(), 'Next')]"
                        ]
                        for sel in next_selectors:
                            next_btns = driver.find_elements(By.XPATH, sel)
                            for nb in next_btns:
                                if nb.is_displayed() and nb.is_enabled():
                                    driver.execute_script("arguments[0].click();", nb)
                                    time.sleep(3)
                                    next_found = True
                                    extract_cards_from_page()
                                    break
                            if next_found:
                                break
                    except Exception:
                        pass

                    # If no next button, check "Search this area" button
                    if not next_found:
                        try:
                            search_area_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Search this area') or contains(@aria-label, 'Search this area')]")
                            if search_area_btns and search_area_btns[0].is_displayed():
                                search_area_btns[0].click()
                                time.sleep(3.5)
                                extract_cards_from_page()
                        except Exception:
                            pass

                    # Try zooming out slightly on map to expand search bounds
                    try:
                        zoom_btns = driver.find_elements(By.XPATH, "//button[contains(@title, 'Zoom out') or contains(@aria-label, 'Zoom out') or contains(@class, 'zoomOut') or @id='zoomOut']")
                        if zoom_btns:
                            zoom_btns[0].click()
                            time.sleep(3.5)
                            # Re-check for search this area
                            area_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Search this area') or contains(@aria-label, 'Search this area')]")
                            if area_btns and area_btns[0].is_displayed():
                                area_btns[0].click()
                                time.sleep(3.5)
                            extract_cards_from_page()
                    except Exception:
                        pass
                        
        safe_print(f"\nFinished Bing Maps extraction! Total records: {len(results)}")
        
    except Exception as e:
        safe_print(f"\nAn error occurred during Bing Maps scraping: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
                
    return results[:target_count]

def main():
    keyword, city, source, require_website = get_user_input()
    if not keyword or not city:
        safe_print("Keyword and City are required!")
        return

    if source == "bing":
        data = scrape_bing_maps(keyword, city, target_count=400, require_website=require_website)
    else:
        data = scrape_google_maps(keyword, city, target_count=400, require_website=require_website)
    
    if data:
        df = pd.DataFrame(data)
        clean_keyword = keyword.replace(" ", "_").lower()
        clean_city = city.replace(" ", "_").lower()
        prefix = "leads_coaching" if require_website else "leads"
        output_file = f"{prefix}_{source}_{clean_keyword}_{clean_city}.csv"
        
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        safe_print(f"\nCSV Exported Successfully: {output_file}")
        safe_print(f"Total Records Extracted: {len(data)}")
    else:
        safe_print("\nNo data was extracted. Please try a different search.")

if __name__ == "__main__":
    main()