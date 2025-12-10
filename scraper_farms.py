import json
import os
import time
import re
import asyncio
from playwright.async_api import async_playwright


class GoogleMapsFarmScraper:
    def __init__(self, config_path='config_farms.json'):
        """Initialize the scraper with configuration."""
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.farms = []
        self.seen_urls = set()
        self.farm_urls = []
        
        # Load existing data if available
        try:
            output_file = self.config.get('output_file', 'farms_data.json')
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                self.farms = existing_data
                # Mark existing URLs as seen
                for farm in existing_data:
                    if farm.get('url'):
                        self.seen_urls.add(farm['url'])
                print(f"Loaded {len(self.farms)} existing farms. Skipping {len(self.seen_urls)} known URLs.")
        except FileNotFoundError:
            print("No existing data found. Starting fresh.")
        except Exception as e:
            print(f"Error loading existing data: {e}")

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
                # PHASE 1: COLLECT URLS
                print("=" * 60)
                print("PHASE 1: Collecting Farm URLs")
                print("=" * 60)
                
                search_queries = self.config.get('search_queries', [])
                if not search_queries:
                    search_queries = [self.config.get('search_query', 'farms in Amsterdam')]
                
                for query_idx, search_query in enumerate(search_queries, 1):
                    print(f"\n[Query {query_idx}/{len(search_queries)}] {search_query}")
                    await self.collect_urls(page, search_query)
                    
                print(f"\n{'=' * 60}")
                print(f"Total unique URLs collected: {len(self.farm_urls)}")
                print(f"{'=' * 60}")
                
                # PHASE 2: EXTRACT DATA
                print("\nPHASE 2: Extracting Data from URLs")
                print("=" * 60)
                
                for idx, url in enumerate(self.farm_urls, 1):
                    print(f"[{idx}/{len(self.farm_urls)}] Processing: {url.split('?')[0][:80]}...")
                    
                    try:
                        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                        await asyncio.sleep(1.5)  # Let dynamic content settle
                        
                        data = await self.extract_farm_data(page)
                        
                        if data:
                            data['url'] = url
                            self.farms.append(data)
                            print(f"  ✓ {data.get('name', 'Unknown')} ({data.get('rating', 'N/A')}★)")
                            
                            # Save periodically
                            if idx % 5 == 0:
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
        """Collect farm URLs for the search query."""
        try:
            url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)
            
            # Accept cookies if present
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
            max_results = self.config.get('max_results_per_query', 100)
            scroll_pause = self.config.get('scroll_pause_time', 2)
            max_scroll_attempts = 30
            
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
            
            print(f"  Found {current_count} links total.                    ")
            
            # Extract URLs
            links = await page.locator('div[role="feed"] > div > div > a').all()
            new_urls = 0
            
            for link in links:
                href = await link.get_attribute('href')
                if href and href not in self.seen_urls:
                    self.seen_urls.add(href)
                    self.farm_urls.append(href)
                    new_urls += 1
            
            print(f"  ✓ Added {new_urls} new unique URLs")
            
        except Exception as e:
            print(f"  Error collecting URLs: {e}")

    async def extract_farm_data(self, page):
        """Extract data from the current farm page."""
        try:
            farm_data = {}
            
            # Extract name
            try:
                await page.wait_for_selector('h1', state='visible', timeout=5000)
                name_element = page.locator('h1.DUwDvf').first
                if await name_element.count() == 0:
                    name_element = page.locator('h1').first
                
                name = await name_element.text_content()
                farm_data['name'] = name.strip() if name else 'Unknown'
            except Exception as e:
                farm_data['name'] = 'Unknown'
            
            # Skip if name is Unknown
            if farm_data['name'] == 'Unknown':
                return None
            
            # Extract rating
            try:
                rating_element = page.locator('div.F7nice span[aria-hidden="true"]').first
                if await rating_element.count() > 0:
                    rating_text = await rating_element.text_content()
                    farm_data['rating'] = float(rating_text.replace(',', '.'))
                else:
                    farm_data['rating'] = None
            except:
                farm_data['rating'] = None
            
            # Extract number of reviews
            try:
                reviews_element = page.locator('div.F7nice span[aria-label*="review"]').first
                if await reviews_element.count() > 0:
                    reviews_text = await reviews_element.get_attribute('aria-label')
                    reviews_match = re.search(r'([\d,.]+)\s*review', reviews_text)
                    if reviews_match:
                        farm_data['reviews'] = int(reviews_match.group(1).replace(',', '').replace('.', ''))
                    else:
                        farm_data['reviews'] = None
                else:
                    farm_data['reviews'] = None
            except:
                farm_data['reviews'] = None
            
            # Extract address
            try:
                address_button = page.locator('button[data-item-id="address"]').first
                if await address_button.count() > 0:
                    address_label = await address_button.get_attribute('aria-label')
                    farm_data['address'] = address_label.replace('Address: ', '')
                else:
                    farm_data['address'] = None
            except:
                farm_data['address'] = None
            
            # Extract phone
            try:
                phone_button = page.locator('button[data-item-id*="phone"]').first
                if await phone_button.count() > 0:
                    phone_label = await phone_button.get_attribute('aria-label')
                    farm_data['phone'] = phone_label.replace('Phone: ', '')
                else:
                    farm_data['phone'] = None
            except:
                farm_data['phone'] = None
            
            # Extract website
            try:
                website_link = page.locator('a[data-item-id="authority"]').first
                if await website_link.count() > 0:
                    farm_data['website'] = await website_link.get_attribute('href')
                else:
                    farm_data['website'] = None
            except:
                farm_data['website'] = None
            
            # Extract farm type (using cuisine field for compatibility)
            try:
                cuisine_button = page.locator('button[jsaction*="category"]').first
                if await cuisine_button.count() > 0:
                    farm_data['cuisine'] = await cuisine_button.text_content()
                else:
                    farm_data['cuisine'] = None
            except:
                farm_data['cuisine'] = None
            
            # Extract coordinates from URL
            try:
                current_url = page.url
                coords_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
                if coords_match:
                    farm_data['latitude'] = float(coords_match.group(1))
                    farm_data['longitude'] = float(coords_match.group(2))
                else:
                    farm_data['latitude'] = None
                    farm_data['longitude'] = None
            except:
                farm_data['latitude'] = None
                farm_data['longitude'] = None
            
            return farm_data
            
        except Exception as e:
            print(f"  Error extracting data: {e}")
            return None
    
    def save_data(self):
        """Save scraped data to JSON file."""
        output_file = self.config.get('output_file', 'farms_data.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.farms, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ Saved {len(self.farms)} farms to {output_file}")


async def main():
    print("=" * 60)
    print("Google Maps Farms Scraper - Amsterdam")
    print("=" * 60)
    
    scraper = GoogleMapsFarmScraper()
    await scraper.scrape()
    
    print("\n" + "=" * 60)
    print("Scraping completed!")
    print(f"Total farms collected: {len(scraper.farms)}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
