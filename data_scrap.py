import os
import sys
import time
import re
import json
import random
import unicodedata
import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Safe encoding configuration for Windows terminals
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Known commercial locality hubs for cities to expand multi-zone harvesting
CITY_LOCALITY_HUBS = {
    # Bihar & Jharkhand
    "gaya": ["Civil Lines", "GB Road", "Medical College Road", "AP Colony", "Gewal Bigha", "Station Road", "Rampur", "Bodh Gaya", "Bypass Road", "Dandibagh"],
    "patna": ["Boring Road", "Kankarbagh", "Bailey Road", "Danapur", "Saguna More", "Rajendra Nagar", "Exhibition Road", "Anisabad", "Ashiana Nagar", "Patliputra", "Fraser Road"],
    "hajipur": ["Sonpur", "Paswan Chowk", "Bagmali", "Konhara Ghat", "Yadav Chowk", "Lalganj Road", "Industrial Area"],
    "muzaffarpur": ["Bhagwanpur", "Mithanpura", "Sutapatti", "Gobarsahi", "Bypass Road", "Brahmpura", "Ramdayalu Nagar", "Zero Mile"],
    "bhagalpur": ["Adampur", "Zero Mile", "Tilkamanjhi", "Bypass Road", "Mirjanhat"],
    "darbhanga": ["Laheriasarai", "Airport Road", "Tower Chowk", "Benta"],
    "ara": ["Gopali Chowk", "Babu Bazar", "Shivganj", "Station Road", "Katira", "Nawada", "Pakari", "Zero Mile"],
    "begusarai": ["Traffic Chowk", "Barauni", "Har Har Mahadev Chowk", "NH-31 Corridor"],
    "purnia": ["Line Bazar", "Bhatta Bazar", "Gulabbagh", "Rambagh"],
    "bihar sharif": ["Ranchi Road", "Hospital More", "Ramchandrapur"],
    "ranchi": ["Lalpur", "Main Road", "Harmu", "Doranda", "Bariatu", "Ratu Road", "Hinoo", "Morabadi", "Namkum"],
    "jamshedpur": ["Bistupur", "Sakchi", "Dimna Road", "Mango", "Gamharia", "Telco", "Kadma", "Sonari"],
    "dhanbad": ["Bank More", "Govindpur", "Saraidhela", "Barwadda", "Hirapur", "Jharia"],
    "bokaro": ["Sector 4", "Chas Highway Corridor", "Sector 1", "Sector 6"],
    "deoghar": ["AIIMS Road", "Tower Chowk", "Castairs Town", "Jasidih"],
    # Major Metros & Regional Capitals
    "delhi": ["Connaught Place", "South Extension", "Lajpat Nagar", "Dwarka", "Rohini", "Karol Bagh", "Janakpuri", "Laxmi Nagar", "Saket", "Pitampura"],
    "noida": ["Sector 18", "Sector 62", "Sector 63", "Greater Noida", "Sector 15"],
    "gurgaon": ["Cyber City", "MG Road", "Golf Course Road", "Sohna Road", "Sector 29", "Sector 14"],
    "mumbai": ["Andheri", "Bandra", "Borivali", "Thane", "Navi Mumbai", "Dadar", "Powai", "Goregaon", "Malad"],
    "pune": ["Kothrud", "Hinjawadi", "Viman Nagar", "Baner", "Wakad", "Shivajinagar", "Hadapsar"],
    "kolkata": ["Salt Lake", "Park Street", "New Town", "Gariahat", "Behala", "Howrah", "Dum Dum"],
    "bangalore": ["Indiranagar", "Koramangala", "Whitefield", "HSR Layout", "Jayanagar", "Electronic City", "Marathahalli"],
    "hyderabad": ["Hitech City", "Madhapur", "Gachibowli", "Banjara Hills", "Jubilee Hills", "Kukatpally", "Secunderabad"],
    "chennai": ["T Nagar", "Anna Nagar", "Velachery", "Adyar", "OMR", "Guindy", "Tambaram"],
    "ahmedabad": ["SG Highway", "Navrangpura", "Satellite", "Maninagar", "Prahlad Nagar", "Vastrapur"],
    "jaipur": ["Malviya Nagar", "Vaishali Nagar", "Mansarovar", "C Scheme", "Tonk Road", "Raja Park"],
    "lucknow": ["Hazratganj", "Gomti Nagar", "Aliganj", "Indira Nagar", "Alambagh", "Charbagh"],
    "kanpur": ["Mall Road", "Swaroop Nagar", "Civil Lines", "Kakadeo", "Govind Nagar"],
    "varanasi": ["Sigra", "Cantt", "Lanka", "Bhelupur", "Pandeypur", "Mahmoorganj"],
    "indore": ["Vijay Nagar", "Palasia", "Bhawarkua", "Rajwada", "AB Road"],
    "bhopal": ["MP Nagar", "Arera Colony", "New Market", "Kolar Road", "Hoshangabad Road"],
    "chandigarh": ["Sector 17", "Sector 35", "Sector 22", "Industrial Area", "Sector 8"]
}

