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

# Add src to python path
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from src.utils.email_finder import is_valid_email
except ImportError:
    def is_valid_email(email):
        e = email.lower().strip()
        if e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
            return False
        bad_domains = ['example.com', 'domain.com', 'company.com', 'acme.com', 'sentry.io', 'wixpress.com']
        return not any(bd in e for bd in bad_domains)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
TARGET_TOTAL_LEADS = 500       # Target 500 Enschede leads
MAX_PER_QUERY      = 40        # Maximum Maps results per query
CONCURRENCY        = 3         # Parallel detail-page tabs
DETAIL_TIMEOUT     = 25000     # ms for Maps details load
WEBSITE_TIMEOUT    = 12000     # ms for website email crawl

OUTPUT_CSV         = "data/enschede_leads.csv"
OUTPUT_EMAILS_CSV  = "data/enschede_leads_WITH_EMAILS.csv"
LOG_FILE           = "logs/enschede_scraper.log"
PROGRESS_F         = "data/enschede_progress.json"

QUERIES = [
    "bedrijven in Enschede",
    "kantoren in Enschede",
    "restaurants in Enschede",
    "horeca in Enschede",
    "adviesbureau in Enschede",
    "IT bedrijf in Enschede",
    "technologiebedrijf Enschede",
    "zakelijke dienstverlening Enschede",
    "marketingbureau Enschede",
    "accountantskantoor Enschede",
    "architectenbureau Enschede",
    "installatiebedrijf Enschede"
]

ENSCHEDE_LOCATIONS = [
    "Enschede",
    "Enschede Centrum",
    "Kennispark Twente Enschede",
    "Enschede West",
    "Enschede Noord",
    "Enschede Zuid",
    "Glanerbrug Enschede",
    "Lonneker Enschede"
]

# ---------------------------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------------------------
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
_log = open(LOG_FILE, "a", encoding="utf-8")

def log(msg: str):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    _log.write(line + "\n")
    _log.flush()

FIELDS = ["Business Name", "Query", "City", "Country", "Phone", "Website", "Email", "Google Reviews", "Google Maps URL"]

