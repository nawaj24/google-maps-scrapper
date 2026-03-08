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
# # DATA MODELS
# # =====================
# @dataclass
# class Business:
#     name: str = ""
#     address: str = ""
#     website: str = ""
#     has_website: str = "No"           # 🆕 Yes / No flag
#     phone_number: str = ""
#     business_type: str = ""           # 🆕 Google's own category tag
#     reviews_count: int | None = None  # 🆕 now actually scraped
#     reviews_average: float | None = None  # 🆕 now actually scraped
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
#     """Try multiple selectors — Google Maps rotates IDs frequently."""
#     for selector in [
#         'input#searchboxinput',
#         'input[name="q"]',
#         'input[aria-label="Search Google Maps"]',
#         'input[aria-label="Search"]',
#         'input#UGojuc',
#         'input.tactile-searchbox-input',
#         'input[jsaction*="search"]',
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

#             # ✅ Handle consent / cookie popups
#             try:
#                 for consent_sel in [
#                     'button[aria-label="Accept all"]',
#                     'button:has-text("Accept all")',
#                     'button:has-text("Agree")',
#                 ]:
#                     btn = page.locator(consent_sel)
#                     if btn.count() > 0:
#                         btn.first.click()
#                         human_sleep(2, 3)
#                         break
#             except Exception:
#                 pass

#             # ✅ Robust search box
#             search_box = find_search_box(page)
#             if search_box is None:
#                 page.screenshot(path=f"debug_searchbox_{zipcode}.png")
#                 print(f"   ❌ Search box not found for ZIP {zipcode}. Screenshot saved. Skipping.")
#                 continue

#             total_keywords = len(keywords)

#             for i, keyword in enumerate(keywords, start=1):
#                 print("\n" + "=" * 70)
#                 print(f"📍 ZIP: {zipcode} | 🔎 KEYWORD ({i}/{total_keywords}): {keyword}")
#                 print("=" * 70)

#                 query = f"{keyword} near {zipcode}"
#                 print(f"🔍 Searching: {query}")

#                 # ✅ Safe search with stale element recovery
#                 try:
#                     search_box.click()
#                     search_box.triple_click()
#                     search_box.fill("")
#                     human_sleep(1, 2)
#                     search_box.type(query, delay=80)
#                     page.keyboard.press("Enter")
#                 except Exception:
#                     print("   ⚠️ Search box stale — reloading Maps...")
#                     page.goto("https://www.google.com/maps?hl=en&gl=us", timeout=60000)
#                     human_sleep(5, 7)
#                     search_box = find_search_box(page)
#                     if search_box is None:
#                         print("   ❌ Could not recover search box. Skipping keyword.")
#                         continue
#                     search_box.fill(query)
#                     page.keyboard.press("Enter")

#                 human_sleep(6, 10)

#                 feed = page.locator('//div[@role="feed"]')
#                 if feed.count() == 0:
#                     print("   ⚠️ No results feed found. Skipping keyword.")
#                     BusinessList(SCRAPED_RESULTS).save_csv("dallas_immigrant_businesses")
#                     continue

#                 # Scroll to load more
#                 prev = 0
#                 stuck = 0
#                 while True:
#                     try:
#                         feed.evaluate("el => el.scrollBy(0, 1000)")
#                     except Exception as e:
#                         print(f"   ⚠️ Scroll failed: {e}. Stopping scroll.")
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
#                             return els.first.inner_text() if els.count() > 0 else ""

#                         address = txt('//button[@data-item-id="address"]//div')

#                         if not is_texas_address(address, zipcode):
#                             print(f"   ⚠️ Skipping non-TX: {address[:60]}...")
#                             continue

#                         # ✅ Reviews — now actually scraped
#                         reviews_count = None
#                         reviews_average = None
#                         try:
#                             reviews_text = txt('//div[@jsaction="pane.reviewChart.moreReviews"]//span')
#                             if not reviews_text:
#                                 reviews_text = txt('//span[@aria-label[contains(.,"reviews")]]')
#                             match = re.search(r'([\d.]+)\s*\(?([\d,]+)\)?', reviews_text)
#                             if match:
#                                 reviews_average = float(match.group(1))
#                                 reviews_count = int(match.group(2).replace(",", ""))
#                         except Exception:
#                             pass

