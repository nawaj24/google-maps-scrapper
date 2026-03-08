import pandas as pd
import re
import os

# =====================
# CONFIG
# =====================
INPUT_FILE = "output/dallas_immigrant_businesses.csv"
OUTPUT_DIR = "output"

# =====================
# UNICODE CLEANER
# =====================
def clean_text(val):
    if not isinstance(val, str):
        return val
    return re.sub(r'[^\x20-\x7E]', '', val).strip()

# =====================
# LOAD & CLEAN
# =====================
print("📂 Loading CSV...")
df = pd.read_csv(INPUT_FILE, dtype=str)
print(f"   Total rows loaded: {len(df)}")

# ✅ Strip unicode garbage + whitespace from every cell
df = df.applymap(clean_text)

# Show sample website values to confirm clean
print("   Sample websites after cleaning:")
for v in df[df["has_website"] == "Yes"]["website"].head(5).tolist():
    print(f"     {repr(v)}")

# =====================
# REMOVE DUPLICATES
# =====================
before = len(df)

df = df.drop_duplicates(subset=["name", "address"], keep="first")
df = df.drop_duplicates(subset=["phone_number"], keep="first")

df_has_web = df[df["has_website"] == "Yes"].copy()
df_no_web  = df[df["has_website"] != "Yes"].copy()
df_has_web = df_has_web.drop_duplicates(subset=["website"], keep="first")

df = pd.concat([df_has_web, df_no_web], ignore_index=True)
after = len(df)
print(f"   ✅ Duplicates removed: {before - after} | Remaining: {after}")

# =====================
# SPLIT
# =====================
df_with_website    = df[df["has_website"] == "Yes"].copy()
df_without_website = df[df["has_website"] == "No"].copy()

print(f"   🌐 With website:    {len(df_with_website)}")
print(f"   ❌ Without website: {len(df_without_website)}")

# Sort by reviews ascending — small businesses first
for d in [df_with_website, df_without_website]:
    d.sort_values(by=["category","reviews_count"], ascending=[True,True], inplace=True)

# =====================
# SAVE CSVs
# =====================
os.makedirs(OUTPUT_DIR, exist_ok=True)

csv_web    = os.path.join(OUTPUT_DIR, "leads_WITH_website.csv")
csv_no_web = os.path.join(OUTPUT_DIR, "leads_NO_website.csv")

df_with_website.to_csv(csv_web,    index=False)
df_without_website.to_csv(csv_no_web, index=False)
print(f"\n✅ {csv_web}")
print(f"✅ {csv_no_web}")

# =====================
# SAVE EXCEL
# =====================
from openpyxl.utils import get_column_letter

excel_path = os.path.join(OUTPUT_DIR, "dallas_leads_cleaned.xlsx")
with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    for sheet, data in [
        ("✅ Has Website",  df_with_website),
        ("❌ No Website",   df_without_website),
    ]:
        data.to_excel(writer, sheet_name=sheet, index=False)
        ws = writer.sheets[sheet]
        ws.freeze_panes = "A2"
        for i, col in enumerate(data.columns, 1):
            try:
                w = min(max(data[col].astype(str).map(len).max(), len(col)) + 4, 50)
                ws.column_dimensions[get_column_letter(i)].width = w
            except Exception:
                pass

print(f"✅ Excel: {excel_path}")

# =====================
# SUMMARY
# =====================
print("\n" + "=" * 50)
print("📊 SUMMARY")
print("=" * 50)
print(f"Total clean leads : {len(df)}")
print(f"With website      : {len(df_with_website)}")
print(f"Without website   : {len(df_without_website)}")
print("\nBy category:")
print(df.groupby("category")[["name"]].count().rename(columns={"name":"count"}).to_string())
print("\nWebsite by category:")
print(df.groupby(["category","has_website"])[["name"]].count().rename(columns={"name":"count"}).to_string())