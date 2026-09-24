"""
IndiaMART Directory B2B Lead Scraper
====================================
Production-grade Playwright crawler for IndiaMART directory listings (https://dir.indiamart.com).
Extracts high-accuracy B2B leads focusing strictly on Company/Supplier Name and Phone Number,
along with basic metadata (Address, City, and Profile URL).

Installation:
    pip install playwright pandas beautifulsoup4
    playwright install chromium

Usage:
    python indiamart_scraper.py --keyword "pharmaceutical-distributors" --city "Patna" --limit 50 --output "leads.csv"
"""

import argparse
import json
import logging
import random
import re
import sys
import time
from typing import Callable, Dict, List, Optional, Set, Tuple
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("indiamart_scraper")

# Realistic Desktop Chrome User-Agent
DESKTOP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Indian mobile & PNS virtual number regex: 10 digits starting with 6, 7, 8, or 9
PHONE_REGEX = re.compile(r'\b[6-9]\d{9}\b')


def clean_phone_number(raw_val: Optional[str]) -> Optional[str]:
    """
    Cleans raw phone string into a standard 10-digit Indian phone number.
    Strips 'tel:', '+91', leading zeros, spaces, hyphens, and extension codes.
    """
    if not raw_val:
        return None
    raw_str = str(raw_val).strip()
    if not raw_str:
        return None

    # Handle comma-separated extension like "8048203659,4480"
    if "," in raw_str:
        raw_str = raw_str.split(",")[0].strip()

    # Remove 'tel:' prefix if present
    cleaned = re.sub(r'^tel:', '', raw_str, flags=re.I).strip()
    # Remove leading country codes '+91', '91', or leading zeros
    cleaned = re.sub(r'^(?:\+91|91|0)+', '', cleaned).strip()
    # Remove separators
    cleaned = re.sub(r'[\s\-\(\)\.]', '', cleaned)

    # Search for standard 10-digit number
    match = PHONE_REGEX.search(cleaned)
    if match:
        return match.group(0)

    # Fallback search on original string
    raw_match = PHONE_REGEX.search(raw_str)
    if raw_match:
        return raw_match.group(0)

    return None


def human_delay(min_s: float = 2.0, max_s: float = 4.0):
    """Implement subtle humanized delay between interactions."""
    time.sleep(random.uniform(min_s, max_s))


def dismiss_overlays(page: Page):
    """
    Dismiss common IndiaMART overlay modals (such as 'Tell us what you need',
    login/OTP popups, lead enquiry forms) using ESC key, close buttons,
    and JS element removal.
    """
    try:
        # Strategy A: Press Escape key
        page.keyboard.press("Escape")
    except Exception:
        pass

    try:
        # Strategy B: Click modal close buttons if present
        close_selectors = [
            ".modal-close", ".close", "button[aria-label='Close']", "#close",
            ".cross", "span.cross", "div.close", ".ui-dialog-titlebar-close",
            "svg.close-icon", ".im-close"
        ]
        for sel in close_selectors:
            try:
                for btn in page.query_selector_all(sel):
                    if btn.is_visible():
                        btn.click()
            except Exception:
                pass
    except Exception:
        pass

    try:
        # Strategy C: Remove stubborn modal overlays from DOM to allow smooth scrolling
        page.evaluate('''() => {
            const modalSelectors = [
                '#remote-login-connect-popup-shell',
                '.im-modal',
                '.modal-backdrop',
                'div[class*="animate-[lcp-fade-in"]',
                'div[class*="z-[9999]"]'
            ];
            modalSelectors.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
            document.body.style.overflow = 'auto';
        }''')
    except Exception:
        pass