#                         # ✅ Business type — Google's own category label
#                         business_type = ""
#                         try:
#                             business_type = txt('//button[@jsaction="pane.rating.category"]')
#                             if not business_type:
#                                 business_type = txt('//span[@jsaction="pane.rating.category"]')
#                         except Exception:
#                             pass

#                         # Build business object
#                         b = Business()
#                         b.name             = l.get_attribute("aria-label") or ""
#                         b.address          = address
#                         b.website          = txt('//a[@data-item-id="authority"]//div')
#                         b.has_website      = "Yes" if b.website else "No"   # 🆕
#                         b.phone_number     = txt('//button[contains(@data-item-id,"phone")]//div')
#                         b.business_type    = business_type                  # 🆕
#                         b.reviews_count    = reviews_count                  # 🆕
#                         b.reviews_average  = reviews_average                # 🆕
#                         b.latitude, b.longitude = extract_coordinates(page.url)
#                         b.keyword          = keyword
#                         b.category         = get_category(keyword)
#                         b.searched_zipcode = zipcode

#                         SCRAPED_RESULTS.append(b)
#                         print(f"   ✔ [{b.category}] {b.name} | ⭐{b.reviews_average}({b.reviews_count}) | 🌐{b.has_website} | {b.phone_number}")

#                     except Exception:
#                         continue

#                 print(f"✅ Done: '{keyword}' | Total so far: {len(SCRAPED_RESULTS)}")
#                 BusinessList(SCRAPED_RESULTS).save_csv("dallas_immigrant_businesses")
#                 human_sleep(5, 8)

#         print("\n🎯 ALL ZIP CODES COMPLETED")
#         print(f"📦 Total businesses scraped: {len(SCRAPED_RESULTS)}")
#         browser.close()

# # =====================
# # MAIN
# # =====================
# if __name__ == "__main__":

#     ZIPCODES = [
#         # Vickery Meadow — highest refugee/immigrant density in Dallas
#         "75231", "75243", "75238",
#         # Oak Cliff — largest Hispanic concentration
#         "75208", "75211", "75212", "75224", "75232",
#         # East Dallas / Little Asia
#         "75214", "75223", "75228",
#         # Garland — Vietnamese, Hispanic, Chinese mix
#         "75040", "75041", "75042", "75043", "75044",
#         # Irving — South Asian, Hispanic
#         "75038", "75039", "75061", "75062",
#         # Carrollton — Koreatown / Asian hub
#         "75006", "75007", "75010",
#         # Richardson — Indian, Chinese
#         "75080", "75081", "75082",
#         # Grand Prairie — Hispanic
#         "75050", "75051", "75052",
#         # Farmers Branch
#         "75234",
#         # Lewisville
#         "75067",
#         # Mesquite
#         "75149", "75150",
#         # Plano — Indian, Korean, Chinese
#         "75023", "75024", "75025", "75074", "75075",
#     ]

#     KEYWORDS = [

#         # ===== 🇲🇽 HISPANIC / LATINO =====
#         "restaurante mexicano",
#         "taqueria",
#         "tacos",
#         "pupuseria",
#         "panaderia mexicana",
#         "carnitas restaurant",
#         "tortilleria",
#         "comida latina",
#         "restaurante salvadoreño",
#         "restaurante guatemalteco",
#         "tienda latina",
#         "supermercado latino",
#         "carniceria latina",
#         "fruteria latina",
#         "salon de belleza latino",
#         "peluqueria latina",
#         "quinceañera shop",
#         "Hispanic owned business",
#         "Latin grocery store",
#         "notario publico",
#         "construccion latina",
#         "landscaping Latino",

#         # ===== 🌍 AFRICAN / WEST AFRICAN =====
#         # "African restaurant",
#         # "Nigerian restaurant",
#         # "Ethiopian restaurant",
#         # "Senegalese restaurant",
#         # "Ghanaian restaurant",
#         # "African food market",
#         # "African catering",
#         # "fufu restaurant",
#         # "African hair braiding",
#         # "African beauty supply",
#         # "African grocery store",
#         # "African clothing store",
#         # "African fabric store",
#         # "African owned business",

