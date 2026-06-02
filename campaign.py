

# import random
# import time
# import os
# import re
# import pandas as pd
# import signal
# from playwright.sync_api import sync_playwright
# from dataclasses import dataclass, asdict, field

# # =====================
# # USER AGENTS
# # =====================
# USER_AGENTS = [
#     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
#     "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
#     "Mozilla/5.0 (Windows NT 10.0; rv:121.0) Gecko/20100101 Firefox/121.0"
# ]

# # =====================
# # UNICODE CLEANER  ← fixes \ue80b and similar icon glyphs
# # =====================
# def clean_text(val: str) -> str:
#     if not val or not isinstance(val, str):
#         return ""
#     # Remove ALL non-printable / non-ASCII unicode characters
#     return re.sub(r'[^\x20-\x7E]', '', val).strip()

# # =====================
# # DATA MODELS
# # =====================
# @dataclass
# class Business:
#     name: str = ""
#     address: str = ""
#     website: str = ""
#     has_website: str = "No"
#     phone_number: str = ""
#     business_type: str = ""
#     reviews_count: int | None = None
#     reviews_average: float | None = None
#     latitude: float | None = None
#     longitude: float | None = None
#     keyword: str = ""
#     category: str = ""
#     searched_zipcode: str = ""

# @dataclass
# class BusinessList:
#     business_list: list[Business] = field(default_factory=list)
#     save_at: str = "output"

#     def dataframe(self):
#         return pd.json_normalize((asdict(b) for b in self.business_list), sep="_")

#     def save_csv(self, filename):
#         os.makedirs(self.save_at, exist_ok=True)
#         df = self.dataframe()
#         filepath = os.path.join(self.save_at, f"{filename}.csv")
#         df.to_csv(filepath, index=False)
#         print(f"✅ Saved {len(self.business_list)} rows → {filepath}")

# # =====================
# # HELPERS
# # =====================
# def human_sleep(a=2, b=4):
#     time.sleep(random.uniform(a, b))

# def extract_coordinates(url):
#     try:
#         coords = url.split("/@")[-1].split("/")[0]
#         lat, lng = coords.split(",")[:2]
#         return float(lat), float(lng)
#     except Exception:
#         return None, None

# def get_category(keyword):
#     k = keyword.lower()
#     if any(w in k for w in [
#         "mexican","taqueria","tacos","pupuseria","panaderia","carnitas",
#         "tortilleria","comida","salvadoreño","guatemalteco","tienda latina",
#         "supermercado","carniceria","fruteria","salon de belleza","peluqueria",
#         "quinceañera","quinceanera","vestidos","pinata","hispanic","latin",
#         "notario","servicios de impuestos","construccion latina","landscaping latino","restaurante"
#     ]):
#         return "Hispanic/Latino"
#     elif any(w in k for w in [
#         "african","nigerian","ethiopian","senegalese","ghanaian","jollof",
#         "fufu","braiding","eritrean","somali","east african"
#     ]):
#         return "African/East African"
#     elif any(w in k for w in [
#         "halal","turkish","lebanese","syrian","palestinian","iraqi","kebab",
#         "shawarma","mediterranean","islamic","arab","hookah","middle eastern"
#     ]):
#         return "Middle Eastern"
#     elif any(w in k for w in [
#         "vietnamese","pho","banh mi","chinese","dim sum","korean","bbq",
#         "indian","pakistani","bangladeshi","desi","filipino","thai",
#         "massage","nail salon","asian","south asian"
#     ]):
#         return "Asian"
#     elif any(w in k for w in [
#         "caribbean","jamaican","cuban","dominican","haitian","reggae","jerk chicken"
#     ]):
#         return "Caribbean"
#     else:
#         return "General Immigrant"

# # =====================
# # TEXAS ADDRESS FILTER
# # =====================
# TEXAS_CITIES = [
#     "Dallas","Garland","Irving","Plano","Carrollton","Richardson",
#     "Grand Prairie","Mesquite","Farmers Branch","Lewisville","Arlington",
#     "Fort Worth","Frisco","McKinney","Allen","Denton"
# ]

# def is_texas_address(address, zipcode):
#     if not address:
#         return False
#     if "TX" in address or "Texas" in address:
#         return True
#     if zipcode in address:
#         return True
#     if any(city in address for city in TEXAS_CITIES):
#         return True
#     return False

