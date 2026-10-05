import sys
import time
import re
import random
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
    as well as general international formats.
    """
    if not raw_str:
        return ""
    s = str(raw_str).strip()
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
    m = re.search(r'(?:\+?91[\s-]?)?(?:0?[6-9]\d{4}[\s\-]?\d{5}|0\d{2,4}[\s\-]?\d{6,8}|\b[6-9]\d{9}\b|\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', s)
    if m:
        cleaned_sub = m.group(0).strip()
        sub_digits = re.sub(r'[^\d]', '', cleaned_sub)
        if len(sub_digits) >= 10:
            return cleaned_sub

    return s if len(digits) >= 7 else ""

def extract_phone_from_text(text):
    """Scan string for phone number pattern."""
    if not text:
        return ""
    m = re.search(r'(?:\+?91[\s-]?)?(?:0?[6-9]\d{4}[\s\-]?\d{5}|0\d{2,4}[\s\-]?\d{6,8}|\b[6-9]\d{9}\b|\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4})', text)
    if m:
        return clean_phone_number(m.group(0))
    return ""

def extract_phone_from_details(soup):
    """Extract phone number from Google Maps place details page HTML."""
    # 1. Copy phone number tooltip button
    phone_btn = soup.find("button", {"data-tooltip": re.compile(r"phone", re.I)})
    if phone_btn:
        aria = phone_btn.get("aria-label", "").replace("Phone:", "").strip()
        text = phone_btn.get_text(strip=True)
        phone = clean_phone_number(aria or text)
        if phone:
            return phone

    # 2. Button with data-item-id containing phone
    phone_item = soup.find(lambda e: e.name in ["button", "div", "a"] and str(e.get("data-item-id", "")).startswith("phone:"))
    if phone_item:
        item_id = str(phone_item.get("data-item-id", "")).replace("phone:tel:", "").replace("phone:", "").strip()
        aria = phone_item.get("aria-label", "").replace("Phone:", "").strip()
        phone = clean_phone_number(item_id or aria)
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
    Generates comprehensive, intelligent synonym and locality query variations
    for Google Maps for ANY business category, service, or locality, so that
    EVERY search seamlessly breaks past Google's ~25-listing single-query wall
    and reliably hits 100+ unique verified leads.
    """
    clean_kw = keyword.strip()
    clean_city = city.strip()
    kw_lower = clean_kw.lower()
    city_lower = clean_city.lower()

    # Core phrase normalization (strip leading modifiers like "best", "top", "famous", "cheap", "good")
    core_kw = re.sub(r'^(?:best|top|famous|cheap|good|verified|popular)\s+', '', clean_kw, flags=re.I).strip()
    if not core_kw:
        core_kw = clean_kw

    queries = []
    
    # 1. Primary User & Core Queries
    queries.append(f"{clean_kw} in {clean_city}")
    if core_kw.lower() != clean_kw.lower():
        queries.append(f"{core_kw} in {clean_city}")

    # 2. Universal Foundational Variations (generated for EVERY search)
    foundational = [
        f"best {core_kw} in {clean_city}",
        f"top {core_kw} in {clean_city}",
        f"{core_kw} near {clean_city}",
        f"{core_kw} services in {clean_city}",
        f"{core_kw} center in {clean_city}",
        f"{core_kw} agency in {clean_city}",
        f"{core_kw} shop in {clean_city}",
        f"famous {core_kw} in {clean_city}",
        f"list of {core_kw} in {clean_city}"
    ]
    for f_q in foundational:
        if f_q not in queries:
            queries.append(f_q)

    # 3. Domain-Specific Semantic Expansions
    # Eye / Vision / Retina
    if any(w in kw_lower for w in ["eye", "surgon", "surgeon", "retina", "vision", "netra", "ophthalm"]):
        syns = [
            f"eye hospital in {clean_city}",
            f"eye care clinic in {clean_city}",
            f"eye specialist doctor in {clean_city}",
            f"ophthalmologist in {clean_city}",
            f"netralaya in {clean_city}",
            f"eye clinic in {clean_city}",
            f"cataract surgeon in {clean_city}",
            f"retina specialist in {clean_city}",
            f"best eye doctors in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Dental / Teeth / Orthodontist
    elif any(w in kw_lower for w in ["dentist", "dental", "teeth", "tooth", "orthodont"]):
        syns = [
            f"dental clinic in {clean_city}",
            f"dentist in {clean_city}",
            f"dental hospital in {clean_city}",
            f"dental care center in {clean_city}",
            f"orthodontist in {clean_city}",
            f"teeth care clinic in {clean_city}",
            f"root canal specialist in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Orthopedic / Bone / Joint
    elif any(w in kw_lower for w in ["ortho", "bone", "joint", "knee", "spine"]):
        syns = [
            f"orthopedic doctor in {clean_city}",
            f"orthopedic hospital in {clean_city}",
            f"bone specialist in {clean_city}",
            f"joint replacement clinic in {clean_city}",
            f"fracture clinic in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Heart / Cardiac
    elif any(w in kw_lower for w in ["cardio", "heart"]):
        syns = [
            f"cardiologist in {clean_city}",
            f"heart hospital in {clean_city}",
            f"cardiac center in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Neuro / Brain / Spine
    elif any(w in kw_lower for w in ["neuro", "brain", "spine"]):
        syns = [
            f"neurologist in {clean_city}",
            f"neuro hospital in {clean_city}",
            f"spine surgeon in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Gynecology / Maternity / IVF
    elif any(w in kw_lower for w in ["gyno", "gynec", "maternity", "women", "ivf", "pregnancy"]):
        syns = [
            f"gynecologist in {clean_city}",
            f"maternity hospital in {clean_city}",
            f"women care clinic in {clean_city}",
            f"ivf fertility center in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Pediatrics / Child Specialist
    elif any(w in kw_lower for w in ["pedia", "child", "baby", "infant"]):
        syns = [
            f"pediatrician in {clean_city}",
            f"child specialist doctor in {clean_city}",
            f"children hospital in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Dermatology / Skin / Hair
    elif any(w in kw_lower for w in ["skin", "derma", "hair", "laser"]):
        syns = [
            f"dermatologist in {clean_city}",
            f"skin clinic in {clean_city}",
            f"hair transplant clinic in {clean_city}",
            f"cosmetology center in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # General Medical / Doctor / Clinic / Hospital
    elif any(w in kw_lower for w in ["doctor", "clinic", "hospital", "physician", "pathology", "diagnostic"]):
        syns = [
            f"private hospital in {clean_city}",
            f"specialist clinic in {clean_city}",
            f"multispeciality hospital in {clean_city}",
            f"nursing home in {clean_city}",
            f"diagnostic center in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Home Services: Plumbers, Electricians, Carpenters, AC repair
    elif any(w in kw_lower for w in ["plumb", "electri", "carpent", "ac repair", "pest control", "painter"]):
        syns = [
            f"{core_kw} services in {clean_city}",
            f"{core_kw} repair in {clean_city}",
            f"emergency {core_kw} in {clean_city}",
            f"professional {core_kw} in {clean_city}",
            f"{core_kw} contractors in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Legal / Chartered Accountant / Tax
    elif any(w in kw_lower for w in ["lawyer", "advocate", "legal", "ca", "chartered accountant", "tax"]):
        syns = [
            f"advocate in {clean_city}",
            f"legal advisor in {clean_city}",
            f"law firm in {clean_city}",
            f"chartered accountants in {clean_city}",
            f"tax consultant in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Salon / Spa / Beauty Parlour
    elif any(w in kw_lower for w in ["salon", "parlour", "spa", "makeup", "bridal", "beauty"]):
        syns = [
            f"beauty parlour in {clean_city}",
            f"hair salon in {clean_city}",
            f"bridal makeup studio in {clean_city}",
            f"luxury spa in {clean_city}",
            f"unisex salon in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Coaching / Tuition / Classes / Institute / Academy
    elif any(w in kw_lower for w in ["coach", "tuition", "class", "academy", "institute", "study"]):
        syns = [
            f"coaching institute in {clean_city}",
            f"tuition classes in {clean_city}",
            f"academy in {clean_city}",
            f"educational institute in {clean_city}",
            f"study center in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Restaurant / Food / Cafe / Hotel
    elif any(w in kw_lower for w in ["restaur", "food", "cafe", "hotel", "dine", "dhaba", "bakery"]):
        syns = [
            f"family restaurant in {clean_city}",
            f"top cafes in {clean_city}",
            f"best food in {clean_city}",
            f"hotels in {clean_city}",
            f"veg restaurant in {clean_city}",
            f"bakery in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Gym / Fitness / Yoga
    elif any(w in kw_lower for w in ["gym", "fit", "workout", "yoga"]):
        syns = [
            f"fitness center in {clean_city}",
            f"gym in {clean_city}",
            f"health club in {clean_city}",
            f"unisex gym in {clean_city}",
            f"yoga classes in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Real Estate / Property
    elif any(w in kw_lower for w in ["real estate", "property", "plot", "builder", "flat"]):
        syns = [
            f"property dealer in {clean_city}",
            f"real estate agent in {clean_city}",
            f"plots for sale in {clean_city}",
            f"builders in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Automobile / Garage / Travel / Taxi
    elif any(w in kw_lower for w in ["car", "auto", "vehicle", "taxi", "travel", "garage", "mechanic"]):
        syns = [
            f"car repair garage in {clean_city}",
            f"auto mechanic in {clean_city}",
            f"car rental in {clean_city}",
            f"tour and travels in {clean_city}",
            f"taxi service in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # Photography / Events / Catering
    elif any(w in kw_lower for w in ["photo", "wedding", "event", "cater", "banquet"]):
        syns = [
            f"wedding photographer in {clean_city}",
            f"photo studio in {clean_city}",
            f"event management in {clean_city}",
            f"banquet hall in {clean_city}",
            f"caterers in {clean_city}"
        ]
        for s in syns:
            if s not in queries:
                queries.append(s)

    # 4. Known Locality / Hub variations for this city
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

    # 5. Universal commercial areas present in virtually every town/city
    generic_areas = ["Civil Lines", "Station Road", "Main Road", "Market", "Bypass Road", "AP Colony", "Rampur", "Town", "Commercial Area", "Chowk"]
    for area in generic_areas:
        gq = f"{core_kw} in {area}, {clean_city}"
        if gq not in queries:
            queries.append(gq)

    return queries

def get_user_input():
    print("\n==============================")
    print("GOOGLE MAPS BUSINESS SCRAPER (NAME & PHONE)")
    print("==============================\n")
    keyword = input("Enter Business Keyword (e.g., Restaurants): ").strip()
    city = input("Enter City (e.g., Patna): ").strip()
    leads_str = input("Enter Number of Leads to Scrape (default 100): ").strip()
    try:
        target_count = int(leads_str) if leads_str else 100
    except ValueError:
        target_count = 100
    return keyword, city, target_count

def scrape_google_maps(keyword, city, target_count=100, progress_callback=None, stop_event=None, headless=False):
    """
    Scrapes Google Maps for a given keyword and city.
    Uses multi-query expansion to comfortably reach 100+ unique leads per city.
    Extracts:
      - Business Name
      - Phone Number
    Returns list of dicts: [{"Business Name": ..., "Phone Number": ...}, ...]
    """
    clean_keyword = keyword.strip()
    clean_city = city.strip()
    target_count = max(1, int(target_count))
    
    queries = generate_search_queries(clean_keyword, clean_city)
    
def create_driver(headless=False):
    """Initializes and returns an undetected Chrome driver instance."""
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    else:
        options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US")
    major_version = get_chrome_major_version()
    if major_version:
        return uc.Chrome(options=options, version_main=major_version)
    return uc.Chrome(options=options)

def scrape_google_maps(keyword, city, target_count=100, progress_callback=None, stop_event=None, headless=False):
    """
    Scrapes Google Maps for a given keyword and city.
    Uses multi-query expansion and human-like natural scrolling
    to comfortably reach 100+ unique leads per city.
    Extracts:
      - Business Name
      - Phone Number
    Returns list of dicts: [{"Business Name": ..., "Phone Number": ...}, ...]
    """
    clean_keyword = keyword.strip()
    clean_city = city.strip()
    target_count = max(1, int(target_count))
    
    queries = generate_search_queries(clean_keyword, clean_city)
    
    safe_print(f"\n[Google Maps Scraper] Starting search for '{clean_keyword}' in '{clean_city}'")
    safe_print(f"Target Leads: {target_count}")
    safe_print(f"Generated {len(queries)} query zones to ensure target of {target_count} leads is met.")
    safe_print("Launching browser, please wait...")

    driver = create_driver(headless)
    results = []
    seen_names = set()
    seen_phones = set()
    feed_xpath = "//div[@role='feed']"
    
    try:
        for q_idx, current_query in enumerate(queries, 1):
            if len(results) >= target_count:
                safe_print(f"\nTarget goal of {target_count} leads successfully reached!")
                break
            if stop_event and stop_event.is_set():
                safe_print("\nStop requested by user. Finishing up...")
                break

            query_encoded = current_query.replace(" ", "+")
            url = f"https://www.google.com/maps/search/{query_encoded}"
            safe_print(f"\n[{q_idx}/{len(queries)}] Searching: \"{current_query}\" (Progress: {len(results)}/{target_count} leads)")

            try:
                driver.get(url)
                time.sleep(4)
            except Exception as e:
                safe_print(f"Error loading {current_query}: {e}")
                # Auto-recovery if browser disconnected during long multi-query run
                err_str = str(e).lower()
                if "invalid session id" in err_str or "disconnected" in err_str or "session deleted" in err_str:
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    driver = create_driver(headless)
                    try:
                        driver.get(url)
                        time.sleep(4)
                    except Exception:
                        continue
                else:
                    continue

            # Check if Google shows a consent banner on first page
            if q_idx == 1:
                try:
                    consent_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Accept all') or contains(., 'Agree')]")
                    if consent_btns:
                        consent_btns[0].click()
                        time.sleep(2)
                except Exception:
                    pass

            # Wait for results feed
            feed_element = None
            try:
                feed_element = WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.XPATH, feed_xpath))
                )
            except Exception:
                # Check for single place match page
                try:
                    soup_single = BeautifulSoup(driver.page_source, "html.parser")
                    h1 = soup_single.find("h1")
                    if h1 and h1.get_text(strip=True).lower() != "results":
                        s_name = h1.get_text(strip=True)
                        norm_s = re.sub(r'[^a-zA-Z0-9]', '', s_name.lower())
                        if norm_s not in seen_names:
                            s_phone = extract_phone_from_details(soup_single)
                            norm_p = re.sub(r'\D', '', s_phone) if s_phone else ""
                            if not norm_p or norm_p not in seen_phones:
                                seen_names.add(norm_s)
                                if norm_p:
                                    seen_phones.add(norm_p)
                                lead = {"Business Name": s_name, "Phone Number": s_phone or "Not available"}
                                results.append(lead)
                                safe_print(f"[{len(results)}/{target_count}] Found: {s_name} | Phone: {lead['Phone Number']}")
                                if progress_callback:
                                    try:
                                        progress_callback(len(results), target_count, lead, current_query)
                                    except TypeError:
                                        progress_callback(len(results), target_count, lead)
                except Exception:
                    pass
                continue

            # Scroll and stream extract leads from this query feed
            retries = 0
            last_card_count = 0
            cards_needing_phone = []

            for scroll_round in range(1, 30):
                if len(results) >= target_count:
                    break
                if stop_event and stop_event.is_set():
                    break

                try:
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                except Exception:
                    break
                    
                cards = soup.find_all("div", class_=lambda c: c and "Nv2PK" in c)
                current_card_count = len(cards)
                
                if current_card_count > last_card_count:
                    last_card_count = current_card_count
                    retries = 0
                else:
                    retries += 1

                for card in cards:
                    if len(results) >= target_count:
                        break
                    if stop_event and stop_event.is_set():
                        break

                    name = ""
                    name_elem = card.find("div", class_=lambda x: x and ("qBF1Pd" in x or "fontHeadlineSmall" in x))
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                    if not name:
                        a_tag = card.find("a", href=re.compile(r"/maps/place/"))
                        if a_tag and a_tag.get("aria-label"):
                            name = a_tag.get("aria-label").strip()

                    if not name:
                        continue

                    norm_name = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
                    if norm_name in seen_names:
                        continue

                    # Extract Phone Number directly from card text snippet
                    card_text = card.get_text(" | ", strip=True)
                    phone = extract_phone_from_text(card_text)
                    
                    a_link = card.find("a", href=re.compile(r"/maps/place/"))
                    link = a_link.get("href") if a_link else ""

                    if phone:
                        norm_phone = re.sub(r'\D', '', phone)
                        if norm_phone and norm_phone in seen_phones:
                            continue
                        if norm_phone:
                            seen_phones.add(norm_phone)
                        seen_names.add(norm_name)

                        lead = {
                            "Business Name": name,
                            "Phone Number": phone
                        }
                        results.append(lead)
                        safe_print(f"[{len(results)}/{target_count}] {name} | Phone: {phone}")
                        if progress_callback:
                            try:
                                progress_callback(len(results), target_count, lead, current_query)
                            except TypeError:
                                progress_callback(len(results), target_count, lead)
                    else:
                        # Queue for fallback details visit if needed
                        if link and norm_name not in seen_names:
                            cards_needing_phone.append({"name": name, "norm_name": norm_name, "link": link})

                if len(results) >= target_count or retries >= 6:
                    break

                # Human-like natural micro-scrolling
                try:
                    # 1. Variable micro-scroll steps with brief pauses
                    steps = random.randint(3, 5)
                    for _ in range(steps):
                        step_px = random.randint(240, 420)
                        driver.execute_script("arguments[0].scrollTop += arguments[1];", feed_element, step_px)
                        time.sleep(random.uniform(0.18, 0.30))

                    # 2. Scroll the last rendered card into view to trigger lazy-load hydration
                    driver.execute_script("""
                        var cards = arguments[0].querySelectorAll('div.Nv2PK');
                        if (cards.length > 0) {
                            cards[cards.length - 1].scrollIntoView({behavior: 'smooth', block: 'end'});
                        }
                    """, feed_element)

                    # 3. Anti-stall jiggle: If feed pauses rendering, scroll up slightly then down to wake up intersection observer
                    if retries >= 2:
                        driver.execute_script("arguments[0].scrollTop -= 200;", feed_element)
                        time.sleep(random.uniform(0.4, 0.7))
                        driver.execute_script("arguments[0].scrollTop += 380;", feed_element)
                        time.sleep(random.uniform(0.6, 1.0))

                    # 4. Settle pause for Google Maps network request and rendering
                    time.sleep(random.uniform(1.3, 1.9))
                except Exception:
                    break

                # Check if reached end of list for this query
                src_lower = driver.page_source.lower()
                if "you've reached the end of the list" in src_lower or "end of results" in src_lower:
                    safe_print("   -> Reached end of listings for this query.")
                    break

            # If still short of target, check place details for cards with unlisted phone numbers
            if len(results) < target_count and cards_needing_phone and (not stop_event or not stop_event.is_set()):
                for item in cards_needing_phone[:15]:
                    if len(results) >= target_count:
                        break
                    if stop_event and stop_event.is_set():
                        break
                    if item["norm_name"] in seen_names:
                        continue

                    try:
                        driver.get(item["link"])
                        time.sleep(2.0)
                        soup_detail = BeautifulSoup(driver.page_source, "html.parser")
                        phone = extract_phone_from_details(soup_detail)
                        
                        seen_names.add(item["norm_name"])
                        norm_phone = re.sub(r'\D', '', phone) if phone else ""
                        if norm_phone:
                            seen_phones.add(norm_phone)

                        lead = {
                            "Business Name": item["name"],
                            "Phone Number": phone if phone else "Not available"
                        }
                        results.append(lead)
                        safe_print(f"[{len(results)}/{target_count}] {item['name']} | Phone: {lead['Phone Number']}")
                        if progress_callback:
                            try:
                                progress_callback(len(results), target_count, lead, current_query)
                            except TypeError:
                                progress_callback(len(results), target_count, lead)
                    except Exception as e:
                        safe_print(f"Error checking {item['name']}: {e}")

        safe_print(f"\nScraping finished! Total extracted: {len(results)} unique leads.")

    except Exception as e:
        safe_print(f"\nAn error occurred during scraping: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
            try:
                driver.__del__ = lambda: None
            except Exception:
                pass

    return results

def main():
    keyword, city, target_count = get_user_input()
    if not keyword or not city:
        safe_print("Both Keyword and City are required!")
        return

    data = scrape_google_maps(keyword, city, target_count=target_count)

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