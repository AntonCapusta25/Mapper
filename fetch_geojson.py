import requests
import json

def fetch_amsterdam_districts():
    # Option 1: Try PC4 from Opendatasoft (Preferred)
    pc4_url = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/georef-netherlands-postcode-pc4/exports/geojson?lang=en&timezone=Europe%2FBerlin"
    print(f"Trying PC4 data from {pc4_url}...")
    
    try:
        response = requests.get(pc4_url)
        if response.status_code == 200:
            print("✓ Found PC4 data!")
            data = response.json()
            
            # Filter for Amsterdam PC4 (1000-1119)
            amsterdam_features = []
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                pc4 = props.get('pc4_code') or props.get('pc4')
                
                if pc4 and str(pc4).isdigit():
                    pc4_int = int(pc4)
                    if 1000 <= pc4_int <= 1119:
                        # Normalize property name to 'pc4'
                        feature['properties']['pc4'] = str(pc4)
                        amsterdam_features.append(feature)
            
            print(f"Found {len(amsterdam_features)} Amsterdam PC4 areas.")
            
            if amsterdam_features:
                save_geojson(amsterdam_features, 'static/amsterdam_pc4.geojson')
                return
    except Exception as e:
        print(f"Error fetching PC4: {e}")

    # Option 2: Fallback to Wijk (Districts) from Cartomap
    years = [2023, 2022, 2021, 2020]
    for year in years:
        url = f"https://cartomap.github.io/nl/wgs84/wijk_{year}.geojson"
        print(f"Trying Wijk data from {url}...")
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"✓ Found Wijk data for {year}!")
                data = response.json()
                
                amsterdam_features = []
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    if props.get('gemeentenaam') == 'Amsterdam' or props.get('GM_NAAM') == 'Amsterdam':
                        amsterdam_features.append(feature)
                
                print(f"Found {len(amsterdam_features)} Amsterdam districts.")
                
                if amsterdam_features:
                    save_geojson(amsterdam_features, 'static/amsterdam_districts.geojson')
                    return
        except Exception as e:
            print(f"Error fetching Wijk {year}: {e}")

def save_geojson(features, filename):
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    with open(filename, 'w') as f:
        json.dump(geojson, f)
    print(f"Saved to {filename}")

if __name__ == "__main__":
    fetch_amsterdam_districts()