# # =====================
# # ROBUST SEARCH BOX FINDER
# # =====================
# def find_search_box(page):
#     for selector in [
#         'input#searchboxinput',
#         'input[name="q"]',
#         'input[aria-label="Search Google Maps"]',
#         'input[aria-label="Search"]',
#         'input#UGojuc',
#         'input.tactile-searchbox-input',
#     ]:
#         try:
#             loc = page.locator(selector)
#             loc.wait_for(state="visible", timeout=6000)
#             print(f"   ✔ Search box found: {selector}")
#             return loc
#         except Exception:
#             continue
#     return None

# # =====================
# # GLOBAL STATE
# # =====================
# SCRAPED_RESULTS = []
# SCRAPED_URLS = set()

# # =====================
# # SCRAPER
# # =====================
# def scrape(keywords, zipcodes, limit_per_search=80):
#     global SCRAPED_RESULTS, SCRAPED_URLS

#     with sync_playwright() as p:
#         browser = p.chromium.launch(
#             headless=False,
#             args=["--disable-blink-features=AutomationControlled"]
#         )
#         context = browser.new_context(user_agent=random.choice(USER_AGENTS))
#         page = context.new_page()

#         def save_partial(sig=None, frame=None):
#             if SCRAPED_RESULTS:
#                 BusinessList(SCRAPED_RESULTS).save_csv("PARTIAL_ALL_RESULTS")
#             print("\n🛑 Interrupted — partial data saved.")
#             browser.close()
#             exit(0)

#         signal.signal(signal.SIGINT, save_partial)

#         for zipcode in zipcodes:
#             print("\n" + "#" * 80)
#             print(f"📍 STARTING ZIPCODE: {zipcode}")
#             print("#" * 80)

#             page.goto("https://www.google.com/maps?hl=en&gl=us", timeout=60000)
#             human_sleep(6, 9)

#             # Handle consent popups
#             try:
#                 for sel in ['button[aria-label="Accept all"]','button:has-text("Accept all")','button:has-text("Agree")']:
#                     btn = page.locator(sel)
#                     if btn.count() > 0:
#                         btn.first.click()
#                         human_sleep(2, 3)
#                         break
#             except Exception:
#                 pass

#             search_box = find_search_box(page)
#             if search_box is None:
#                 page.screenshot(path=f"debug_{zipcode}.png")
#                 print(f"   ❌ Search box not found. Skipping ZIP {zipcode}.")
#                 continue

#             for i, keyword in enumerate(keywords, start=1):
#                 print("\n" + "=" * 70)
#                 print(f"📍 ZIP: {zipcode} | 🔎 ({i}/{len(keywords)}): {keyword}")
#                 print("=" * 70)

#                 query = f"{keyword} near {zipcode}"

#                 try:
#                     search_box.click()
#                     search_box.triple_click()
#                     search_box.fill("")
#                     human_sleep(1, 2)
#                     search_box.type(query, delay=80)
#                     page.keyboard.press("Enter")
#                 except Exception:
#                     print("   ⚠️ Search box stale — reloading...")
#                     page.goto("https://www.google.com/maps?hl=en&gl=us", timeout=60000)
#                     human_sleep(5, 7)
#                     search_box = find_search_box(page)
#                     if search_box is None:
#                         continue
#                     search_box.fill(query)
#                     page.keyboard.press("Enter")

#                 human_sleep(6, 10)

#                 feed = page.locator('//div[@role="feed"]')
#                 if feed.count() == 0:
#                     print("   ⚠️ No results. Skipping keyword.")
#                     BusinessList(SCRAPED_RESULTS).save_csv("dallas_immigrant_businesses")
#                     continue

#                 prev = 0
#                 stuck = 0
#                 while True:
#                     try:
#                         feed.evaluate("el => el.scrollBy(0, 1000)")
#                     except Exception:
#                         break
#                     human_sleep(1.5, 3)
#                     count = page.locator('//a[contains(@href,"/maps/place")]').count()
#                     print(f"📊 Listings loaded: {count}")
#                     if count >= limit_per_search:
#                         break
#                     if count == prev:
#                         stuck += 1
#                     else:
#                         stuck = 0
#                     if stuck >= 3:
#                         break
#                     prev = count