#         # ===== 🌙 MIDDLE EASTERN =====
#         # "halal restaurant",
#         # "halal market",
#         # "halal grocery",
#         # "Turkish restaurant",
#         # "Lebanese restaurant",
#         # "Syrian restaurant",
#         # "Palestinian restaurant",
#         # "Iraqi restaurant",
#         # "halal butcher",
#         # "kebab restaurant",
#         # "shawarma restaurant",
#         # "Mediterranean restaurant",
#         # "Islamic clothing store",
#         # "Middle Eastern grocery",
#         # "hookah lounge",

#         # ===== 🌸 ASIAN =====
#         # "Vietnamese nail salon",
#         # "Vietnamese restaurant",
#         # "pho restaurant",
#         # "banh mi restaurant",
#         # "Vietnamese grocery",
#         # "Chinese restaurant",
#         # "dim sum restaurant",
#         # "Chinese grocery store",
#         # "Korean restaurant",
#         # "Korean BBQ",
#         # "Korean grocery store",
#         # "Korean beauty store",
#         # "Indian restaurant",
#         # "Indian grocery store",
#         # "Pakistani restaurant",
#         # "Bangladeshi restaurant",
#         # "desi restaurant",
#         # "Indian sweets shop",
#         # "Indian clothing store",
#         # "Filipino restaurant",
#         # "Filipino grocery store",
#         # "Thai restaurant",
#         # "Thai massage",

#         # ===== 🌎 CARIBBEAN =====
#         # "Caribbean restaurant",
#         # "Jamaican restaurant",
#         # "Cuban restaurant",
#         # "Dominican restaurant",
#         # "Haitian restaurant",
#         # "Caribbean grocery",
#         # "jerk chicken restaurant",
#         # "Caribbean catering",

#         # ===== 🌐 GENERAL IMMIGRANT =====
#         # "immigrant owned business",
#         # "minority owned business",
#         # "international grocery store",
#         # "world food market",
#         # "ethnic restaurant",
#         # "international restaurant",
#         # "multicultural business",
#     ]

#     scrape(KEYWORDS, ZIPCODES)



import random
import time
import os
import re
import pandas as pd
import signal
from playwright.sync_api import sync_playwright
from dataclasses import dataclass, asdict, field

# =====================
# USER AGENTS
# =====================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:121.0) Gecko/20100101 Firefox/121.0"
]

# =====================
# UNICODE CLEANER  ← fixes \ue80b and similar icon glyphs
# =====================
def clean_text(val: str) -> str:
    if not val or not isinstance(val, str):
        return ""
    # Remove ALL non-printable / non-ASCII unicode characters
    return re.sub(r'[^\x20-\x7E]', '', val).strip()

# =====================
# DATA MODELS
# =====================
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
    save_at: str = "output"

    def dataframe(self):
        return pd.json_normalize((asdict(b) for b in self.business_list), sep="_")

    def save_csv(self, filename):
        os.makedirs(self.save_at, exist_ok=True)
        df = self.dataframe()
        filepath = os.path.join(self.save_at, f"{filename}.csv")
        df.to_csv(filepath, index=False)
        print(f"✅ Saved {len(self.business_list)} rows → {filepath}")

# =====================
# HELPERS
# =====================
def human_sleep(a=2, b=4):
    time.sleep(random.uniform(a, b))

def extract_coordinates(url):
    try:
        coords = url.split("/@")[-1].split("/")[0]
        lat, lng = coords.split(",")[:2]
        return float(lat), float(lng)
    except Exception:
        return None, None

