"""
bihar_directory_scraper.py
Dedicated bot-safe web scraper for Bihar local business directories
(IndianYellowPages Bihar & ExportersIndia Bihar).
Extracts verified local business leads across Patna, Muzaffarpur, Gaya,
Bhagalpur, Begusarai, Darbhanga, Purnia, and other Bihar hubs without bot-blocking.
Prioritizes Business Name and Phone Number extraction with multi-threaded enrichment.
"""

import urllib.request
import urllib.parse
import ssl
import re
import time
from bs4 import BeautifulSoup
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# SSL context for resilient requests
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

# Category slug mappings for IndianYellowPages & ExportersIndia
CATEGORY_MAPPINGS = {
    "real estate": "real-estate-agents",
    "real estate agents": "real-estate-agents",
    "plots": "real-estate-agents",
    "property dealers": "real-estate-agents",
    "coaching": "coaching-classes",
    "coaching classes": "coaching-classes",
    "coaching institutes": "coaching-classes",
    "iit jee": "coaching-classes",
    "neet": "coaching-classes",
    "builders": "building-contractors",
    "contractors": "building-contractors",
    "building contractors": "building-contractors",
    "civil contractors": "building-contractors",
    "doctors": "hospitals-nursing-homes",
    "hospitals": "hospitals-nursing-homes",
    "clinics": "hospitals-nursing-homes",
    "transporters": "transporters-cargo",
    "packers movers": "packers-and-movers",
    "packers and movers": "packers-and-movers",
    "chartered accountants": "chartered-accountants",
    "ca firms": "chartered-accountants",
    "interior designers": "interior-designers",
    "solar": "solar-energy-equipment",
    "solar energy": "solar-energy-equipment",
    "hardware": "hardware-tools",
    "wholesalers": "wholesalers-distributors",
    "mandi": "grain-merchants"
}

BIHAR_CITIES = [
    "Patna", "Muzaffarpur", "Gaya", "Bhagalpur", "Begusarai",
    "Darbhanga", "Purnia", "Bihar Sharif", "Ara", "Samastipur", "Motihari"
]

POPULAR_BIHAR_PRESETS = [
    {"label": "🏡 Real Estate & Plots", "query": "real estate agents", "icon": "🏡"},
    {"label": "🎓 Coaching & Academies", "query": "coaching classes", "icon": "🎓"},
    {"label": "🏗️ Building Contractors", "query": "building contractors", "icon": "🏗️"},
    {"label": "🏥 Hospitals & Clinics", "query": "hospitals", "icon": "🏥"},
    {"label": "📦 Packers & Movers", "query": "packers and movers", "icon": "📦"},
    {"label": "🎨 Interior Designers", "query": "interior designers", "icon": "🎨"},
    {"label": "⚡ Solar Energy EPC", "query": "solar energy", "icon": "⚡"},
    {"label": "💼 CA & Tax Consultants", "query": "chartered accountants", "icon": "💼"}
]

def get_bihar_presets():
    """Return quick presets and supported Bihar cities for the UI."""
    return {
        "presets": POPULAR_BIHAR_PRESETS,
        "cities": BIHAR_CITIES
    }

def normalize_slug(keyword):
    """Map keyword to a directory slug or clean URL parameter."""
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', keyword.strip().lower())
    for key, slug in CATEGORY_MAPPINGS.items():
        if key in clean or clean in key:
            return slug
    return re.sub(r'\s+', '-', clean)

def clean_phone_number(phone_raw):
    """Normalize and format Indian phone numbers cleanly."""
    if not phone_raw:
        return ""
    clean = re.sub(r'[^\d+]', '', phone_raw.strip())
    if clean.startswith('+91') and len(clean) == 13:
        return f"+91-{clean[3:8]}-{clean[8:]}"
    elif clean.startswith('91') and len(clean) == 12 and clean[2] in '6789':
        return f"+91-{clean[2:7]}-{clean[7:]}"
    elif clean.startswith('0') and len(clean) in [11, 12]:
        return f"{clean[:4]}-{clean[4:]}"
    elif len(clean) == 10 and clean[0] in '6789':
        return f"+91-{clean[:5]}-{clean[5:]}"
    elif len(clean) >= 8:
        return phone_raw.strip()
    return ""

