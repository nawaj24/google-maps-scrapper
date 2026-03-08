import re
import asyncio
import aiohttp
import pandas as pd
import os
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# =====================
# CONFIG
# =====================
INPUT_FILE  = "output/leads_WITH_website.csv"
OUTPUT_FILE = "output/leads_WITH_emails.csv"
EXCEL_FILE  = "output/leads_final.xlsx"
BATCH_SIZE  = 10
CONCURRENCY = 5

# =====================
# USER AGENTS
# =====================
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# =====================
# UNICODE CLEANER  ← shared across all 3 scripts
# =====================
def clean_text(val):
    if not isinstance(val, str):
        return val
    return re.sub(r'[^\x20-\x7E]', '', val).strip()

# =====================
# EMAIL PATTERNS
# =====================
STRICT_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
EMAIL_RE        = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

IGNORED_DOMAINS = {
    "sentry.io","wixpress.com","example.com","domain.com","yourdomain.com",
    "squarespace.com","shopify.com","wordpress.com","googletagmanager.com",
    "schema.org","w3.org","amazonaws.com","cloudflare.com","google.com",
    "apple.com","microsoft.com","adobe.com","jquery.com","bootstrapcdn.com",
    "fontawesome.com","gravatar.com",
}
IGNORED_PREFIXES = (
    "noreply","no-reply","donotreply","mailer-daemon",
    "bounce","postmaster","webmaster"
)

def clean_email(raw: str):
    if not raw:
        return None
    email = clean_text(raw).lower()
    email = re.sub(r'^[^a-zA-Z0-9]+', '', email)
    email = re.sub(r'[^a-zA-Z0-9]+$', '', email)
    email = re.sub(r'\s+', '', email)
    if re.search(r'\.(png|jpg|jpeg|gif|js|css|svg|webp|woff|ttf)$', email):
        return None
    if not STRICT_EMAIL_RE.match(email):
        return None
    domain = email.split("@")[-1]
    if domain in IGNORED_DOMAINS:
        return None
    if email.startswith(IGNORED_PREFIXES):
        return None
    return email

# =====================
# URL HELPERS
# =====================
def normalize_url(url):
    if not url or not isinstance(url, str):
        return None
    url = clean_text(url)          # ✅ strips \ue80b and all unicode garbage
    if not url:
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")

def is_valid_url(url):
    if not url:
        return False
    try:
        p = urlparse(url)
        return bool(p.scheme and p.netloc and "." in p.netloc)
    except Exception:
        return False

def same_domain(url1, url2):
    try:
        return urlparse(url1).netloc == urlparse(url2).netloc
    except Exception:
        return False

def find_contact_links(soup, base_url):
    keywords = [
        "contact","about","contact-us","about-us","reach-us",
        "get-in-touch","connect","support","info","location","team","staff"
    ]
    found = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text(strip=True).lower()
        if not href or href.startswith(("mailto:","tel:","javascript:","#")):
            continue
        if any(kw in href.lower() for kw in keywords) or \
           any(kw in text         for kw in keywords):
            full = urljoin(base_url, href)
            if same_domain(full, base_url):
                found.add(full)
    return list(found)[:6]

# =====================
# SEMAPHORE
# =====================
SEM = asyncio.Semaphore(CONCURRENCY)