#                 listings = page.locator('//a[contains(@href,"/maps/place")]').all()[:limit_per_search]

#                 for l in listings:
#                     try:
#                         url = l.get_attribute("href")
#                         if not url or url in SCRAPED_URLS:
#                             continue
#                         SCRAPED_URLS.add(url)

#                         l.click()
#                         human_sleep(3, 5)

#                         def txt(selector):
#                             els = page.locator(selector)
#                             return clean_text(els.first.inner_text()) if els.count() > 0 else ""

#                         address = txt('//button[@data-item-id="address"]//div')

#                         if not is_texas_address(address, zipcode):
#                             print(f"   ⚠️ Skipping non-TX: {address[:60]}")
#                             continue

#                         # Reviews
#                         reviews_count = None
#                         reviews_average = None
#                         try:
#                             rt = txt('//div[@jsaction="pane.reviewChart.moreReviews"]//span')
#                             if not rt:
#                                 rt = txt('//span[@aria-label[contains(.,"reviews")]]')
#                             m = re.search(r'([\d.]+)\s*\(?([\d,]+)\)?', rt)
#                             if m:
#                                 reviews_average = float(m.group(1))
#                                 reviews_count   = int(m.group(2).replace(",", ""))
#                         except Exception:
#                             pass

#                         # Business type
#                         business_type = txt('//button[@jsaction="pane.rating.category"]')
#                         if not business_type:
#                             business_type = txt('//span[@jsaction="pane.rating.category"]')

#                         b = Business()
#                         b.name           = clean_text(l.get_attribute("aria-label") or "")
#                         b.address        = address
#                         b.website        = txt('//a[@data-item-id="authority"]//div')  # clean_text already applied via txt()
#                         b.has_website    = "Yes" if b.website else "No"
#                         b.phone_number   = txt('//button[contains(@data-item-id,"phone")]//div')
#                         b.business_type  = business_type
#                         b.reviews_count  = reviews_count
#                         b.reviews_average = reviews_average
#                         b.latitude, b.longitude = extract_coordinates(page.url)
#                         b.keyword        = keyword
#                         b.category       = get_category(keyword)
#                         b.searched_zipcode = zipcode

#                         SCRAPED_RESULTS.append(b)
#                         print(f"   ✔ [{b.category}] {b.name} | ⭐{b.reviews_average}({b.reviews_count}) | 🌐{b.has_website} | {b.phone_number}")

#                     except Exception:
#                         continue

#                 print(f"✅ Done: '{keyword}' | Total: {len(SCRAPED_RESULTS)}")
#                 BusinessList(SCRAPED_RESULTS).save_csv("scraper_1")
#                 human_sleep(5, 8)

#         print("\n🎯 ALL ZIP CODES COMPLETED")
#         print(f"📦 Total: {len(SCRAPED_RESULTS)}")
#         browser.close()

# # =====================
# # MAIN
# # =====================
# if __name__ == "__main__":
#     ZIPCODES = [
#         "75231","75243","75238",
#         "75208","75211","75212","75224","75232",
#         "75214","75223","75228",
#         "75040","75041","75042","75043","75044",
#         "75038","75039","75061","75062",
#         "75006","75007","75010",
#         "75080","75081","75082",
#         "75050","75051","75052",
#         "75234","75067",
#         "75149","75150",
#         "75023","75024","75025","75074","75075",
#     ]

#     KEYWORDS = [
#         #         # ===== 🌍 AFRICAN / WEST AFRICAN =====
#         "African restaurant",
#         "Nigerian restaurant",
#         "Ethiopian restaurant",
#         "Senegalese restaurant",
#         "Ghanaian restaurant",
#         "African food market",
#         "African catering",
#         "fufu restaurant",
#         "African hair braiding",
#         "African beauty supply",
#         "African grocery store",
#         "African clothing store",
#         "African fabric store",
#         "African owned business",
#     ]

#     scrape(KEYWORDS, ZIPCODES)




import random
import time
import os
import re
import json
import signal