def safe_print(*args, **kwargs):
    """Safely print text avoiding UnicodeEncodeError crashes on Windows."""
    kwargs.setdefault('flush', True)
    try:
        print(*args, **kwargs)
    except Exception:
        try:
            cleaned = [str(a).encode('ascii', errors='replace').decode('ascii') for a in args]
            print(*cleaned, **kwargs)
        except Exception:
            pass

def get_chrome_major_version():
    """Detect the installed Google Chrome major version to prevent driver mismatch."""
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

def clean_phone_number(raw_str):
    """
    Format and clean phone numbers, handling Indian mobile/landline numbers
    as well as general international formats, normalizing non-breaking spaces.
    """
    if not raw_str:
        return ""
    
    # Normalize unicode spaces (\u202f narrow space, \xa0 non-breaking space)
    s = unicodedata.normalize('NFKD', str(raw_str)).strip()
    s = re.sub(r'^(?:phone|call|tel|mobile):\s*', '', s, flags=re.I).strip()
    
    digits = re.sub(r'[^\d]', '', s)
    
    # 1. Indian 12 digits with 91 country code (e.g. 919835012345)
    if len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
        return f"+91 {digits[2:7]} {digits[7:]}"
    # 2. Indian 11 digits with 0 prefix (e.g. 09835012345)
    if len(digits) == 11 and digits.startswith("0") and digits[1] in "6789":
        return f"0{digits[1:6]} {digits[6:]}"
    # 3. Indian 11 digits landline with STD (e.g. 06122234567)
    if len(digits) == 11 and digits.startswith("0"):
        return f"{digits[:5]} {digits[5:]}"
    # 4. Indian 10 digits mobile (e.g. 9835012345)
    if len(digits) == 10 and digits[0] in "6789":
        return f"{digits[:5]} {digits[5:]}"
    # 5. Landline 10 digits (e.g. 0112345678)
    if len(digits) == 10 and digits.startswith("0"):
        return f"{digits[:4]} {digits[4:]}"
    
    # General phone regex extraction if embedded in text
    m = re.search(r'(?:\+?91[\s-]?)?(?:0?[6-9]\d{4}[\s\-]?\d{5}|0\d{1,4}[\s\-]?(?:\d{3,4}[\s\-]?\d{4}|\d{6,8})|\b[6-9]\d{9}\b|\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', s)
    if m:
        cleaned_sub = m.group(0).strip()
        sub_digits = re.sub(r'[^\d]', '', cleaned_sub)
        if len(sub_digits) >= 10:
            return cleaned_sub

    return s if len(digits) >= 7 else ""

def extract_phone_from_text(text):
    """Scan string for phone number pattern with unicode normalization."""
    if not text:
        return ""
    norm = unicodedata.normalize('NFKD', str(text))
    norm = re.sub(r'[\xa0\u202f\u200b\u200e]', ' ', norm)
    
    m = re.search(r'(?:\+?91[\s-]?)?(?:0?[6-9]\d{4}[\s\-]?\d{5}|0\d{1,4}[\s\-]?(?:\d{3,4}[\s\-]?\d{4}|\d{6,8})|\b[6-9]\d{9}\b|\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', norm)
    if m:
        return clean_phone_number(m.group(0))
    return ""

