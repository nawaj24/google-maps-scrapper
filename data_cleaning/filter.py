import pandas as pd
import re
from urllib.parse import urlparse
from pathlib import Path

# --- Config ---
RAW_INPUT = 'master.csv'         # NEW scraped data (daily)
MASTER_FILE = 'main.csv'  # EXISTING master list (to be updated)

# Define desired column order (MUST match your master_main.csv structure)
TARGET_COLS = [
    'name', 'address', 'website', 'phone_number',
    'reviews_count', 'reviews_average',
    'latitude', 'longitude', 'keyword', 'searched_zipcode'
]

def clean_field(val):
    if pd.isna(val) or val == '':
        return ''
    val = str(val)
    return re.sub(r'[\uE000-\uF8FF]', '', val).strip()

def standardize_url(url):
    if pd.isna(url) or not str(url).strip():
        return None
    url = clean_field(url)
    if not url:
        return None
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        netloc = urlparse(url).netloc.lower().strip()
        if not netloc:
            return None
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        netloc = netloc.split(':')[0].split('/')[0]
        return f"https://{netloc}" if netloc else None
    except:
        return None

def extract_domain(url):
    if pd.isna(url):
        return None
    try:
        return urlparse(url).netloc.lower()
    except:
        return None

def is_virginia_address(address):
    if pd.isna(address) or not str(address).strip():
        return False
    addr = str(address).upper()
    return bool(re.search(r',\s*VA\b', addr)) or bool(re.search(r'\bVA\s+\d{5}', addr))

# --- Load RAW new data (master.csv) ---
raw_df = pd.read_csv(RAW_INPUT, dtype=str)

# Map common raw column names to TARGET_COLS
column_mapping = {
    'Name': 'name',
    'Address': 'address',
    'Website': 'website',
    'Phone': 'phone_number',
    'Lat': 'latitude',
    'Lng': 'longitude',
    'Keyword': 'keyword',
    'Zipcode': 'searched_zipcode',
}

# Apply mapping if needed
renamed_cols = {}
for old, new in column_mapping.items():
    if old in raw_df.columns:
        renamed_cols[old] = new

if renamed_cols:
    raw_df = raw_df.rename(columns=renamed_cols)

# Ensure all TARGET_COLS exist (add missing as empty)
for col in TARGET_COLS:
    if col not in raw_df.columns:
        raw_df[col] = ''

# Reorder and select only TARGET_COLS
raw_df = raw_df[TARGET_COLS].copy()

# Clean text fields
for col in ['name', 'address', 'website', 'phone_number']:
    raw_df[col] = raw_df[col].apply(clean_field)

# Filter VA addresses only
raw_df = raw_df[raw_df['address'].apply(is_virginia_address)].copy()

# Standardize URLs
raw_df['website_clean'] = raw_df['website'].apply(standardize_url)
raw_df['domain'] = raw_df['website_clean'].apply(extract_domain)

# Exclude government domains
GOV_DOMAINS = {'fairfaxcounty.gov', 'fcps.edu', 'apsva.us', 'alexandriava.gov', 'virginia.gov', 'nih.gov', 'ymca.org'}
def is_gov(domain):
    if pd.isna(domain):
        return False
    return domain.endswith('.gov') or any(gov in domain for gov in GOV_DOMAINS)
raw_df = raw_df[~raw_df['domain'].apply(is_gov)].copy()

# --- Load existing MASTER (master_main.csv) ---
if Path(MASTER_FILE).exists():
    master_df = pd.read_csv(MASTER_FILE, dtype=str)
    # Ensure master has all TARGET_COLS
    for col in TARGET_COLS:
        if col not in master_df.columns:
            master_df[col] = ''
    master_df = master_df[TARGET_COLS].copy()  # Enforce order
    
    # Build dedupe keys
    master_df['website_clean'] = master_df['website'].apply(standardize_url)
    master_df['domain'] = master_df['website_clean'].apply(extract_domain)
    existing_domains = set(master_df['domain'].dropna().unique())
    existing_name_addr = set(
        zip(master_df['name'].str.lower(), master_df['address'].str.lower())
    )
else:
    master_df = pd.DataFrame(columns=TARGET_COLS)
    existing_domains = set()
    existing_name_addr = set()

# --- Find truly new records ---
def is_new(row):
    domain = row['domain']
    name_addr = (row['name'].lower(), row['address'].lower())
    if pd.notna(domain) and domain in existing_domains:
        return False
    if pd.isna(domain) and name_addr in existing_name_addr:
        return False
    return True

raw_df['is_new'] = raw_df.apply(is_new, axis=1)
new_records = raw_df[raw_df['is_new']].copy()

# --- Prepare final new records with correct column order ---
if not new_records.empty:
    new_records['website'] = new_records['website_clean']  # Use cleaned URL
    new_records_final = new_records[TARGET_COLS].copy()   # Enforce column order
else:
    new_records_final = pd.DataFrame(columns=TARGET_COLS)

# --- Update MASTER FILE ---
updated_master = pd.concat([master_df, new_records_final], ignore_index=True)
updated_master.to_csv(MASTER_FILE, index=False)

# --- Save today's new records (with correct column order) ---
new_records_final.to_excel('today_new_providers.xlsx', index=False, engine='openpyxl')

# --- Summary ---
print(f"✅ Original master: {len(master_df)} records")
print(f"✅ New unique records: {len(new_records_final)}")
print(f"✅ Updated master ({MASTER_FILE}): {len(updated_master)} records")
print(f"✅ New records saved to: today_new_providers.xlsx")