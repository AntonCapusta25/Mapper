import json
import os
import time
import re
import asyncio
import argparse
from playwright.async_api import async_playwright


class GoogleMapsRestaurantScraper:
    def __init__(self, config_path='config.json'):
        """Initialize the scraper with configuration."""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.restaurants = []
        self.seen_urls = set()
        self.restaurant_urls = []
        
        # Load existing data if available
        try:
            output_file = self.config.get('output_file', 'restaurants_data.json')
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                self.restaurants = existing_data
                # Mark existing URLs as seen
                for r in existing_data:
                    if r.get('url'):
                        self.seen_urls.add(r['url'])
                print(f"Loaded {len(self.restaurants)} existing restaurants. Skipping {len(self.seen_urls)} known URLs.")
        except FileNotFoundError:
            print("No existing data found. Starting fresh.")
        except Exception as e:
            print(f"Error loading existing data: {e}")

        
        self.collected_urls_file = 'collected_urls.json'
        self.all_collected_urls = set()
        self.load_collected_urls()
        
    def load_collected_urls(self):
        """Load previously collected URLs."""
        try:
            if os.path.exists(self.collected_urls_file):
                with open(self.collected_urls_file, 'r') as f:
                    self.all_collected_urls = set(json.load(f))
                print(f"Loaded {len(self.all_collected_urls)} previously collected URLs.")
        except Exception as e:
            print(f"Error loading collected URLs: {e}")

    def save_collected_urls(self):
        """Save collected URLs to file."""
        try:
            with open(self.collected_urls_file, 'w') as f:
                json.dump(list(self.all_collected_urls), f)
        except Exception as e:
            print(f"Error saving collected URLs: {e}")
        
    async def scrape(self):
        """Main scraping method using Collect-Then-Visit strategy."""
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=self.config.get('headless', False)
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = await context.new_page()
            
            try:
                # Check if we can resume Phase 2 directly
                # URLs we know about MINUS URLs we have data for
                unvisited_urls = [url for url in self.all_collected_urls if url not in self.seen_urls]
                
                if len(unvisited_urls) > 0:
                    print("=" * 60)
                    print(f"RESUMING: Found {len(unvisited_urls)} collected but unvisited URLs.")
                    print("Skipping Phase 1 (Search) and jumping to Phase 2 (Extraction).")
                    print("=" * 60)
                    self.restaurant_urls = unvisited_urls
                else:
                    # PHASE 1: COLLECT URLS
                    print("=" * 60)
                    print("PHASE 1: Collecting Restaurant URLs")
                    print("=" * 60)
                    
                    search_queries = self.config.get('search_queries', [])
                    if not search_queries:
                        search_queries = [self.config.get('search_query', 'restaurants in Amsterdam')]
                    
                    for query_idx, search_query in enumerate(search_queries, 1):
                        print(f"\n[Query {query_idx}/{len(search_queries)}] {search_query}")
                        await self.collect_urls(page, search_query)
                        
                    print(f"\n{'=' * 60}")
                    print(f"Total unique URLs collected: {len(self.restaurant_urls)}")
                    print(f"{'=' * 60}")
                
                # PHASE 2: EXTRACT DATA
                print("\nPHASE 2: Extracting Data from URLs")
                print("=" * 60)
                
                for idx, url in enumerate(self.restaurant_urls, 1):
                    print(f"[{idx}/{len(self.restaurant_urls)}] Processing: {url.split('?')[0]}")
                    
                    try:
                        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        await asyncio.sleep(1) # Small delay to let dynamic content settle
                        
                        data = await self.extract_restaurant_data(page)
                        
                        if data:
                            data['url'] = url
                            self.restaurants.append(data)
                            print(f"  ✓ {data.get('name', 'Unknown')} ({data.get('rating', 'N/A')}★)")
                            
                            # Save periodically
                            if idx % 10 == 0:
                                self.save_data()
                        else:
                            print("  ⚠ Failed to extract data")
                            
                    except Exception as e:
                        print(f"  ⚠ Error visiting URL: {e}")
                
            except Exception as e:
                print(f"Error during scraping: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                await browser.close()
                self.save_data()
    
    async def collect_urls(self, page, search_query):
        """Collect restaurant URLs for a single search query."""
        try:
            url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # Accept cookies if present (only on first query)
            try:
                accept_button = page.locator('button:has-text("Accept all"), button:has-text("Accepteer allemaal")').first
                if await accept_button.is_visible(timeout=3000):
                    await accept_button.click()
                    await asyncio.sleep(1)
            except:
                pass
            
            # Find scrollable div
            try:
                scrollable_div = page.locator('div[role="feed"]').first
                await scrollable_div.wait_for(timeout=10000)
            except:
                print("  ⚠ Could not find scrollable results panel")
                return

            # Scroll loop
            max_results = self.config.get('max_results_per_query', 200)
            scroll_pause = self.config.get('scroll_pause_time', 2)
            max_scroll_attempts = self.config.get('max_scroll_attempts', 30)
            
            previous_count = 0
            no_change_count = 0
            
            for _ in range(max_scroll_attempts):
                await scrollable_div.evaluate('el => el.scrollTop = el.scrollHeight')
                await asyncio.sleep(scroll_pause)
                
                # Check link count
                links = await page.locator('div[role="feed"] > div > div > a').all()
                current_count = len(links)
                
                if current_count > previous_count:
                    no_change_count = 0
                    print(f"  Loaded {current_count} links...", end='\r')
                else:
                    no_change_count += 1
                
                previous_count = current_count
                
                if current_count >= max_results or no_change_count >= 4:
                    break
            
            print(f"  Found {current_count} links total.")
            
            # Extract URLs
            links = await page.locator('div[role="feed"] > div > div > a').all()
            new_urls = 0
            
            for link in links:
                href = await link.get_attribute('href')
                if href:
                    # Add to persistent collection
                    if href not in self.all_collected_urls:
                        self.all_collected_urls.add(href)
                        self.save_collected_urls()
                    
                    # Add to current run if not seen in data
                    if href not in self.seen_urls:
                        self.seen_urls.add(href)
                        self.restaurant_urls.append(href)
                        new_urls += 1
            
            print(f"  ✓ Added {new_urls} new unique URLs")
            
        except Exception as e:
            print(f"  Error collecting URLs: {e}")

    async def extract_restaurant_data(self, page):
        """Extract data from the current restaurant page."""
        try:
            restaurant_data = {}
            
            # Extract name
            try:
                # Wait for the main heading to be visible
                try:
                    await page.wait_for_selector('h1', state='visible', timeout=5000)
                except:
                    print("  ⚠ Timeout waiting for h1")

                name_element = page.locator('h1.DUwDvf').first
                if await name_element.count() == 0:
                    name_element = page.locator('h1').first
                
                name = await name_element.text_content()
                restaurant_data['name'] = name.strip() if name else 'Unknown'
            except Exception as e:
                print(f"  ⚠ Error extracting name: {e}")
                restaurant_data['name'] = 'Unknown'
            
            # Skip if name is Unknown
            if restaurant_data['name'] == 'Unknown':
                print(f"  ⚠ Skipping {page.url} - Name not found")
                return None
            
            # Extract rating
            try:
                rating_element = page.locator('div.F7nice span[aria-hidden="true"]').first
                if await rating_element.count() > 0:
                    rating_text = await rating_element.text_content()
                    restaurant_data['rating'] = float(rating_text.replace(',', '.'))
                else:
                    restaurant_data['rating'] = None
            except:
                restaurant_data['rating'] = None
            
            # Extract number of reviews
            try:
                reviews_element = page.locator('div.F7nice span[aria-label*="review"]').first
                if await reviews_element.count() > 0:
                    reviews_text = await reviews_element.get_attribute('aria-label')
                    reviews_match = re.search(r'([\d,.]+)\s*review', reviews_text)
                    if reviews_match:
                        restaurant_data['reviews'] = int(reviews_match.group(1).replace(',', '').replace('.', ''))
                    else:
                        restaurant_data['reviews'] = None
                else:
                    restaurant_data['reviews'] = None
            except:
                restaurant_data['reviews'] = None
            
            # Extract price level
            try:
                # Try multiple selectors for price level
                price_level = None
                
                # Strategy 1: Look for aria-label with "Price:"
                price_element = page.locator('span[aria-label*="Price"]').first
                if await price_element.count() > 0:
                    price_text = await price_element.get_attribute('aria-label')
                    if price_text:
                        price_level = price_text.replace('Price: ', '')
                
                # Strategy 2: Look for dollar signs in the page
                if not price_level:
                    # Look for elements containing only $ symbols
                    dollar_elements = await page.locator('span:has-text("$")').all()
                    for elem in dollar_elements:
                        text = await elem.text_content()
                        if text and all(c in '$' for c in text.strip()):
                            price_level = text.strip()
                            break
                
                # Strategy 3: Look in the F7nice div (same area as rating)
                if not price_level:
                    price_in_rating_area = page.locator('div.F7nice span:has-text("$")').first
                    if await price_in_rating_area.count() > 0:
                        text = await price_in_rating_area.text_content()
                        if text and '$' in text:
                            # Extract just the dollar signs
                            price_level = ''.join(c for c in text if c == '$')
                
                restaurant_data['price_level'] = price_level
            except Exception as e:
                print(f"  ⚠ Error extracting price: {e}")
                restaurant_data['price_level'] = None
            
            # Extract address
            try:
                address_button = page.locator('button[data-item-id="address"]').first
                if await address_button.count() > 0:
                    address_label = await address_button.get_attribute('aria-label')
                    restaurant_data['address'] = address_label.replace('Address: ', '')
                else:
                    restaurant_data['address'] = None
            except:
                restaurant_data['address'] = None
            
            # Extract phone
            try:
                phone_button = page.locator('button[data-item-id*="phone"]').first
                if await phone_button.count() > 0:
                    phone_label = await phone_button.get_attribute('aria-label')
                    restaurant_data['phone'] = phone_label.replace('Phone: ', '')
                else:
                    restaurant_data['phone'] = None
            except:
                restaurant_data['phone'] = None
            
            # Extract website
            try:
                website_link = page.locator('a[data-item-id="authority"]').first
                if await website_link.count() > 0:
                    restaurant_data['website'] = await website_link.get_attribute('href')
                else:
                    restaurant_data['website'] = None
            except:
                restaurant_data['website'] = None
            
            # Extract cuisine type
            try:
                cuisine_button = page.locator('button[jsaction*="category"]').first
                if await cuisine_button.count() > 0:
                    restaurant_data['cuisine'] = await cuisine_button.text_content()
                else:
                    restaurant_data['cuisine'] = None
            except:
                restaurant_data['cuisine'] = None
            
            # Extract coordinates from URL
            try:
                current_url = page.url
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
            print(f"  Error extracting data: {e}")
            return None
    
    def save_data(self):
        """Save scraped data to JSON file."""
        output_file = self.config.get('output_file', 'restaurants_data.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.restaurants, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved {len(self.restaurants)} restaurants to {output_file}")


async def main():
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
    
    print("=" * 60)
    print(f"Google Maps {args.type.capitalize()} Scraper - Amsterdam")
    print("Robust Collect-Then-Visit Strategy")
    print("=" * 60)
    print(f"Using config: {args.config}")
    print(f"Scraping type: {args.type}")
    print("=" * 60)
    
    scraper = GoogleMapsRestaurantScraper(config_path=args.config)
    await scraper.scrape()
    
    print("\n" + "=" * 60)
    print("Scraping completed!")
    print(f"Data saved to: {scraper.config.get('output_file')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
