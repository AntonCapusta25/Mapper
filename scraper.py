import json
import time
import re
import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup


class GoogleMapsRestaurantScraper:
    def __init__(self, config_path='config.json'):
        """Initialize the scraper with configuration."""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.restaurants = []
        self.driver = None
        
    def setup_driver(self):
        """Set up Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        
        if self.config.get('headless', True):
            chrome_options.add_argument('--headless=new')
        
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Install and get the correct chromedriver path
        import os
        driver_path = ChromeDriverManager().install()
        
        # Fix for macOS ARM - ensure we have the actual chromedriver executable
        # The webdriver-manager sometimes returns the wrong file
        parent_dir = os.path.dirname(driver_path)
        
        # Look for the actual chromedriver executable (not THIRD_PARTY_NOTICES or LICENSE)
        for filename in os.listdir(parent_dir):
            if filename == 'chromedriver':  # Exact match only
                potential_path = os.path.join(parent_dir, filename)
                if os.path.isfile(potential_path) and os.access(potential_path, os.X_OK):
                    driver_path = potential_path
                    break
        
        print(f"Using ChromeDriver at: {driver_path}")
        service = Service(driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.maximize_window()



        
    def search_restaurants(self):
        """Navigate to Google Maps and search for restaurants."""
        search_query = self.config.get('search_query', 'restaurants in Amsterdam')
        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        
        print(f"Searching for: {search_query}")
        self.driver.get(url)
        
        # Wait for results to load
        time.sleep(5)
        
        # Accept cookies if present
        try:
            accept_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Accept all') or contains(., 'Accepteer allemaal')]"))
            )
            accept_button.click()
            time.sleep(2)
        except TimeoutException:
            print("No cookie banner found or already accepted")
        
    def scroll_results(self):
        """Scroll through the results panel to load more restaurants."""
        print("Scrolling through results...")
        
        # Find the scrollable results panel
        try:
            scrollable_div = self.driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
        except NoSuchElementException:
            print("Could not find scrollable results panel")
            return
        
        max_results = self.config.get('max_results', 100)
        scroll_pause = self.config.get('scroll_pause_time', 2)
        
        last_height = 0
        scroll_attempts = 0
        max_scroll_attempts = 50
        
        while len(self.restaurants) < max_results and scroll_attempts < max_scroll_attempts:
            # Scroll down
            self.driver.execute_script('arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
            time.sleep(scroll_pause)
            
            # Check if we've reached the end
            new_height = self.driver.execute_script('return arguments[0].scrollHeight', scrollable_div)
            
            if new_height == last_height:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                
            last_height = new_height
            
            # Count current results
            results = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="feed"] > div > div > a')
            print(f"Loaded {len(results)} results so far...")
            
            if scroll_attempts >= 3:
                print("Reached end of results")
                break
    
    def extract_restaurant_data(self, element):
        """Extract data from a single restaurant element."""
        try:
            # Click on the restaurant to open details
            element.click()
            time.sleep(self.config.get('request_delay', 1.5))
            
            restaurant_data = {}
            
            # Extract name
            try:
                name_element = self.driver.find_element(By.CSS_SELECTOR, 'h1.DUwDvf')
                restaurant_data['name'] = name_element.text
            except NoSuchElementException:
                restaurant_data['name'] = 'Unknown'
            
            # Extract rating
            try:
                rating_element = self.driver.find_element(By.CSS_SELECTOR, 'div.F7nice span[aria-hidden="true"]')
                restaurant_data['rating'] = float(rating_element.text.replace(',', '.'))
            except (NoSuchElementException, ValueError):
                restaurant_data['rating'] = None
            
            # Extract number of reviews
            try:
                reviews_element = self.driver.find_element(By.CSS_SELECTOR, 'div.F7nice span[aria-label*="review"]')
                reviews_text = reviews_element.get_attribute('aria-label')
                reviews_match = re.search(r'([\d,]+)\s*review', reviews_text)
                if reviews_match:
                    restaurant_data['reviews'] = int(reviews_match.group(1).replace(',', ''))
                else:
                    restaurant_data['reviews'] = None
            except NoSuchElementException:
                restaurant_data['reviews'] = None
            
            # Extract price level
            try:
                price_element = self.driver.find_element(By.CSS_SELECTOR, 'span[aria-label*="Price"]')
                price_text = price_element.get_attribute('aria-label')
                restaurant_data['price_level'] = price_text
            except NoSuchElementException:
                restaurant_data['price_level'] = None
            
            # Extract address
            try:
                address_button = self.driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"]')
                restaurant_data['address'] = address_button.get_attribute('aria-label').replace('Address: ', '')
            except NoSuchElementException:
                restaurant_data['address'] = None
            
            # Extract phone
            try:
                phone_button = self.driver.find_element(By.CSS_SELECTOR, 'button[data-item-id*="phone"]')
                restaurant_data['phone'] = phone_button.get_attribute('aria-label').replace('Phone: ', '')
            except NoSuchElementException:
                restaurant_data['phone'] = None
            
            # Extract website
            try:
                website_link = self.driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
                restaurant_data['website'] = website_link.get_attribute('href')
            except NoSuchElementException:
                restaurant_data['website'] = None
            
            # Extract cuisine type
            try:
                cuisine_button = self.driver.find_element(By.CSS_SELECTOR, 'button[jsaction*="category"]')
                restaurant_data['cuisine'] = cuisine_button.get_attribute('aria-label')
            except NoSuchElementException:
                restaurant_data['cuisine'] = None
            
            # Extract coordinates from URL
            try:
                current_url = self.driver.current_url
                coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
                if coords_match:
                    restaurant_data['latitude'] = float(coords_match.group(1))
                    restaurant_data['longitude'] = float(coords_match.group(2))
                else:
                    restaurant_data['latitude'] = None
                    restaurant_data['longitude'] = None
            except:
                restaurant_data['latitude'] = None
                restaurant_data['longitude'] = None
            
            return restaurant_data
            
        except Exception as e:
            print(f"Error extracting restaurant data: {e}")
            return None
    
    def scrape(self):
        """Main scraping method."""
        try:
            self.setup_driver()
            self.search_restaurants()
            self.scroll_results()
            
            # Get all restaurant links
            restaurant_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="feed"] > div > div > a')
            
            max_results = self.config.get('max_results', 100)
            total_to_scrape = min(len(restaurant_elements), max_results)
            
            print(f"\nExtracting data from {total_to_scrape} restaurants...")
            
            for idx, element in enumerate(restaurant_elements[:total_to_scrape]):
                print(f"Processing restaurant {idx + 1}/{total_to_scrape}")
                
                data = self.extract_restaurant_data(element)
                
                if data and data.get('name') != 'Unknown':
                    self.restaurants.append(data)
                    print(f"  ✓ {data['name']} - Rating: {data.get('rating', 'N/A')}")
                
                # Go back to results list
                try:
                    back_button = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label*="Back"]')
                    back_button.click()
                    time.sleep(1)
                except NoSuchElementException:
                    # If back button not found, re-search
                    self.search_restaurants()
                    self.scroll_results()
                    restaurant_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="feed"] > div > div > a')
            
            print(f"\n✓ Successfully scraped {len(self.restaurants)} restaurants")
            
        except Exception as e:
            print(f"Error during scraping: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def save_data(self):
        """Save scraped data to JSON file."""
        output_file = self.config.get('output_file', 'restaurants_data.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.restaurants, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Data saved to {output_file}")
        print(f"Total restaurants: {len(self.restaurants)}")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Google Maps Scraper for Amsterdam')
    parser.add_argument('--type', 
                        choices=['restaurants', 'farms'], 
                        default='restaurants',
                        help='Type of places to scrape (default: restaurants)')
    parser.add_argument('--config', 
                        default='config.json',
                        help='Path to configuration file (default: config.json)')
    
    args = parser.parse_args()
    
    # Display header based on type
    print("=" * 60)
    print(f"Google Maps {args.type.capitalize()} Scraper - Amsterdam")
    print("=" * 60)
    print(f"Using config: {args.config}")
    print(f"Scraping type: {args.type}")
    print("=" * 60)
    
    scraper = GoogleMapsRestaurantScraper(config_path=args.config)
    scraper.scrape()
    scraper.save_data()
    
    print("\n" + "=" * 60)
    print("Scraping completed!")
    print(f"Data saved to: {scraper.config.get('output_file')}")
    print("=" * 60)
