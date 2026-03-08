import random
import time
import os
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
# DATA MODELS
# =====================
@dataclass
class Business:
    name: str = ""
    address: str = ""
    website: str = ""
    phone_number: str = ""
    reviews_count: int | None = None
    reviews_average: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    keyword: str = ""
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
    except:
        return None, None

def region_match(b: Business):
    if not b.address:
        return False
    return (
        b.searched_zipcode in b.address or
        "VA" in b.address or
        "Virginia" in b.address
    )

# =====================
# SCRAPER
# =====================
SCRAPED_RESULTS = []
SCRAPED_URLS = set()

def scrape(keywords, zipcodes, limit_per_search=80):
    global SCRAPED_RESULTS

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(user_agent=random.choice(USER_AGENTS))
        page = context.new_page()

        # Ctrl+C handler
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

                feed = page.locator('//div[@role="feed"]')
                prev = 0
                stuck = 0

                while True:
                    feed.evaluate("el => el.scrollBy(0, 1000)")
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

                new_batch = []

                for l in listings:
                    try:
                        url = l.get_attribute("href")
                        if not url or url in SCRAPED_URLS:
                            continue
                        SCRAPED_URLS.add(url)

                        l.click()
                        human_sleep(3, 5)

                        b = Business()
                        b.name = l.get_attribute("aria-label") or ""
                        b.keyword = keyword
                        b.searched_zipcode = zipcode

                        def txt(x):
                            return page.locator(x).first.inner_text() if page.locator(x).count() else ""

                        b.address = txt('//button[@data-item-id="address"]//div')
                        b.website = txt('//a[@data-item-id="authority"]//div')
                        b.phone_number = txt('//button[contains(@data-item-id,"phone")]//div')
                        b.latitude, b.longitude = extract_coordinates(page.url)

                        new_batch.append(b)
                        SCRAPED_RESULTS.append(b)

                    except Exception as e:
                        # Optional: log error for debugging
                        # print(f"⚠️ Error scraping listing: {e}")
                        continue

                # Save cumulative results to ONE CSV file (overwrite each time)
                BusinessList(SCRAPED_RESULTS).save_csv("stem")

                print(f"✅ Finished keyword: {keyword}")
                human_sleep(5, 8)

        # # Final filtered save
        # filtered = [b for b in SCRAPED_RESULTS if region_match(b)]
        # BusinessList(filtered).save_csv("FILTERED_RESULTS_22203")

        print("\n🎯 SCRAPING COMPLETE")
        browser.close()

# =====================
# RUN
# =====================

if __name__ == "__main__":
    ZIPCODES = [

                # Fairfax, VA ZIP Codes
       '20120',
         '20121', '20122', '20124', '20151', '20152', '20153', '20164', '20166', '20170', '20171', '20172', '20190', '20191', '20192', '20194', '20195', '20196', '22003', '22009', '22015', '22018', '22019', '22027', '22030', '22031', '22032', 
        '22033', '22035', '22037', '22038', '22039', '22041', '22042', '22043', '22044', '22046', '22060', '22066', '22067', '22079', '22081', '22082', '22101', '22102', '22106', 
        
        '22116', '22121', '22124', '22150', '22151', '22152', '22153', '22158', 
        '22159', '22160', '22161', '22180', '22181', '22182', '22183', '22185', '22199', '22213'
        #Arlington, VA ZIP Codes
        # "22203"
                # "22204","22205","22206","22207",
        #         "22209","22210",
        # "22211","22212","22213","22214","22215","22216","22217","22218","22219",
        # "22222","22225","22226","22227","22230","22240","22241","22242","22243",
        # "22244","22245","22246","20231","20301","20310","20330","20350","20406",
        # "20598","20453",

#Alexandria, VA ZIP Codes
        # "22301","22302","22303","22304","22305","22306","22307","22308","22309",
        # "22310","22311","22312","22313","22314","22315","22320","22331","22332",
        # "22333","22334"
                ]
    KEYWORDS = [
        # "basketball classes for kids",
        # "basketball training for kids",
        # "youth basketball league",
        # "basketball academy for kids",
        # "basketball camp",
        # "basketball skills training",
        # "soccer classes for kids",
        # "soccer training for kids",
        # "youth soccer programs",
        # "soccer academy for kids",
        # "soccer camp for kids"

    "summer camps for kids",
"stem camps",
"educational camps",
"science camps",
"coding camps for kids",
"robotics camps",
"kids learning center",
"educational programs for kids",
"after school programs for kids",
    ]
    scrape(KEYWORDS, ZIPCODES)