def init_csv():
    if not os.path.exists(OUTPUT_CSV):
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(FIELDS)
    if not os.path.exists(OUTPUT_EMAILS_CSV):
        with open(OUTPUT_EMAILS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(FIELDS)

def append_row(row: dict):
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([row.get(k, "") for k in FIELDS])
    if row.get("Email"):
        with open(OUTPUT_EMAILS_CSV, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([row.get(k, "") for k in FIELDS])

def saved_leads_count() -> int:
    if not os.path.exists(OUTPUT_CSV):
        return 0
    try:
        with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)
    except Exception:
        return 0

def saved_emails_count() -> int:
    if not os.path.exists(OUTPUT_EMAILS_CSV):
        return 0
    try:
        with open(OUTPUT_EMAILS_CSV, "r", encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)
    except Exception:
        return 0

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

# Email cleaners
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
IGNORE_E = {"sentry", "example", "no-reply", "noreply", "test@", "user@domain",
            "privacy@", "support@wix", "info@wixpress", "schema", "yourname",
            "youremail", "placeholder", "domain.com", "email.com"}

def clean_email(text: str) -> str:
    found_emails = EMAIL_RE.findall(text or "")
    for m in found_emails:
        m = m.lower().rstrip(".")
        if m.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")):
            continue
        if any(ig in m for ig in IGNORE_E):
            continue
        if is_valid_email(m):
            return m
    return ""

def parse_review_count(text: str) -> int:
    m = re.search(r'[\(\s]([0-9][0-9,]*)\s*(?:reviews?|recensies?|Google reviews?)?\s*[\)\s]', text, re.I)
    if not m:
        m = re.search(r'([0-9][0-9,]+)', text)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except Exception:
            pass
    return -1

# ---------------------------------------------------------------------------
# CORE SCRAPER
# ---------------------------------------------------------------------------
class EnschedeLeadsScraper:
    def __init__(self):
        self.seen_urls = set()
        self.seen_names = set()
        self.done_queries = load_progress()
        init_csv()
        
        for existing_file in [OUTPUT_CSV, "data/enschede_offices.csv", "data/companies_enschede.csv"]:
            if os.path.exists(existing_file):
                try:
                    with open(existing_file, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for r in reader:
                            if r.get("Google Maps URL"):
                                self.seen_urls.add(r["Google Maps URL"])
                            if r.get("Business Name"):
                                self.seen_names.add(r["Business Name"].lower().strip())
                except Exception:
                    pass

    async def run(self):
        log("=" * 70)
        log("START: Enschede Leads Scraper")
        log(f"Target limit: {TARGET_TOTAL_LEADS} leads in Enschede")
        log(f"Already saved leads in batch: {saved_leads_count()} (Emails: {saved_emails_count()})")
        log("=" * 70)

        while True:
            current_count = saved_leads_count()
            if current_count >= TARGET_TOTAL_LEADS:
                log(f"SUCCESS: Target limit of {TARGET_TOTAL_LEADS} leads reached. Stopping.")
                return

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

                    for loc in ENSCHEDE_LOCATIONS:
                        for q in QUERIES:
                            current_count = saved_leads_count()
                            if current_count >= TARGET_TOTAL_LEADS:
                                log(f"SUCCESS: Target limit of {TARGET_TOTAL_LEADS} leads reached. Stopping.")
                                await browser.close()
                                return

                            query_key = f"{q}|{loc}"
                            if query_key in self.done_queries:
                                continue

                            full_query = f"{q} in {loc}"
                            log(f"QUERY: [{full_query}] (Progress: {current_count}/{TARGET_TOTAL_LEADS} leads, Emails: {saved_emails_count()})")

                            urls = await self._collect_urls(nav_page, full_query)
                            new_urls = [u for u in urls if u not in self.seen_urls]
                            for u in new_urls:
                                self.seen_urls.add(u)

                            log(f"Found {len(urls)} listings ({len(new_urls)} new)")

                            sem = asyncio.Semaphore(CONCURRENCY)
                            tasks = [
                                self._process_place(context, url, q, "Enschede", "Netherlands", sem)
                                for url in new_urls
                            ]
                            await asyncio.gather(*tasks)

                            self.done_queries.add(query_key)
                            save_progress(self.done_queries)

                    await browser.close()
                    break
            except Exception as e:
                log(f"WARNING: Browser crashed: {e}. Recreating browser in 5 seconds...")
                await asyncio.sleep(5)

        log("COMPLETE: Enschede Scraper finished work.")

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
            for _ in range(10):
                await feed.evaluate("el => el.scrollTop = el.scrollHeight")
                await asyncio.sleep(1.5)
                links = await page.locator('a[href*="/maps/place/"]').all()
                cur = len(links)
                stall = 0 if cur > prev else stall + 1
                prev = cur
                if cur >= MAX_PER_QUERY or stall >= 3:
                    break

            links = await page.locator('a[href*="/maps/place/"]').all()
            hrefs = [h for l in links if (h := await l.get_attribute("href"))]
            return list(dict.fromkeys(hrefs))
        except Exception as e:
            log(f"URL COLLECTION ERROR: {e}")
            return []

    async def _process_place(self, context, url: str, query: str, city: str, country: str, sem):
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

            reviews = data.get("reviews", -1)

            email = ""
            if data.get("website"):
                email = await self._find_email(context, data["website"])

            row = {
                "Business Name": data["name"],
                "Query": query,
                "City": city,
                "Country": country,
                "Phone": data.get("phone", ""),
                "Website": data.get("website", ""),
                "Email": email,
                "Google Reviews": reviews if reviews >= 0 else "",
                "Google Maps URL": url
            }
            append_row(row)
            log(f"SAVED: {data['name']} | City: {city}, {country} | Phone: {row['Phone']} | Email: {email or 'none'} | Reviews: {reviews}")

    async def _extract_detail(self, page, url: str) -> dict | None:
        data = {"url": url, "name": "", "website": "", "phone": "", "reviews": -1}
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=DETAIL_TIMEOUT)
            await asyncio.sleep(1.0)

            # Name
            try:
                el = page.locator("h1.DUwDvf, h1").first
                data["name"] = ((await el.text_content()) or "").strip()
            except Exception:
                pass

            # Reviews
            try:
                rating_el = page.locator('span[aria-label*="reviews"], span[aria-label*="recensies"]').first
                if await rating_el.count() > 0:
                    label = await rating_el.get_attribute("aria-label") or ""
                    data["reviews"] = parse_review_count(label)
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

    async def _find_email(self, context, url: str) -> str:
        if not url or not url.startswith("http"):
            return ""
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(headers=headers, timeout=6, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    html = resp.text
                    email = clean_email(html)
                    if email:
                        return email
                        
                    sub_links = re.findall(r'href=["\']([^"\']*(?:contact|over-ons|contact-ons|info)[^"\']*)["\']', html, re.IGNORECASE)
                    for path in list(set(sub_links))[:3]:
                        sub_url = urllib.parse.urljoin(url, path)
                        if sub_url.startswith("http"):
                            try:
                                sub_resp = await client.get(sub_url, timeout=4)
                                if sub_resp.status_code == 200:
                                    email = clean_email(sub_resp.text)
                                    if email:
                                        return email
                            except Exception:
                                pass
        except Exception:
            pass

        page = await context.new_page()
        try:
            await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())
            await page.goto(url, wait_until="domcontentloaded", timeout=WEBSITE_TIMEOUT)
            await asyncio.sleep(1)

            for link in await page.locator('a[href^="mailto:"]').all():
                href = (await link.get_attribute("href") or "").replace("mailto:", "").split("?")[0].strip()
                email = clean_email(href)
                if email:
                    return email

            body = await page.evaluate("document.body.innerText")
            email = clean_email(body)
            if email:
                return email

            contact_btn = page.locator('a:has-text("Contact"), a:has-text("Over ons"), a[href*="contact"]').first
            if await contact_btn.count() > 0:
                contact_href = await contact_btn.get_attribute("href") or ""
                contact_url = urllib.parse.urljoin(url, contact_href)
                await page.goto(contact_url, wait_until="domcontentloaded", timeout=8000)
                await asyncio.sleep(1)

                for link in await page.locator('a[href^="mailto:"]').all():
                    href = (await link.get_attribute("href") or "").replace("mailto:", "").split("?")[0].strip()
                    email = clean_email(href)
                    if email:
                        return email

                body = await page.evaluate("document.body.innerText")
                email = clean_email(body)
                if email:
                    return email
        except Exception:
            pass
        finally:
            await page.close()
            
        return ""

if __name__ == "__main__":
    scraper = EnschedeLeadsScraper()
    asyncio.run(scraper.run())
