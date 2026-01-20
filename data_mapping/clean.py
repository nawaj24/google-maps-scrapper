import pandas as pd

# 1️⃣ Load your Excel file
# Replace 'input.xlsx' with the path to your Excel file
df = pd.read_excel('swimming_4_1.xlsx')

# 2️⃣ Replace '+' signs with spaces in the 'Name' column
# Replace 'Name' with the exact column header in your Excel file
df['name'] = df['name'].str.replace('+', ' ', regex=False)

# 3️⃣ Save the cleaned data to a new Excel file
df.to_excel('swimming_4.xlsx', index=False)

print("✅ Names cleaned and saved to 'cleaned_output.xlsx'")