# =====================
# FETCH
# =====================
async def fetch(session, url):
    async with SEM:
        for attempt in range(2):
            try:
                await asyncio.sleep(random.uniform(0.5, 1.5))
                async with session.get(
                    url,
                    headers={
                        "User-Agent": random.choice(USER_AGENTS),
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate",
                        "Connection": "keep-alive",
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                    ssl=False,
                    allow_redirects=True,
                ) as resp:
                    print(f"      🌐 {url[:65]} → {resp.status}")
                    if resp.status == 200:
                        return await resp.text(errors="ignore")
                    return None
            except Exception as e:
                print(f"      ❌ {url[:55]} → {type(e).__name__}: {str(e)[:50]}")
                if attempt == 0:
                    await asyncio.sleep(2)
        return None

# =====================
# SCRAPE ONE PAGE
# =====================
async def scrape_page(session, url):
    html = await fetch(session, url)
    if not html:
        return {"emails":[],"facebook":None,"instagram":None,"contact_links":[]}

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script","style","meta","link","noscript"]):
        tag.decompose()

    emails = []

    # Method 1: mailto links
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().startswith("mailto:"):
            raw = href.replace("mailto:","").split("?")[0].strip()
            c = clean_email(raw)
            if c and c not in emails:
                emails.append(c)

    # Method 2: visible text
    for raw in EMAIL_RE.findall(soup.get_text(separator=" ")):
        c = clean_email(raw)
        if c and c not in emails:
            emails.append(c)

    facebook = instagram = None
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "facebook.com" in href and "/sharer" not in href and not facebook:
            facebook = href
        if "instagram.com" in href and not instagram:
            instagram = href

    return {
        "emails":        emails,
        "facebook":      facebook,
        "instagram":     instagram,
        "contact_links": find_contact_links(soup, url),
    }

# =====================
# SCRAPE FACEBOOK
# =====================
async def scrape_facebook_email(session, fb_url):
    try:
        if "facebook.com" in fb_url and "m.facebook.com" not in fb_url:
            fb_url = fb_url.replace("https://www.","https://m.")
            fb_url = fb_url.replace("https://facebook.com","https://m.facebook.com")
        async with session.get(
            fb_url,
            headers={"User-Agent": random.choice(USER_AGENTS)},
            timeout=aiohttp.ClientTimeout(total=15),
            ssl=False,
        ) as resp:
            if resp.status != 200:
                return None
            for raw in EMAIL_RE.findall(await resp.text(errors="ignore")):
                c = clean_email(raw)
                if c:
                    return c
    except Exception:
        pass
    return None

# =====================
# SCRAPE ONE WEBSITE
# =====================
async def scrape_website(website):
    base_url = normalize_url(str(website) if website else "")

    if not base_url or not is_valid_url(base_url):
        print(f"      ⚠️  Invalid: {repr(website)}")
        return {"emails":[],"facebook":None,"instagram":None,"scrape_status":"invalid_url"}

    print(f"      🔎 {base_url}")
    static_paths = ["/contact","/about","/contact-us","/about-us","/reach-us","/info"]

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        best = {"emails":[],"facebook":None,"instagram":None}

        # Step 1: Homepage
        hp = await scrape_page(session, base_url)
        if hp["emails"]:
            hp["scrape_status"] = "found_homepage"
            print(f"      ✅ {hp['emails']}")
            return hp
        best["facebook"]  = hp.get("facebook")
        best["instagram"] = hp.get("instagram")

        # Step 2: Subpages
        all_pages = list(set(
            [base_url + p for p in static_paths] + hp.get("contact_links",[])
        ))
        for res in await asyncio.gather(*[scrape_page(session, u) for u in all_pages], return_exceptions=True):
            if not res or isinstance(res, Exception):
                continue
            if res["emails"]:
                best["emails"]    = res["emails"]
                best["facebook"]  = best["facebook"]  or res.get("facebook")
                best["instagram"] = best["instagram"] or res.get("instagram")
                best["scrape_status"] = "found_subpage"
                print(f"      ✅ {best['emails']}")
                return best
            best["facebook"]  = best["facebook"]  or res.get("facebook")
            best["instagram"] = best["instagram"] or res.get("instagram")

        # Step 3: Facebook fallback
        if best.get("facebook"):
            fb_email = await scrape_facebook_email(session, best["facebook"])
            if fb_email:
                best["emails"] = [fb_email]
                best["scrape_status"] = "found_facebook"
                return best

        best["scrape_status"] = "no_contact_found"
        return best

# =====================
# LOAD CSV
# =====================
def load_input_csv(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"❌ Not found: {filepath}")

    df = pd.read_csv(filepath, dtype=str)

    # ✅ Strip unicode garbage from every cell
    df = df.applymap(clean_text)

    print(f"   Columns : {list(df.columns)}")
    print(f"   Total   : {len(df)}")

    col_lower = {c.lower().strip(): c for c in df.columns}
    if "website" not in col_lower:
        raise ValueError(f"❌ No website column. Found: {list(df.columns)}")

    df = df.rename(columns={col_lower["website"]: "website"})
    if "has_website" in col_lower:
        df = df.rename(columns={col_lower["has_website"]: "has_website"})
        df = df[df["has_website"].str.lower() == "yes"].copy()

    df = df[df["website"].notna() & (df["website"].str.strip() != "")].copy()

    # Normalize all URLs
    df["website"] = df["website"].apply(normalize_url)
    df = df[df["website"].apply(is_valid_url)].copy()
    df = df.reset_index(drop=True)

    print(f"   Sample websites:")
    for v in df["website"].head(5).tolist():
        print(f"     {v}")
    print(f"   ✅ Valid rows: {len(df)}")
    return df

# =====================
# RESUME
# =====================
def load_existing(output_file):
    if not os.path.exists(output_file):
        return [], set()
    df = pd.read_csv(output_file, dtype=str)
    df = df.applymap(clean_text)
    done = set(df["website"].dropna().str.strip().str.lower().tolist())
    print(f"   ▶ Resume: {len(done)} already done")
    return df.to_dict("records"), done

# =====================
# SAVE EXCEL
# =====================
def save_excel(records, path):
    from openpyxl.utils import get_column_letter
    df = pd.DataFrame(records)
    df_y = df[df["email_found"] == "Yes"].copy()
    df_n = df[df["email_found"] == "No"].copy()
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet, data in [("✅ Email Found",df_y),("❌ No Email",df_n),("📋 All",df)]:
            data.to_excel(writer, sheet_name=sheet, index=False)
            ws = writer.sheets[sheet]
            ws.freeze_panes = "A2"
            for i, col in enumerate(data.columns, 1):
                try:
                    w = min(max(data[col].astype(str).map(len).max(), len(col)) + 4, 55)
                    ws.column_dimensions[get_column_letter(i)].width = w
                except Exception:
                    pass
    print(f"   📊 {path}")

# =====================
# MAIN
# =====================
async def main():
    os.makedirs("output", exist_ok=True)

    # ✅ Clear old output for fresh run — comment out after first success
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
        print("🗑️  Cleared old output — fresh run")

    print(f"\n📂 {INPUT_FILE}")
    try:
        df = load_input_csv(INPUT_FILE)
    except (FileNotFoundError, ValueError) as e:
        print(e)
        return

    existing, done = load_existing(OUTPUT_FILE)
    df = df[~df["website"].str.lower().isin(done)].copy()
    print(f"   Remaining: {len(df)}")

    if df.empty:
        print("✅ All done!")
        save_excel(existing, EXCEL_FILE)
        return

    rows    = df.to_dict("records")
    total   = len(rows)
    records = existing.copy()

    for start in range(0, total, BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        end   = min(start + BATCH_SIZE, total)
        print(f"\n🔄 Batch {start+1}–{end} / {total}")

        results = await asyncio.gather(
            *[scrape_website(r["website"]) for r in batch],
            return_exceptions=True
        )

        found_now = 0
        for row, result in zip(batch, results):
            rec = dict(row)
            if isinstance(result, Exception) or not result:
                rec.update({"email_1":"","email_2":"","email_3":"","all_emails":"",
                            "facebook":"","instagram":"","email_found":"No","scrape_status":"error"})
            else:
                emails = result.get("emails",[])
                rec["email_1"]       = emails[0] if len(emails) > 0 else ""
                rec["email_2"]       = emails[1] if len(emails) > 1 else ""
                rec["email_3"]       = emails[2] if len(emails) > 2 else ""
                rec["all_emails"]    = " | ".join(emails)
                rec["facebook"]      = result.get("facebook")  or row.get("facebook","")
                rec["instagram"]     = result.get("instagram") or row.get("instagram","")
                rec["email_found"]   = "Yes" if emails else "No"
                rec["scrape_status"] = result.get("scrape_status","")
                if emails:
                    found_now += 1

            records.append(rec)
            ok  = rec.get("email_found") == "Yes"
            msg = f"✔  {rec.get('email_1','')[:45]}" if ok else "✖  no email"
            print(f"   {row.get('name','?')[:38]:<38} | {msg}  [{rec.get('scrape_status','')}]")

        pd.DataFrame(records).to_csv(OUTPUT_FILE, index=False)
        total_found = sum(1 for r in records if r.get("email_found") == "Yes")
        pct = round(total_found / len(records) * 100, 1) if records else 0
        print(f"   💾 {len(records)} saved | ✅ {total_found} ({pct}%) | +{found_now} this batch")

        if end < total:
            w = random.uniform(3, 6)
            print(f"   ⏳ {w:.1f}s...")
            await asyncio.sleep(w)

    save_excel(records, EXCEL_FILE)
    df_f  = pd.DataFrame(records)
    found = len(df_f[df_f["email_found"] == "Yes"])
    print(f"\n{'='*55}")
    print(f"🎯  DONE  |  Total: {len(df_f)}  |  ✅ {found}  |  ❌ {len(df_f)-found}")

if __name__ == "__main__":
    asyncio.run(main())