def extract_from_initial_state(html: str) -> List[Dict[str, str]]:
    """
    Extracts high-accuracy listings directly from IndiaMART's embedded
    window.__INITIAL_STATE__ JSON object when present on the page.
    """
    extracted: List[Dict[str, str]] = []
    # Match JSON payload assigned to window.__INITIAL_STATE__
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*(?:var|</script>)', html, re.DOTALL)
    if not match:
        return extracted

    try:
        state_data = json.loads(match.group(1))

        # 1. Main listing data items
        for item in state_data.get("data", []):
            name = item.get("CMP") or item.get("f_nm")
            if not name:
                continue
            raw_phone = item.get("c_ct") or ""
            phone = clean_phone_number(raw_phone)
            city_val = item.get("city") or ""
            address_val = item.get("ad") or item.get("f_ad") or city_val
            profile = item.get("s_url") or item.get("p_url") or ""

            extracted.append({
                "company_name": str(name).strip(),
                "phone": phone or "N/A",
                "city": str(city_val).strip(),
                "address": str(address_val).strip(),
                "profile_url": str(profile).strip()
            })

        # 2. PLA Widget items
        for item in state_data.get("plaWidgetData", []):
            name = item.get("COMPANYNAME")
            if not name:
                continue
            raw_phone = item.get("CONTACT_NUMBER") or ""
            phone = clean_phone_number(raw_phone)
            city_val = item.get("CITY_NAME") or ""
            state_val = item.get("STATE_NAME") or ""
            address_val = f"{city_val}, {state_val}".strip(", ")
            profile = item.get("PDP_URL") or ""

            extracted.append({
                "company_name": str(name).strip(),
                "phone": phone or "N/A",
                "city": str(city_val).strip(),
                "address": str(address_val).strip(),
                "profile_url": str(profile).strip()
            })

        # 3. Local sellers list
        for item in state_data.get("localSellers", []):
            name = item.get("CMP") or item.get("f_nm")
            if not name:
                continue
            city_val = item.get("city") or ""
            profile = item.get("s_url") or item.get("p_url") or ""
            extracted.append({
                "company_name": str(name).strip(),
                "phone": "N/A",
                "city": str(city_val).strip(),
                "address": str(city_val).strip(),
                "profile_url": str(profile).strip()
            })

    except Exception as e:
        logger.debug(f"Could not parse __INITIAL_STATE__: {e}")

    return extracted


def extract_from_dom(html: str) -> List[Dict[str, str]]:
    """
    Extracts leads from HTML DOM using priority cascades for business name,
    phone number, address, and profile URL.
    """
    extracted: List[Dict[str, str]] = []
    soup = BeautifulSoup(html, "html.parser")

    # Card containers
    cards = soup.select(
        "li.pCard1, article.pCard2, div.m-card, div.card, "
        "div[id*='item_'], div.lst, div.clg, div.r-cnt"
    )

    for card in cards:
        # --- 1. Business Name ---
        company_name = None
        profile_url = ""

        # Check explicit company title selectors
        name_el = card.select_one("a.company-name, span.company-name, h2 a, a.lcname, a.cncf1, .c-name, .cmpny-name")
        if name_el:
            company_name = name_el.get_text(strip=True)
            if name_el.name == "a" and name_el.get("href"):
                profile_url = name_el.get("href")

        # Fallback to search any supplier links
        if not company_name or not profile_url:
            for a in card.find_all("a"):
                href = a.get("href", "")
                text = a.get_text(strip=True)
                if text and "indiamart.com" in href and not any(x in href for x in ["proddetail", "search.mp", "help.indiamart"]):
                    if not company_name:
                        company_name = text
                    if not profile_url:
                        profile_url = href
                    break

        if not company_name:
            continue

        # --- 2. Phone Number (Priority Strategy) ---
        phone = None

        # Strategy 1: data-pnsno or #footerPNS inside card
        pns_el = card.find(attrs={"data-pnsno": True})
        if pns_el:
            phone = clean_phone_number(pns_el.get("data-pnsno"))

        if not phone:
            footer_pns = card.select_one("#footerPNS")
            if footer_pns:
                phone = clean_phone_number(footer_pns.get_text(strip=True))

        # Strategy 2: Extract href starting with 'tel:'
        if not phone:
            tel_el = card.find("a", href=re.compile(r'^tel:', re.I))
            if tel_el:
                phone = clean_phone_number(tel_el.get("href"))

        # Strategy 3: Check classes matching call containers
        if not phone:
            call_container = card.select_one(".bo-call-btn, .mobtxt, [class*='phone_no'], span.du-no, .pns-no, [class*='pns'], [class*='call']")
            if call_container:
                phone = clean_phone_number(call_container.get_text(strip=True))

        # Strategy 4: Fallback regex on contact button element or entire card
        if not phone:
            for btn in card.find_all(["button", "a", "span", "div"]):
                t = btn.get_text(strip=True)
                m = PHONE_REGEX.search(t)
                if m:
                    phone = m.group(0)
                    break

        # --- 3. Location & City ---
        city = ""
        address = ""
        loc_el = card.select_one(".city-name, span.loc-name, .city, .loc, [class*='loc'], [class*='city'], [class*='address']")
        if loc_el:
            loc_text = loc_el.get_text(strip=True)
            if loc_text and loc_text.lower() != company_name.lower():
                address = loc_text
                city = loc_text.split(",")[-1].strip()

        # Canonical profile URL check
        if profile_url and not profile_url.startswith("http"):
            profile_url = f"https://www.indiamart.com{profile_url}"

        extracted.append({
            "company_name": company_name,
            "phone": phone or "N/A",
            "city": city,
            "address": address or city,
            "profile_url": profile_url
        })

    return extracted