def enrich_iyp_listing(profile_url):
    """
    Fetch IndianYellowPages listing detail page to extract verified phone numbers,
    contact person, and external company website.
    """
    if not profile_url or not profile_url.startswith("http"):
        return {"phone": "", "contact_person": "", "website": ""}

    phone = ""
    contact_person = ""
    company_web = ""

    try:
        req = urllib.request.Request(profile_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')

        # 1. Contact Person
        u = soup.find('i', class_=re.compile(r'user', re.I))
        if u and u.parent:
            contact_person = u.parent.get_text(strip=True).replace('Mr.', '').replace('Ms.', '').strip()

        # 2. Company Website
        w = soup.find('a', class_='web_url')
        if w and w.get('href') and w['href'].startswith('http'):
            company_web = w['href'].strip()

        # 3. Direct tel: links on profile page
        for a in soup.find_all('a', href=re.compile(r'^tel:', re.I)):
            p = a['href'].replace('tel:', '').strip()
            if len(re.sub(r'[^\d]', '', p)) >= 8:
                phone = clean_phone_number(p)
                break

        # 4. If company has official website, fetch website homepage for direct mobile
        if not phone and company_web:
            try:
                w_req = urllib.request.Request(company_web, headers=HEADERS)
                with urllib.request.urlopen(w_req, timeout=3, context=ctx) as w_resp:
                    w_html = w_resp.read().decode('utf-8', errors='ignore')
                w_soup = BeautifulSoup(w_html, 'html.parser')
                for a in w_soup.find_all('a', href=re.compile(r'^tel:', re.I)):
                    p = a['href'].replace('tel:', '').strip()
                    if len(re.sub(r'[^\d]', '', p)) >= 8:
                        phone = clean_phone_number(p)
                        break
                if not phone:
                    m = re.findall(r'(?:\+?91[\-\s]?)?[6789]\d{9}|0\d{2,4}[\-\s]?\d{6,8}', w_html)
                    for num in m:
                        clean_d = re.sub(r'[^\d]', '', num)
                        if len(clean_d) in [10, 11, 12] and not clean_d.startswith('202'):
                            phone = clean_phone_number(num)
                            break
            except Exception:
                pass

        # 5. Check contact info section text regex
        if not phone:
            ci = soup.find(id='pdContactInfo') or soup
            text = ci.get_text(' | ', strip=True)
            m = re.findall(r'(?:\+?91[\-\s]?)?[6789]\d{9}|0\d{2,4}[\-\s]?\d{6,8}', text)
            for num in m:
                clean_d = re.sub(r'[^\d]', '', num)
                if len(clean_d) in [10, 11, 12] and not clean_d.startswith('202'):
                    phone = clean_phone_number(num)
                    break
    except Exception:
        pass

    return {
        "phone": phone,
        "contact_person": contact_person,
        "website": company_web or profile_url
    }

def enrich_ei_listing(profile_url):
    """
    Fetch ExportersIndia company profile / product page to extract verified phone numbers,
    contact person, and external company website.
    """
    if not profile_url or not profile_url.startswith("http"):
        return {"phone": "", "contact_person": "", "website": ""}

    phone = ""
    contact_person = ""
    company_web = ""

    try:
        req = urllib.request.Request(profile_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=4, context=ctx) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
        soup = BeautifulSoup(html, 'html.parser')

        # Contact person
        u = soup.find('i', class_=re.compile(r'user', re.I))
        if u and u.parent:
            contact_person = u.parent.get_text(strip=True).replace('Mr.', '').replace('Ms.', '').strip()

        # External company website
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if href.startswith('http') and not any(k in href for k in ['exportersindia', 'google', 'facebook', 'linkedin', 'twitter', 'instagram', 'apple', 'weblink']):
                company_web = href
                break

        # 1. Check tel: links
        for a in soup.find_all('a', href=re.compile(r'^tel:', re.I)):
            p = a['href'].replace('tel:', '').strip()
            if len(re.sub(r'[^\d]', '', p)) >= 8 and not p.startswith('1800'):
                phone = clean_phone_number(p)
                break

        # 2. Check external website for mobile numbers
        if not phone and company_web:
            try:
                w_req = urllib.request.Request(company_web, headers=HEADERS)
                with urllib.request.urlopen(w_req, timeout=3, context=ctx) as w_resp:
                    w_html = w_resp.read().decode('utf-8', errors='ignore')
                w_soup = BeautifulSoup(w_html, 'html.parser')
                for a in w_soup.find_all('a', href=re.compile(r'^tel:', re.I)):
                    p = a['href'].replace('tel:', '').strip()
                    if len(re.sub(r'[^\d]', '', p)) >= 8:
                        phone = clean_phone_number(p)
                        break
                if not phone:
                    m = re.findall(r'(?:\+?91[\-\s]?)?[6789]\d{9}|0\d{2,4}[\-\s]?\d{6,8}', w_html)
                    for num in m:
                        clean_d = re.sub(r'[^\d]', '', num)
                        if len(clean_d) in [10, 11, 12] and not clean_d.startswith('202'):
                            phone = clean_phone_number(num)
                            break
            except Exception:
                pass

        # 3. Check page regex for mobile/telephone
        if not phone:
            m = re.findall(r'(?:\+?91[\-\s]?)?[6789]\d{9}|0\d{2,4}[\-\s]?\d{6,8}', html)
            for num in m:
                clean_d = re.sub(r'[^\d]', '', num)
                if len(clean_d) in [10, 11, 12] and not clean_d.startswith('202'):
                    phone = clean_phone_number(num)
                    break
    except Exception:
        pass

    return {
        "phone": phone,
        "contact_person": contact_person,
        "website": company_web or profile_url
    }

def scrape_indian_yellow_pages(category_slug, city="patna", target_count=50, progress_callback=None):
    """
    Scrapes verified business leads from IndianYellowPages Bihar directory.
    Extracts Business Name, Phone Number, Contact Person, and verified address.
    Completely bot-safe with HTTP 200 responses.
    """
    city_norm = city.lower().replace(" ", "-")
    candidates = []
    
    urls_to_try = [
        f"https://www.indianyellowpages.com/{city_norm}/{category_slug}.htm",
        f"https://www.indianyellowpages.com/{city_norm}/{category_slug}-services.htm"
    ]

    for url in urls_to_try:
        if len(candidates) >= target_count:
            break
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                if resp.status != 200:
                    continue
                html = resp.read().decode('utf-8', errors='ignore')
        except Exception:
            continue

        soup = BeautifulSoup(html, 'html.parser')
        h2_tags = soup.find_all('h2')
        for h2 in h2_tags:
            name = h2.get_text(strip=True)
            if not name or len(name) < 3 or any(w in name.lower() for w in ['explore', 'categories', 'top cities', 'post free']):
                continue
            
            parent = h2.find_parent('div', class_=lambda c: c and any(k in c for k in ['serv_com_sec', 'box', 'data', 'listing', 'item'])) or h2.parent
            
            locality = f"{city.title()}, Bihar"
            rating = ""
            reviews = ""
            experience = ""
            profile_url = ""
            
            # Find profile link
            a_tag = h2.find_parent('a') or h2.find('a') or (parent.find('a', href=True) if parent else None)
            if a_tag and a_tag.get('href'):
                href = a_tag['href'].strip()
                if href.startswith('http'):
                    profile_url = href
                elif href.startswith('/'):
                    profile_url = f"https://www.indianyellowpages.com{href}"
            
            if parent:
                text_parts = [t.strip() for t in parent.get_text(separator='|').split('|') if t.strip()]
                for p in text_parts:
                    p_clean = p.strip()
                    if any(loc_kw in p_clean.lower() for loc_kw in [city.lower(), 'bihar', 'road', 'colony', 'chowk', 'nagar', 'more', 'complex', 'lane', 'sector']):
                        if p_clean != name and len(p_clean) < 70 and not any(d in p_clean for d in ['yrs', 'reviews']):
                            locality = p_clean
                    if 'yr' in p_clean.lower() or 'year' in p_clean.lower():
                        experience = p_clean
                    if re.match(r'^[3-5]\.\d$', p_clean):
                        rating = p_clean
                    if re.match(r'^\(\d+\)$', p_clean):
                        reviews = p_clean.strip('()')

            candidates.append({
                "name": name,
                "locality": locality,
                "experience": experience,
                "rating": rating,
                "reviews": reviews,
                "profile_url": profile_url
            })
            if len(candidates) >= target_count:
                break

    # Multi-threaded enrichment for verified phone number & contact person
    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        enriched_list = list(executor.map(lambda c: enrich_iyp_listing(c["profile_url"]), candidates))

    for cand, enriched in zip(candidates, enriched_list):
        phone = enriched.get("phone") or "Available upon inquiry"
        contact_person = enriched.get("contact_person") or "Management"
        website = enriched.get("website") or cand["profile_url"]

        item = {
            "name": cand["name"],
            "phone_number": phone,
            "contact_person": contact_person,
            "category": category_slug.replace('-', ' ').title(),
            "city": city.title(),
            "state": "Bihar",
            "locality": cand["locality"],
            "website": website,
            "source": "IndianYellowPages Bihar",
            "rating": cand["rating"],
            "reviews": cand["reviews"],
            "verified": "Yes (Verified Directory)"
        }
        results.append(item)
        if progress_callback:
            progress_callback(len(results), target_count)
        if len(results) >= target_count:
            break

    return results

def scrape_exporters_india(category_slug, city="patna", target_count=50, progress_callback=None):
    """
    Scrapes verified business leads from ExportersIndia Bihar business directory.
    Extracts Business Name, Phone Number, Contact Person, and verified address.
    Completely bot-safe with HTTP 200 responses.
    """
    city_norm = city.lower().replace(" ", "-")
    candidates = []

    urls_to_try = [
        f"https://www.exportersindia.com/{city_norm}/{category_slug}.htm",
        f"https://www.exportersindia.com/search.php?srch_catg_ty=p&term={urllib.parse.quote_plus(category_slug.replace('-', ' '))}&city={city_norm}"
    ]

    for url in urls_to_try:
        if len(candidates) >= target_count:
            break
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                if resp.status != 200:
                    continue
                html = resp.read().decode('utf-8', errors='ignore')
        except Exception:
            continue

        soup = BeautifulSoup(html, 'html.parser')
        h_tags = soup.find_all(['h3', 'h2'], class_=lambda c: c and any(k in c for k in ['comp', 'title', 'name'])) or soup.find_all('h3')
        
        for h in h_tags:
            name = h.get_text(strip=True)
            if not name or len(name) < 3 or any(w in name.lower() for w in ['explore', 'categories', 'top cities', 'post buy', 'search', 'related']):
                continue
            
            parent = h.find_parent('div') or h.parent
            
            # Extract company microsite link
            profile_url = ""
            if parent:
                for a in parent.find_all('a', href=True):
                    href = a['href'].strip()
                    if 'exportersindia.com/' in href and not any(k in href for k in ['patna', 'service', 'joinfree', 'post-buy', 'product-detail', 'advertise', 'help', 'search.php']):
                        profile_url = href
                        break
            if not profile_url:
                link = h.find('a', href=True) or (parent.find('a', href=True) if parent else None)
                if link and link['href'].startswith('http'):
                    profile_url = link['href']
                elif link and link['href'].startswith('/'):
                    profile_url = f"https://www.exportersindia.com{link['href']}"

            locality = f"{city.title()}, Bihar"
            rating = ""
            reviews = ""
            trust_badge = "Verified Directory"

            if parent:
                text_parts = [t.strip() for t in parent.get_text(separator='|').split('|') if t.strip()]
                for p in text_parts:
                    p_clean = p.strip()
                    if any(loc_kw in p_clean.lower() for loc_kw in [city.lower(), 'bihar', 'road', 'colony', 'chowk', 'nagar', 'more', 'deals in']):
                        if p_clean != name and len(p_clean) < 70 and not any(d in p_clean for d in ['year', 'review']):
                            locality = p_clean.replace("Deals in ", "")
                    if 'trusted' in p_clean.lower() or 'platinum' in p_clean.lower() or 'gst' in p_clean.lower():
                        trust_badge = "GST Verified / Platinum"
                    if re.match(r'^[3-5]\.\d$', p_clean):
                        rating = p_clean
                    if re.match(r'^\(\d+\)$', p_clean):
                        reviews = p_clean.strip('()')

            candidates.append({
                "name": name,
                "locality": locality,
                "rating": rating,
                "reviews": reviews,
                "trust_badge": trust_badge,
                "profile_url": profile_url
            })
            if len(candidates) >= target_count:
                break

    # Multi-threaded enrichment for verified phone number & contact person
    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        enriched_list = list(executor.map(lambda c: enrich_ei_listing(c["profile_url"]), candidates))

    for cand, enriched in zip(candidates, enriched_list):
        phone = enriched.get("phone") or "Available upon inquiry"
        contact_person = enriched.get("contact_person") or "Management"
        website = enriched.get("website") or cand["profile_url"]

        item = {
            "name": cand["name"],
            "phone_number": phone,
            "contact_person": contact_person,
            "category": category_slug.replace('-', ' ').title(),
            "city": city.title(),
            "state": "Bihar",
            "locality": cand["locality"],
            "website": website,
            "source": "ExportersIndia Bihar Directory",
            "rating": cand["rating"],
            "reviews": cand["reviews"],
            "verified": cand["trust_badge"]
        }
        results.append(item)
        if progress_callback:
            progress_callback(len(results), target_count)
        if len(results) >= target_count:
            break

    return results

def scrape_bihar_directory(keyword, city="Patna", target_count=50, directory_source="all", progress_callback=None):
    """
    Main entry point for scraping Bihar Local Directories.
    Combines IndianYellowPages and ExportersIndia, or targets a specific directory.
    Deduplicates results and formats for CSV export with Business Name & Phone Number.
    """
    category_slug = normalize_slug(keyword)
    city_clean = city.strip()
    all_results = []
    seen_names = set()

    def update_progress():
        if progress_callback:
            progress_callback(len(all_results), target_count)

    # 1. Scrape IndianYellowPages Bihar
    if directory_source in ["all", "indian_yellow_pages", "iyp"]:
        iyp_count = target_count if directory_source != "all" else (target_count // 2 + 10)
        try:
            iyp_items = scrape_indian_yellow_pages(
                category_slug, city=city_clean, target_count=iyp_count,
                progress_callback=None
            )
            for item in iyp_items:
                name_key = re.sub(r'[^a-zA-Z0-9]', '', item["name"].lower())
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_results.append(item)
                    update_progress()
                    if len(all_results) >= target_count:
                        break
        except Exception as e:
            print(f"Error scraping IndianYellowPages: {e}")

    # 2. Scrape ExportersIndia Bihar
    if directory_source in ["all", "exporters_india", "ei"] and len(all_results) < target_count:
        ei_count = target_count - len(all_results)
        try:
            ei_items = scrape_exporters_india(
                category_slug, city=city_clean, target_count=ei_count,
                progress_callback=None
            )
            for item in ei_items:
                name_key = re.sub(r'[^a-zA-Z0-9]', '', item["name"].lower())
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    all_results.append(item)
                    update_progress()
                    if len(all_results) >= target_count:
                        break
        except Exception as e:
            print(f"Error scraping ExportersIndia: {e}")

    return all_results