import pandas as pd
from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
OUTPUT_DIR  = "output"
OUTPUT_FILE = "dallas_food_businesses_03"          # final CSV name (no extension)
CHECKPOINT  = os.path.join(OUTPUT_DIR, "_checkpoint.json")
LIMIT_PER_SEARCH = 80                           # max listings per keyword×zipcode combo

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# ─────────────────────────────────────────
# DATA MODELS
# ─────────────────────────────────────────
@dataclass
class Business:
    name: str = ""
    address: str = ""
    website: str = ""
    has_website: str = "No"
    phone_number: str = ""
    business_type: str = ""
    reviews_count: int | None = None
    reviews_average: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    keyword: str = ""
    category: str = ""
    searched_zipcode: str = ""

@dataclass
class BusinessList:
    business_list: list[Business] = field(default_factory=list)
    save_at: str = OUTPUT_DIR

    def dataframe(self):
        return pd.json_normalize((asdict(b) for b in self.business_list), sep="_")

    def save_csv(self, filename: str):
        os.makedirs(self.save_at, exist_ok=True)
        filepath = os.path.join(self.save_at, f"{filename}.csv")
        self.dataframe().to_csv(filepath, index=False)
        print(f"  💾 Saved {len(self.business_list)} rows → {filepath}")

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def human_sleep(a=2, b=4):
    time.sleep(random.uniform(a, b))

def clean_text(val: str) -> str:
    """Strip non-printable / non-ASCII unicode characters (icon glyphs, etc.)."""
    if not val or not isinstance(val, str):
        return ""
    return re.sub(r"[^\x20-\x7E]", "", val).strip()

def normalize_key(name: str, address: str) -> str:
    """
    Dedup key: lowercase alphanum only from name + address.
    Two listings are considered the same business if both match.
    """
    n = re.sub(r"[^a-z0-9]", "", name.lower())
    a = re.sub(r"[^a-z0-9]", "", address.lower())
    return f"{n}||{a}"

def extract_coordinates(url: str):
    try:
        coords = url.split("/@")[-1].split("/")[0]
        lat, lng = coords.split(",")[:2]
        return float(lat), float(lng)
    except Exception:
        return None, None

# ─────────────────────────────────────────
# CATEGORY CLASSIFIER
# ─────────────────────────────────────────
def get_category(keyword: str) -> str:
    k = keyword.lower()
    food_words = [
        "restaurant","food","cafe","coffee","diner","catering","pizza","burger",
        "sandwich","breakfast","fast food","food truck","bakery","bistro","grill",
        "bbq","barbecue","seafood","steak","brunch","donut","smoothie","juice",
        "buffet","taqueria","tacos","sushi","ramen","pho","banh mi","soul food",
        "fried chicken","wings","sub","hoagie","dessert","ice cream","boba","tea",
    ]
    if any(w in k for w in food_words):
        return "Food & Restaurant"

    if any(w in k for w in [
        "mexican","taqueria","tacos","pupuseria","panaderia","carnitas",
        "tortilleria","comida","salvadoreño","guatemalteco","tienda latina",
        "supermercado","carniceria","fruteria","salon de belleza","peluqueria",
        "quinceañera","quinceanera","vestidos","pinata","hispanic","latin",
        "notario","servicios de impuestos","construccion latina","landscaping latino","restaurante",
    ]):
        return "Hispanic/Latino"

    if any(w in k for w in [
        "african","nigerian","ethiopian","senegalese","ghanaian","jollof",
        "fufu","braiding","eritrean","somali","east african",
    ]):
        return "African/East African"

    if any(w in k for w in [
        "halal","turkish","lebanese","syrian","palestinian","iraqi","kebab",
        "shawarma","mediterranean","islamic","arab","hookah","middle eastern",
    ]):
        return "Middle Eastern"

    if any(w in k for w in [
        "vietnamese","pho","banh mi","chinese","dim sum","korean","indian",
        "pakistani","bangladeshi","desi","filipino","thai","massage","nail salon",
        "asian","south asian",
    ]):
        return "Asian"

    if any(w in k for w in [
        "caribbean","jamaican","cuban","dominican","haitian","reggae","jerk chicken",
    ]):
        return "Caribbean"

    return "General"

