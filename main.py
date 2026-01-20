import random
import time
import os
import pandas as pd
import signal
from urllib.parse import urlparse
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
# DATA MODELS
# =====================
@dataclass
class Business:
    name: str = ""
    address: str = ""
    website: str = ""
    phone_number: str = ""
    latitude: float | None = None
    longitude: float | None = None
    keyword: str = ""
    searched_zipcode: str = ""
    category: str = ""

@dataclass
class BusinessList:
    business_list: list[Business] = field(default_factory=list)
    save_at: str = "output"

    def dataframe(self):
        return pd.json_normalize((asdict(b) for b in self.business_list), sep="_")

    def save_csv(self, filename):
        os.makedirs(self.save_at, exist_ok=True)
        df = self.dataframe()
        # Keep only useful columns (no reviews)
        df = df[[
            'name','address','website','phone_number',
            'latitude','longitude','keyword','searched_zipcode','category'
        ]]
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
    except:
        return None, None

# =====================
# CATEGORY FILTERING
# =====================
def is_relevant_listing(category_text: str) -> tuple[bool, str]:
    if not category_text:
        return True, "no category – kept by default"

    text = category_text.lower().strip()

    blocked_patterns = [
        "church","temple","mosque","synagogue","cathedral","religious","worship",
        "hospital","clinic","medical","healthcare","dentist","urgent care",
        "government","city of","county of","state of","public library","fire department",
        "police","sheriff","post office","school district","elementary school",
        "middle school","high school","charter school","private school","preschool",
        "daycare","nursery","nonprofit","organization","foundation","association",
        "society","community center","youth center","store","shop","retail","mall",
        "apartment","real estate","lawyer","attorney","insurance","bank","gym",
        "fitness center","personal trainer","salon","barber","restaurant","cafe",
        "hotel","motel"
    ]

    for block in blocked_patterns:
        if block in text:
            return False, f"blocked pattern: '{block}'"

    allowed_keywords = [
        "camp","after school","enrichment","program","club","center","academy","studio",
        "school of","learning","education","tutoring","lessons","classes","workshop",
        "training","coaching","sports","swim","swimming","aquatic","water safety",
        "soccer","basketball","baseball","softball","football","volleyball","tennis",
        "gymnastics","martial arts","dance","yoga","track","stem","science","coding",
        "robotics","music","piano","art","theater","chess","language","ballet",
        "drawing","painting","drama","adventure","outdoor","nature","climbing",
        "hiking","kayaking","fitness","skills","development","creative","multi-sport"
    ]

    for kw in allowed_keywords:
        if kw in text:
            return True, f"allowed keyword: '{kw}'"

    return False, "no relevant keyword found"

# =====================
# GLOBALS
# =====================
SCRAPED_RESULTS = []
SCRAPED_URLS = set()
FAILED_SEARCHES = []

