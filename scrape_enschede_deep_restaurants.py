import sys
import os
import asyncio
import csv
import re
import urllib.parse
import httpx
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
OUTPUT_CSV  = "data/enschede_restaurants_data.csv"
OUTPUT_JSON = "data/enschede_restaurants_data.json"
LOG_FILE    = "logs/enschede_deep_restaurants.log"
PROGRESS_F  = "data/enschede_deep_progress.json"

MAX_PER_QUERY  = 60
CONCURRENCY    = 4
DETAIL_TIMEOUT = 25000

DEEP_QUERIES = [
    # General & Dining
    "restaurants in Enschede",
    "eetcafé in Enschede",
    "bistro in Enschede",
    "brasserie in Enschede",
    "diner in Enschede",
    "buffet in Enschede",
    "fine dining Enschede",
    "familierestaurant Enschede",
    "terras restaurant Enschede",
    
    # Lunch, Cafes & Drinks
    "lunchroom in Enschede",
    "koffiebar in Enschede",
    "café in Enschede",
    "grand café in Enschede",
    "theehuis in Enschede",
    "ontbijt restaurant Enschede",
    "brunch in Enschede",
    "broodjeszaak in Enschede",
    "bakkerij met lunch Enschede",
    "banketbakkerij Enschede",
    "ijssalon in Enschede",
    "ijswinkel in Enschede",
    "bar in Enschede",
    "pub in Enschede",
    "borrel Bar Enschede",
    "proeflokaal Enschede",
    "cocktailbar Enschede",

    # Fastfood, Snacks & Delivery
    "cafetaria in Enschede",
    "snackbar in Enschede",
    "frituur in Enschede",
    "patatzaak in Enschede",
    "shoarma in Enschede",
    "döner in Enschede",
    "kebab in Enschede",
    "grillroom in Enschede",
    "burgers in Enschede",
    "hamburger restaurant Enschede",
    "kiprestaurant Enschede",
    "afhaalrestaurant Enschede",
    "maaltijdbezorging Enschede",
    "traiteur in Enschede",
    "cateraar in Enschede",
    "foodtruck Enschede",

    # World Cuisines
    "Italiaans restaurant in Enschede",
    "Pizzeria in Enschede",
    "pizza bezorgen Enschede",
    "Aziatisch restaurant in Enschede",
    "Sushi in Enschede",
    "sushi bar Enschede",
    "Chinees restaurant in Enschede",
    "Indisch restaurant in Enschede",
    "Indonesisch restaurant in Enschede",
    "Thais restaurant in Enschede",
    "Vietnamees restaurant in Enschede",
    "Japans restaurant in Enschede",
    "Koreaans restaurant in Enschede",
    "Grieks restaurant in Enschede",
    "Turks restaurant in Enschede",
    "Syrisch restaurant in Enschede",
    "Libanees restaurant in Enschede",
    "Spaans restaurant in Enschede",
    "tapas bar in Enschede",
    "Mexicaans restaurant in Enschede",
    "Argentijns restaurant in Enschede",
    "Steakhouse in Enschede",
    "Balkan restaurant in Enschede",
    "Surinaams restaurant in Enschede",
    "Surinaamse eethuis Enschede",
    "Vegan restaurant in Enschede",
    "Vegetarisch restaurant in Enschede",
    "Halal restaurant in Enschede"
]

MICRO_LOCATIONS = [
    "Enschede",
    "Oude Markt Enschede",
    "Langestraat Enschede",
    "De Heurne Enschede",
    "Haverstraatpassage Enschede",
    "Binnenstad Enschede",
    "Station Enschede",
    "Roombeek Enschede",
    "Deppenbroek Enschede",
    "Mekkelholt Enschede",
    "Boddenkamp Enschede",
    "Horstlanden Enschede",
    "Getfert Enschede",
    "Hogeland Enschede",
    "Ribbelt Enschede",
    "Stokhorst Enschede",
    "Eschmarke Enschede",
    "Dolphia Enschede",
    "Glanerbrug Enschede",
    "Glanerbrug Centrum",
    "Lonneker Enschede",
    "Twekkelerveld Enschede",
    "Tubantia Enschede",
    "Pathmos Enschede",
    "Stadsveld Enschede",
    "Boswinkel Enschede",
    "Ruwenbos Enschede",
    "Wesselerbrink Enschede",
    "Wesselerbrink Winkelcentrum",
    "Helmerhoek Enschede",
    "Usselo Enschede",
    "Boekelo Enschede",
    "Kennispark Twente Enschede",
    "Universiteit Twente Enschede"
]

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
_log = open(LOG_FILE, "a", encoding="utf-8")

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    _log.write(line + "\n")
    _log.flush()

