import pandas as pd
import re
from urllib.parse import urlparse

# =====================
# FILES
# =====================
INPUT_FILE = "combined.csv"
OUTPUT_FILE = "filtered_va_camps.csv"

# =====================
# EXCLUSION KEYWORDS
# =====================
EXCLUSION_KEYWORDS = {
    'mosque','masjid','church','temple','synagogue','ministry','faith',
    'fire station','fire department','police','sheriff',
    'city of','county','town of','municipal',
    'department','authority','public works',
    'senior','assisted living','retirement','nursing home',
    'cemetery','funeral','memorial','embassy'
}

GOV_DOMAINS = {
    'gov','va.us','edu','k12.va.us',
    'arlingtonva.us','fairfaxcounty.gov','alexandriava.gov'
}

# =====================
# INCLUSION KEYWORDS
# =====================
PROGRAM_KEYWORDS = {
    'camp','summer','afterschool','after school','before school',
    'learning','education','educational','academy','institute',
    'center','centre','studio','lab','workshop',
    'kids','children','youth','teen','preschool','prek','pre-k',
    'childcare','daycare',
    'training','coaching','instruction','classes','lessons','program',
    'arts','music','dance','sports','fitness','stem','robotics',
    'coding','math','science','chess','basketball','soccer'
}

# =====================
# HELPERS
# =====================
def is_virginia_address(address):
    if pd.isna(address):
        return False
    addr = str(address).lower()
    return ', va' in addr or ' virginia' in addr

def clean_domain(url):
    if pd.isna(url):
        return None
    url = str(url).strip()
    if not url.startswith(('http://','https://')):
        url = 'https://' + url
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace('www.','')
        return host if host else None
    except:
        return None

def is_valid_program(row):
    name = str(row.get('name','')).lower()
    domain = row.get('domain')

    # Exclude by name
    if any(bad in name for bad in EXCLUSION_KEYWORDS):
        return False

    # Exclude government domains
    if domain and any(gov in domain for gov in GOV_DOMAINS):
        return False

    # Include by program keywords (PRIMARY)
    if any(kw in name for kw in PROGRAM_KEYWORDS):
        return True

    # Fallback logic
    youth = {'kid','child','youth','teen'}
    program = {'class','program','academy','training'}

    if any(y in name for y in youth) and any(p in name for p in program):
        return True

    return False

# =====================
# MAIN FLOW
# =====================
df = pd.read_csv(INPUT_FILE, dtype=str)

# Keep only Virginia addresses
df = df[df['address'].apply(is_virginia_address)]

# Normalize domains
df['domain'] = df['website'].apply(clean_domain)

# Apply camp / after-school filter
df = df[df.apply(is_valid_program, axis=1)]

# Deduplicate by domain (keeps one per brand)
df = df.drop_duplicates(subset=['domain'])

# Remove ZIP-related columns if present
df = df.drop(columns=['searched_zipcode'], errors='ignore')

# Save clean CSV
df.to_csv(OUTPUT_FILE, index=False)

print(f"Virginia camp providers saved to: {OUTPUT_FILE}")
print(f"Final rows: {len(df)}")