# =====================
# SCRAPER
# =====================
def scrape(keywords, zipcodes, limit_per_search=80):
    global SCRAPED_RESULTS, FAILED_SEARCHES

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
            if FAILED_SEARCHES:
                fail_df = pd.DataFrame(FAILED_SEARCHES, columns=["zipcode", "keyword"])
                os.makedirs("output", exist_ok=True)
                fail_df.to_csv("output/FAILED_SEARCHES.csv", index=False)
                print(f"⚠️ Saved {len(FAILED_SEARCHES)} failed searches → output/FAILED_SEARCHES.csv")
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

            search_box = page.locator("input#UGojuc")
            search_box.wait_for(state="visible", timeout=60000)

            total_keywords = len(keywords)

            for i, keyword in enumerate(keywords, start=1):
                print("\n" + "=" * 70)
                print(f"📍 ZIP: {zipcode}")
                print(f"🔎 KEYWORD ({i}/{total_keywords}): {keyword}")
                print("=" * 70)

                query = f"{keyword} near {zipcode}"
                print(f"🔍 Searching: {query}")

                search_box.fill("")
                human_sleep(1, 2)
                search_box.fill(query)
                page.keyboard.press("Enter")
                human_sleep(6, 10)

                # === BOT WARNING CHECK ===
                if page.locator("text=unusual traffic from your computer").is_visible(timeout=3000):
                    print("🛑 Google detected unusual traffic! Solve CAPTCHA.")
                    input("👉 Press ENTER after solving CAPTCHA...")
                    FAILED_SEARCHES.append((zipcode, keyword))
                    continue

                # === FEED CHECK ===
                feed = page.locator('//div[@role="feed"]')
                try:
                    if not feed.is_visible(timeout=10000):
                        print("⚠️ No results feed found — skipping.")
                        FAILED_SEARCHES.append((zipcode, keyword))
                        continue
                except:
                    FAILED_SEARCHES.append((zipcode, keyword))
                    continue

                # SCROLL TO LOAD
                prev = 0
                stuck = 0
                while True:
                    try:
                        feed.evaluate("el => el.scrollBy(0, 1000)")
                    except:
                        break
                    human_sleep(1.5, 3)
                    count = page.locator('//a[contains(@href,"/maps/place")]').count()
                    if count >= limit_per_search:
                        break
                    if count == prev:
                        stuck += 1
                    else:
                        stuck = 0
                    if stuck >= 3:
                        break
                    prev = count

                # PROCESS LISTINGS
                listings = page.locator('//a[contains(@href,"/maps/place")]').all()[:limit_per_search]

                for l in listings:
                    try:
                        url = l.get_attribute("href")
                        if not url or url in SCRAPED_URLS:
                            continue

                        # --- Extract Name ---
                        name_elem = l.locator('xpath=.//div[contains(@class,"fontHeadlineSmall")]')
                        name = ""
                        if name_elem.count() > 0:
                            name = name_elem.first.inner_text().strip()
                        if not name:
                            domain = url.split("/place/")[-1].split("/")[0]
                            name = domain.replace("-", " ").replace("_", " ").title()

                        # --- Extract Category ---
                        desc_elems = l.locator(
                            'xpath=.//div[contains(@class,"fontBodyMedium")] | .//span[contains(@class,"fontBodyMedium")]'
                        ).all()
                        category_text = ""
                        if desc_elems:
                            for el in desc_elems:
                                txt = el.inner_text().strip()
                                if txt and not any(c in txt for c in ["·", "★", "stars"]) and not any(char.isdigit() for char in txt[:5]):
                                    category_text = txt
                                    break

                        is_relevant, reason = is_relevant_listing(category_text)
                        if not is_relevant:
                            print(f"⏭️ SKIPPED: '{name}' | Category: '{category_text}' | Reason: {reason}")
                            continue

                        SCRAPED_URLS.add(url)
                        l.click()
                        human_sleep(3, 5)

                        b = Business()
                        b.name = name
                        b.category = category_text
                        b.keyword = keyword
                        b.searched_zipcode = zipcode

                        def txt(x):
                            return page.locator(x).first.inner_text().strip() if page.locator(x).count() else ""

                        b.address = txt('//button[@data-item-id="address"]//div')
                        b.website = txt('//a[@data-item-id="authority"]//div')
                        b.phone_number = txt('//button[contains(@data-item-id,"phone")]//div')
                        b.latitude, b.longitude = extract_coordinates(page.url)

                        SCRAPED_RESULTS.append(b)

                    except Exception as e:
                        print(f"⚠️ Error processing listing: {e}")
                        continue

                # Save partial results
                BusinessList(SCRAPED_RESULTS).save_csv("swimming_4")
                print(f"✅ Finished keyword: {keyword}")
                human_sleep(5, 8)

        # Save failed searches
        if FAILED_SEARCHES:
            fail_df = pd.DataFrame(FAILED_SEARCHES, columns=["zipcode", "keyword"])
            os.makedirs("output", exist_ok=True)
            fail_df.to_csv("output/FAILED_SEARCHES.csv", index=False)
            print(f"\n⚠️ Total failed searches: {len(FAILED_SEARCHES)} → output/FAILED_SEARCHES.csv")

        print("\n🎯 SCRAPING COMPLETE")
        browser.close()



# =====================
# RUN
# =====================

if __name__ == "__main__":
    ZIPCODES = [
        # Fairfax, VA ZIP Codes
    #    '20120',
        #  '20121', '20122', '20124', '20151', '20152', '20153', '20164', '20166', '20170', '20171', '20172', '20190', '20191', '20192', '20194', '20195', '20196', '22003', '22009', '22015', '22018', '22019', '22027', '22030', '22031', '22032', 
        # '22033', '22035', '22037', '22038', '22039', '22041', '22042', '22043', '22044', '22046', '22060', '22066', '22067', '22079', '22081', '22082', '22101', '22102', '22106', 
        
        # '22116', '22121', '22124', '22150', '22151', '22152', '22153', '22158', 
        '22159', '22160', '22161', '22180', '22181', '22182', '22183', '22185', '22199', '22213'
    ]
    KEYWORDS = [
"kids swimming lessons",
"indoor swim lessons for kids" ,
"swimming classes for kids",
"youth swimming programs",
"water safety classes for kids",
"private swim lessons for kids",
"aquatic center for kids",
"swim academy for kids",
"learn to swim for kids",
"youth swim team"

    ]
    scrape(KEYWORDS, ZIPCODES)