import time
import re
import pandas as pd
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_user_input():
    print("\n==============================")
    print("GOOGLE MAPS BUSINESS SCRAPER (NAME & PHONE)")
    print("==============================\n")
    keyword = input("Enter Business Keyword (e.g., Restaurants): ").strip()
    city = input("Enter City (e.g., Patna): ").strip()
    return keyword, city

def scrape_google_maps(keyword, city, target_count=200):
    query = f"{keyword} in {city}".replace(" ", "+")
    url = f"https://www.google.com/maps/search/{query}"
    
    print(f"\nSearch URL: {url}")
    print("Initializing browser... please wait.")
    
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--lang=en-US")
    
    driver = uc.Chrome(options=options)
    results = []
    
    try:
        print("Opening Google Maps and searching...")
        driver.get(url)
        time.sleep(5) 
        
        # Step 1: Scroll to grab listing URLs
        feed_xpath = "//div[@role='feed']"
        listing_urls = {} # URL to Name mapping
        
        print(f"Scrolling to find {target_count} business links. This may take a couple of minutes...")
        
        try:
            feed_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, feed_xpath))
            )
            
            last_count = 0
            retries = 0
            
            while len(listing_urls) < target_count and retries < 10:
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
            
        urls_to_visit = list(listing_urls.keys())[:target_count]
        print(f"\nFinished scrolling! Extracted {len(urls_to_visit)} unique business links.")
        print("Now extracting phone numbers for each business...")
        
        # Step 2: Visit each URL to get phone number
        for i, link in enumerate(urls_to_visit, 1):
            name = listing_urls[link]
            print(f"[{i}/{len(urls_to_visit)}] Extracting data for: {name}")
            
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
                    print(f"   -> Phone: {phone}")
                else:
                    print("   -> Phone: Not available")
                    
            except Exception as e:
                print(f"Failed to extract details for {name}: {e}")
                
            results.append({
                "Business Name": name,
                "Phone Number": phone
            })
                
    except Exception as e:
        print(f"\nAn error occurred during scraping: {e}")
    finally:
        driver.quit()
        
    return results

def main():
    keyword, city = get_user_input()
    if not keyword or not city:
        print("Keyword and City are required!")
        return

    data = scrape_google_maps(keyword, city, target_count=200)
    
    if data:
        df = pd.DataFrame(data)
        
        # Create a dynamic filename based on user input
        clean_keyword = keyword.replace(" ", "_").lower()
        clean_city = city.replace(" ", "_").lower()
        output_file = f"leads_{clean_keyword}_{clean_city}.csv"
        
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\nCSV Exported Successfully: {output_file}")
        print(f"Total Records Extracted: {len(data)}")
    else:
        print("\nNo data was extracted. Please try a different search.")

if __name__ == "__main__":
    main()