def extract_phone_from_details(soup):
    """Extract phone number from Google Maps place details HTML or panel."""
    # 1. Element with data-item-id containing phone (most accurate)
    phone_item = soup.find(lambda e: e.name in ["button", "div", "a"] and str(e.get("data-item-id", "")).startswith("phone:"))
    if phone_item:
        item_id = str(phone_item.get("data-item-id", "")).replace("phone:tel:", "").replace("phone:", "").strip()
        aria = phone_item.get("aria-label", "").replace("Phone:", "").strip()
        phone = clean_phone_number(item_id or aria)
        if phone:
            return phone

    # 2. Tooltip button containing phone
    phone_btn = soup.find("button", {"data-tooltip": re.compile(r"phone", re.I)})
    if phone_btn:
        aria = phone_btn.get("aria-label", "").replace("Phone:", "").strip()
        text = phone_btn.get_text(strip=True)
        phone = clean_phone_number(aria or text)
        if phone:
            return phone

    # 3. Anchor with tel: protocol
    tel_a = soup.find("a", href=re.compile(r"^tel:", re.I))
    if tel_a:
        raw_tel = re.sub(r"^tel:", "", tel_a.get("href", ""), flags=re.I).strip()
        phone = clean_phone_number(raw_tel)
        if phone:
            return phone

    # 4. Search all elements with aria-label containing Phone
    for el in soup.find_all(attrs={"aria-label": re.compile(r"Phone:", re.I)}):
        phone = clean_phone_number(el.get("aria-label"))
        if phone:
            return phone

    return ""

def generate_search_queries(keyword, city):
    """
    Generates structured queries prioritizing geographic zone dispersion.
    By alternating locality hubs immediately after the primary search,
    the scraper bypasses Google's single-query result cap (~120 listings)
    and fetches distinct, non-overlapping leads across the entire city.
    """
    clean_kw = keyword.strip()
    clean_city = city.strip()
    kw_lower = clean_kw.lower()
    city_lower = clean_city.lower()

    core_kw = re.sub(r'^(?:best|top|famous|cheap|good|verified|popular)\s+', '', clean_kw, flags=re.I).strip()
    if not core_kw:
        core_kw = clean_kw

    queries = []

    # 1. Primary User & Core Queries
    queries.append(f"{clean_kw} in {clean_city}")
    if core_kw.lower() != clean_kw.lower():
        queries.append(f"{core_kw} in {clean_city}")

    # 2. Known Locality / Hub variations for this city (High Yield)
    hubs = CITY_LOCALITY_HUBS.get(city_lower, [])
    if not hubs:
        for k, v in CITY_LOCALITY_HUBS.items():
            if k in city_lower:
                hubs = v
                break

    for hub in hubs:
        hq = f"{core_kw} in {hub}, {clean_city}"
        if hq not in queries:
            queries.append(hq)

    # 3. Universal Directional & Commercial Sectors for ANY city worldwide
    universal_sectors = [
        f"{core_kw} in North {clean_city}",
        f"{core_kw} in South {clean_city}",
        f"{core_kw} in East {clean_city}",
        f"{core_kw} in West {clean_city}",
        f"{core_kw} in Central {clean_city}",
        f"{core_kw} in {clean_city} Market",
        f"{core_kw} in {clean_city} Station Road",
        f"{core_kw} in {clean_city} Bypass Road",
        f"{core_kw} in {clean_city} Civil Lines",
        f"{core_kw} in {clean_city} Industrial Area",
        f"{core_kw} in {clean_city} Ring Road",
        f"{core_kw} in {clean_city} City Center",
        f"{core_kw} in {clean_city} Main Road",
        f"{core_kw} near {clean_city}"
    ]
    for uq in universal_sectors:
        if uq not in queries:
            queries.append(uq)

    # 4. Domain-Specific Semantic Expansions
    syns = []
    if any(w in kw_lower for w in ["eye", "surgeon", "retina", "vision", "ophthalm"]):
        syns = [f"eye hospital in {clean_city}", f"eye care clinic in {clean_city}", f"ophthalmologist in {clean_city}"]
    elif any(w in kw_lower for w in ["dentist", "dental", "teeth", "tooth"]):
        syns = [f"dental clinic in {clean_city}", f"dentist in {clean_city}", f"dental care center in {clean_city}"]
    elif any(w in kw_lower for w in ["ortho", "bone", "joint", "spine"]):
        syns = [f"orthopedic doctor in {clean_city}", f"bone specialist in {clean_city}"]
    elif any(w in kw_lower for w in ["cardio", "heart"]):
        syns = [f"cardiologist in {clean_city}", f"heart hospital in {clean_city}"]
    elif any(w in kw_lower for w in ["skin", "derma", "hair", "laser"]):
        syns = [f"dermatologist in {clean_city}", f"skin clinic in {clean_city}", f"hair clinic in {clean_city}"]
    elif any(w in kw_lower for w in ["doctor", "clinic", "hospital", "pathology", "diagnostic"]):
        syns = [f"diagnostic center in {clean_city}", f"pathology lab in {clean_city}", f"multispeciality hospital in {clean_city}"]
    elif any(w in kw_lower for w in ["salon", "parlour", "spa", "makeup", "bridal", "beauty"]):
        syns = [f"beauty parlour in {clean_city}", f"hair salon in {clean_city}", f"bridal makeup in {clean_city}", f"unisex salon in {clean_city}"]
    elif any(w in kw_lower for w in ["coach", "tuition", "class", "academy", "institute"]):
        syns = [f"coaching institute in {clean_city}", f"tuition classes in {clean_city}", f"academy in {clean_city}"]
    elif any(w in kw_lower for w in ["restaur", "food", "cafe", "hotel", "dine"]):
        syns = [f"family restaurant in {clean_city}", f"top cafes in {clean_city}", f"hotel in {clean_city}"]
    elif any(w in kw_lower for w in ["gym", "fit", "workout", "yoga"]):
        syns = [f"fitness center in {clean_city}", f"gym in {clean_city}", f"yoga classes in {clean_city}"]
    elif any(w in kw_lower for w in ["real estate", "property", "plot", "builder"]):
        syns = [f"property dealer in {clean_city}", f"real estate agent in {clean_city}"]

    for s in syns:
        if s not in queries:
            queries.append(s)

    # 5. Generic Quality Filters (last priority)
    generic_extras = [
        f"best {core_kw} in {clean_city}",
        f"top {core_kw} in {clean_city}",
        f"famous {core_kw} in {clean_city}"
    ]
    for g in generic_extras:
        if g not in queries:
            queries.append(g)

    return queries