# ─────────────────────────────────────────
# TEXAS / DALLAS ADDRESS FILTER
# ─────────────────────────────────────────
TEXAS_CITIES = [
    "Dallas", "Garland", "Irving", "Plano", "Carrollton", "Richardson",
    "Grand Prairie", "Mesquite", "Farmers Branch", "Lewisville", "Arlington",
    "Fort Worth", "Frisco", "McKinney", "Allen", "Denton", "Addison",
    "Balch Springs", "Rowlett", "Sachse", "Sunnyvale", "Hutchins",
]

def is_texas_address(address: str, zipcode: str) -> bool:
    if not address:
        return False
    if "TX" in address or "Texas" in address:
        return True
    if zipcode in address:
        return True
    if any(city in address for city in TEXAS_CITIES):
        return True
    return False

# ─────────────────────────────────────────
# SEARCH BOX LOCATOR
# ─────────────────────────────────────────
def find_search_box(page):
    for selector in [
        "input#searchboxinput",
        'input[name="q"]',
        'input[aria-label="Search Google Maps"]',
        'input[aria-label="Search"]',
        "input#UGojuc",
        "input.tactile-searchbox-input",
    ]:
        try:
            loc = page.locator(selector)
            loc.wait_for(state="visible", timeout=6000)
            print(f"   ✔ Search box: {selector}")
            return loc
        except Exception:
            continue
    return None

# ─────────────────────────────────────────
# CHECKPOINT + RESUME HELPERS
# ─────────────────────────────────────────
def load_checkpoint() -> set:
    """Return set of (zipcode, keyword) tuples already completed."""
    if os.path.exists(CHECKPOINT):
        try:
            with open(CHECKPOINT) as f:
                data = json.load(f)
            completed = set(tuple(x) for x in data.get("completed", []))
            print(f"  📂 Checkpoint: {len(completed)} searches already done.")
            return completed
        except Exception:
            pass
    return set()

def save_checkpoint(completed: set):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(CHECKPOINT, "w") as f:
        json.dump({"completed": [list(x) for x in completed]}, f, indent=2)

def load_existing_csv() -> tuple[list[Business], set, set]:
    """
    Load any previously saved CSV and return:
      - list of Business objects
      - set of seen URLs  (secondary dedup)
      - set of seen normalize_key strings (primary dedup)
    """
    results, urls, keys = [], set(), set()
    filepath = os.path.join(OUTPUT_DIR, f"{OUTPUT_FILE}.csv")
    if not os.path.exists(filepath):
        return results, urls, keys

    try:
        df = pd.read_csv(filepath, dtype=str)
        df = df.where(pd.notna(df), other=None)
        for _, row in df.iterrows():
            def g(col):
                return str(row[col]) if row.get(col) is not None else ""
            def gn(col):
                v = row.get(col)
                return float(v) if v is not None else None

            b = Business(
                name=g("name"), address=g("address"), website=g("website"),
                has_website=g("has_website"), phone_number=g("phone_number"),
                business_type=g("business_type"),
                reviews_count=int(float(row["reviews_count"])) if row.get("reviews_count") else None,
                reviews_average=gn("reviews_average"),
                latitude=gn("latitude"), longitude=gn("longitude"),
                keyword=g("keyword"), category=g("category"),
                searched_zipcode=g("searched_zipcode"),
            )
            results.append(b)
            keys.add(normalize_key(b.name, b.address))
        print(f"  📂 Loaded {len(results)} existing records (dedup active).")
    except Exception as e:
        print(f"  ⚠️ Could not load existing CSV: {e}")

    return results, urls, keys

# ─────────────────────────────────────────
# GLOBAL MUTABLE STATE  (mutated by signal handler)
# ─────────────────────────────────────────
SCRAPED_RESULTS: list[Business] = []
SCRAPED_URLS:    set = set()
SCRAPED_KEYS:    set = set()
COMPLETED:       set = set()

