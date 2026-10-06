import json
import csv
import os

json_path = "/Users/alexandrfilippov/Desktop/amsterdam-restaurants-scraper/data/restaurants_data.json"
csv_path = "/Users/alexandrfilippov/Desktop/amsterdam-restaurants-scraper/data/restaurants_data.csv"

if not os.path.exists(json_path):
    print(f"Error: JSON file not found at {json_path}")
    exit(1)

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

if not data:
    print("Error: JSON file is empty")
    exit(1)

# Get headers from first element, but hardcode standard keys to be safe and order them logically
headers = ["name", "cuisine", "rating", "reviews", "price_level", "address", "phone", "website", "latitude", "longitude", "url"]

with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    for row in data:
        # Filter row keys to match specified headers
        filtered_row = {k: row.get(k) for k in headers}
        writer.writerow(filtered_row)

print(f"Successfully converted {len(data)} restaurants to CSV at {csv_path}")
