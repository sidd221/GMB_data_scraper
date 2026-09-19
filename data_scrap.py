import sys
import time
import re
import json
import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

def get_user_input():
    print("\n==============================")
    print("BUSINESS LEADS SCRAPER (NAME & PHONE)")
    print("==============================\n")
    print("Select Platform:")
    print("  1. Google Maps")
    print("  2. Bing Maps")
    choice = input("Enter choice (1 or 2, default 1): ").strip()
    source = "bing" if choice == "2" else "google"
    keyword = input("Enter Business Keyword (e.g., Restaurants): ").strip()
    city = input("Enter City (e.g., Patna): ").strip()
    return keyword, city, source

def scrape_google_maps(keyword, city, target_count=200):
    query = f"{keyword} in {city}".replace(" ", "+")
    url = f"https://www.google.com/maps/search/{query}"
    
    print(f"\nSearch URL: {url}")
    print("Initializing browser... please wait.")
    
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US")
    
    major_version = get_chrome_major_version()
    if major_version:
        print(f"Detected Chrome version: {major_version}")
        driver = uc.Chrome(options=options, version_main=major_version)
    else:
        driver = uc.Chrome(options=options)

    results = []
    
    try:
        print("Opening Google Maps and searching...")
        driver.get(url)
        time.sleep(5) 
        
        # Step 1: Scroll to grab listing URLs
        feed_xpath = "//div[@role='feed']"
        listing_urls = {} # URL to Name mapping
        url_target = int(target_count * 1.5)
        
        print(f"Scrolling to find business links (target: {target_count} leads with phone numbers)...")
        
        try:
            feed_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, feed_xpath))
            )
            
            last_count = 0
            retries = 0
            
            while len(listing_urls) < url_target and retries < 10:
                # Scroll down
                driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", feed_element)
                time.sleep(3)
                
                # Parse current HTML for links
                soup = BeautifulSoup(driver.page_source, "html.parser")
                cards = soup.find_all("a", href=re.compile(r"/maps/place/"))
                
                for card in cards:
                    name = card.get("aria-label")
                    link = card.get("href")
                    if name and link and link not in listing_urls:
                        listing_urls[link] = name
                
                current_count = len(listing_urls)
                print(f"Found {current_count} links so far...")
                
                if current_count == last_count:
                    retries += 1
                else:
                    retries = 0
                    
                last_count = current_count
                
        except Exception as e:
            print("Finished scrolling or could not find more results.")
            
        urls_to_visit = list(listing_urls.keys())
        print(f"\nFinished scrolling! Extracted {len(urls_to_visit)} unique business links.")
        print("Now extracting phone numbers for each business (skipping those without phone numbers)...")
        
        # Step 2: Visit each URL to get phone number
        for i, link in enumerate(urls_to_visit, 1):
            if len(results) >= target_count:
                print(f"Reached target limit of {target_count} leads with phone numbers!")
                break

            name = listing_urls[link]
            print(f"[{i}/{len(urls_to_visit)}] Checking data for: {name}")
            
            phone = ""
            try:
                driver.get(link)
                # Wait for page to load
                time.sleep(2.5) 
                
                html = driver.page_source
                soup = BeautifulSoup(html, "html.parser")
                
                # Look for standard Google Maps phone button
                phone_btn = soup.find("button", {"data-tooltip": "Copy phone number"})
                if phone_btn:
                    phone = phone_btn.get("aria-label", "").replace("Phone:", "").strip()
                    if not phone:
                        phone = phone_btn.get_text(strip=True)
                
                # Fallback: scan buttons with phone regex
                if not phone:
                    for btn in soup.find_all("button"):
                        text = btn.get_text(strip=True)
                        if re.match(r'^\+?\d[\d \-\(\)]{8,14}\d$', text):
                            phone = text
                            break
                            
                if phone:
                    print(f"   -> [SAVED] Phone: {phone}")
                    results.append({
                        "Business Name": name,
                        "Phone Number": phone
                    })
                else:
                    print("   -> [SKIPPED] No phone number found.")
                    
            except Exception as e:
                print(f"Failed to extract details for {name}: {e}")
                
    except Exception as e:
        print(f"\nAn error occurred during scraping: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        
    return results

def scrape_bing_maps(keyword, city, target_count=100):
    query = f"{keyword} in {city}".replace(" ", "+")
    url = f"https://www.bing.com/maps?q={query}"
    
    print(f"\n[Bing Maps] Search URL: {url}")
    print("Initializing browser... please wait.")
    
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US")
    
    major_version = get_chrome_major_version()
    if major_version:
        print(f"Detected Chrome version: {major_version}")
        driver = uc.Chrome(options=options, version_main=major_version)
    else:
        driver = uc.Chrome(options=options)

    results = []
    seen_names = set()
    
    try:
        print("Opening Bing Maps and searching...")
        driver.get(url)
        time.sleep(6)
        
        def extract_cards_from_page():
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.find_all("div", class_="b_maglistcard")
            extracted = 0
            for card in cards:
                name = ""
                phone = ""
                
                # Method 1: Check embedded data-entity JSON
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
                
                # Method 3: Fallback phone from DOM
                if not phone:
                    phone_elem = card.find("span", class_="nowrap")
                    if phone_elem:
                        phone = phone_elem.get_text(strip=True)
                        
                if not phone:
                    m = re.search(r'(\+?\d[\d \-\(\)]{8,14}\d)', card.get_text())
                    if m:
                        phone = m.group(1).strip()
                        
                # Only keep leads with a valid phone number
                if name and phone and name not in seen_names:
                    seen_names.add(name)
                    print(f"[{len(results)+1}] [SAVED] Found: {name} | Phone: {phone}")
                    results.append({
                        "Business Name": name,
                        "Phone Number": phone
                    })
                    extracted += 1
                    if len(results) >= target_count:
                        break
                elif name and not phone and name not in seen_names:
                    # Skip businesses without a phone number
                    seen_names.add(name)
                    print(f"   -> [SKIPPED] {name} (No phone number)")
            return extracted

        # Initial extraction from current view
        extract_cards_from_page()
        print(f"Initial batch extracted: {len(results)} valid leads with phone numbers.")
        
        # Scroll & interact to load more results if requested
        retries = 0
        scroll_attempts = 0
        max_scroll_attempts = min(30, max(5, target_count // 5))
        
        while len(results) < target_count and scroll_attempts < max_scroll_attempts and retries < 6:
            scroll_attempts += 1
            
            # Scroll content pane container
            driver.execute_script("""
                var el = document.getElementById('contentPane') || 
                         document.getElementById('localSearchContent') || 
                         document.querySelector('[class*="listingsCard"]') ||
                         document.querySelector('.b_lstcards');
                if (el) {
                    el.scrollTop = el.scrollHeight;
                }
                var lastCard = document.querySelector('.b_maglistcard:last-child');
                if (lastCard) {
                    lastCard.scrollIntoView({behavior: 'smooth', block: 'end'});
                }
            """)
            time.sleep(2.5)
            
            new_count = extract_cards_from_page()
            if new_count > 0:
                retries = 0
            else:
                retries += 1
                # Try zooming out slightly on map to expand search bounds
                try:
                    zoom_btns = driver.find_elements(By.XPATH, "//button[contains(@title, 'Zoom out') or contains(@aria-label, 'Zoom out') or contains(@class, 'zoomOut') or @id='zoomOut']")
                    if zoom_btns:
                        zoom_btns[0].click()
                        time.sleep(3)
                        extract_cards_from_page()
                except Exception:
                    pass
                    
        print(f"\nFinished Bing Maps extraction! Total records: {len(results)}")
        
    except Exception as e:
        print(f"\nAn error occurred during Bing Maps scraping: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
                
    return results[:target_count]

def main():
    keyword, city, source = get_user_input()
    if not keyword or not city:
        print("Keyword and City are required!")
        return

    if source == "bing":
        data = scrape_bing_maps(keyword, city, target_count=100)
    else:
        data = scrape_google_maps(keyword, city, target_count=200)
    
    if data:
        df = pd.DataFrame(data)
        clean_keyword = keyword.replace(" ", "_").lower()
        clean_city = city.replace(" ", "_").lower()
        output_file = f"leads_{source}_{clean_keyword}_{clean_city}.csv"
        
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\nCSV Exported Successfully: {output_file}")
        print(f"Total Records Extracted: {len(data)}")
    else:
        print("\nNo data was extracted. Please try a different search.")

if __name__ == "__main__":
    main()