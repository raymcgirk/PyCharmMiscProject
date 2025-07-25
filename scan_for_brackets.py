import os
import re
import csv

path_to_scan = r"Y:\\"  # Update this to your directory
output_csv = r"C:\Users\RayMc\OneDrive\Desktop\bracketed_files.csv"  # Output path for CSV
pattern = re.compile(r"\[.*?\]")

matches = []

for root, dirs, files in os.walk(path_to_scan):
    for filename in files:
        if pattern.search(filename):
            full_path = os.path.join(root, filename)
            matches.append([full_path])

# Write to CSV
with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["FilePath"])  # Header row
    writer.writerows(matches)

print(f"Found {len(matches)} file(s) with brackets. Results saved to {output_csv}")