def get_category(keyword):
    k = keyword.lower()
    if any(w in k for w in [
        "mexican","taqueria","tacos","pupuseria","panaderia","carnitas",
        "tortilleria","comida","salvadoreño","guatemalteco","tienda latina",
        "supermercado","carniceria","fruteria","salon de belleza","peluqueria",
        "quinceañera","quinceanera","vestidos","pinata","hispanic","latin",
        "notario","servicios de impuestos","construccion latina","landscaping latino","restaurante"
    ]):
        return "Hispanic/Latino"
    elif any(w in k for w in [
        "african","nigerian","ethiopian","senegalese","ghanaian","jollof",
        "fufu","braiding","eritrean","somali","east african"
    ]):
        return "African/East African"
    elif any(w in k for w in [
        "halal","turkish","lebanese","syrian","palestinian","iraqi","kebab",
        "shawarma","mediterranean","islamic","arab","hookah","middle eastern"
    ]):
        return "Middle Eastern"
    elif any(w in k for w in [
        "vietnamese","pho","banh mi","chinese","dim sum","korean","bbq",
        "indian","pakistani","bangladeshi","desi","filipino","thai",
        "massage","nail salon","asian","south asian"
    ]):
        return "Asian"
    elif any(w in k for w in [
        "caribbean","jamaican","cuban","dominican","haitian","reggae","jerk chicken"
    ]):
        return "Caribbean"
    else:
        return "General Immigrant"

# =====================
# TEXAS ADDRESS FILTER
# =====================
TEXAS_CITIES = [
    "Dallas","Garland","Irving","Plano","Carrollton","Richardson",
    "Grand Prairie","Mesquite","Farmers Branch","Lewisville","Arlington",
    "Fort Worth","Frisco","McKinney","Allen","Denton"
]

def is_texas_address(address, zipcode):
    if not address:
        return False
    if "TX" in address or "Texas" in address:
        return True
    if zipcode in address:
        return True
    if any(city in address for city in TEXAS_CITIES):
        return True
    return False

# =====================
# ROBUST SEARCH BOX FINDER
# =====================
def find_search_box(page):
    for selector in [
        'input#searchboxinput',
        'input[name="q"]',
        'input[aria-label="Search Google Maps"]',
        'input[aria-label="Search"]',
        'input#UGojuc',
        'input.tactile-searchbox-input',
    ]:
        try:
            loc = page.locator(selector)
            loc.wait_for(state="visible", timeout=6000)
            print(f"   ✔ Search box found: {selector}")
            return loc
        except Exception:
            continue
    return None

# =====================
# GLOBAL STATE
# =====================
SCRAPED_RESULTS = []
SCRAPED_URLS = set()