def create_driver(headless=False):
    """
    Initializes a resilient undetected Chrome instance equipped with stealth flags
    and automation masking. Uses isolated instance configurations to avoid file lock collisions.
    """
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    else:
        options.add_argument("--start-maximized")

    # Anti-bot stealth arguments
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--no-first-run")
    options.add_argument("--no-service-autorun")
    options.add_argument("--password-store=basic")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")

    # Suppress permission popups (geolocation, notifications)
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    major_version = get_chrome_major_version()
    driver = None
    try:
        if major_version:
            driver = uc.Chrome(options=options, version_main=major_version)
        else:
            driver = uc.Chrome(options=options)
    except Exception as e:
        safe_print(f"Driver launch notice: {e}. Retrying clean instance...")
        time.sleep(1.5)
        clean_opts = uc.ChromeOptions()
        if headless:
            clean_opts.add_argument("--headless=new")
        else:
            clean_opts.add_argument("--start-maximized")
        clean_opts.add_argument("--lang=en-US,en;q=0.9")
        clean_opts.add_argument("--disable-blink-features=AutomationControlled")
        if major_version:
            driver = uc.Chrome(options=clean_opts, version_main=major_version)
        else:
            driver = uc.Chrome(options=clean_opts)

    # Inject CDP stealth scripts to hide webdriver indicators
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.navigator.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            """
        })
    except Exception:
        pass

    return driver

def check_for_captcha_or_block(driver):
    """Detect if Google is presenting a rate limit or CAPTCHA challenge."""
    try:
        src = driver.page_source.lower()
        triggers = [
            "unusual traffic from your computer network",
            "recaptcha",
            "sorry/index",
            "our systems have detected unusual traffic",
            "please show you're not a robot"
        ]
        return any(t in src for t in triggers)
    except Exception:
        return False

def scrape_google_maps(keyword, city, target_count=100, progress_callback=None, stop_event=None, headless=False, existing_names=None, existing_phones=None):
    """
    Extracts verified Google Maps business listings (Name & Phone).
    Features:
      - In-place 'a.hfpxzc' click inspection: opens details side panel dynamically without full-page reloads
      - Geo-zone expansion across commercial localities
      - Anti-stall infinite scrolling with adaptive jiggling
      - Auto-detection & pause recovery if Google prompts CAPTCHA
    """
    clean_keyword = keyword.strip()
    clean_city = city.strip()
    target_count = max(1, int(target_count))

    queries = generate_search_queries(clean_keyword, clean_city)

    safe_print(f"\n[Google Maps Scraper] Starting search for '{clean_keyword}' in '{clean_city}'")
    safe_print(f"Target Leads: {target_count}")
    safe_print(f"Prepared {len(queries)} geographic zone queries to harvest maximum unique leads.")
    safe_print("Launching browser with anti-detection shielding, please wait...")

    driver = create_driver(headless)
    results = []
    seen_names = set(existing_names) if existing_names else set()
    seen_phones = set(existing_phones) if existing_phones else set()

    def notify(lead=None, query_info=""):
        if progress_callback:
            try:
                progress_callback(len(results), target_count, lead, query_info)
            except TypeError:
                try:
                    progress_callback(len(results), target_count, lead)
                except Exception:
                    pass

    try:
        for q_idx, current_query in enumerate(queries, 1):
            if len(results) >= target_count:
                safe_print(f"\nTarget goal of {target_count} leads successfully reached!")
                break
            if stop_event and stop_event.is_set():
                safe_print("\nStop requested by user. Finalizing results...")
                break

            query_encoded = current_query.replace(" ", "+")
            url = f"https://www.google.com/maps/search/{query_encoded}"
            safe_print(f"\n[{q_idx}/{len(queries)}] Google Maps Zone: \"{current_query}\" (Progress: {len(results)}/{target_count} leads)")

            try:
                driver.get(url)
                time.sleep(random.uniform(3.0, 4.5))
            except Exception as e:
                safe_print(f"Error loading {current_query}: {e}")
                err_str = str(e).lower()
                if "invalid session id" in err_str or "disconnected" in err_str:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = create_driver(headless)
                    try:
                        driver.get(url)
                        time.sleep(3.5)
                    except Exception:
                        continue
                else:
                    continue

            # Check if Google verification is required
            if check_for_captcha_or_block(driver):
                safe_print("\n[ALERT] Google verification / unusual traffic detected!")
                safe_print("Please complete the quick verification in the opened Chrome window. Waiting up to 60s...")
                for _ in range(30):
                    if stop_event and stop_event.is_set():
                        break
                    time.sleep(2)
                    if not check_for_captcha_or_block(driver):
                        safe_print("Verification cleared! Resuming scraper...")
                        time.sleep(2)
                        break

            # Dismiss consent banner if shown
            if q_idx <= 2:
                try:
                    consent_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Accept all') or contains(., 'Agree') or contains(., 'I agree')]")
                    if consent_btns and consent_btns[0].is_displayed():
                        consent_btns[0].click()
                        time.sleep(1.5)
                except Exception:
                    pass

            # Detect dead-end queries early
            src_check = driver.page_source.lower()
            if "no results found for" in src_check or "make sure all words are spelled correctly" in src_check:
                safe_print("   -> No listings in this zone. Advancing to next zone...")
                continue

            # Find the search results feed container
            feed_element = None
            feed_selectors = [
                "//div[@role='feed']",
                "//div[contains(@class, 'm6QErb') and contains(@aria-label, 'Results')]",
                "//div[contains(@class, 'm6QErb') and contains(@class, 'DxyBCb')]"
            ]
            for sel in feed_selectors:
                try:
                    elems = driver.find_elements(By.XPATH, sel)
                    if elems and elems[0].is_displayed():
                        feed_element = elems[0]
                        break
                except Exception:
                    pass

            # Check if redirected directly to single place match page
            if not feed_element:
                try:
                    soup_single = BeautifulSoup(driver.page_source, "html.parser")
                    h1 = soup_single.find("h1")
                    if h1 and h1.get_text(strip=True).lower() not in ["results", "google maps"]:
                        s_name = h1.get_text(strip=True)
                        norm_s = re.sub(r'[^a-zA-Z0-9]', '', s_name.lower())
                        if norm_s and norm_s not in seen_names:
                            s_phone = extract_phone_from_details(soup_single)
                            norm_p = re.sub(r'\D', '', s_phone) if s_phone else ""
                            if not norm_p or norm_p not in seen_phones:
                                seen_names.add(norm_s)
                                if norm_p:
                                    seen_phones.add(norm_p)
                                lead = {"Business Name": s_name, "Phone Number": s_phone or "Not available"}
                                results.append(lead)
                                safe_print(f"[{len(results)}/{target_count}] Single Place: {s_name} | Phone: {lead['Phone Number']}")
                                notify(lead, current_query)
                except Exception:
                    pass
                continue

            # Stream Extraction: Scroll feed and inspect cards in-place
            retries = 0
            last_card_count = 0
            inspected_indices = set()

            for scroll_round in range(1, 35):
                if len(results) >= target_count:
                    break
                if stop_event and stop_event.is_set():
                    break

                try:
                    card_links = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
                except Exception:
                    break

                current_card_count = len(card_links)
                if current_card_count > last_card_count:
                    last_card_count = current_card_count
                    retries = 0
                else:
                    retries += 1

                # Inspect newly rendered card links
                for idx in range(len(card_links)):
                    if len(results) >= target_count:
                        break
                    if stop_event and stop_event.is_set():
                        break
                    if idx in inspected_indices:
                        continue

                    inspected_indices.add(idx)

                    try:
                        # Re-fetch elements to avoid stale references
                        all_links = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
                        if idx >= len(all_links):
                            break
                        link = all_links[idx]

                        name = link.get_attribute("aria-label") or ""
                        if not name:
                            continue

                        norm_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
                        if norm_name in seen_names:
                            continue

                        # Click card anchor in-place to open details panel
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", link)
                        time.sleep(0.2)
                        driver.execute_script("arguments[0].click();", link)
                        time.sleep(random.uniform(1.2, 1.6))

                        # Extract phone from opened panel
                        soup_panel = BeautifulSoup(driver.page_source, "html.parser")
                        phone = extract_phone_from_details(soup_panel)

                        if not phone:
                            phone = extract_phone_from_text(soup_panel.get_text())

                        seen_names.add(norm_name)
                        norm_phone = re.sub(r'\D', '', phone) if phone else ""
                        if norm_phone:
                            seen_phones.add(norm_phone)

                        lead = {
                            "Business Name": name,
                            "Phone Number": phone if phone else "Not available"
                        }
                        results.append(lead)
                        safe_print(f"[{len(results)}/{target_count}] {name} | Phone: {lead['Phone Number']}")
                        notify(lead, current_query)

                    except Exception:
                        continue

                if len(results) >= target_count or retries >= 6:
                    break

                # Adaptive Scrolling
                try:
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed_element)
                    time.sleep(random.uniform(0.4, 0.7))
                    driver.execute_script("""
                        var cards = arguments[0].querySelectorAll('a.hfpxzc');
                        if (cards.length > 0) {
                            cards[cards.length - 1].scrollIntoView({behavior: 'smooth', block: 'end'});
                        }
                    """, feed_element)

                    if retries >= 2:
                        driver.execute_script("arguments[0].scrollTop -= 200;", feed_element)
                        time.sleep(0.3)
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", feed_element)

                    time.sleep(random.uniform(1.4, 2.0))
                except Exception:
                    break

                src_lower = driver.page_source.lower()
                if "you've reached the end of the list" in src_lower or "end of results" in src_lower:
                    safe_print("   -> Reached end of listings for this zone.")
                    break

        safe_print(f"\n[Google Maps Complete] Total extracted: {len(results)} unique leads.")

    except Exception as e:
        safe_print(f"\nGoogle Maps scraping notice: {e}")
    finally:
        if driver:
            try:
                driver.__del__ = lambda: None
            except Exception:
                pass
            try:
                driver.quit()
            except Exception:
                pass

    return results

def scrape_bing_maps(keyword, city, target_count=100, progress_callback=None, stop_event=None, headless=False, existing_names=None, existing_phones=None):
    """
    Alternative resilient business scraper powered by Bing Maps.
    Features:
      - Zero CAPTCHA / rate-limit restrictions
      - Direct extraction of verified phone numbers embedded in data-entity JSON
      - Rapid pagination across city listings
    """
    clean_keyword = keyword.strip()
    clean_city = city.strip()
    target_count = max(1, int(target_count))

    query = f"{clean_keyword} in {clean_city}".replace(" ", "+")
    url = f"https://www.bing.com/maps?q={query}"

    safe_print(f"\n[Bing Maps Scraper] Searching for '{clean_keyword}' in '{clean_city}'")
    safe_print(f"Target Leads: {target_count}")
    safe_print("Launching browser, please wait...")

    driver = create_driver(headless)
    results = []
    seen_names = set(existing_names) if existing_names else set()
    seen_phones = set(existing_phones) if existing_phones else set()

    try:
        driver.get(url)
        time.sleep(random.uniform(4.5, 6.0))

        def extract_cards_from_page():
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.find_all("div", class_="b_maglistcard")
            extracted = 0
            for card in cards:
                if len(results) >= target_count:
                    break
                if stop_event and stop_event.is_set():
                    break

                name = ""
                phone = ""

                # 1. Embedded data-entity JSON
                data_attr = card.get("data-entity")
                if data_attr:
                    try:
                        data_obj = json.loads(data_attr)
                        ent = data_obj.get("entity", {})
                        name = ent.get("title", "").strip()
                        phone = ent.get("phone", "").strip()
                    except Exception:
                        pass

                # 2. Fallback title
                if not name:
                    title_elem = card.find(class_=re.compile(r"title|name|header|cnm|bm_ib_title", re.I))
                    if title_elem:
                        name = title_elem.get_text(strip=True)

                # 3. Fallback phone
                if not phone:
                    phone_elem = card.find("span", class_="nowrap")
                    if phone_elem:
                        phone = phone_elem.get_text(strip=True)

                if not phone:
                    phone = extract_phone_from_text(card.get_text())

                if not name:
                    continue

                norm_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
                if norm_name in seen_names:
                    continue

                phone_clean = clean_phone_number(phone)
                norm_phone = re.sub(r'\D', '', phone_clean) if phone_clean else ""

                if norm_phone and norm_phone in seen_phones:
                    continue

                seen_names.add(norm_name)
                if norm_phone:
                    seen_phones.add(norm_phone)

                lead = {
                    "Business Name": name,
                    "Phone Number": phone_clean if phone_clean else "Not available"
                }
                results.append(lead)
                extracted += 1
                safe_print(f"[Bing] [{len(results)}/{target_count}] {name} | Phone: {lead['Phone Number']}")
                if progress_callback:
                    try:
                        progress_callback(len(results), target_count, lead, f"Bing: {clean_keyword} in {clean_city}")
                    except TypeError:
                        progress_callback(len(results), target_count, lead)

            return extracted

        # Initial page extraction
        extract_cards_from_page()

        # Infinite Scroll & Pagination on Bing Maps
        retries = 0
        for _ in range(25):
            if len(results) >= target_count:
                break
            if stop_event and stop_event.is_set():
                break

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
            """)
            time.sleep(random.uniform(2.2, 3.2))

            new_leads = extract_cards_from_page()
            if new_leads > 0:
                retries = 0
            else:
                retries += 1
                # Try Next Page pagination button
                try:
                    next_btns = driver.find_elements(By.XPATH, "//a[contains(@class, 'sb_pagN') or contains(@class, 'c_pagNext') or contains(@title, 'Next') or contains(@aria-label, 'Next')]")
                    if next_btns and next_btns[0].is_displayed():
                        driver.execute_script("arguments[0].click();", next_btns[0])
                        time.sleep(3.5)
                        extract_cards_from_page()
                        continue
                except Exception:
                    pass

                # Try 'Search this area' button
                try:
                    area_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Search this area') or contains(@aria-label, 'Search this area')]")
                    if area_btns and area_btns[0].is_displayed():
                        area_btns[0].click()
                        time.sleep(3.5)
                        extract_cards_from_page()
                        continue
                except Exception:
                    pass

                if retries >= 4:
                    break

        safe_print(f"\n[Bing Maps Complete] Total extracted: {len(results)} unique leads.")

    except Exception as e:
        safe_print(f"Bing Maps scraping notice: {e}")
    finally:
        if driver:
            try:
                driver.__del__ = lambda: None
            except Exception:
                pass
            try:
                driver.quit()
            except Exception:
                pass

    return results

