import os
import sys
import time
import re
import json
import random
import unicodedata
from datetime import datetime
import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import db_memory

# Safe encoding configuration for Windows terminals
try:
    if hasattr(sys.stdout, 'reconfigure'):
        getattr(sys.stdout, 'reconfigure')(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        getattr(sys.stderr, 'reconfigure')(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Known commercial locality hubs for cities to expand multi-zone harvesting
CITY_LOCALITY_HUBS = {
    # Bihar & Jharkhand
    "gaya": ["Civil Lines", "GB Road", "Medical College Road", "AP Colony", "Gewal Bigha", "Station Road", "Rampur", "Bodh Gaya", "Bypass Road", "Dandibagh", "Delha", "Manpur", "Tekari Road"],
    "patna": [
        "Boring Road", "Kankarbagh", "Bailey Road", "Danapur", "Saguna More", "Rajendra Nagar", "Exhibition Road",
        "Anisabad", "Ashiana Nagar", "Patliputra", "Fraser Road", "Bazar Samiti", "Musallahpur Hat", "Ashok Rajpath",
        "Raja Bazar", "Jagdeo Path", "Gola Road", "Khagaul", "Kumhrar", "Agam Kuan", "Mithapur", "Jakkanpur",
        "Gardanibagh", "Gulzarbagh", "Patna City", "Zero Mile", "Didarganj", "Bihta", "Phulwari Sharif", "Digha",
        "Kurji", "Nala Road", "Govind Mitra Road", "SP Verma Road", "Chhajju Bagh", "Rukanpura", "Boring Canal Road",
        "Dak Bungalow", "Gandhi Maidan", "Kidwaipuri", "SK Puri", "Rupaspur", "Shastri Nagar", "Indrapuri"
    ],
    "hajipur": ["Sonpur", "Paswan Chowk", "Bagmali", "Konhara Ghat", "Yadav Chowk", "Lalganj Road", "Industrial Area", "Subhash Chowk", "Anjanpir Chowk"],
    "muzaffarpur": ["Bhagwanpur", "Mithanpura", "Sutapatti", "Gobarsahi", "Bypass Road", "Brahmpura", "Ramdayalu Nagar", "Zero Mile", "Aghoria Bazar", "Saraiyaganj", "Kalyani", "Juran Chhapra", "Motijheel"],
    "bhagalpur": ["Adampur", "Zero Mile", "Tilkamanjhi", "Bypass Road", "Mirjanhat", "Aliganj", "Khalifabag", "SujaGanj", "Station Road"],
    "darbhanga": ["Laheriasarai", "Airport Road", "Tower Chowk", "Benta", "Donar", "Mirzapur", "Allpatti", "Kadambag"],
    "ara": ["Gopali Chowk", "Babu Bazar", "Shivganj", "Station Road", "Katira", "Nawada", "Pakari", "Zero Mile", "Dharhara", "Anaith"],
    "begusarai": ["Traffic Chowk", "Barauni", "Har Har Mahadev Chowk", "NH-31 Corridor", "Karpuri Sthan", "Zero Mile", "Subhash Chowk"],
    "purnia": ["Line Bazar", "Bhatta Bazar", "Gulabbagh", "Rambagh", "Madhubani", "Navratan", "Bus Stand"],
    "bihar sharif": ["Ranchi Road", "Hospital More", "Ramchandrapur", "Khandakpar", "Bhainsasur", "Amber"],
    "ranchi": ["Lalpur", "Main Road", "Harmu", "Doranda", "Bariatu", "Ratu Road", "Hinoo", "Morabadi", "Namkum", "Kanke Road", "Kokar", "Ashok Nagar", "Dhurwa", "Tatisilwai"],
    "jamshedpur": ["Bistupur", "Sakchi", "Dimna Road", "Mango", "Gamharia", "Telco", "Kadma", "Sonari", "Adityapur", "Golmuri", "Baridih"],
    "dhanbad": ["Bank More", "Govindpur", "Saraidhela", "Barwadda", "Hirapur", "Jharia", "Steel Gate", "Dhaiya", "Katras"],
    "bokaro": ["Sector 4", "Chas Highway Corridor", "Sector 1", "Sector 6", "Sector 9", "Co-operative Colony", "Chas Bazar"],
    "deoghar": ["AIIMS Road", "Tower Chowk", "Castairs Town", "Jasidih", "Bilaspur", "Kunda", "Williams Town"],
    # Major Metros & Regional Capitals
    "delhi": [
        "Connaught Place", "South Extension", "Lajpat Nagar", "Dwarka", "Rohini", "Karol Bagh", "Janakpuri",
        "Laxmi Nagar", "Saket", "Pitampura", "Hauz Khas", "Nehru Place", "Rajouri Garden", "Vasant Kunj",
        "Chandni Chowk", "Preet Vihar", "Shahdara", "Paschim Vihar", "Mayur Vihar", "Green Park", "Kalkaji"
    ],
    "noida": ["Sector 18", "Sector 62", "Sector 63", "Greater Noida", "Sector 15", "Sector 16", "Sector 50", "Sector 137", "Sector 128", "Sector 76"],
    "gurgaon": ["Cyber City", "MG Road", "Golf Course Road", "Sohna Road", "Sector 29", "Sector 14", "DLF Phase 1", "DLF Phase 3", "Sector 56", "Udyog Vihar", "Sector 49"],
    "mumbai": [
        "Andheri", "Bandra", "Borivali", "Thane", "Navi Mumbai", "Dadar", "Powai", "Goregaon", "Malad",
        "Kandivali", "Ghatkopar", "Mulund", "Kurla", "Chembur", "Vashi", "Kalyan", "Santacruz", "Juhu"
    ],
    "pune": ["Kothrud", "Hinjawadi", "Viman Nagar", "Baner", "Wakad", "Shivajinagar", "Hadapsar", "Aundh", "Pimpri", "Chinchwad", "Magarpatta", "Kalyani Nagar"],
    "kolkata": ["Salt Lake", "Park Street", "New Town", "Gariahat", "Behala", "Howrah", "Dum Dum", "Jadavpur", "Shyambazar", "Rajarhat", "Tollygunge", "Ballygunge"],
    "bangalore": [
        "Indiranagar", "Koramangala", "Whitefield", "HSR Layout", "Jayanagar", "Electronic City",
        "Marathahalli", "JP Nagar", "BTM Layout", "Hebbal", "Yelahanka", "Malleshwaram", "Rajajinagar"
    ],
    "hyderabad": ["Hitech City", "Madhapur", "Gachibowli", "Banjara Hills", "Jubilee Hills", "Kukatpally", "Secunderabad", "Ameerpet", "Dilsukhnagar", "Kondapur", "Begumpet"],
    "chennai": ["T Nagar", "Anna Nagar", "Velachery", "Adyar", "OMR", "Guindy", "Tambaram", "Mylapore", "Nungambakkam", "Porur", "Kilpauk"],
    "ahmedabad": ["SG Highway", "Navrangpura", "Satellite", "Maninagar", "Prahlad Nagar", "Vastrapur", "Bodakdev", "Bopal", "Paldi", "Chandkheda"],
    "jaipur": ["Malviya Nagar", "Vaishali Nagar", "Mansarovar", "C Scheme", "Tonk Road", "Raja Park", "Jagatpura", "Ajmer Road", "Vidhyadhar Nagar", "MI Road"],
    "lucknow": ["Hazratganj", "Gomti Nagar", "Aliganj", "Indira Nagar", "Alambagh", "Charbagh", "Mahanagar", "Jankipuram", "Ashiyana", "Vikas Nagar"],
    "kanpur": ["Mall Road", "Swaroop Nagar", "Civil Lines", "Kakadeo", "Govind Nagar", "Kidwai Nagar", "Gumti No 5", "Arya Nagar"],
    "varanasi": ["Sigra", "Cantt", "Lanka", "Bhelupur", "Pandeypur", "Mahmoorganj", "Godowlia", "Orderly Bazar", "Durgakund", "Shivpur"],
    "indore": ["Vijay Nagar", "Palasia", "Bhawarkua", "Rajwada", "AB Road", "Sapna Sangeeta", "Geeta Bhawan", "Annapurna"],
    "bhopal": ["MP Nagar", "Arera Colony", "New Market", "Kolar Road", "Hoshangabad Road", "Bairagarh", "Bittan Market", "Shahpura"],
    "chandigarh": ["Sector 17", "Sector 35", "Sector 22", "Industrial Area", "Sector 8", "Sector 34", "Sector 43", "Sector 9", "Mohali", "Panchkula"]
}

# Universal commercial town hubs for ANY city worldwide
GENERIC_TOWN_HUBS = [
    "Station Road", "Main Market", "Bypass Road", "Cinema Road", "Civil Lines",
    "Hospital Road", "Gandhi Chowk", "Bus Stand", "College Road", "Industrial Area",
    "Court Road", "Zero Mile", "Railway Colony", "City Center", "Town Hall",
    "Super Market", "Commercial Complex", "New Colony", "Old Bazar", "Subhash Chowk",
    "Thana Road", "Purani Bazar", "Naya Bazar", "Tower Chowk", "Main Road",
    "Market Yard", "Commercial Corridor", "High Street", "Shopping Center"
]

# Postal Pincodes for high-yield localized search expansion
CITY_PINCODES = {
    "patna": [
        "800001", "800002", "800003", "800004", "800005", "800006", "800007", "800008",
        "800009", "800010", "800011", "800012", "800013", "800014", "800015", "800016",
        "800020", "800023", "800024", "800025", "800026", "800027", "800028"
    ],
    "ranchi": ["834001", "834002", "834003", "834004", "834005", "834006", "834008", "834009", "834010"],
    "delhi": [
        "110001", "110002", "110003", "110005", "110006", "110007", "110008", "110009",
        "110011", "110012", "110016", "110017", "110019", "110020", "110024", "110025",
        "110027", "110028", "110030", "110034", "110048", "110051", "110052", "110058"
    ],
    "mumbai": [
        "400001", "400002", "400004", "400011", "400014", "400016", "400028", "400049",
        "400050", "400051", "400053", "400058", "400064", "400069", "400076", "400092"
    ],
    "bangalore": [
        "560001", "560002", "560004", "560011", "560025", "560034", "560038", "560041",
        "560066", "560068", "560076", "560078", "560100", "560102", "560103"
    ],
    "kolkata": ["700001", "700016", "700019", "700020", "700026", "700029", "700032", "700064", "700091", "700106"],
    "hyderabad": ["500001", "500003", "500004", "500016", "500032", "500034", "500072", "500081", "500082", "500084"],
    "pune": ["411001", "411002", "411004", "411007", "411014", "411016", "411028", "411038", "411045", "411057"]
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
def human_delay(min_sec=1.5, max_sec=3.0):
    """Randomized human delay with natural jitter."""
    time.sleep(random.uniform(min_sec, max_sec))

def human_click(driver, element):
    """
    Simulates organic human clicking behavior:
    1. Smoothly scrolls the element into view.
    2. Moves the mouse to the element with realistic coordinate jitter.
    3. Triggers genuine hardware mouse events with natural micro-pauses.
    """
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(random.uniform(0.18, 0.35))

        # Randomize click offset slightly off-center (simulating human inaccuracy)
        x_offset = random.randint(-6, 6)
        y_offset = random.randint(-4, 4)

        actions = ActionChains(driver)
        actions.move_to_element_with_offset(element, x_offset, y_offset)
        actions.pause(random.uniform(0.08, 0.20))
        actions.click()
        actions.perform()
    except Exception:
        # Fallback: Dispatch full synthetic mouse lifecycle with randomized coordinates
        try:
            driver.execute_script("""
                var el = arguments[0];
                var rect = el.getBoundingClientRect();
                var cx = rect.left + rect.width / 2 + (Math.random() * 8 - 4);
                var cy = rect.top + rect.height / 2 + (Math.random() * 6 - 3);

                ['mousemove', 'mouseenter', 'mouseover', 'mousedown', 'mouseup', 'click'].forEach(function(eventType) {
                    var evt = new MouseEvent(eventType, {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: cx,
                        clientY: cy
                    });
                    el.dispatchEvent(evt);
                });
            """, element)
        except Exception:
            try:
                driver.execute_script("arguments[0].click();", element)
            except Exception:
                pass

def human_smooth_scroll(driver, feed_element=None, total_distance=None, direction="down"):
    """
    Simulates human mouse wheel scrolling and triggers Google Maps infinite feed loading.
    Dynamically targets the results feed and scrolls the bottom card into view to fire
    IntersectionObserver events, preventing stale references or stalled lists.
    """
    try:
        driver.execute_script("""
            var back = document.querySelector("button[aria-label='Back'], button[jsaction*='pane.back'], button[data-tooltip='Back']");
            if (back) try { back.click(); } catch(e) {}
            
            var feed = document.querySelector("div[role='feed']") ||
                       document.querySelector("div.m6QErb[aria-label*='Results']") ||
                       document.querySelector("div.m6QErb[class*='DxyBCb']") ||
                       document.querySelector("div.m6QErb");
            if (feed) {
                feed.scrollTop = feed.scrollHeight;
                try {
                    feed.dispatchEvent(new Event('scroll', { bubbles: true }));
                } catch(e) {}
            }
            var cards = document.querySelectorAll("a.hfpxzc");
            if (cards.length > 0) {
                try {
                    cards[cards.length - 1].scrollIntoView({ behavior: 'instant', block: 'end' });
                } catch(e) {}
            }
        """)
    except Exception:
        pass
    time.sleep(random.uniform(0.9, 1.4))

def human_reading_pause(card_count):
    """Light micro-pause to allow DOM rendering without stalling the scraper."""
    time.sleep(random.uniform(0.1, 0.25))

def human_subtle_jitter(driver):
    """Occasionally moves mouse slightly across viewport to maintain organic activity signals."""
    if random.random() < 0.4:
        try:
            driver.execute_script("""
                var x = Math.floor(Math.random() * (window.innerWidth - 100) + 50);
                var y = Math.floor(Math.random() * (window.innerHeight - 100) + 50);
                var evt = new MouseEvent('mousemove', {
                    bubbles: true,
                    cancelable: true,
                    clientX: x,
                    clientY: y
                });
                document.dispatchEvent(evt);
            """)
        except Exception:
            pass

def normalize_for_dedup(name):
    """
    Normalizes a business name for deduplication, stripping SEO spam keywords,
    leading articles, honorifics, corporate entities, parenthetical additions,
    branch identifiers, and special characters.
    """
    if not name:
        return ""
    s = str(name).lower().strip()
    # Strip leading honorifics and articles
    s = re.sub(r'^(?:the|hotel|a|an|dr|dr\.|doctor|shri|shree|sri|m/s|ms)\s+', '', s, flags=re.I)
    # Strip parentheticals like (Boring Road) or (CBSE)
    s = re.sub(r'\s*\([^)]*\)', '', s)
    # Strip trailing branch or location details separated by spaces and dashes/pipes/slashes
    s = re.sub(r'\s+[\-|–|—|\|•/]\s+.*$', '', s)
    # Strip promotional tags or location tags
    s = re.sub(r'\s*[\-|–|—|\|•/]\s*(?:best|top|famous|cheap|popular|weddingz|fully ac|marriage|banquet|hotel|resort|premier|luxury|verified|branch|opp|near|in|at).*$', '', s, flags=re.I)
    # Strip trailing comma location: ", Patna"
    s = re.sub(r',\s*[a-zA-Z\s]+$', '', s)
    # Strip common corporate legal entity suffixes
    s = re.sub(r'\b(?:pvt|private|ltd|limited|llp|inc|incorporated|corp|corporation|co|company|enterprises|associates)\b', '', s, flags=re.I)
    # Remove non-alphanumeric characters
    norm = re.sub(r'[^a-z0-9]', '', s)
    if not norm:
        norm = re.sub(r'[^a-z0-9]', '', str(name).lower())
    return norm

def canonical_phone(raw_phone):
    """
    Standardizes any phone number into a canonical subscriber identifier for 100% duplicate detection.
    Correctly recognizes that:
      +91 98350 12345 == 098350 12345 == 9835012345
      +91 612 2234567 == (0612) 2234567
      +1 555-234-5678 == 555-234-5678
    """
    if not raw_phone:
        return ""
    digits = re.sub(r'\D', '', str(raw_phone))
    if len(digits) < 7:
        return ""
    # Indian 12 digits starting with country code 91
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    # 11 digits starting with 0 (mobile or landline with STD prefix)
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    # US/Canada 11 digits starting with 1
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    # Standard 10+ digits: last 10 digits identify the subscriber number
    if len(digits) >= 10:
        return digits[-10:]
    return digits

def deduplicate_leads(leads):
    """
    Final deduplication filter to guarantee zero duplicate business names
    and zero duplicate phone numbers in the final leads dataset.
    Strictly excludes listings that do not have a valid phone number.
    Ensures 'Website' is present on every lead (defaulting to 'NA').
    """
    if not leads:
        return []

    unique_leads = []
    seen_names = set()
    seen_phones = set()

    for lead in leads:
        name = str(lead.get("Business Name", "")).strip()
        phone = str(lead.get("Phone Number", "")).strip()
        if not name:
            continue

        # Reject leads missing a phone number or marked as not available
        if not phone or phone.lower() in ["not available", "n/a", "none", "nan", ""]:
            continue

        canon_p = canonical_phone(phone)
        if not canon_p:
            continue

        norm_name = normalize_for_dedup(name)
        if not norm_name or norm_name in seen_names:
            continue

        if canon_p in seen_phones:
            continue

        seen_names.add(norm_name)
        seen_phones.add(canon_p)

        # Standardize Website field
        w_val = str(lead.get("Website", "")).strip()
        lead["Website"] = w_val if w_val and w_val.lower() not in ["none", "nan", ""] else "NA"

        unique_leads.append(lead)

    return unique_leads

def parse_cities(city_input, max_cities=4):
    """
    Parses comma-separated city input into a clean list of unique city names.
    Enforces a strict maximum of max_cities (default 4).
    Example:
        'Patna, Gaya, Muzaffarpur, Ranchi' -> ['Patna', 'Gaya', 'Muzaffarpur', 'Ranchi']
    """
    if not city_input:
        return []
    if isinstance(city_input, (list, tuple)):
        raw_items = city_input
    else:
        raw_items = str(city_input).split(",")

    cities = []
    seen = set()
    for item in raw_items:
        clean = item.strip()
        if clean and clean.lower() not in seen:
            cities.append(clean)
            seen.add(clean.lower())
    return cities[:max_cities]

def clean_phone_number(raw_str):
    """
    Strictly validates, formats, and cleans phone numbers.
    Rejects coordinates, rating IDs, decimals, or invalid prefixes.
    """
    if not raw_str:
        return ""

    # Normalize unicode spaces
    s = unicodedata.normalize('NFKD', str(raw_str)).strip()

    # Reject coordinates or floating point garbage (e.g. 543214.2380)
    if '.' in s and re.search(r'\d+\.\d{2,}', s):
        return ""

    # Strip repeated prefixes like "phone:", "tel:", "mobile:", "call:"
    while True:
        new_s = re.sub(r'^(?:phone|call|tel|mobile):\s*', '', s, flags=re.I).strip()
        if new_s == s:
            break
        s = new_s

    digits = re.sub(r'[^\d]', '', s)

    # Must be valid length for phone numbers
    if len(digits) < 7 or len(digits) > 15:
        return ""

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

    # Generic valid international format (starting with +)
    if s.startswith("+") and len(digits) >= 10:
        return s

    # Regex extraction fallback only if strictly matching valid mobile/landline patterns
    m = re.search(r'(?:\+?91[\s-]?)?(?:0?[6-9]\d{4}[\s\-]?\d{5}|0\d{1,4}[\s\-]?(?:\d{3,4}[\s\-]?\d{4}|\d{6,8})|\b[6-9]\d{9}\b)', s)
    if m:
        cleaned_sub = m.group(0).strip()
        sub_digits = re.sub(r'[^\d]', '', cleaned_sub)
        if len(sub_digits) == 10 and sub_digits[0] in "6789":
            return f"{sub_digits[:5]} {sub_digits[5:]}"
        elif len(sub_digits) == 11 and sub_digits.startswith("0"):
            return f"0{sub_digits[1:6]} {sub_digits[6:]}"
        elif len(sub_digits) == 12 and sub_digits.startswith("91"):
            return f"+91 {sub_digits[2:7]} {sub_digits[7:]}"

    return ""

def extract_phone_from_text(text):
    """Searches plain text block for phone numbers using strict phone cleaner."""
    if not text:
        return ""
    m = re.search(r'(?:\+?\d{1,4}[\s-]?)?(?:(?:\(?\d{2,5}\)?[\s-]?)?\d{6,10})', str(text))
    if m:
        cleaned = clean_phone_number(m.group(0))
        if cleaned:
            return cleaned
    return clean_phone_number(text)

def extract_phone_from_details(soup):
    """Extract phone number from Google Maps place details HTML or panel."""
    # 1. Element with data-item-id containing phone (most accurate)
    phone_item = soup.find(lambda e: e.name in ["button", "div", "a"] and "phone:" in str(e.get("data-item-id", "")))
    if phone_item:
        item_id = str(phone_item.get("data-item-id", ""))
        aria = phone_item.get("aria-label", "")
        phone = clean_phone_number(item_id) or clean_phone_number(aria)
        if phone:
            return phone

    # 2. Tooltip button containing phone
    phone_btn = soup.find("button", {"data-tooltip": re.compile(r"phone", re.I)})
    if phone_btn:
        aria = phone_btn.get("aria-label", "")
        text = phone_btn.get_text(strip=True)
        phone = clean_phone_number(aria) or clean_phone_number(text)
        if phone:
            return phone

    # 3. Anchor with tel: protocol
    tel_a = soup.find("a", href=re.compile(r"^tel:", re.I))
    if tel_a:
        phone = clean_phone_number(tel_a.get("href", ""))
        if phone:
            return phone

    # 4. Search all elements with aria-label containing Phone
    for el in soup.find_all(attrs={"aria-label": re.compile(r"Phone:", re.I)}):
        phone = clean_phone_number(el.get("aria-label"))
        if phone:
            return phone

    return ""

def clean_website_url(raw_url):
    """
    Cleans, normalizes, and validates business website URLs.
    Extracts destination URLs from Google & Bing redirection wrappers.
    Returns 'NA' if no valid external website is found.
    """
    if not raw_url:
        return "NA"
    s = str(raw_url).strip()
    if s.lower() in ["not available", "n/a", "na", "none", "null", "nan", ""]:
        return "NA"

    # Reject non-web schemes
    if any(s.lower().startswith(prefix) for prefix in ["javascript:", "mailto:", "tel:", "#", "data:"]):
        return "NA"

    # Decode Google redirection URL: https://www.google.com/url?q=...
    try:
        import urllib.parse
        parsed = urllib.parse.urlparse(s)
        if "google." in parsed.netloc and "/url" in parsed.path:
            qs = urllib.parse.parse_qs(parsed.query)
            if "q" in qs and qs["q"]:
                s = qs["q"][0]
                parsed = urllib.parse.urlparse(s)
            elif "url" in qs and qs["url"]:
                s = qs["url"][0]
                parsed = urllib.parse.urlparse(s)
    except Exception:
        pass

    # Decode Bing redirection URL: https://www.bing.com/ck/a?...&u=a1aHR0c...
    try:
        import urllib.parse
        import base64
        parsed = urllib.parse.urlparse(s)
        if "bing.com" in parsed.netloc and "/ck/a" in parsed.path:
            qs = urllib.parse.parse_qs(parsed.query)
            if "u" in qs and qs["u"]:
                u_val = qs["u"][0]
                if u_val.startswith("a1"):
                    b64 = u_val[2:] + "=="
                    dec = base64.b64decode(b64).decode("utf-8", errors="ignore")
                    if dec.startswith("http"):
                        s = dec
                        parsed = urllib.parse.urlparse(s)
    except Exception:
        pass

    # Normalize protocol
    if not re.match(r'^https?://', s, re.I):
        if s.startswith("//"):
            s = "https:" + s
        else:
            s = "https://" + s
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(s)
        except Exception:
            return "NA"

    netloc = parsed.netloc.lower()
    path = parsed.path.lower()

    # Reject internal Google/Bing search/maps links (allow sites.google.com as legitimate business website)
    if "maps.google." in netloc or ("google." in netloc and any(p in path for p in ["/maps", "/search", "/sorry", "/intl", "/preferences"])):
        return "NA"
    if any(h in netloc for h in ["gstatic.com", "ggpht.com", "googleusercontent.com", "googleapis.com"]):
        return "NA"
    if ("bing.com" in netloc and any(p in path for p in ["/maps", "/search", "/ck"])) or "microsoft.com" in netloc:
        return "NA"

    # Must have a valid domain format
    if "." not in netloc or len(netloc) < 4:
        return "NA"

    clean = s.strip()
    return clean if clean else "NA"

def extract_website_from_details(soup):
    """Extracts website URL from place details HTML panel."""
    if not soup:
        return "NA"

    # 1. Authority item link (standard Google Maps attribute)
    auth = soup.find(lambda e: e.name == "a" and "authority" in str(e.get("data-item-id", "")).lower())
    if auth and auth.get("href"):
        w = clean_website_url(auth.get("href"))
        if w != "NA":
            return w

    # 2. Tooltip or aria-label or data-value containing 'website'
    web_a = soup.find(lambda e: e.name == "a" and (
        "website" in str(e.get("aria-label", "")).lower() or
        "website" in str(e.get("data-tooltip", "")).lower() or
        "website" in str(e.get("data-value", "")).lower()
    ))
    if web_a and web_a.get("href"):
        w = clean_website_url(web_a.get("href"))
        if w != "NA":
            return w

    # 3. Action container or detail rows containing website indicators
    for a in soup.find_all("a", href=re.compile(r"^https?://", re.I)):
        href = a.get("href", "")
        aria = str(a.get("aria-label", "")).lower()
        text = a.get_text(strip=True).lower()
        if "website" in aria or "website" in text:
            w = clean_website_url(href)
            if w != "NA":
                return w

    return "NA"

def generate_search_queries(keyword, city, target_count=100, pass_num=1):
    """
    Generates structured queries prioritizing geographic zone dispersion.
    Dynamically expands the query pool based on target_count and pass_num so
    large requests (e.g. 175 leads) NEVER run out of queries before reaching the goal.
    Pass 1: Core queries, top locality hubs, directional sectors, and base synonyms.
    Pass 2: Deep Pass - specialty subcategories, complete hub x synonym matrix, pincodes, and landmarks.
    Pass 3: Ultra-Deep Pass - remaining hub permutations, landmark sectors, and auxiliary variations.
    """
    clean_kw = keyword.strip()
    clean_city = city.strip()
    kw_lower = clean_kw.lower()
    city_lower = clean_city.lower()

    core_kw = re.sub(r'^(?:best|top|famous|cheap|good|verified|popular)\s+', '', clean_kw, flags=re.I).strip()
    if not core_kw:
        core_kw = clean_kw

    queries = []

    # Locality Hubs for this city
    hubs = list(CITY_LOCALITY_HUBS.get(city_lower, []))
    if not hubs:
        for k, v in CITY_LOCALITY_HUBS.items():
            if k in city_lower:
                hubs = list(v)
                break
    # Supplement with generic town hubs if hubs list is small or target_count is large
    if len(hubs) < 15 or target_count > 60:
        for gh in GENERIC_TOWN_HUBS:
            if gh not in hubs:
                hubs.append(gh)

    # Domain synonyms and specialty sub-categories
    syns = []
    subcats = []
    if any(w in kw_lower for w in ["coach", "tuition", "class", "academy", "institute", "study", "tutorial"]):
        syns = [
            f"coaching classes in {clean_city}",
            f"tuition classes in {clean_city}",
            f"academy in {clean_city}",
            f"study center in {clean_city}",
            f"tutorials in {clean_city}",
            f"coaching institute in {clean_city}",
            f"competitive exam coaching in {clean_city}"
        ]
        subcats = ["neet coaching", "iit jee coaching", "commerce coaching", "cbse coaching", "upsc classes", "spoken english", "computer institute", "study library"]
    elif any(w in kw_lower for w in ["eye", "surgeon", "retina", "vision", "ophthalm"]):
        syns = [f"eye hospital in {clean_city}", f"eye care clinic in {clean_city}", f"ophthalmologist in {clean_city}", f"eye doctor in {clean_city}"]
        subcats = ["retina specialist", "lasik laser center", "cataract clinic", "optical shop", "eye care center"]
    elif any(w in kw_lower for w in ["dentist", "dental", "teeth", "tooth"]):
        syns = [f"dental clinic in {clean_city}", f"dentist in {clean_city}", f"dental care center in {clean_city}"]
        subcats = ["dental clinic", "root canal specialist", "teeth aligner center", "orthodontist clinic", "dental hospital"]
    elif any(w in kw_lower for w in ["ortho", "bone", "joint", "spine"]):
        syns = [f"orthopedic doctor in {clean_city}", f"bone specialist in {clean_city}", f"orthopedic hospital in {clean_city}"]
        subcats = ["bone joint clinic", "spine specialist", "fracture clinic", "physiotherapy center"]
    elif any(w in kw_lower for w in ["cardio", "heart"]):
        syns = [f"cardiologist in {clean_city}", f"heart hospital in {clean_city}"]
        subcats = ["heart clinic", "cardiology center", "ecg echo center", "cardiac specialist"]
    elif any(w in kw_lower for w in ["skin", "derma", "hair", "laser"]):
        syns = [f"dermatologist in {clean_city}", f"skin clinic in {clean_city}", f"hair clinic in {clean_city}"]
        subcats = ["skin specialist", "hair transplant clinic", "laser skin clinic", "cosmetologist", "derma care"]
    elif any(w in kw_lower for w in ["doctor", "clinic", "hospital", "pathology", "diagnostic", "surgeon"]):
        syns = [f"diagnostic center in {clean_city}", f"pathology lab in {clean_city}", f"multispeciality hospital in {clean_city}", f"specialist doctor in {clean_city}", f"clinic in {clean_city}"]
        subcats = ["general physician", "child specialist pediatrician", "gynecologist clinic", "pathology laboratory", "ultrasound center", "nursing home"]
    elif any(w in kw_lower for w in ["salon", "parlour", "spa", "makeup", "bridal", "beauty"]):
        syns = [f"beauty parlour in {clean_city}", f"hair salon in {clean_city}", f"bridal makeup in {clean_city}", f"unisex salon in {clean_city}"]
        subcats = ["bridal makeover studio", "hair styling salon", "skin parlour", "spa and massage", "nail art studio", "men hair salon"]
    elif any(w in kw_lower for w in ["restaur", "food", "cafe", "hotel", "dine", "sweets", "bakery"]):
        syns = [f"family restaurant in {clean_city}", f"top cafes in {clean_city}", f"hotel in {clean_city}", f"food court in {clean_city}"]
        subcats = ["veg restaurant", "non veg restaurant", "chinese restaurant", "biryani corner", "fast food center", "cafe and lounge", "family dining", "dhaba", "sweet shop", "bakery"]
    elif any(w in kw_lower for w in ["gym", "fit", "workout", "yoga"]):
        syns = [f"fitness center in {clean_city}", f"gym in {clean_city}", f"yoga classes in {clean_city}"]
        subcats = ["unisex fitness gym", "crossfit center", "weight training gym", "yoga meditation studio", "aerobics zumba class"]
    elif any(w in kw_lower for w in ["real estate", "property", "plot", "builder"]):
        syns = [f"property dealer in {clean_city}", f"real estate agent in {clean_city}"]
        subcats = ["property dealer", "real estate broker", "commercial property agent", "residential plot dealer", "building contractor", "flat for sale"]
    else:
        subcats = [f"{core_kw} services", f"{core_kw} dealers", f"{core_kw} center", f"{core_kw} store", f"{core_kw} agency", f"{core_kw} shop"]

    pincodes = CITY_PINCODES.get(city_lower, [])
    if not pincodes:
        for k, v in CITY_PINCODES.items():
            if k in city_lower:
                pincodes = v
                break

    if pass_num == 1:
        # Pass 1: Standard primary queries, top hubs, directional sectors, core synonyms
        queries.append(f"{clean_kw} in {clean_city}")
        if core_kw.lower() != clean_kw.lower():
            queries.append(f"{core_kw} in {clean_city}")

        hub_limit = 50 if target_count >= 200 else 35
        for hub in hubs[:hub_limit]:
            hq = f"{core_kw} in {hub}, {clean_city}"
            if hq not in queries:
                queries.append(hq)

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
            f"{core_kw} in {clean_city} Commercial Complex",
            f"{core_kw} in {clean_city} Mall Road",
            f"{core_kw} in {clean_city} Highway",
            f"{core_kw} near {clean_city}"
        ]
        for uq in universal_sectors:
            if uq not in queries:
                queries.append(uq)

        for s in syns:
            if s not in queries:
                queries.append(s)

        if target_count > 60 and syns:
            for syn_phrase in syns[:3]:
                base_term = re.sub(r'\s+in\s+.*$', '', syn_phrase, flags=re.I).strip()
                for th in hubs[:12]:
                    comb = f"{base_term} in {th}, {clean_city}"
                    if comb not in queries:
                        queries.append(comb)

        if target_count > 100 and pincodes:
            for pin in pincodes[:10]:
                pq = f"{core_kw} in {pin}"
                if pq not in queries:
                    queries.append(pq)

    elif pass_num == 2:
        # Pass 2: Deep Pass - Remaining hubs, all subcategories, complete hub x synonym matrix, full pincodes
        start_hub = 50 if target_count >= 200 else 35
        for hub in hubs[start_hub:]:
            hq = f"{core_kw} in {hub}, {clean_city}"
            if hq not in queries:
                queries.append(hq)

        for sc in subcats:
            sc_q = f"{sc} in {clean_city}"
            if sc_q not in queries:
                queries.append(sc_q)

        for sc in subcats[:4]:
            for hub in hubs[:20]:
                comb = f"{sc} in {hub}, {clean_city}"
                if comb not in queries:
                    queries.append(comb)

        for syn_phrase in syns:
            base_term = re.sub(r'\s+in\s+.*$', '', syn_phrase, flags=re.I).strip()
            for th in hubs[10:30]:
                comb = f"{base_term} in {th}, {clean_city}"
                if comb not in queries:
                    queries.append(comb)

        for pin in pincodes:
            p1 = f"{core_kw} in {pin}"
            p2 = f"{clean_kw} near {pin}"
            if p1 not in queries:
                queries.append(p1)
            if p2 not in queries:
                queries.append(p2)

        for hub in hubs[:20]:
            c1 = f"{core_kw} near {hub} Chowk, {clean_city}"
            c2 = f"{core_kw} near {hub} Main Road, {clean_city}"
            if c1 not in queries:
                queries.append(c1)
            if c2 not in queries:
                queries.append(c2)

    elif pass_num == 3:
        # Pass 3: Ultra-Deep Pass - Exhaustive subcategory permutations & landmark sweeps
        for sc in subcats[4:]:
            for hub in hubs[:35]:
                comb = f"{sc} in {hub}, {clean_city}"
                if comb not in queries:
                    queries.append(comb)

        for pin in pincodes:
            for sc in subcats[:3]:
                comb = f"{sc} in {pin}"
                if comb not in queries:
                    queries.append(comb)

        generic_extras = [
            f"best {core_kw} in {clean_city}",
            f"top {core_kw} in {clean_city}",
            f"famous {core_kw} in {clean_city}",
            f"popular {core_kw} in {clean_city}",
            f"top rated {core_kw} in {clean_city}",
            f"verified {core_kw} in {clean_city}",
            f"contact number {core_kw} in {clean_city}",
            f"{clean_kw} contact details in {clean_city}",
            f"trusted {core_kw} in {clean_city}",
            f"leading {core_kw} in {clean_city}"
        ]
        for g in generic_extras:
            if g not in queries:
                queries.append(g)

    else:
        # Pass 4+: Ultra-Wide Geographic Corridor & Outskirts Expansion (guarantees up to 500 leads)
        for hub in hubs[35:]:
            for sc in subcats[:2]:
                comb = f"{sc} in {hub}, {clean_city}"
                if comb not in queries:
                    queries.append(comb)

        corridor_terms = [
            f"{core_kw} near {clean_city}",
            f"{core_kw} around {clean_city}",
            f"{core_kw} outer {clean_city}",
            f"{core_kw} in Greater {clean_city}",
            f"{core_kw} in {clean_city} District",
            f"{core_kw} in {clean_city} Cantonment",
            f"{core_kw} in {clean_city} Extension",
            f"{core_kw} in Old {clean_city}",
            f"{core_kw} in New {clean_city}",
            f"{core_kw} along {clean_city} Highway",
            f"{core_kw} near {clean_city} Railway Station",
            f"{core_kw} near {clean_city} Bus Stand",
            f"{core_kw} near {clean_city} Airport"
        ]
        for ct in corridor_terms:
            if ct not in queries:
                queries.append(ct)

        for sc in subcats:
            for dir_sec in ["North", "South", "East", "West", "Central"]:
                sc_dir = f"{sc} in {dir_sec} {clean_city}"
                if sc_dir not in queries:
                    queries.append(sc_dir)

    return queries

PROFILE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", BASE_DIR), "DataScraper_ChromeProfile")

def is_remote_debugging_available(port=9222):
    """Check if an existing Google Chrome instance is running with remote debugging on port 9222."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=0.8) as res:
            return res.status == 200
    except Exception:
        return False

def get_scraper_profile_dir():
    """Return the persistent directory path where the scraper browser stores cookies and logins."""
    os.makedirs(PROFILE_DIR, exist_ok=True)
    return PROFILE_DIR

def cleanup_lingering_scraper_chrome():
    """Terminate any orphan Chrome processes holding the DataScraper_ChromeProfile lock."""
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                cmdline = " ".join(proc.info.get('cmdline') or [])
                if 'DataScraper_ChromeProfile' in cmdline:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
        time.sleep(0.5)
    except Exception:
        pass

def find_chrome_executable():
    """Locate the installed Google Chrome binary path on Windows."""
    paths = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return "chrome.exe"

def open_google_login_browser(target_url="https://accounts.google.com"):
    """
    Launches genuine Google Chrome using the scraper's persistent profile.
    This lets the user sign into Google without encountering bot/automation blocks.
    Once signed in, the session is saved permanently for all future scrapes.
    """
    cleanup_lingering_scraper_chrome()
    chrome_exe = find_chrome_executable()
    profile_dir = get_scraper_profile_dir()

    cmd = [
        chrome_exe,
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        target_url
    ]
    import subprocess
    return subprocess.Popen(cmd)

def check_auth_status():
    """
    Check if the persistent scraper profile or a live remote debugging session is authenticated.
    """
    if is_remote_debugging_available(9222):
        return {
            "logged_in": True,
            "email": "Live Chrome Session (Port 9222)",
            "mode": "remote_debug",
            "details": "Connected to active Chrome browser with your open accounts and tabs."
        }

    profile_dir = get_scraper_profile_dir()
    cand_prefs = [
        os.path.join(profile_dir, "Default", "Preferences"),
        os.path.join(profile_dir, "Preferences")
    ]
    for p in cand_prefs:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                accounts = data.get("account_info", [])
                if isinstance(accounts, list) and accounts:
                    emails = [a.get("email") for a in accounts if a.get("email")]
                    if emails:
                        return {
                            "logged_in": True,
                            "email": emails[0],
                            "mode": "persistent_profile",
                            "details": f"Signed in as {emails[0]}"
                        }
            except Exception:
                pass

    # Check cookies database for Google authentication cookies
    cand_cookies = [
        os.path.join(profile_dir, "Default", "Network", "Cookies"),
        os.path.join(profile_dir, "Network", "Cookies")
    ]
    for c in cand_cookies:
        if os.path.exists(c):
            try:
                import sqlite3
                conn = sqlite3.connect(f"file:{c}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM cookies WHERE host_key LIKE '%google%' AND name IN ('SID', 'SSID', 'HSID', 'SAPISID')")
                rows = cursor.fetchall()
                conn.close()
                if len(rows) >= 2:
                    return {
                        "logged_in": True,
                        "email": "Google Account Active",
                        "mode": "persistent_profile",
                        "details": "Google authentication session verified"
                    }
            except Exception:
                pass

    return {
        "logged_in": False,
        "email": None,
        "mode": "persistent_profile",
        "details": "Not signed in yet. Click 'Sign In to Google' to sign in once."
    }

def create_driver(headless=False):
    """
    Initializes a resilient undetected Chrome instance equipped with stealth flags
    and automation masking.
    
    1. If Chrome is already running with remote debugging (--remote-debugging-port=9222),
       it attaches directly to that live, already signed-in browser.
    2. Otherwise, uses the persistent scraper profile (DataScraper_ChromeProfile)
       so any Google sign-in is permanently saved across all future scraper runs.
    """
    major_version = get_chrome_major_version()

    # 1. Check for live Chrome session on remote debugging port
    if is_remote_debugging_available(9222):
        safe_print("[Browser] Found active Chrome instance on remote debugging port 9222. Attaching directly...")
        try:
            options = uc.ChromeOptions()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = uc.Chrome(options=options)
            setattr(driver, "_is_remote_debug", True)
            safe_print("[Browser] Successfully attached to live Chrome session!")
            return driver
        except Exception as e:
            safe_print(f"[Browser] Notice attaching to port 9222: {e}. Falling back to persistent profile...")

    # 2. Use persistent scraper profile
    cleanup_lingering_scraper_chrome()
    profile_dir = get_scraper_profile_dir()
    safe_print(f"[Browser] Launching with persistent profile at: {profile_dir}")

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

    # Suppress permission popups
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "profile.default_content_setting_values.geolocation": 2
    }
    options.add_experimental_option("prefs", prefs)

    driver = None
    try:
        if major_version:
            driver = uc.Chrome(options=options, user_data_dir=profile_dir, version_main=major_version)
        else:
            driver = uc.Chrome(options=options, user_data_dir=profile_dir)
    except Exception as e:
        safe_print(f"[Browser] Notice on launch: {e}. Retrying clean profile instance...")
        cleanup_lingering_scraper_chrome()
        time.sleep(1.5)
        clean_opts = uc.ChromeOptions()
        if headless:
            clean_opts.add_argument("--headless=new")
        else:
            clean_opts.add_argument("--start-maximized")
        clean_opts.add_argument("--lang=en-US,en;q=0.9")
        clean_opts.add_argument("--disable-blink-features=AutomationControlled")
        if major_version:
            driver = uc.Chrome(options=clean_opts, user_data_dir=profile_dir, version_main=major_version)
        else:
            driver = uc.Chrome(options=clean_opts, user_data_dir=profile_dir)
    if driver is not None:
        setattr(driver, "_is_remote_debug", False)

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

def scrape_google_maps(keyword, city, target_count=100, progress_callback=None, stop_event=None, headless=False, existing_names=None, existing_phones=None, existing_name_city=None, driver=None):
    """
    Extracts verified Google Maps business listings (Name & Phone).
    Features:
      - In-place 'a.hfpxzc' click inspection: opens details side panel dynamically without full-page reloads
      - Geo-zone expansion across commercial localities
      - Anti-stall infinite scrolling with adaptive jiggling
      - Auto-detection & pause recovery if Google prompts CAPTCHA
      - Checks persistent SQLite memory to skip previously scraped leads across all sessions
    """
    clean_keyword = keyword.strip()
    clean_city = city.strip()
    target_count = max(1, int(target_count))

    queries = generate_search_queries(clean_keyword, clean_city, target_count=target_count)

    safe_print(f"\n[Google Maps Scraper] Starting search for '{clean_keyword}' in '{clean_city}'")
    safe_print(f"Target Leads: {target_count}")
    safe_print(f"Prepared {len(queries)} geographic zone queries to harvest maximum unique leads.")

    created_here = False
    if driver is None:
        created_here = True
        safe_print("Launching browser with anti-detection shielding, please wait...")
        driver = create_driver(headless)

    results = []
    seen_names = {normalize_for_dedup(n) for n in existing_names if n} if existing_names else set()
    seen_phones = {canonical_phone(p) for p in existing_phones if p} if existing_phones else set()
    seen_name_city = set(existing_name_city) if existing_name_city else set()
    skipped_memory_count = 0

    def notify(lead=None, query_info=""):
        if progress_callback:
            q_label = f"{query_info} [Skipped {skipped_memory_count} from memory]" if skipped_memory_count > 0 else query_info
            try:
                progress_callback(len(results), target_count, lead, q_label)
            except TypeError:
                try:
                    progress_callback(len(results), target_count, lead)
                except Exception:
                    pass

    try:
        query_queue = list(queries)
        seen_queries = set(query_queue)
        q_idx = 0

        while query_queue and len(results) < target_count:
            if stop_event and stop_event.is_set():
                safe_print("\nStop requested by user. Finalizing results...")
                break

            current_query = query_queue.pop(0)
            q_idx += 1
            query_encoded = current_query.replace(" ", "+")

            if q_idx > 1:
                time.sleep(random.uniform(1.0, 1.8))

            url = f"https://www.google.com/maps/search/{query_encoded}"
            safe_print(f"\n[{q_idx}] Google Maps Zone: \"{current_query}\" (Progress: {len(results)}/{target_count} leads)")

            try:
                driver.get(url)
                try:
                    WebDriverWait(driver, 8).until(
                        EC.any_of(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")),
                            EC.presence_of_element_located((By.CSS_SELECTOR, "a.hfpxzc")),
                            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'm6QErb') and contains(@aria-label, 'Results')]")),
                            EC.presence_of_element_located((By.XPATH, "//h1"))
                        )
                    )
                except Exception:
                    pass
                time.sleep(1.2)
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

            # Dismiss consent banner or One Tap overlay if shown
            try:
                driver.execute_script("""
                    var prompt = document.getElementById('credential_picker_container');
                    if (prompt) prompt.remove();
                    var iframes = document.querySelectorAll("iframe[src*='accounts.google.com/gsi']");
                    iframes.forEach(f => f.remove());
                """)
            except Exception:
                pass

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
                        norm_s = normalize_for_dedup(s_name)
                        c_lower = clean_city.lower()
                        if norm_s and norm_s not in seen_names and (norm_s, c_lower) not in seen_name_city:
                            s_phone = clean_phone_number(extract_phone_from_details(soup_single))
                            s_website = clean_website_url(extract_website_from_details(soup_single))
                            canon_p = canonical_phone(s_phone)
                            if s_phone and canon_p and canon_p not in seen_phones:
                                seen_names.add(norm_s)
                                seen_phones.add(canon_p)
                                seen_name_city.add((norm_s, c_lower))
                                lead = {
                                    "Business Name": s_name,
                                    "Phone Number": s_phone,
                                    "Website": s_website if s_website else "NA",
                                    "City": clean_city
                                }
                                results.append(lead)
                                db_memory.save_lead(lead, keyword=clean_keyword, city=clean_city, source="google")
                                safe_print(f"[{len(results)}/{target_count}] Single Place: {s_name} | Phone: {lead['Phone Number']} | Website: {lead['Website']} | City: {clean_city}")
                                notify(lead, current_query)
                            else:
                                safe_print(f"   -> Skipped single place '{s_name}': Duplicate or invalid phone number.")
                        else:
                            skipped_memory_count += 1
                            safe_print(f"   -> [Memory Skip] Single place '{s_name}': Already in memory.")
                except Exception:
                    pass
                continue

            # Stream Extraction: Scroll feed and inspect cards in-place
            retries = 0
            last_card_count = 0
            inspected_indices = set()

            js_extract_robust = """
                var res = { phone: '', website: '' };

                // 1. Phone extraction
                var telLink = document.querySelector("a[href^='tel:']");
                if (telLink) {
                    var h = (telLink.getAttribute('href') || '').replace(/^tel:/, '').trim();
                    var digits = h.replace(/\\D/g, '');
                    if (digits.length >= 7 && digits.length <= 15) res.phone = h;
                }
                if (!res.phone) {
                    var candidates = document.querySelectorAll("[data-item-id*='phone'], button[aria-label*='Phone'], a[aria-label*='Phone'], button[data-tooltip*='phone' i], [data-item-id^='phone:']");
                    for (var el of candidates) {
                        var attrs = [
                            el.getAttribute('data-item-id') || '',
                            el.getAttribute('aria-label') || '',
                            el.innerText || '',
                            el.getAttribute('href') || ''
                        ];
                        for (var val of attrs) {
                            var digits = val.replace(/\\D/g, '');
                            if (digits.length >= 7 && digits.length <= 15) {
                                res.phone = val;
                                break;
                            }
                        }
                        if (res.phone) break;
                    }
                }
                if (!res.phone) {
                    var allButtons = document.querySelectorAll("div[role='main'] button, div[role='main'] a, div.m6QErb button, div.m6QErb a");
                    for (var btn of allButtons) {
                        var aria = btn.getAttribute('aria-label') || '';
                        var txt = btn.innerText || '';
                        for (var s of [aria, txt]) {
                            var digits = s.replace(/\\D/g, '');
                            if (digits.length >= 10 && digits.length <= 13) {
                                res.phone = s;
                                break;
                            }
                        }
                        if (res.phone) break;
                    }
                }

                // 2. Website extraction
                // Check authority link (standard in Google Maps place panel)
                var authLink = document.querySelector("a[data-item-id='authority'], a[data-item-id*='authority']");
                if (authLink && authLink.href) {
                    res.website = authLink.href;
                }
                // Check aria-label / tooltip / data-value website links
                if (!res.website) {
                    var webLink = document.querySelector("a[aria-label*='Website' i], a[data-tooltip*='website' i], a[data-value='Website']");
                    if (webLink && webLink.href) {
                        res.website = webLink.href;
                    }
                }
                // Check links inside main details container
                if (!res.website) {
                    var mainPanel = document.querySelector("div[role='main'], div.m6QErb.DxyBCb, div.m6QErb");
                    if (mainPanel) {
                        var links = mainPanel.querySelectorAll("a[href^='http']");
                        for (var a of links) {
                            var aria = (a.getAttribute('aria-label') || '').toLowerCase();
                            var tip = (a.getAttribute('data-tooltip') || '').toLowerCase();
                            var txt = (a.innerText || '').toLowerCase();
                            var item = (a.getAttribute('data-item-id') || '').toLowerCase();
                            if (item.includes('authority') || aria.includes('website') || tip.includes('website') || txt.includes('website')) {
                                res.website = a.href;
                                break;
                            }
                        }
                    }
                }

                return res;
            """

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
                        all_links = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
                        if idx >= len(all_links):
                            break
                        link = all_links[idx]

                        name = link.get_attribute("aria-label") or ""
                        if not name:
                            continue

                        norm_name = normalize_for_dedup(name)
                        c_lower = clean_city.lower()

                        # Fast check against in-memory & SQLite cache before clicking
                        if norm_name in seen_names or (norm_name, c_lower) in seen_name_city:
                            skipped_memory_count += 1
                            if skipped_memory_count <= 5 or skipped_memory_count % 15 == 0:
                                safe_print(f"   -> [Memory Skip #{skipped_memory_count}] '{name}': Already collected in past session.")
                            continue

                        # Click card to open in-page details side panel
                        driver.execute_script("arguments[0].click();", link)

                        # Robust multi-attempt phone & website polling (waits for async place panel render)
                        phone = ""
                        website = "NA"
                        for _ in range(6):
                            time.sleep(0.25)
                            ext_data = driver.execute_script(js_extract_robust)
                            if isinstance(ext_data, dict):
                                raw_p = ext_data.get("phone", "")
                                raw_w = ext_data.get("website", "")
                            else:
                                raw_p = str(ext_data or "")
                                raw_w = ""
                            if not phone and raw_p:
                                phone = clean_phone_number(raw_p)
                            if website == "NA" and raw_w:
                                w_clean = clean_website_url(raw_w)
                                if w_clean != "NA":
                                    website = w_clean
                            if phone and website != "NA":
                                break
                            if phone:
                                # Quick extra 0.2s pause in case website element takes slightly longer to render
                                if website == "NA":
                                    time.sleep(0.2)
                                    ext2 = driver.execute_script(js_extract_robust)
                                    if isinstance(ext2, dict) and ext2.get("website"):
                                        w_clean2 = clean_website_url(ext2.get("website"))
                                        if w_clean2 != "NA":
                                            website = w_clean2
                                break

                        # Fallback: check if card itself has website chip before or after click
                        if website == "NA":
                            try:
                                card_elem = link.find_element(By.XPATH, "./ancestor::div[contains(@class, 'Nv2PK') or contains(@class, 'm6QErb')][1]")
                                card_web = card_elem.find_elements(By.XPATH, ".//a[@data-value='Website' or contains(@aria-label, 'Website') or contains(@data-tooltip, 'website')]")
                                if card_web:
                                    w_href = card_web[0].get_attribute("href")
                                    w_clean = clean_website_url(w_href)
                                    if w_clean != "NA":
                                        website = w_clean
                            except Exception:
                                pass

                        phone_clean = phone
                        canon_phone = canonical_phone(phone_clean)

                        # Do not collect leads without a valid phone number
                        if not phone_clean or not canon_phone:
                            safe_print(f"   -> Skipped '{name}': No phone number found.")
                            continue

                        # Prevent duplicate phone numbers across different listings or names, or from memory
                        if canon_phone in seen_phones or norm_name in seen_names or (norm_name, c_lower) in seen_name_city:
                            skipped_memory_count += 1
                            safe_print(f"   -> [Memory Skip #{skipped_memory_count}] '{name}': Phone ({phone_clean}) or name already saved previously.")
                            seen_phones.add(canon_phone)
                            seen_names.add(norm_name)
                            seen_name_city.add((norm_name, c_lower))
                            continue

                        seen_phones.add(canon_phone)
                        seen_names.add(norm_name)
                        seen_name_city.add((norm_name, c_lower))

                        # Clean display name (strip trailing promotional / keyword stuffing noise)
                        display_name = re.sub(r'\s*[\-|–|—|\|]\s*(?:best|top|famous|cheap|popular|weddingz|fully ac).*$', '', name, flags=re.I).strip()
                        if not display_name:
                            display_name = name

                        lead = {
                            "Business Name": display_name,
                            "Phone Number": phone_clean,
                            "Website": website if website else "NA",
                            "City": clean_city
                        }
                        results.append(lead)

                        # Persist immediately to SQLite memory
                        db_memory.save_lead(lead, keyword=clean_keyword, city=clean_city, source="google")

                        safe_print(f"[{len(results)}/{target_count}] {display_name} | Phone: {lead['Phone Number']} | Website: {lead['Website']} | City: {clean_city}")
                        notify(lead, current_query)

                    except Exception:
                        continue

                if len(results) >= target_count or retries >= 6:
                    break

                # Trigger Google Maps infinite scroll to append the next batch of cards
                try:
                    human_smooth_scroll(driver, feed_element, direction="down")
                except Exception:
                    pass

                src_lower = driver.page_source.lower()
                if "you've reached the end of the list" in src_lower or "end of results" in src_lower:
                    safe_print("   -> Reached end of listings for this zone.")
                    break

            # If query queue runs dry before target is reached, trigger Pass 2 / Pass 3 / Pass 4 deep expansion!
            if not query_queue and len(results) < target_count and not (stop_event and stop_event.is_set()):
                safe_print(f"\n[Google Maps Pass 2] Collected {len(results)}/{target_count}. Triggering deep postal and sub-area expansion...")
                more_queries = generate_search_queries(clean_keyword, clean_city, target_count=target_count, pass_num=2)
                for mq in more_queries:
                    if mq not in seen_queries:
                        query_queue.append(mq)
                        seen_queries.add(mq)

            if not query_queue and len(results) < target_count and not (stop_event and stop_event.is_set()):
                safe_print(f"\n[Google Maps Pass 3] Collected {len(results)}/{target_count}. Triggering ultra-deep specialty and landmark expansion...")
                pass3_queries = generate_search_queries(clean_keyword, clean_city, target_count=target_count, pass_num=3)
                for pq in pass3_queries:
                    if pq not in seen_queries:
                        query_queue.append(pq)
                        seen_queries.add(pq)

            if not query_queue and len(results) < target_count and not (stop_event and stop_event.is_set()):
                safe_print(f"\n[Google Maps Pass 4] Collected {len(results)}/{target_count}. Triggering wide geographic corridor expansion...")
                pass4_queries = generate_search_queries(clean_keyword, clean_city, target_count=target_count, pass_num=4)
                for pq in pass4_queries:
                    if pq not in seen_queries:
                        query_queue.append(pq)
                        seen_queries.add(pq)

        safe_print(f"\n[Google Maps Complete] Total extracted for '{clean_city}': {len(results)} unique leads.")

    except Exception as e:
        safe_print(f"\nGoogle Maps scraping notice: {e}")
    finally:
        if created_here and driver:
            if getattr(driver, "_is_remote_debug", False):
                safe_print("[Browser] Scrape finished. Detaching from live Chrome session without closing.")
            else:
                try:
                    driver.__del__ = lambda: None
                except Exception:
                    pass
                try:
                    driver.quit()
                except Exception:
                    pass

    return results

def scrape_bing_maps(keyword, city, target_count=100, progress_callback=None, stop_event=None, headless=False, existing_names=None, existing_phones=None, existing_name_city=None, queries=None, driver=None):
    """
    Alternative resilient business scraper powered by Bing Maps.
    Features:
      - Zero CAPTCHA / rate-limit restrictions
      - Direct extraction of verified phone numbers embedded in data-entity JSON
      - Geographic multi-zone queue iteration guaranteeing high-volume yield
      - Rapid scrolling and pagination across city listings
      - Checks persistent SQLite memory to skip previously scraped leads across all sessions
    """
    clean_keyword = keyword.strip()
    clean_city = city.strip()
    target_count = max(1, int(target_count))

    if queries is None:
        queries = generate_search_queries(clean_keyword, clean_city, target_count=target_count, pass_num=1)

    safe_print(f"\n[Bing Maps Scraper] Searching for '{clean_keyword}' in '{clean_city}'")
    safe_print(f"Target Leads: {target_count}")
    safe_print(f"Prepared {len(queries)} geographic zone queries for Bing Maps.")

    created_here = False
    if driver is None:
        created_here = True
        safe_print("Launching browser, please wait...")
        driver = create_driver(headless)

    results = []
    seen_names = {normalize_for_dedup(n) for n in existing_names if n} if existing_names else set()
    seen_phones = {canonical_phone(p) for p in existing_phones if p} if existing_phones else set()
    seen_name_city = set(existing_name_city) if existing_name_city else set()
    skipped_memory_count = 0

    try:
        query_queue = list(queries)
        seen_queries = set(query_queue)
        q_idx = 0

        while query_queue and len(results) < target_count:
            if stop_event and stop_event.is_set():
                safe_print("\nStop requested by user. Finalizing Bing results...")
                break

            current_query = query_queue.pop(0)
            q_idx += 1
            query_encoded = current_query.replace(" ", "+")
            url = f"https://www.bing.com/maps?q={query_encoded}"

            safe_print(f"\n[{q_idx}] Bing Maps Zone: \"{current_query}\" (Progress: {len(results)}/{target_count} leads)")

            try:
                driver.get(url)
                time.sleep(random.uniform(2.5, 3.8))
            except Exception as e:
                safe_print(f"Error loading {current_query}: {e}")
                continue

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
                    website = "NA"

                    # 1. Embedded data-entity JSON
                    data_attr = card.get("data-entity")
                    if data_attr:
                        try:
                            data_obj = json.loads(data_attr)
                            ent = data_obj.get("entity", {})
                            name = ent.get("title", "").strip()
                            phone = ent.get("phone", "").strip()
                            raw_w = ent.get("website") or ent.get("url") or ent.get("websiteUrl") or ent.get("officialWebsite") or ""
                            if raw_w:
                                w_clean = clean_website_url(raw_w)
                                if w_clean != "NA":
                                    website = w_clean
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

                    # 4. Fallback website from card HTML
                    if website == "NA":
                        web_elem = card.find("a", attrs={"title": re.compile(r"website", re.I)}) or \
                                   card.find("a", attrs={"aria-label": re.compile(r"website", re.I)}) or \
                                   card.find("a", string=re.compile(r"^\s*website\s*$", re.I)) or \
                                   card.find("a", class_=re.compile(r"bm_action|website|b_anchor", re.I))
                        if web_elem and web_elem.get("href"):
                            w_clean = clean_website_url(web_elem.get("href"))
                            if w_clean != "NA":
                                website = w_clean

                    if not name:
                        continue

                    norm_name = normalize_for_dedup(name)
                    c_lower = clean_city.lower()
                    if not norm_name or norm_name in seen_names or (norm_name, c_lower) in seen_name_city:
                        skipped_memory_count += 1
                        continue

                    phone_clean = clean_phone_number(phone)
                    canon_phone = canonical_phone(phone_clean)

                    # Do not collect leads without a valid phone number
                    if not phone_clean or not canon_phone:
                        continue

                    if canon_phone in seen_phones or norm_name in seen_names or (norm_name, c_lower) in seen_name_city:
                        skipped_memory_count += 1
                        seen_names.add(norm_name)
                        seen_phones.add(canon_phone)
                        seen_name_city.add((norm_name, c_lower))
                        continue

                    seen_names.add(norm_name)
                    seen_phones.add(canon_phone)
                    seen_name_city.add((norm_name, c_lower))

                    lead = {
                        "Business Name": name,
                        "Phone Number": phone_clean,
                        "Website": website if website else "NA",
                        "City": clean_city
                    }
                    results.append(lead)

                    # Persist immediately to SQLite memory
                    db_memory.save_lead(lead, keyword=clean_keyword, city=clean_city, source="bing")

                    extracted += 1
                    safe_print(f"[Bing] [{len(results)}/{target_count}] {name} | Phone: {lead['Phone Number']} | Website: {lead['Website']} | City: {clean_city}")
                    if progress_callback:
                        q_label = f"Bing: {current_query} (Skipped {skipped_memory_count} from memory)" if skipped_memory_count > 0 else f"Bing: {current_query}"
                        try:
                            progress_callback(len(results), target_count, lead, q_label)
                        except TypeError:
                            progress_callback(len(results), target_count, lead)

                return extracted

            # Extract initial listings
            extract_cards_from_page()

            # Fast pagination & scroll within this zone
            retries = 0
            for _ in range(8):
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
                time.sleep(random.uniform(1.4, 2.2))

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
                            time.sleep(2.5)
                            extract_cards_from_page()
                            continue
                    except Exception:
                        pass

                    if retries >= 2:
                        break

            # If query queue runs dry before target is reached, trigger Pass 2 / Pass 3 / Pass 4 deep expansion!
            if not query_queue and len(results) < target_count and not (stop_event and stop_event.is_set()):
                safe_print(f"\n[Bing Maps Pass 2] Collected {len(results)}/{target_count}. Triggering deep postal and sub-area expansion...")
                more_queries = generate_search_queries(clean_keyword, clean_city, target_count=target_count, pass_num=2)
                for mq in more_queries:
                    if mq not in seen_queries:
                        query_queue.append(mq)
                        seen_queries.add(mq)

            if not query_queue and len(results) < target_count and not (stop_event and stop_event.is_set()):
                safe_print(f"\n[Bing Maps Pass 3] Collected {len(results)}/{target_count}. Triggering ultra-deep specialty expansion...")
                pass3_queries = generate_search_queries(clean_keyword, clean_city, target_count=target_count, pass_num=3)
                for pq in pass3_queries:
                    if pq not in seen_queries:
                        query_queue.append(pq)
                        seen_queries.add(pq)

            if not query_queue and len(results) < target_count and not (stop_event and stop_event.is_set()):
                safe_print(f"\n[Bing Maps Pass 4] Collected {len(results)}/{target_count}. Triggering wide geographic corridor expansion...")
                pass4_queries = generate_search_queries(clean_keyword, clean_city, target_count=target_count, pass_num=4)
                for pq in pass4_queries:
                    if pq not in seen_queries:
                        query_queue.append(pq)
                        seen_queries.add(pq)

        safe_print(f"\n[Bing Maps Complete] Total extracted: {len(results)} unique leads.")

    except Exception as e:
        safe_print(f"Bing Maps scraping notice: {e}")
    finally:
        if created_here and driver:
            if getattr(driver, "_is_remote_debug", False):
                safe_print("[Browser] Scrape finished. Detaching from live Chrome session without closing.")
            else:
                try:
                    driver.__del__ = lambda: None
                except Exception:
                    pass
                try:
                    driver.quit()
                except Exception:
                    pass

    return results

def _scrape_single_city(keyword, city, target_count=100, source="all", progress_callback=None, stop_event=None, headless=False, driver=None, existing_names=None, existing_phones=None, existing_name_city=None):
    """
    Lead generator for a single city entity. Supports engine routing,
    fallback between Google and Bing, and shared driver pass-through.
    """
    target_count = max(1, min(500, int(target_count)))
    source = (source or "all").lower()

    if source == "bing":
        leads = scrape_bing_maps(
            keyword=keyword,
            city=city,
            target_count=target_count,
            progress_callback=progress_callback,
            stop_event=stop_event,
            headless=headless,
            existing_names=existing_names,
            existing_phones=existing_phones,
            existing_name_city=existing_name_city,
            driver=driver
        )
        return deduplicate_leads(leads)[:target_count]
    elif source == "google":
        leads = scrape_google_maps(
            keyword=keyword,
            city=city,
            target_count=target_count,
            progress_callback=progress_callback,
            stop_event=stop_event,
            headless=headless,
            existing_names=existing_names,
            existing_phones=existing_phones,
            existing_name_city=existing_name_city,
            driver=driver
        )
        all_leads = deduplicate_leads(leads)
        if len(all_leads) < target_count and not (stop_event and stop_event.is_set()):
            remaining = target_count - len(all_leads)
            safe_print(f"\n========================================================")
            safe_print(f"[Target Guarantee] Google Maps reached available capacity ({len(all_leads)}/{target_count} leads in '{city}').")
            safe_print(f"Auto-activating secondary engine to fulfill remaining {remaining} leads...")
            safe_print(f"========================================================\n")
            current_names = set(existing_names or set()) | {normalize_for_dedup(l["Business Name"]) for l in all_leads if l.get("Business Name")}
            current_phones = set(existing_phones or set()) | {canonical_phone(l["Phone Number"]) for l in all_leads if l.get("Phone Number") and l["Phone Number"] not in ["Not available", "N/A"]}
            current_name_city = set(existing_name_city or set()) | {(normalize_for_dedup(l["Business Name"]), city.lower()) for l in all_leads if l.get("Business Name")}

            def google_fallback_callback(count, total, lead, q_info=""):
                if progress_callback:
                    current_total = len(all_leads) + count
                    try:
                        progress_callback(min(current_total, target_count), target_count, lead, q_info)
                    except TypeError:
                        progress_callback(min(current_total, target_count), target_count, lead)

            b_leads = scrape_bing_maps(
                keyword=keyword,
                city=city,
                target_count=remaining,
                progress_callback=google_fallback_callback,
                stop_event=stop_event,
                headless=headless,
                existing_names=current_names,
                existing_phones=current_phones,
                existing_name_city=current_name_city,
                driver=driver
            )
            all_leads = deduplicate_leads(all_leads + b_leads)
        return all_leads[:target_count]
    else:
        # Multi-Engine Mode: Harvest Google Maps first, then Bing Maps for guaranteed 100% target fulfillment
        safe_print(f"\n========================================================")
        safe_print(f"[Multi-Engine Scraper] Target: {target_count} leads for '{keyword}' in '{city}'")
        safe_print(f"Stage 1: Harvesting Google Maps with in-page side panel inspection...")
        safe_print(f"========================================================\n")

        g_leads = scrape_google_maps(
            keyword=keyword,
            city=city,
            target_count=target_count,
            progress_callback=progress_callback,
            stop_event=stop_event,
            headless=headless,
            existing_names=existing_names,
            existing_phones=existing_phones,
            existing_name_city=existing_name_city,
            driver=driver
        )

        all_leads = deduplicate_leads(g_leads)
        if len(all_leads) >= target_count or (stop_event and stop_event.is_set()):
            safe_print(f"\n[Stage 1 Complete] Google Maps delivered {len(all_leads)} leads (Target: {target_count}).")
            return all_leads[:target_count]

        remaining = target_count - len(all_leads)
        safe_print(f"\n========================================================")
        safe_print(f"Stage 2: Google Maps provided {len(all_leads)} leads in '{city}'. Seamlessly switching to Bing Maps for remaining {remaining} leads...")
        safe_print(f"========================================================\n")

        current_names = set(existing_names or set()) | {normalize_for_dedup(l["Business Name"]) for l in all_leads if l.get("Business Name")}
        current_phones = set(existing_phones or set()) | {canonical_phone(l["Phone Number"]) for l in all_leads if l.get("Phone Number") and l["Phone Number"] not in ["Not available", "N/A"]}
        current_name_city = set(existing_name_city or set()) | {(normalize_for_dedup(l["Business Name"]), city.lower()) for l in all_leads if l.get("Business Name")}

        def bing_callback(count, total, lead, q_info=""):
            if progress_callback:
                current_total = len(all_leads) + count
                try:
                    progress_callback(min(current_total, target_count), target_count, lead, q_info)
                except TypeError:
                    progress_callback(min(current_total, target_count), target_count, lead)

        b_leads = scrape_bing_maps(
            keyword=keyword,
            city=city,
            target_count=remaining,
            progress_callback=bing_callback,
            stop_event=stop_event,
            headless=headless,
            existing_names=current_names,
            existing_phones=current_phones,
            existing_name_city=current_name_city,
            driver=driver
        )

        all_leads = deduplicate_leads(all_leads + b_leads)
        safe_print(f"\n[Stage 2 Complete] Current total in '{city}': {len(all_leads)}/{target_count} leads ({len(g_leads)} from Google, {len(b_leads)} from Bing).")

        # Stage 3: Deep Pass Guarantee if still under target
        if len(all_leads) < target_count and not (stop_event and stop_event.is_set()):
            remaining_deep = target_count - len(all_leads)
            safe_print(f"\n========================================================")
            safe_print(f"Stage 3: Deep Pass Expansion for remaining {remaining_deep} leads in '{city}'...")
            safe_print(f"========================================================\n")
            deep_names = set(existing_names or set()) | {normalize_for_dedup(l["Business Name"]) for l in all_leads if l.get("Business Name")}
            deep_phones = set(existing_phones or set()) | {canonical_phone(l["Phone Number"]) for l in all_leads if l.get("Phone Number") and l["Phone Number"] not in ["Not available", "N/A"]}
            deep_name_city = set(existing_name_city or set()) | {(normalize_for_dedup(l["Business Name"]), city.lower()) for l in all_leads if l.get("Business Name")}
            deep_queries = (
                generate_search_queries(keyword, city, target_count=target_count, pass_num=2) +
                generate_search_queries(keyword, city, target_count=target_count, pass_num=3) +
                generate_search_queries(keyword, city, target_count=target_count, pass_num=4)
            )

            deep_leads = scrape_bing_maps(
                keyword=keyword,
                city=city,
                target_count=remaining_deep,
                progress_callback=bing_callback,
                stop_event=stop_event,
                headless=headless,
                existing_names=deep_names,
                existing_phones=deep_phones,
                existing_name_city=deep_name_city,
                queries=deep_queries,
                driver=driver
            )
            all_leads = deduplicate_leads(all_leads + deep_leads)

        final_leads = all_leads[:target_count]
        safe_print(f"\n[City Scrape Complete] Delivered {len(final_leads)} verified leads for '{city}' (Target: {target_count}).")
        return final_leads

def scrape_leads(keyword, city, target_count=100, source="all", progress_callback=None, stop_event=None, headless=False, skip_memory=True):
    """
    Master Lead Generation Router.
    Supports targeting multiple cities separated by comma (up to 4 cities at a time).
    Example: 'Patna, Arrah, Muzaffarpur'
    `target_count` specifies the leads limit per city (max 500 per city).
    For example: 200 leads limit with 3 cities targets up to 600 total leads.
    `skip_memory` (default True): automatically checks persistent SQLite memory and skips any
    leads previously scraped across past runs or app restarts, guaranteeing fresh leads every time.
    """
    per_city_target = max(1, min(500, int(target_count)))
    source = (source or "all").lower()

    # Preload persistent memory cache for high-speed deduplication across restarts
    known_phones, known_names, known_name_city = db_memory.get_known_identifiers() if skip_memory else (set(), set(), set())
    if skip_memory and (known_phones or known_names):
        safe_print(f"\n========================================================")
        safe_print(f"[Lead Memory Active] {len(known_phones)} past leads loaded from database.")
        safe_print(f"Any matching listings will be automatically skipped to guarantee NEW leads.")
        safe_print(f"========================================================\n")

    cities = parse_cities(city, max_cities=4)
    if not cities:
        safe_print("No valid target cities provided.")
        return []

    # Single-city fast path: No extra browser wrapping needed
    if len(cities) == 1:
        return _scrape_single_city(
            keyword=keyword,
            city=cities[0],
            target_count=per_city_target,
            source=source,
            progress_callback=progress_callback,
            stop_event=stop_event,
            headless=headless,
            existing_names=set(known_names),
            existing_phones=set(known_phones),
            existing_name_city=set(known_name_city)
        )

    # Multi-City Mode (2 to 4 cities): per-city target * number of cities
    total_target = per_city_target * len(cities)
    city_summary = ", ".join(cities)
    safe_print(f"\n========================================================")
    safe_print(f"[Multi-City Harvester] Targeting {len(cities)} cities: {city_summary}")
    safe_print(f"Goal: {per_city_target} leads per city (Up to {total_target} total leads for '{keyword}')")
    safe_print(f"========================================================\n")

    driver = create_driver(headless)
    all_leads = []
    seen_names = set(known_names)
    seen_phones = set(known_phones)
    seen_name_city = set(known_name_city)

    try:
        for idx, current_city in enumerate(cities):
            if stop_event and stop_event.is_set():
                safe_print("\nStop requested by user. Finalizing multi-city collection...")
                break

            safe_print(f"\n>>> [City {idx+1}/{len(cities)}] Harvesting up to {per_city_target} leads from '{current_city}' (Current Global Leads: {len(all_leads)}/{total_target})")

            def city_progress(count, total, lead, q_info=""):
                if progress_callback:
                    current_total = len(all_leads) + count
                    info_prefix = f"[{current_city}] ({count}/{per_city_target}) "
                    display_info = f"{info_prefix}{q_info}" if q_info else f"[{current_city}] Harvesting ({count}/{per_city_target})"
                    try:
                        progress_callback(current_total, total_target, lead, display_info)
                    except TypeError:
                        progress_callback(current_total, total_target, lead)

            city_leads = _scrape_single_city(
                keyword=keyword,
                city=current_city,
                target_count=per_city_target,
                source=source,
                progress_callback=city_progress,
                stop_event=stop_event,
                headless=headless,
                driver=driver,
                existing_names=seen_names,
                existing_phones=seen_phones,
                existing_name_city=seen_name_city
            )

            new_in_city = 0
            c_norm = current_city.lower()
            for l in city_leads:
                n_norm = normalize_for_dedup(l.get("Business Name"))
                p_canon = canonical_phone(l.get("Phone Number"))
                if n_norm and p_canon and n_norm not in seen_names and p_canon not in seen_phones and (n_norm, c_norm) not in seen_name_city:
                    seen_names.add(n_norm)
                    seen_phones.add(p_canon)
                    seen_name_city.add((n_norm, c_norm))
                    all_leads.append(l)
                    new_in_city += 1

            safe_print(f">>> [City {idx+1}/{len(cities)} '{current_city}' Finished] Collected {new_in_city} NEW leads from '{current_city}'. Global total now: {len(all_leads)} leads.")
            if new_in_city < per_city_target and not (stop_event and stop_event.is_set()):
                safe_print(f"    (Note: '{current_city}' yielded {new_in_city}/{per_city_target} leads. Proceeding immediately to next selected city...)")

        safe_print(f"\n[Multi-City Complete] Successfully delivered {len(all_leads)} verified unique leads across {len(cities)} cities.")
        return all_leads

    finally:
        if driver:
            if getattr(driver, "_is_remote_debug", False):
                safe_print("[Browser] Multi-city run complete. Detaching from remote Chrome session.")
            else:
                try:
                    driver.__del__ = lambda: None
                except Exception:
                    pass
                try:
                    driver.quit()
                except Exception:
                    pass

def main():
    print("\n==============================")
    print("BUSINESS LEAD SCRAPER (NAME, PHONE & WEBSITE)")
    print("==============================\n")
    keyword = input("Enter Business Keyword (e.g., Restaurants): ").strip()
    city = input("Enter City (or up to 4 cities separated by comma, e.g. Patna, Gaya): ").strip()
    leads_str = input("Enter Number of Leads to Scrape per City (default 100, max 500): ").strip()
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
        col_order = ["Business Name", "Phone Number", "Website", "City"]
        df = pd.DataFrame(data)
        ordered_cols = [c for c in col_order if c in df.columns] + [c for c in df.columns if c not in col_order]
        df = df[ordered_cols]
        clean_kw = re.sub(r'[^a-zA-Z0-9]', '_', keyword.strip()).lower()
        cities = parse_cities(city, max_cities=4)
        clean_ct = "_".join([re.sub(r'[^a-zA-Z0-9]', '', c).lower() for c in cities])
        date_str = datetime.now().strftime("%Y-%m-%d")
        base_name = f"leads_{clean_kw}_{clean_ct}_{date_str}"
        output_file = f"{base_name}.csv"
        if os.path.exists(output_file):
            time_str = datetime.now().strftime("%H%M%S")
            output_file = f"{base_name}_{time_str}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        safe_print(f"\nSuccess! Exported {len(data)} leads to: {output_file}")
    else:
        safe_print("\nNo data was extracted. Please try a different search.")

if __name__ == "__main__":
    main()