def scrape_indiamart(
    keyword: str,
    city: str,
    target_count: int = 50,
    progress_callback: Optional[Callable[[int, int, int], None]] = None
) -> List[Dict[str, str]]:
    """
    Main scraping function using Playwright with Chromium.
    Scrapes IndiaMART directory for `keyword` in `city` until `target_count` valid leads
    are collected or listings are exhausted.

    Parameters:
        keyword: e.g. "pharmaceutical-distributors"
        city: e.g. "Patna"
        target_count: Total target valid leads (default: 50)
        progress_callback: Optional callback(valid_count, total_processed, target_count)
    """
    clean_kw = keyword.strip()
    clean_city = city.strip()
    kw_slug = re.sub(r'[\s_]+', '-', clean_kw.lower())
    city_slug = re.sub(r'[\s_]+', '-', clean_city.lower())

    results: List[Dict[str, str]] = []
    seen_keys: Set[Tuple[str, str]] = set()
    total_processed = 0

    logger.info(f"Starting IndiaMART scraper for '{clean_kw}' in '{clean_city}' (Target: {target_count} leads)")

    # Candidate URLs to query
    primary_search_url = f"https://dir.indiamart.com/search.mp?ss={kw_slug}&cq={clean_city}"
    direct_cat_url = f"https://dir.indiamart.com/{city_slug}/{kw_slug}.html"

    urls_to_visit = [primary_search_url, direct_cat_url]
    visited_urls = set()

    with sync_playwright() as p:
        # Launch Chromium with realistic stealth arguments
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1366,768"
            ]
        )
        context = browser.new_context(
            user_agent=DESKTOP_UA,
            viewport={"width": 1366, "height": 768},
            locale="en-IN"
        )
        # Remove navigator.webdriver detection
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        page = context.new_page()

        while urls_to_visit and len(results) < target_count:
            current_url = urls_to_visit.pop(0)
            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            logger.info(f"Navigating to: {current_url}")
            try:
                page.goto(current_url, wait_until="domcontentloaded", timeout=35000)
            except Exception as e:
                logger.warning(f"Timeout or navigation error on {current_url}: {e}")
                continue

            human_delay(2.0, 3.5)
            dismiss_overlays(page)

            # Check if search.mp redirected to a dummy/fallback page (e.g. tags=NA)
            if "tags=NA" in page.url or "v=4" in page.url:
                logger.info("Search URL redirected to fallback. Ensuring direct category URL is queued.")
                if direct_cat_url not in visited_urls and direct_cat_url not in urls_to_visit:
                    urls_to_visit.insert(0, direct_cat_url)

            # Dynamic scrolling to trigger lazy-loaded listings
            for scroll_idx in range(1, 5):
                page.evaluate("window.scrollBy(0, 1000);")
                time.sleep(1.5)
                dismiss_overlays(page)

            # Get complete page HTML
            html = page.content()

            # 1. First extract from embedded __INITIAL_STATE__ (highest accuracy)
            state_leads = extract_from_initial_state(html)
            # 2. Extract from DOM cards
            dom_leads = extract_from_dom(html)

            # Merge and deduplicate
            batch = state_leads + dom_leads
            for item in batch:
                total_processed += 1
                c_name = item.get("company_name", "").strip()
                phone = item.get("phone", "N/A").strip()
                if not c_name:
                    continue

                # Ensure city is set
                if not item.get("city"):
                    item["city"] = clean_city
                if not item.get("address"):
                    item["address"] = clean_city

                dedup_key = (c_name.lower(), phone)
                if dedup_key not in seen_keys:
                    seen_keys.add(dedup_key)
                    # If this company already exists without a phone and we found a phone now, update it
                    updated_existing = False
                    if phone != "N/A":
                        for existing in results:
                            if existing["company_name"].lower() == c_name.lower() and existing["phone"] == "N/A":
                                existing["phone"] = phone
                                updated_existing = True
                                break

                    if not updated_existing:
                        results.append(item)

                    valid_phones = sum(1 for r in results if r.get("phone") != "N/A")
                    logger.info(
                        f"Progress: [{len(results)}/{target_count} leads] "
                        f"(Verified Phones: {valid_phones}) | Latest: {c_name} -> {phone}"
                    )

                    if progress_callback:
                        progress_callback(len(results), total_processed, target_count)

                    if len(results) >= target_count:
                        break

            # If we still need more leads, extract related category links from page
            if len(results) < target_count:
                # Check for related subcategories in __INITIAL_STATE__
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*(?:var|</script>)', html, re.DOTALL)
                if match:
                    try:
                        state = json.loads(match.group(1))
                        for rc in state.get("relCat", []):
                            sub_url = rc.get("URL")
                            if sub_url:
                                if not sub_url.startswith("http"):
                                    sub_url = f"https://dir.indiamart.com{sub_url}"
                                if sub_url not in visited_urls and sub_url not in urls_to_visit:
                                    urls_to_visit.append(sub_url)
                    except Exception:
                        pass

                # Also check DOM for related links
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.select("a[href*='/patna/'], a[href*='search.mp']"):
                    h = a.get("href", "")
                    if h.endswith(".html") and not any(x in h for x in ["proddetail", "aboutus", "contact"]):
                        if not h.startswith("http"):
                            h = f"https://dir.indiamart.com{h}"
                        if h not in visited_urls and h not in urls_to_visit:
                            urls_to_visit.append(h)

        browser.close()

    valid_phone_count = sum(1 for r in results if r.get("phone") != "N/A")
    logger.info(f"Scraping completed! Total leads collected: {len(results)} (Valid Phones: {valid_phone_count})")
    return results[:target_count]


