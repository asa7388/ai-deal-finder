import time
import os
import requests
import re
from dotenv import load_dotenv
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- AI SETUP ---
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    print("GEMINI_API_KEY not found in .env file. AI analysis will be skipped.")

# --- SLICKDEALS SCRAPER ---
def scrape_slickdeals():
    url = "https://slickdeals.net/deals/"
    print(f"Fetching deals from: {url}")
    firefox_options = Options()
    firefox_options.add_argument("--headless")
    driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=firefox_options)
    deals = []
    try:
        driver.get(url)
        driver.maximize_window()
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.dealRow")))
        print("Slickdeals content loaded!")
        posts = driver.find_elements(By.CSS_SELECTOR, 'div.dealRow')
        print(f"Found {len(posts)} deal rows on Slickdeals. Parsing now...")
        for post in posts:
            try:
                title_element = post.find_element(By.CSS_SELECTOR, 'div.dealTitle a')
                price_element = post.find_element(By.CSS_SELECTOR, 'div.price > span')
                link = title_element.get_attribute('href')
                title = title_element.text
                price = price_element.text
                if title and price:
                    deals.append({"title": title, "price": price, "link": link, "source": "Slickdeals"})
            except Exception:
                continue
        print(f"Successfully parsed {len(deals)} deals from Slickdeals.")
    except Exception as e:
        print(f"An error occurred during Slickdeals scraping: {e}")
    finally:
        driver.quit()
    return deals

# --- REDDIT API SCRAPER ---
def get_reddit_deals():
    url = "https://www.reddit.com/r/deals/new.json"
    headers = {"User-Agent": "DealFinder/1.0"}
    print(f"\nFetching deals from: {url}")
    deals = []
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        posts = data['data']['children']
        for post in posts:
            post_data = post['data']
            if not post_data['stickied']:
                deals.append({"title": post_data['title'], "price": "N/A", "link": post_data['url'], "source": "Reddit"})
        print(f"Successfully parsed {len(deals)} deals from Reddit.")
    except Exception as e:
        print(f"An error occurred during Reddit fetching: {e}")
    return deals

# --- AI ANALYSIS FUNCTION ---
def analyze_deals_with_ai(deals):
    if not api_key:
        print("Skipping AI analysis due to missing API key.")
        return deals
        
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("\n--- Analyzing deals with AI... (This will take a few minutes) ---")
    for deal in deals:
        prompt = f"Analyze the following deal. On a scale of 1-10, how likely is this to be a price error or an amazing deal? Respond with ONLY a single number and nothing else. DEAL: \"{deal['title']}\""
        try:
            response = model.generate_content(prompt)
            match = re.search(r'\d+', response.text)
            if match:
                rating = int(match.group(0))
                deal['ai_rating'] = rating
                print(f"Rated '{deal['title'][:50]}...' as a {rating}/10")
            else:
                raise ValueError("No number found in AI response")
        except Exception as e:
            deal['ai_rating'] = 0
            print(f"Could not rate '{deal['title'][:50]}...'. Error: {e}")
            if 'response' in locals():
                print(f"   Problematic AI response: {response.text}")
        
        # --- RATE LIMIT FIX ---
        # Wait 4 seconds between each API call to stay within the 15 requests/minute limit
        time.sleep(4)
        
    return deals

if __name__ == "__main__":
    slickdeals = scrape_slickdeals()
    reddit_deals = get_reddit_deals()
    all_deals = slickdeals + reddit_deals
    print(f"\nFound a total of {len(all_deals)} deals.")
    if all_deals:
        analyzed_deals = analyze_deals_with_ai(all_deals)
        print("\n--- AI-Rated Deals (Best First) ---")
        sorted_deals = sorted(analyzed_deals, key=lambda d: d.get('ai_rating', 0), reverse=True)
        for deal in sorted_deals:
            rating = deal.get('ai_rating', 'N/A')
            print(f"Source: {deal['source']} | Rating: {rating}/10")
            print(f"  Title: {deal['title']}")
            print(f"  Price: {deal['price']}")
            print(f"  Link: {deal['link']}\n")