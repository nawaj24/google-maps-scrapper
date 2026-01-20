import pandas as pd
import glob
import os

# =====================
# CONFIG
# =====================
INPUT_FOLDER = "../output/final_data"           # folder containing CSV files
OUTPUT_FILE = "combined.csv"    # final merged file

# =====================
# LOAD & COMBINE
# =====================
csv_files = glob.glob(os.path.join(INPUT_FOLDER, "*.csv"))

if not csv_files:
    raise ValueError("No CSV files found in the folder.")

df_list = []

for file in csv_files:
    df = pd.read_csv(file, dtype=str)
    df['source_file'] = os.path.basename(file)  # optional: track origin
    df_list.append(df)

combined_df = pd.concat(df_list, ignore_index=True)

# =====================
# OPTIONAL CLEANUP
# =====================
combined_df = combined_df.drop_duplicates()

# =====================
# SAVE
# =====================
combined_df.to_csv(OUTPUT_FILE, index=False)

print(f"Combined {len(csv_files)} CSV files into {OUTPUT_FILE}")
print(f"Total rows: {len(combined_df)}")