FIELDS = ["name", "cuisine", "rating", "reviews", "price_level", "address", "phone", "website", "latitude", "longitude", "url"]

def init_files():
    if not os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(FIELDS)

def save_json(records: list):
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def append_csv_row(row: dict):
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([row.get(k, "") for k in FIELDS])

def load_records_from_csv() -> list:
    if not os.path.exists(OUTPUT_CSV):
        return []
    records = []
    try:
        with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                records.append(r)
    except Exception:
        pass
    return records

def load_progress() -> set:
    if os.path.exists(PROGRESS_F):
        try:
            return set(json.load(open(PROGRESS_F)))
        except Exception:
            pass
    return set()

def save_progress(done: set):
    with open(PROGRESS_F, "w") as f:
        json.dump(list(done), f)

def parse_review_count(text: str) -> str:
    m = re.search(r'[\(\s]([0-9][0-9,]*)\s*(?:reviews?|recensies?|Google reviews?)?\s*[\)\s]', text, re.I)
    if not m:
        m = re.search(r'([0-9][0-9,]+)', text)
    if m:
        return m.group(1).replace(",", "")
    return ""

def parse_lat_lng(url: str) -> tuple[str, str]:
    m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
    if m:
        return m.group(1), m.group(2)
    return "", ""

# ---------------------------------------------------------------------------
# SCRAPER CLASS
# ---------------------------------------------------------------------------
class EnschedeDeepRestaurantScraper:
    def __init__(self):
        self.seen_urls = set()
        self.seen_names = set()
        self.records = load_records_from_csv()
        self.done_queries = load_progress()
        init_files()

        for r in self.records:
            if r.get("url"):
                self.seen_urls.add(r["url"])
            if r.get("name"):
                self.seen_names.add(r["name"].lower().strip())

    async def run(self):
        log("=" * 70)
        log("START: Enschede Deep Restaurant & Food Spot Scraper")
        log(f"Existing records in database: {len(self.records)}")
        log("=" * 70)

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                
                nav_page = await context.new_page()

                for loc in MICRO_LOCATIONS:
                    for q in DEEP_QUERIES:
                        query_key = f"{q}|{loc}"
                        if query_key in self.done_queries:
                            continue

                        full_query = f"{q} in {loc}"
                        log(f"QUERY: [{full_query}] (Total mapped in dataset: {len(self.records)})")

                        urls = await self._collect_urls(nav_page, full_query)
                        new_urls = [u for u in urls if u not in self.seen_urls]
                        for u in new_urls:
                            self.seen_urls.add(u)

                        log(f"Found {len(urls)} links ({len(new_urls)} new)")

                        sem = asyncio.Semaphore(CONCURRENCY)
                        tasks = [
                            self._process_restaurant(context, url, q, sem)
                            for url in new_urls
                        ]
                        await asyncio.gather(*tasks)

                        self.done_queries.add(query_key)
                        save_progress(self.done_queries)

                await browser.close()
        except Exception as e:
            log(f"WARNING: Browser encountered error: {e}")

        save_json(self.records)
        log(f"COMPLETE: Deep scraper finished. Total Enschede food spots mapped: {len(self.records)}")

    async def _collect_urls(self, page, query: str) -> list[str]:
        encoded = urllib.parse.quote(query)
        url = f"https://www.google.com/maps/search/{encoded}/?hl=nl&gl=nl"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(3)

            for selector in ['button:has-text("Alles accepteren")', 'button:has-text("Accept all")', 'button:has-text("Ik ga akkoord")', '[aria-label="Alles accepteren"]']:
                try:
                    btn = page.locator(selector).first
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        await asyncio.sleep(1.5)
                        break
                except Exception:
                    pass

            feed = page.locator('div[role="feed"]').first
            try:
                await feed.wait_for(state="visible", timeout=6000)
            except Exception:
                links = await page.locator('a[href*="/maps/place/"]').all()
                return list(dict.fromkeys([h for l in links if (h := await l.get_attribute("href"))]))

            stall, prev = 0, 0
            for _ in range(15):
                await feed.evaluate("el => el.scrollTop = el.scrollHeight")
                await asyncio.sleep(1.5)
                links = await page.locator('a[href*="/maps/place/"]').all()
                cur = len(links)
                stall = 0 if cur > prev else stall + 1
                prev = cur
                if cur >= MAX_PER_QUERY or stall >= 4:
                    break

            links = await page.locator('a[href*="/maps/place/"]').all()
            hrefs = [h for l in links if (h := await l.get_attribute("href"))]
            return list(dict.fromkeys(hrefs))
        except Exception as e:
            log(f"URL COLLECTION ERROR: {e}")
            return []

    async def _process_restaurant(self, context, url: str, query_type: str, sem):
        async with sem:
            page = await context.new_page()
            try:
                await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
            except Exception:
                pass
                
            try:
                data = await self._extract_detail(page, url)
            finally:
                await page.close()

            if not data or not data.get("name"):
                return

            name_key = data["name"].lower().strip()
            if name_key in self.seen_names:
                return
            self.seen_names.add(name_key)

            lat, lng = parse_lat_lng(url)

            record = {
                "name": data["name"],
                "cuisine": data.get("cuisine", query_type.replace(" in Enschede", "")),
                "rating": data.get("rating", ""),
                "reviews": data.get("reviews", ""),
                "price_level": data.get("price_level", ""),
                "address": data.get("address", ""),
                "phone": data.get("phone", ""),
                "website": data.get("website", ""),
                "latitude": lat,
                "longitude": lng,
                "url": url
            }
            append_csv_row(record)
            self.records.append(record)
            save_json(self.records)

            log(f"SAVED: {record['name']} | Cuisine: {record['cuisine']} | Rating: {record['rating']} ({record['reviews']} reviews)")

    async def _extract_detail(self, page, url: str) -> dict | None:
        data = {"url": url, "name": "", "cuisine": "", "rating": "", "reviews": "", "price_level": "", "address": "", "phone": "", "website": ""}
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=DETAIL_TIMEOUT)
            await asyncio.sleep(1.0)

            # Name
            try:
                el = page.locator("h1.DUwDvf, h1").first
                data["name"] = ((await el.text_content()) or "").strip()
            except Exception:
                pass

            # Category / Cuisine
            try:
                el = page.locator("button.DkCrMe, button[jsaction*='category']").first
                if await el.count() > 0:
                    data["cuisine"] = ((await el.text_content()) or "").strip()
            except Exception:
                pass

            # Rating & Reviews
            try:
                rating_el = page.locator('span[aria-label*="sterren"], span[aria-label*="stars"], span[aria-label*="recensies"], span[aria-label*="reviews"]').first
                if await rating_el.count() > 0:
                    label = await rating_el.get_attribute("aria-label") or ""
                    m_rate = re.search(r'(\d+[.,]\d+)', label)
                    if m_rate:
                        data["rating"] = m_rate.group(1).replace(",", ".")
                    data["reviews"] = parse_review_count(label)
            except Exception:
                pass

            # Price Level (e.g. €, €€, €€€)
            try:
                price_el = page.locator('span:has-text("€")').first
                if await price_el.count() > 0:
                    data["price_level"] = ((await price_el.text_content()) or "").strip()
            except Exception:
                pass

            # Address
            try:
                el = page.locator('button[data-item-id="address"]').first
                if await el.count() > 0:
                    label = await el.get_attribute("aria-label") or ""
                    data["address"] = re.sub(r"^(Adres|Address):\s*", "", label).strip()
            except Exception:
                pass

            # Website
            try:
                el = page.locator('a[data-item-id="authority"]').first
                if await el.count() > 0:
                    data["website"] = await el.get_attribute("href") or ""
            except Exception:
                pass

            # Phone
            try:
                el = page.locator('button[data-item-id*="phone"]').first
                if await el.count() > 0:
                    label = await el.get_attribute("aria-label") or ""
                    data["phone"] = re.sub(r"^(Phone|Telefoon|Tel):\s*", "", label).strip()
            except Exception:
                pass

            return data
        except Exception:
            return None

if __name__ == "__main__":
    scraper = EnschedeDeepRestaurantScraper()
    asyncio.run(scraper.run())
