import json

with open('restaurants_data.json', 'r') as f:
    data = json.load(f)
    seen = set(r['url'] for r in data if r.get('url'))

with open('collected_urls.json', 'r') as f:
    collected = set(json.load(f))

new_urls = collected - seen
print(f"Total collected: {len(collected)}")
print(f"Already processed: {len(collected & seen)}")
print(f"New to process: {len(new_urls)}")
