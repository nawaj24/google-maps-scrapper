# import pandas as pd
# import re
# from urllib.parse import urlparse

# # =========================
# # CONFIG
# # =========================
# MASTER_FILE = "master.xlsx"
# NEW_FILE = "test2.xlsx"
# UNIQUE_OUTPUT = "unique_new.xlsx"

# # =========================
# # HELPERS
# # =========================
# def normalize_text(text):
#     if pd.isna(text):
#         return ""
#     text = str(text).lower()
#     text = re.sub(r'\s+', ' ', text)
#     text = re.sub(r'[^\w\s]', '', text)
#     return text.strip()

# def extract_domain(url):
#     if pd.isna(url) or not str(url).strip():
#         return ""
#     url = str(url).strip()
#     if not url.startswith(('http://', 'https://')):
#         url = 'https://' + url
#     try:
#         return urlparse(url).netloc.replace('www.', '').lower()
#     except:
#         return ""

# def build_unique_key(row):
#     if row['domain']:
#         return f"domain::{row['domain']}"
#     return f"name_addr::{row['name_norm']}|{row['address_norm']}"

# # =========================
# # LOAD FILES (EXCEL)
# # =========================
# master_df = pd.read_excel(MASTER_FILE, dtype=str)
# new_df = pd.read_excel(NEW_FILE, dtype=str)

# # =========================
# # NORMALIZATION
# # =========================
# for df in (master_df, new_df):
#     df['name_norm'] = df['name'].apply(normalize_text)
#     df['address_norm'] = df['address'].apply(normalize_text)
#     df['domain'] = df['website'].apply(extract_domain)
#     df['unique_key'] = df.apply(build_unique_key, axis=1)

# # =========================
# # FIND UNIQUE ROWS
# # =========================
# existing_keys = set(master_df['unique_key'])

# unique_new_df = new_df[~new_df['unique_key'].isin(existing_keys)].copy()

# # =========================
# # SAVE UNIQUE NEW DATA
# # =========================
# unique_new_df.drop(
#     columns=['name_norm', 'address_norm', 'domain', 'unique_key'],
#     inplace=True
# )

# unique_new_df.to_excel(UNIQUE_OUTPUT, index=False)

# # =========================
# # UPDATE MASTER FILE
# # =========================
# updated_master = pd.concat([master_df, unique_new_df], ignore_index=True)

# updated_master.drop(
#     columns=['name_norm', 'address_norm', 'domain', 'unique_key'],
#     errors='ignore',
#     inplace=True
# )

# updated_master.to_excel(MASTER_FILE, index=False)

# # =========================
# # SUMMARY
# # =========================
# print("✅ Excel comparison complete")
# print(f"Master rows before: {len(master_df)}")
# print(f"Unique new rows added: {len(unique_new_df)}")
# print(f"Master rows after update: {len(updated_master)}")
# print(f"📁 Unique rows saved to: {UNIQUE_OUTPUT}")






import pandas as pd
import re
from urllib.parse import urlparse

# =========================
# CONFIG
# =========================
MASTER_FILE = "master.xlsx"
NEW_FILE = "test2.xlsx"
UNIQUE_OUTPUT = "unique_new1.xlsx"

# =========================
# EXCLUSIONS
# =========================
EXCLUSION_KEYWORDS = {
    'church','chapel','ministry','faith','mosque','masjid',
    'temple','synagogue','baptist','catholic','methodist',
    'lutheran','presbyterian','episcopal',
    'fire station','fire department','police','sheriff',
    'city of','county','town of','municipal','department',
    'authority','public works','government',
    'cemetery','funeral','memorial','embassy',
    'senior','assisted living','retirement','nursing home'
}

GOV_DOMAIN_HINTS = {
    '.gov','va.us','edu','k12'
}

# =========================
# HELPERS
# =========================
def normalize_text(text):
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()

def extract_domain(url):
    if pd.isna(url) or not str(url).strip():
        return ""
    url = str(url).strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    try:
        return urlparse(url).netloc.replace('www.', '').lower()
    except:
        return ""

def build_unique_key(row):
    if row.get('domain'):
        return f"domain::{row['domain']}"
    return f"name_addr::{row.get('name_norm','')}|{row.get('address_norm','')}"

def normalize_columns(df):
    df.columns = df.columns.str.strip()
    COLUMN_MAP = {
        'Name': 'name',
        'Address': 'address',
        'Full Address': 'address',
        'Location': 'address',
        'Website': 'website',
        'URL': 'website'
    }
    for old, new in COLUMN_MAP.items():
        if old in df.columns and new not in df.columns:
            df.rename(columns={old: new}, inplace=True)
    return df

def is_excluded(row):
    name = str(row.get('name','')).lower()
    domain = str(row.get('domain','')).lower()

    if any(bad in name for bad in EXCLUSION_KEYWORDS):
        return True

    if any(hint in domain for hint in GOV_DOMAIN_HINTS):
        return True

    return False

# =========================
# LOAD FILES
# =========================
master_df = pd.read_excel(MASTER_FILE, dtype=str)
new_df = pd.read_excel(NEW_FILE, dtype=str)

master_df = normalize_columns(master_df)
new_df = normalize_columns(new_df)

# =========================
# NORMALIZATION
# =========================
for df in (master_df, new_df):
    df['name_norm'] = df['name'].apply(normalize_text) if 'name' in df.columns else ""
    df['address_norm'] = df['address'].apply(normalize_text) if 'address' in df.columns else ""
    df['domain'] = df['website'].apply(extract_domain) if 'website' in df.columns else ""
    df['unique_key'] = df.apply(build_unique_key, axis=1)

# =========================
# APPLY EXCLUSIONS
# =========================
master_df = master_df[~master_df.apply(is_excluded, axis=1)]
new_df = new_df[~new_df.apply(is_excluded, axis=1)]

# =========================
# FIND UNIQUE ROWS
# =========================
existing_keys = set(master_df['unique_key'])

unique_new_df = new_df[~new_df['unique_key'].isin(existing_keys)].copy()

# =========================
# SAVE UNIQUE NEW DATA
# =========================
unique_new_df.drop(
    columns=['name_norm', 'address_norm', 'domain', 'unique_key'],
    errors='ignore',
    inplace=True
)

unique_new_df.to_excel(UNIQUE_OUTPUT, index=False)

# =========================
# UPDATE MASTER
# =========================
updated_master = pd.concat([master_df, unique_new_df], ignore_index=True)

updated_master.drop(
    columns=['name_norm', 'address_norm', 'domain', 'unique_key'],
    errors='ignore',
    inplace=True
)

updated_master.to_excel(MASTER_FILE, index=False)

# =========================
# SUMMARY
# =========================
print("✅ Comparison & exclusion complete")
print(f"Master rows before: {len(master_df)}")
print(f"Unique new rows added: {len(unique_new_df)}")
print(f"Master rows after update: {len(updated_master)}")
print(f"📁 Unique rows saved to: {UNIQUE_OUTPUT}")