def main():
    parser = argparse.ArgumentParser(description="Production-grade IndiaMART B2B Lead Scraper via Playwright")
    parser.add_argument("--keyword", type=str, default="pharmaceutical-distributors", help="Keyword/category to scrape")
    parser.add_argument("--city", type=str, default="Patna", help="Target city")
    parser.add_argument("--limit", type=int, default=50, help="Target lead count threshold")
    parser.add_argument("--output", type=str, default="indiamart_leads.csv", help="Output CSV filepath")

    args = parser.parse_args()

    def console_progress(valid_count: int, processed_count: int, target: int):
        print(f"\r[Real-Time Progress] Valid Leads: {valid_count}/{target} | Total Processed: {processed_count}", end="", flush=True)

    start = time.time()
    leads = scrape_indiamart(
        keyword=args.keyword,
        city=args.city,
        target_count=args.limit,
        progress_callback=console_progress
    )
    print()

    # Save to CSV using Pandas with exact required columns
    columns = ["company_name", "phone", "city", "address", "profile_url"]
    if leads:
        df = pd.DataFrame(leads)
        # Ensure all required columns exist in specified order
        for col in columns:
            if col not in df.columns:
                df[col] = "N/A"
        df = df[columns]
        df.to_csv(args.output, index=False, encoding="utf-8-sig")
        print(f"\nSaved {len(df)} leads to '{args.output}' in {time.time() - start:.1f}s.")
        print("\nSample Preview:")
        print(df.head(10).to_string(index=False))
    else:
        print("\nNo leads could be collected. Please verify search terms.")


if __name__ == "__main__":
    main()