# ─────────────────────────────────────────
# MAIN SCRAPER
# ─────────────────────────────────────────
def scrape(keywords: list[str], zipcodes: list[str]):
    global SCRAPED_RESULTS, SCRAPED_URLS, SCRAPED_KEYS, COMPLETED

    # ── Load existing state ──────────────
    SCRAPED_RESULTS, SCRAPED_URLS, SCRAPED_KEYS = load_existing_csv()
    COMPLETED = load_checkpoint()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(user_agent=random.choice(USER_AGENTS))
        page = context.new_page()

        # ── Ctrl+C handler ───────────────
        def save_and_exit(sig=None, frame=None):
            print("\n\n🛑 Interrupted — saving progress...")
            BusinessList(SCRAPED_RESULTS).save_csv(OUTPUT_FILE)
            save_checkpoint(COMPLETED)
            browser.close()
            exit(0)

        signal.signal(signal.SIGINT, save_and_exit)

        # ── Outer loop: zipcodes ─────────
        for zipcode in zipcodes:
            pending = [kw for kw in keywords if (zipcode, kw) not in COMPLETED]
            if not pending:
                print(f"\n⏭️  ZIP {zipcode}: all keywords done, skipping.")
                continue

            print(f"\n{'#'*80}")
            print(f"📍 ZIP: {zipcode}  ({len(pending)} keywords remaining)")
            print(f"{'#'*80}")

            # Navigate fresh for each zipcode
            page.goto("https://www.google.com/maps?hl=en&gl=us", timeout=60000)
            human_sleep(6, 9)

            # Dismiss consent / cookie popups
            for sel in [
                'button[aria-label="Accept all"]',
                'button:has-text("Accept all")',
                'button:has-text("Agree")',
            ]:
                try:
                    btn = page.locator(sel)
                    if btn.count() > 0:
                        btn.first.click()
                        human_sleep(2, 3)
                        break
                except Exception:
                    pass

            search_box = find_search_box(page)
            if search_box is None:
                page.screenshot(path=f"debug_{zipcode}.png")
                print(f"  ❌ Search box not found — screenshot saved. Skipping ZIP.")
                continue

            # ── Inner loop: keywords ─────
            for idx, keyword in enumerate(pending, start=1):
                print(f"\n{'='*70}")
                print(f"  ZIP {zipcode} | {idx}/{len(pending)}: {keyword}")
                print(f"{'='*70}")

                # Anchor query to Dallas TX for geo accuracy
                query = f"{keyword} in {zipcode} Dallas TX"

                # ── Type query ──────────
                try:
                    search_box.click()
                    search_box.triple_click()
                    search_box.fill("")
                    human_sleep(0.8, 1.5)
                    search_box.type(query, delay=75)
                    page.keyboard.press("Enter")
                except Exception:
                    print("  ⚠️ Search box stale — reloading Maps...")
                    page.goto("https://www.google.com/maps?hl=en&gl=us", timeout=60000)
                    human_sleep(5, 7)
                    search_box = find_search_box(page)
                    if not search_box:
                        continue
                    search_box.fill(query)
                    page.keyboard.press("Enter")

                human_sleep(6, 10)

                # ── Wait for results feed ─
                feed = page.locator('//div[@role="feed"]')
                if feed.count() == 0:
                    print("  ⚠️ No results feed — skipping keyword.")
                    COMPLETED.add((zipcode, keyword))
                    save_checkpoint(COMPLETED)
                    continue

                # ── Scroll to load more ───
                prev_count = 0
                stuck = 0
                while True:
                    try:
                        feed.evaluate("el => el.scrollBy(0, 1500)")
                    except Exception:
                        break
                    human_sleep(1.5, 3.0)

                    # Detect Google's "reached the end" banner
                    end_banners = [
                        '//span[contains(text(),"reached the end")]',
                        '//span[contains(text(),"end of results")]',
                        '//p[contains(text(),"reached the end")]',
                    ]
                    at_end = any(page.locator(sel).count() > 0 for sel in end_banners)
                    if at_end:
                        print("  📄 End of list reached.")
                        break

                    count = page.locator('//a[contains(@href,"/maps/place")]').count()
                    print(f"  📊 Listings loaded: {count}")

                    if count >= LIMIT_PER_SEARCH:
                        break
                    if count == prev_count:
                        stuck += 1
                    else:
                        stuck = 0
                    if stuck >= 5:   # patient: 5 unchanged scrolls before giving up
                        break
                    prev_count = count

                # ── Scrape each listing ───
                listings = page.locator('//a[contains(@href,"/maps/place")]').all()[:LIMIT_PER_SEARCH]
                new_count = dup_count = skip_count = 0

                for listing in listings:
                    try:
                        href = listing.get_attribute("href") or ""
                        raw_name = clean_text(listing.get_attribute("aria-label") or "")

                        # Click to open side panel
                        listing.click()
                        human_sleep(3, 5)

                        # Helper: safely get text from first matching element
                        def txt(selector: str) -> str:
                            els = page.locator(selector)
                            return clean_text(els.first.inner_text()) if els.count() > 0 else ""

                        address = txt('//button[@data-item-id="address"]//div')

                        # ── Geography filter ─────────────────────
                        if not is_texas_address(address, zipcode):
                            print(f"  ⚠️ Non-TX skipped: {address[:55]}")
                            skip_count += 1
                            continue

                        # ── Dedup check (primary: name+address) ──
                        dedup_key = normalize_key(raw_name, address)
                        if dedup_key in SCRAPED_KEYS or href in SCRAPED_URLS:
                            dup_count += 1
                            print(f"  🔁 Dup: {raw_name[:45]}")
                            continue

                        # Register immediately to prevent double-add within same run
                        SCRAPED_KEYS.add(dedup_key)
                        if href:
                            SCRAPED_URLS.add(href)

                        # ── Reviews ──────────────────────────────
                        reviews_count   = None
                        reviews_average = None
                        try:
                            rt = txt('//div[@jsaction="pane.reviewChart.moreReviews"]//span')
                            if not rt:
                                rt = txt('//span[contains(@aria-label,"reviews")]')
                            m = re.search(r"([\d.]+)\s*\(?([\d,]+)\)?", rt)
                            if m:
                                reviews_average = float(m.group(1))
                                reviews_count   = int(m.group(2).replace(",", ""))
                        except Exception:
                            pass

                        # ── Business type ─────────────────────────
                        btype = txt('//button[@jsaction="pane.rating.category"]')
                        if not btype:
                            btype = txt('//span[@jsaction="pane.rating.category"]')

                        # ── Website ───────────────────────────────
                        website = txt('//a[@data-item-id="authority"]//div')

                        b = Business(
                            name            = raw_name,
                            address         = address,
                            website         = website,
                            has_website     = "Yes" if website else "No",
                            phone_number    = txt('//button[contains(@data-item-id,"phone")]//div'),
                            business_type   = btype,
                            reviews_count   = reviews_count,
                            reviews_average = reviews_average,
                            latitude        = extract_coordinates(page.url)[0],
                            longitude       = extract_coordinates(page.url)[1],
                            keyword         = keyword,
                            category        = get_category(keyword),
                            searched_zipcode= zipcode,
                        )

                        SCRAPED_RESULTS.append(b)
                        new_count += 1
                        print(
                            f"  ✔ [{b.category}] {b.name[:40]} | "
                            f"⭐{b.reviews_average}({b.reviews_count}) | "
                            f"{'🌐' if b.has_website=='Yes' else '  '} | {b.phone_number}"
                        )

                    except Exception as ex:
                        print(f"  ⚠️ Listing error: {ex}")
                        continue

                # ── Post-keyword summary & save ────────────────
                print(
                    f"\n  ✅ '{keyword}' done → "
                    f"+{new_count} new | {dup_count} dupes | {skip_count} non-TX | "
                    f"Total unique: {len(SCRAPED_RESULTS)}"
                )
                COMPLETED.add((zipcode, keyword))
                BusinessList(SCRAPED_RESULTS).save_csv(OUTPUT_FILE)
                save_checkpoint(COMPLETED)
                human_sleep(4, 7)

        # ── Final save ─────────────────────────────────────────
        print(f"\n{'='*80}")
        print(f"🎯 ALL DONE — {len(SCRAPED_RESULTS)} unique businesses saved.")
        BusinessList(SCRAPED_RESULTS).save_csv(OUTPUT_FILE)
        save_checkpoint(COMPLETED)
        browser.close()