# =====================
# SCRAPER
# =====================
def scrape(keywords, zipcodes, limit_per_search=80):
    global SCRAPED_RESULTS, SCRAPED_URLS

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(user_agent=random.choice(USER_AGENTS))
        page = context.new_page()

        def save_partial(sig=None, frame=None):
            if SCRAPED_RESULTS:
                BusinessList(SCRAPED_RESULTS).save_csv("PARTIAL_ALL_RESULTS")
            print("\n🛑 Interrupted — partial data saved.")
            browser.close()
            exit(0)

        signal.signal(signal.SIGINT, save_partial)

        for zipcode in zipcodes:
            print("\n" + "#" * 80)
            print(f"📍 STARTING ZIPCODE: {zipcode}")
            print("#" * 80)

            page.goto("https://www.google.com/maps?hl=en&gl=us", timeout=60000)
            human_sleep(6, 9)

            # Handle consent popups
            try:
                for sel in ['button[aria-label="Accept all"]','button:has-text("Accept all")','button:has-text("Agree")']:
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
                print(f"   ❌ Search box not found. Skipping ZIP {zipcode}.")
                continue

            for i, keyword in enumerate(keywords, start=1):
                print("\n" + "=" * 70)
                print(f"📍 ZIP: {zipcode} | 🔎 ({i}/{len(keywords)}): {keyword}")
                print("=" * 70)

                query = f"{keyword} near {zipcode}"

                try:
                    search_box.click()
                    search_box.triple_click()
                    search_box.fill("")
                    human_sleep(1, 2)
                    search_box.type(query, delay=80)
                    page.keyboard.press("Enter")
                except Exception:
                    print("   ⚠️ Search box stale — reloading...")
                    page.goto("https://www.google.com/maps?hl=en&gl=us", timeout=60000)
                    human_sleep(5, 7)
                    search_box = find_search_box(page)
                    if search_box is None:
                        continue
                    search_box.fill(query)
                    page.keyboard.press("Enter")

                human_sleep(6, 10)

                feed = page.locator('//div[@role="feed"]')
                if feed.count() == 0:
                    print("   ⚠️ No results. Skipping keyword.")
                    BusinessList(SCRAPED_RESULTS).save_csv("dallas_immigrant_businesses")
                    continue

                prev = 0
                stuck = 0
                while True:
                    try:
                        feed.evaluate("el => el.scrollBy(0, 1000)")
                    except Exception:
                        break
                    human_sleep(1.5, 3)
                    count = page.locator('//a[contains(@href,"/maps/place")]').count()
                    print(f"📊 Listings loaded: {count}")
                    if count >= limit_per_search:
                        break
                    if count == prev:
                        stuck += 1
                    else:
                        stuck = 0
                    if stuck >= 3:
                        break
                    prev = count

                listings = page.locator('//a[contains(@href,"/maps/place")]').all()[:limit_per_search]

                for l in listings:
                    try:
                        url = l.get_attribute("href")
                        if not url or url in SCRAPED_URLS:
                            continue
                        SCRAPED_URLS.add(url)

                        l.click()
                        human_sleep(3, 5)

                        def txt(selector):
                            els = page.locator(selector)
                            return clean_text(els.first.inner_text()) if els.count() > 0 else ""

                        address = txt('//button[@data-item-id="address"]//div')

                        if not is_texas_address(address, zipcode):
                            print(f"   ⚠️ Skipping non-TX: {address[:60]}")
                            continue

                        # Reviews
                        reviews_count = None
                        reviews_average = None
                        try:
                            rt = txt('//div[@jsaction="pane.reviewChart.moreReviews"]//span')
                            if not rt:
                                rt = txt('//span[@aria-label[contains(.,"reviews")]]')
                            m = re.search(r'([\d.]+)\s*\(?([\d,]+)\)?', rt)
                            if m:
                                reviews_average = float(m.group(1))
                                reviews_count   = int(m.group(2).replace(",", ""))
                        except Exception:
                            pass

                        # Business type
                        business_type = txt('//button[@jsaction="pane.rating.category"]')
                        if not business_type:
                            business_type = txt('//span[@jsaction="pane.rating.category"]')

                        b = Business()
                        b.name           = clean_text(l.get_attribute("aria-label") or "")
                        b.address        = address
                        b.website        = txt('//a[@data-item-id="authority"]//div')  # clean_text already applied via txt()
                        b.has_website    = "Yes" if b.website else "No"
                        b.phone_number   = txt('//button[contains(@data-item-id,"phone")]//div')
                        b.business_type  = business_type
                        b.reviews_count  = reviews_count
                        b.reviews_average = reviews_average
                        b.latitude, b.longitude = extract_coordinates(page.url)
                        b.keyword        = keyword
                        b.category       = get_category(keyword)
                        b.searched_zipcode = zipcode

                        SCRAPED_RESULTS.append(b)
                        print(f"   ✔ [{b.category}] {b.name} | ⭐{b.reviews_average}({b.reviews_count}) | 🌐{b.has_website} | {b.phone_number}")

                    except Exception:
                        continue

                print(f"✅ Done: '{keyword}' | Total: {len(SCRAPED_RESULTS)}")
                BusinessList(SCRAPED_RESULTS).save_csv("scraper_1")
                human_sleep(5, 8)

        print("\n🎯 ALL ZIP CODES COMPLETED")
        print(f"📦 Total: {len(SCRAPED_RESULTS)}")
        browser.close()

# =====================
# MAIN
# =====================
if __name__ == "__main__":
    ZIPCODES = [
        "75231","75243","75238",
        "75208","75211","75212","75224","75232",
        "75214","75223","75228",
        "75040","75041","75042","75043","75044",
        "75038","75039","75061","75062",
        "75006","75007","75010",
        "75080","75081","75082",
        "75050","75051","75052",
        "75234","75067",
        "75149","75150",
        "75023","75024","75025","75074","75075",
    ]

    KEYWORDS = [
        #         # ===== 🌍 AFRICAN / WEST AFRICAN =====
        "African restaurant",
        "Nigerian restaurant",
        "Ethiopian restaurant",
        "Senegalese restaurant",
        "Ghanaian restaurant",
        "African food market",
        "African catering",
        "fufu restaurant",
        "African hair braiding",
        "African beauty supply",
        "African grocery store",
        "African clothing store",
        "African fabric store",
        "African owned business",
    ]

    scrape(KEYWORDS, ZIPCODES)