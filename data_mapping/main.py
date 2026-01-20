import pandas as pd
import re

# Define ZIP code sets
FAIRFAX_ZIPS = {
   '20120', '20121', '20122', '20124', '20151', '20152', '20153', '20164', '20166', '20170', '20171', '20172', '20190', '20191', '20192', '20194', '20195', '20196', '22003', '22009', '22015', '22018', '22019', '22027', '22030', '22031', '22032', '22033', '22035', '22037', '22038', '22039', '22041', '22042', '22043', '22044', '22046', '22060', '22066', '22067', '22079', '22081', '22082', '22101', '22102', '22106', '22116', '22121', '22124', '22150', '22151', '22152', '22153', '22158', '22159', '22160', '22161', '22180', '22181', '22182', '22183', '22185', '22199', '22213'

}

ARLINGTON_ZIPS = {
    '22201', '22202', '22203', '22204', '22205', '22206', '22207', '22209', '22210', '22211', '22212', '22213', '22214', '22215', '22216', '22217', '22218', '22219', '22222', '22225', '22226', '22227', '22230', '22240', '22241', '22242', '22243', '22244', '22245', '22246', '20231', '20301', '20310', '20330', '20350', '20406', '20598', '20453'
}

ALEXANDRIA_ZIPS = {
   '22301', '22302', '22303', '22304', '22305', '22306', '22307', '22308', '22309', '22310', '22311', '22312', '22313', '22314', '22315', '22320', '22331', '22332', '22333', '22334'

}

# Combine all valid zips for quick lookup (optional)
ALL_VALID_ZIPS = FAIRFAX_ZIPS | ARLINGTON_ZIPS | ALEXANDRIA_ZIPS

def extract_zip(address):
    """Extract 5-digit ZIP from address string."""
    if not isinstance(address, str):
        return None
    match = re.search(r'\b(\d{5})\b', address)
    return match.group(1) if match else None

def classify_region(zip_code):
    if zip_code in FAIRFAX_ZIPS:
        return 'Fairfax'
    elif zip_code in ARLINGTON_ZIPS:
        return 'Arlington'
    elif zip_code in ALEXANDRIA_ZIPS:
        return 'Alexandria'
    else:
        return None  # or 'Other'

def split_excel_by_region(input_file, output_prefix='output'):
    # Read Excel file
    df = pd.read_excel(input_file)

    # Ensure 'Address' column exists
    if 'address' not in df.columns:
        raise ValueError("Column 'Address' not found in the Excel file.")

    # Extract ZIP
    df['ZIP'] = df['address'].apply(extract_zip)
    
    # Classify region
    df['Region'] = df['ZIP'].apply(classify_region)

    # Drop rows that don't match any region (optional: keep them in 'Other' if needed)
    df = df[df['Region'].notna()]

    # Split and save
    for region in ['Fairfax', 'Arlington', 'Alexandria']:
        subset = df[df['Region'] == region].drop(columns=['ZIP', 'Region'])
        output_file = f"{output_prefix}_{region.lower()}.xlsx"
        subset.to_excel(output_file, index=False)
        print(f"Saved {len(subset)} rows to {output_file}")

# -------------------------
# Usage Example:
# -------------------------
if __name__ == "__main__":
    input_excel = "stem_virginia.xlsx"  # Replace with your file name
    split_excel_by_region(input_excel, output_prefix="stem")