def scrape_leads(keyword, city, target_count=100, source="all", progress_callback=None, stop_event=None, headless=False):
    """
    Master Lead Generation Router.
    Modes:
      - 'all': Multi-Engine (Google Maps + Bing Maps). Guaranteed to maximize lead yield by falling over to Bing Maps if Google hits query limits.
      - 'google': Google Maps only.
      - 'bing': Bing Maps only.
    """
    target_count = max(1, int(target_count))
    source = (source or "all").lower()

    if source == "bing":
        return scrape_bing_maps(
            keyword=keyword,
            city=city,
            target_count=target_count,
            progress_callback=progress_callback,
            stop_event=stop_event,
            headless=headless
        )
    elif source == "google":
        return scrape_google_maps(
            keyword=keyword,
            city=city,
            target_count=target_count,
            progress_callback=progress_callback,
            stop_event=stop_event,
            headless=headless
        )
    else:
        # Multi-Engine Mode: Harvest Google Maps first, then Bing Maps for guaranteed maximum yield
        safe_print(f"\n[Multi-Engine Scraper] Target: {target_count} leads for '{keyword}' in '{city}'")
        safe_print("Stage 1: Harvesting Google Maps with in-page side panel inspection...")

        g_leads = scrape_google_maps(
            keyword=keyword,
            city=city,
            target_count=target_count,
            progress_callback=progress_callback,
            stop_event=stop_event,
            headless=headless
        )

        if len(g_leads) >= target_count or (stop_event and stop_event.is_set()):
            return g_leads

        remaining = target_count - len(g_leads)
        safe_print(f"\nStage 2: Google Maps provided {len(g_leads)} leads. Seamlessly switching to Bing Maps for remaining {remaining} leads...")

        existing_names = {re.sub(r'[^a-zA-Z0-9]', '', l["Business Name"].lower()) for l in g_leads}
        existing_phones = {re.sub(r'\D', '', l["Phone Number"]) for l in g_leads if l.get("Phone Number") and l["Phone Number"] != "Not available"}

        def bing_callback(count, total, lead, q_info):
            if progress_callback:
                try:
                    progress_callback(len(g_leads) + count, target_count, lead, q_info)
                except TypeError:
                    progress_callback(len(g_leads) + count, target_count, lead)

        b_leads = scrape_bing_maps(
            keyword=keyword,
            city=city,
            target_count=remaining,
            progress_callback=bing_callback,
            stop_event=stop_event,
            headless=headless,
            existing_names=existing_names,
            existing_phones=existing_phones
        )

        all_leads = g_leads + b_leads
        safe_print(f"\n[Multi-Engine Complete] Extracted {len(all_leads)} unique leads ({len(g_leads)} from Google, {len(b_leads)} from Bing).")
        return all_leads

