import os
import re
import sqlite3
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "leads_memory.db")

def get_connection():
    """Returns a SQLite connection configured for thread safety and WAL mode."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # WAL (Write-Ahead Logging) enables high-performance concurrent reads & writes
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

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

def init_db():
    """Initializes the SQLite schema with indexing for fast deduplication lookups."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                norm_name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                canon_phone TEXT NOT NULL UNIQUE,
                website TEXT DEFAULT 'NA',
                city TEXT DEFAULT '',
                keyword TEXT DEFAULT '',
                source TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Auto-migrate table if 'website' column is missing from previous version
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(leads_memory);")
        cols = [r[1] for r in cursor.fetchall()]
        if "website" not in cols:
            try:
                conn.execute("ALTER TABLE leads_memory ADD COLUMN website TEXT DEFAULT 'NA';")
            except Exception:
                pass

        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_canon_phone ON leads_memory(canon_phone);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_norm_name ON leads_memory(norm_name);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_city ON leads_memory(city);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_keyword ON leads_memory(keyword);")
        conn.commit()

def get_known_identifiers(city_filter=None):
    """
    Returns pre-loaded sets for high-speed O(1) in-memory deduplication during scraping:
      - known_phones: set of all canonical phone numbers (global)
      - known_names: set of normalized names (global)
      - known_name_city: set of (norm_name, city_lower) pairs
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT norm_name, canon_phone, city FROM leads_memory")
        rows = cursor.fetchall()

        known_phones = set()
        known_names = set()
        known_name_city = set()

        for r in rows:
            np = r["norm_name"]
            cp = r["canon_phone"]
            ct = (r["city"] or "").strip().lower()

            if cp:
                known_phones.add(cp)
            if np:
                known_names.add(np)
                if ct:
                    known_name_city.add((np, ct))

        return known_phones, known_names, known_name_city

def is_lead_known(norm_name=None, canon_phone=None, city=None, known_phones=None, known_names=None, known_name_city=None):
    """
    Checks if a lead is already stored in memory:
    - If canon_phone matches ANY existing lead: True (phone number is globally unique)
    - If norm_name + city matches: True (same business name in the same city)
    """
    if canon_phone and known_phones is not None and canon_phone in known_phones:
        return True

    if norm_name and city and known_name_city is not None:
        if (norm_name, str(city).strip().lower()) in known_name_city:
            return True

    if canon_phone and known_phones is None:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM leads_memory WHERE canon_phone = ? LIMIT 1", (canon_phone,))
            if cursor.fetchone():
                return True

    if norm_name and city and known_name_city is None:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM leads_memory WHERE norm_name = ? AND LOWER(city) = ? LIMIT 1", (norm_name, str(city).strip().lower()))
            if cursor.fetchone():
                return True

    return False

def save_lead(lead_dict, keyword="", city="", source=""):
    """
    Saves a single lead to SQLite memory.
    Returns True if successfully inserted as a new lead, False if it was already known.
    """
    name = (lead_dict.get("Business Name") or lead_dict.get("business_name") or lead_dict.get("name") or "").strip()
    phone = (lead_dict.get("Phone Number") or lead_dict.get("phone_number") or lead_dict.get("phone") or "").strip()
    website = (lead_dict.get("Website") or lead_dict.get("website") or "NA").strip() or "NA"
    lead_city = (lead_dict.get("City") or lead_dict.get("city") or city or "").strip()

    if not name or not phone:
        return False

    norm_name = normalize_for_dedup(name)
    canon_p = canonical_phone(phone)

    if not norm_name or not canon_p:
        return False

    init_db()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO leads_memory
                (business_name, norm_name, phone_number, canon_phone, website, city, keyword, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, norm_name, phone, canon_p, website, lead_city, keyword.strip(), source.strip()))
            inserted = cursor.rowcount > 0
            conn.commit()
            return inserted
    except Exception:
        return False

def save_leads_batch(leads, keyword="", city="", source=""):
    """
    Saves a batch of leads to SQLite memory in a single fast transaction.
    Returns the count of newly added unique leads.
    """
    if not leads:
        return 0

    init_db()
    records = []
    seen_in_batch = set()

    for l in leads:
        name = (l.get("Business Name") or l.get("business_name") or l.get("name") or "").strip()
        phone = (l.get("Phone Number") or l.get("phone_number") or l.get("phone") or "").strip()
        website = (l.get("Website") or l.get("website") or "NA").strip() or "NA"
        lead_city = (l.get("City") or l.get("city") or city or "").strip()

        if not name or not phone:
            continue

        norm_name = normalize_for_dedup(name)
        canon_p = canonical_phone(phone)

        if not norm_name or not canon_p or canon_p in seen_in_batch:
            continue

        seen_in_batch.add(canon_p)
        records.append((name, norm_name, phone, canon_p, website, lead_city, keyword.strip(), source.strip()))

    if not records:
        return 0

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO leads_memory
                (business_name, norm_name, phone_number, canon_phone, website, city, keyword, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, records)
            new_count = cursor.rowcount
            conn.commit()
            return new_count
    except Exception:
        return 0

def get_memory_stats():
    """
    Returns summary statistics about the persistent lead memory.
    """
    init_db()
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM leads_memory")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT DISTINCT city FROM leads_memory WHERE city != '' AND city IS NOT NULL ORDER BY city ASC")
            cities = [r["city"] for r in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT keyword FROM leads_memory WHERE keyword != '' AND keyword IS NOT NULL ORDER BY keyword ASC")
            keywords = [r["keyword"] for r in cursor.fetchall()]

            cursor.execute("SELECT MAX(created_at) as last_scraped FROM leads_memory")
            row_last = cursor.fetchone()
            last_scraped = row_last["last_scraped"] if row_last else None

            return {
                "total_leads": total,
                "cities_count": len(cities),
                "cities": cities,
                "keywords": keywords,
                "last_scraped": last_scraped
            }
    except Exception as e:
        return {
            "total_leads": 0,
            "cities_count": 0,
            "cities": [],
            "keywords": [],
            "last_scraped": None,
            "error": str(e)
        }

def clear_memory():
    """
    Clears all saved leads from SQLite memory so the user can re-scrape from scratch if desired.
    """
    init_db()
    with get_connection() as conn:
        conn.execute("DELETE FROM leads_memory;")
        conn.execute("VACUUM;")
        conn.commit()
    return True

def export_all_leads():
    """
    Exports all stored leads as a list of dicts.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT business_name AS "Business Name",
                   phone_number AS "Phone Number",
                   COALESCE(NULLIF(website, ''), 'NA') AS "Website",
                   city AS "City",
                   keyword AS "Keyword",
                   source AS "Source",
                   created_at AS "Scraped At"
            FROM leads_memory
            ORDER BY id ASC
        """)
        return [dict(r) for r in cursor.fetchall()]

def auto_import_existing_csvs():
    """
    Scans BASE_DIR for existing leads_*.csv files and imports any historical leads into memory.
    This guarantees any previous scraping session is remembered immediately.
    """
    init_db()
    imported_count = 0
    if not os.path.exists(BASE_DIR):
        return 0

    for fname in os.listdir(BASE_DIR):
        if fname.startswith("leads") and fname.endswith(".csv"):
            fpath = os.path.join(BASE_DIR, fname)
            try:
                df = pd.read_csv(fpath)
                # Check for standard columns
                name_col = next((c for c in df.columns if "name" in c.lower()), None)
                phone_col = next((c for c in df.columns if "phone" in c.lower()), None)
                website_col = next((c for c in df.columns if "website" in c.lower() or "site" in c.lower() or "url" in c.lower()), None)
                city_col = next((c for c in df.columns if "city" in c.lower()), None)

                if name_col and phone_col:
                    leads_to_add = []
                    for _, row in df.iterrows():
                        b_name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ""
                        p_num = str(row[phone_col]).strip() if pd.notna(row[phone_col]) else ""
                        w_val = str(row[website_col]).strip() if website_col and pd.notna(row[website_col]) else "NA"
                        c_val = str(row[city_col]).strip() if city_col and pd.notna(row[city_col]) else ""

                        if b_name and p_num and p_num.lower() not in ["not available", "nan", "n/a", ""]:
                            leads_to_add.append({
                                "Business Name": b_name,
                                "Phone Number": p_num,
                                "Website": w_val if w_val and w_val.lower() not in ["none", "nan", ""] else "NA",
                                "City": c_val
                            })
                    if leads_to_add:
                        # Extract keyword and source hints from filename if possible
                        clean_fn = fname.replace(".csv", "")
                        added = save_leads_batch(leads_to_add, keyword=clean_fn, source="csv_import")
                        imported_count += added
            except Exception:
                pass

    return imported_count

if __name__ == "__main__":
    init_db()
    imported = auto_import_existing_csvs()
    stats = get_memory_stats()
    print(f"Leads Memory DB Initialized at: {DB_PATH}")
    print(f"Imported from CSVs: {imported}")
    print(f"Current Stats: {stats}")