# ─────────────────────────────────────────
# DALLAS TX ZIPCODES
# ─────────────────────────────────────────
ZIPCODES = [
    # Core Dallas
    # "75201","75202",
    "75203","75204","75205",
    "75206","75207","75208","75209","75210",
    "75211","75212","75214","75215","75216",
    "75217","75218","75219","75220","75223",
    "75224","75225","75226","75227","75228",
    "75229","75230","75231","75232","75233",
    "75234","75235","75238","75240","75243",
    "75244","75246","75247","75248","75249",
    "75251","75252","75253",
    # Garland
    "75040","75041","75042","75043","75044",
    # Irving
    "75038","75039","75061","75062","75063",
    # Carrollton / Farmers Branch
    "75006","75007","75010",
    # Richardson / Plano
    "75080","75081","75082",
    "75023","75024","75025","75074","75075",
    # Grand Prairie / Mesquite
    "75050","75051","75052",
    "75149","75150",
    # Lewisville / Denton area
    "75067","75057",
]

# ─────────────────────────────────────────
# KEYWORDS  — Restaurants & Food Businesses
# ─────────────────────────────────────────
KEYWORDS = [

    # ── FAST FOOD ──────────────────────────────────────────────
    # "fast food restaurant",
    "quick service restaurant",
    "burger restaurant",
    "chicken sandwich shop",
    "fried chicken restaurant",
    "hot wings restaurant",
    "hot dog stand",
    "drive through restaurant",

    # ── FOOD TRUCKS ────────────────────────────────────────────
    "food truck",
    "mobile food vendor",
    "street food vendor",
    "food trailer",

    # ── CAFES & COFFEE ──────────────────────────────────────────
    "cafe",
    "coffee shop",
    "espresso bar",
    "coffee roaster",
    "tea house",
    "boba tea shop",
    "bubble tea cafe",

    # ── DINERS ─────────────────────────────────────────────────
    "diner",
    "American diner",
    "family diner",
    "breakfast diner",
    "lunch diner",

    # ── CATERING ───────────────────────────────────────────────
    "catering company",
    "catering service",
    "event catering",
    "wedding catering",
    "food catering",

    # ── BAKERIES & SWEETS ───────────────────────────────────────
    "bakery",
    "donut shop",
    "pastry shop",
    "dessert shop",
    "ice cream shop",
    "smoothie bar",
    "juice bar",

    # ── PIZZA & ITALIAN ─────────────────────────────────────────
    "pizza restaurant",
    "pizza delivery",
    "Italian restaurant",

    # ── BBQ & GRILL ─────────────────────────────────────────────
    "BBQ restaurant",
    "barbecue restaurant",
    "smokehouse restaurant",
    "steakhouse",
    "grill restaurant",

    # ── SEAFOOD ────────────────────────────────────────────────
    "seafood restaurant",
    "fish and chips",
    "shrimp restaurant",

    # ── BREAKFAST & BRUNCH ──────────────────────────────────────
    "breakfast restaurant",
    "brunch restaurant",
    "pancake house",
    "waffle house",

    # ── SANDWICHES & SUBS ───────────────────────────────────────
    "sandwich shop",
    "sub shop",
    "deli",
    "hoagie shop",

    # ── SOUL FOOD & SOUTHERN ────────────────────────────────────
    "soul food restaurant",
    "southern food restaurant",
    "comfort food restaurant",

    # ── BUFFET ──────────────────────────────────────────────────
    "buffet restaurant",
    "all you can eat buffet",

    # ── ETHNIC & SPECIALTY (food-focused) ───────────────────────
    "Mexican restaurant",
    "taqueria",
    "tacos",
    "Chinese restaurant",
    "Indian restaurant",
    "Vietnamese restaurant",
    "Thai restaurant",
    "Korean BBQ",
    "Japanese restaurant",
    "sushi restaurant",
    "ramen restaurant",
    "Mediterranean restaurant",
    "Middle Eastern restaurant",
    "halal restaurant",
    "African restaurant",
    "Nigerian restaurant",
    "Ethiopian restaurant",
    "Caribbean restaurant",
    "Jamaican restaurant",
    "Salvadoran restaurant",
    "Guatemalan restaurant",

    # ── SMALL / INDEPENDENT ─────────────────────────────────────
    "small restaurant",
    "family restaurant",
    "local restaurant",
    "hole in the wall restaurant",
    "neighborhood restaurant",
    "bistro",
    "eatery",
    "lunch spot",
    "dinner restaurant",

    # ── HEALTH / SPECIALTY ──────────────────────────────────────
    "vegan restaurant",
    "vegetarian restaurant",
    "health food restaurant",
    "organic cafe",
]


# ─────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    scrape(KEYWORDS, ZIPCODES)