def main():
    print("\n==============================")
    print("BUSINESS LEAD SCRAPER (NAME & PHONE)")
    print("==============================\n")
    keyword = input("Enter Business Keyword (e.g., Restaurants): ").strip()
    city = input("Enter City (e.g., Patna): ").strip()
    leads_str = input("Enter Number of Leads to Scrape (default 100): ").strip()
    try:
        target_count = int(leads_str) if leads_str else 100
    except ValueError:
        target_count = 100

    print("\nSelect Source:")
    print("1. Multi-Engine: Google + Bing Maps (Recommended for Maximum Leads)")
    print("2. Google Maps Only")
    print("3. Bing Maps Only")
    choice = input("Enter choice (1-3, default 1): ").strip()
    source_map = {"1": "all", "2": "google", "3": "bing"}
    source = source_map.get(choice, "all")

    if not keyword or not city:
        safe_print("Both Keyword and City are required!")
        return

    data = scrape_leads(keyword, city, target_count=target_count, source=source)

    if data:
        df = pd.DataFrame(data)
        clean_kw = re.sub(r'[^a-zA-Z0-9]', '_', keyword.strip()).lower()
        clean_ct = re.sub(r'[^a-zA-Z0-9]', '_', city.strip()).lower()
        output_file = f"leads_{clean_kw}_{clean_ct}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        safe_print(f"\nSuccess! Exported {len(data)} leads to: {output_file}")
    else:
        safe_print("\nNo data was extracted. Please try a different search.")

if __name__ == "__main__":
    main()