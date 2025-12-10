#!/usr/bin/env python3
"""
Analyze pricing data from the collected restaurant data.
"""

import json
from collections import Counter

def analyze_pricing():
    """Analyze pricing information in the dataset."""
    
    # Load restaurant data
    with open('restaurants_data.json', 'r', encoding='utf-8') as f:
        restaurants = json.load(f)
    
    print("=" * 60)
    print("PRICING DATA ANALYSIS")
    print("=" * 60)
    print(f"\nTotal restaurants: {len(restaurants)}")
    
    # Count pricing data availability
    has_price = [r for r in restaurants if r.get('price_level')]
    no_price = [r for r in restaurants if not r.get('price_level')]
    
    print(f"\nRestaurants with pricing data: {len(has_price)} ({len(has_price)/len(restaurants)*100:.1f}%)")
    print(f"Restaurants without pricing data: {len(no_price)} ({len(no_price)/len(restaurants)*100:.1f}%)")
    
    # Analyze price level distribution
    if has_price:
        print("\n" + "=" * 60)
        print("PRICE LEVEL DISTRIBUTION")
        print("=" * 60)
        
        price_counter = Counter(r['price_level'] for r in has_price)
        
        for price_level, count in sorted(price_counter.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(has_price) * 100
            print(f"{price_level:30s}: {count:5d} ({percentage:5.1f}%)")
        
        # Show examples of each price level
        print("\n" + "=" * 60)
        print("EXAMPLES BY PRICE LEVEL")
        print("=" * 60)
        
        price_examples = {}
        for r in has_price:
            price = r['price_level']
            if price not in price_examples:
                price_examples[price] = []
            if len(price_examples[price]) < 3:
                price_examples[price].append({
                    'name': r.get('name', 'Unknown'),
                    'cuisine': r.get('cuisine', 'Unknown'),
                    'rating': r.get('rating', 'N/A')
                })
        
        for price_level in sorted(price_examples.keys()):
            print(f"\n{price_level}:")
            for example in price_examples[price_level]:
                print(f"  • {example['name']} ({example['cuisine']}) - {example['rating']}⭐")
    
    # Analyze pricing by cuisine
    print("\n" + "=" * 60)
    print("AVERAGE PRICING BY CUISINE (Top 10)")
    print("=" * 60)
    
    cuisine_pricing = {}
    for r in has_price:
        cuisine = r.get('cuisine', 'Unknown')
        price = r['price_level']
        
        if cuisine not in cuisine_pricing:
            cuisine_pricing[cuisine] = []
        cuisine_pricing[cuisine].append(price)
    
    # Count most common price level per cuisine
    cuisine_stats = []
    for cuisine, prices in cuisine_pricing.items():
        if len(prices) >= 5:  # Only cuisines with at least 5 restaurants
            most_common = Counter(prices).most_common(1)[0][0]
            cuisine_stats.append({
                'cuisine': cuisine,
                'count': len(prices),
                'most_common_price': most_common
            })
    
    cuisine_stats.sort(key=lambda x: x['count'], reverse=True)
    
    for stat in cuisine_stats[:10]:
        print(f"{stat['cuisine']:30s}: {stat['most_common_price']:20s} ({stat['count']} restaurants)")
    
    # Export pricing data to CSV
    print("\n" + "=" * 60)
    print("EXPORTING PRICING DATA")
    print("=" * 60)
    
    with open('pricing_analysis.csv', 'w', encoding='utf-8') as f:
        f.write("Name,Cuisine,Price Level,Rating,Reviews,Address\n")
        for r in has_price:
            name = r.get('name', '').replace(',', ';')
            cuisine = r.get('cuisine', '').replace(',', ';')
            price = r.get('price_level', '').replace(',', ';')
            rating = r.get('rating', '')
            reviews = r.get('reviews', '')
            address = r.get('address', '').replace(',', ';')
            f.write(f"{name},{cuisine},{price},{rating},{reviews},{address}\n")
    
    print("✓ Exported pricing data to pricing_analysis.csv")
    
    # Show restaurants missing pricing data
    print("\n" + "=" * 60)
    print("SAMPLE RESTAURANTS WITHOUT PRICING DATA")
    print("=" * 60)
    
    for r in no_price[:10]:
        print(f"• {r.get('name', 'Unknown')} ({r.get('cuisine', 'Unknown')})")

if __name__ == "__main__":
    analyze_pricing()
