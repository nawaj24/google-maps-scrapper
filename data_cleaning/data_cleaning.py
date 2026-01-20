


import pandas as pd
import re
from urllib.parse import urlparse

# --- Government / Institutional Domains to Exclude ---
GOV_DOMAINS = {
    'arlingtonva.us',
    'fairfaxcounty.gov',
    'fcps.edu',
    'apsva.us',
    'acps.k12.va.us',
    'parks.arlingtonva.us',
    'recreation.fairfaxcounty.gov',
    'alexandriava.gov',
    'va.us',
    'virginia.gov',
    'usda.gov',
    'nih.gov',
    'ymca.org'  # Fixed typo from 'ymcs.org'
}

def clean_field(val):
    """Remove invisible Unicode artifacts (e.g., , , ) and strip whitespace."""
    if pd.isna(val) or val == '':
        return ''
    val = str(val)
    # Remove all Private Use Area characters (U+E000–U+F8FF)
    val = re.sub(r'[\uE000-\uF8FF]', '', val)
    return val.strip()

def is_virginia_address(address):
    """Check if address contains Virginia state abbreviation 'VA' in standard format."""
    if pd.isna(address) or not str(address).strip():
        return False
    addr = str(address).upper()
    # Match patterns like ", VA", ",VA", or "VA 20151"
    if re.search(r',\s*VA\b', addr):
        return True
    if re.search(r'\bVA\s+\d{5}', addr):
        return True
    return False

def standardize_url(url):
    """Convert URL to clean https://domain.com (no www, no path, no port)."""
    if pd.isna(url) or not str(url).strip():
        return None
    url = clean_field(url)
    if not url:
        return None
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().strip()
        if not netloc:
            return None
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        netloc = netloc.split(':')[0].split('/')[0]  # remove port and path
        if not netloc:
            return None
        return f"https://{netloc}"
    except Exception:
        return None

def is_excluded_domain(website):
    """Return True if the website belongs to a government/institutional entity."""
    if pd.isna(website):
        return False  # Missing website ≠ excluded
    try:
        domain = urlparse(website).netloc.lower()
        if domain.endswith('.gov'):
            return True
        if any(gov in domain for gov in GOV_DOMAINS):
            return True
    except Exception:
        pass
    return False

# --- MAIN SCRIPT ---
INPUT_FILE = 'stem_virginia_filtered.csv'
OUTPUT_FILE = 'stem_virginia.xlsx'

# Expected columns (as per your data structure)
expected_cols = [
    'name', 'address', 'website', 'phone_number',
    'reviews_count', 'reviews_average',
    'latitude', 'longitude', 'keyword', 'searched_zipcode'
]

# Load data
df = pd.read_csv(INPUT_FILE, dtype=str)

# Ensure all expected columns exist (fill missing with empty string)
for col in expected_cols:
    if col not in df.columns:
        df[col] = ''

# Clean text fields
text_cols = ['name', 'address', 'website', 'phone_number']
for col in text_cols:
    df[col] = df[col].apply(clean_field)

# STEP 1: Keep only rows where address contains "VA" (Virginia)
df = df[df['address'].apply(is_virginia_address)].copy()
if df.empty:
    print("No rows found with 'VA' in address.")
    exit()

# STEP 2: Standardize website URLs
df['website_clean'] = df['website'].apply(standardize_url)

# STEP 3: Exclude government/institutional domains (but keep non-web entries)
df['is_excluded'] = df['website_clean'].apply(is_excluded_domain)
df = df[~df['is_excluded']].copy()

# STEP 4: Deduplicate by domain (only for entries with a valid website)
df['domain'] = df['website_clean'].apply(lambda x: urlparse(x).netloc.lower() if pd.notna(x) else None)

# Split: with vs without domain
with_domain = df[df['domain'].notna()].copy()
without_domain = df[df['domain'].isna()].copy()

# Deduplicate only the with-domain group
with_domain_unique = with_domain.drop_duplicates(subset=['domain'], keep='first')

# Recombine
df_final = pd.concat([with_domain_unique, without_domain], ignore_index=True)

# Replace original 'website' with cleaned version
df_final['website'] = df_final['website_clean']

# Keep only original columns in correct order
df_output = df_final[expected_cols]

# Save to Excel
df_output.to_excel(OUTPUT_FILE, index=False, engine='openpyxl')

# Print summary
original_total = len(pd.read_csv(INPUT_FILE, dtype=str))
va_filtered = len(df)
final_count = len(df_output)

print(f"Original rows: {original_total}")
print(f"Rows with 'VA' in address: {va_filtered}")
print(f"Final rows after deduplication & exclusion: {final_count}")
print(f"Saved to: {OUTPUT_FILE}")