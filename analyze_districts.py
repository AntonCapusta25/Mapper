import json
import re
from collections import defaultdict, Counter
import statistics

def extract_pc4(address):
    """Extract 4-digit postal code from address."""
    if not address:
        return None
    match = re.search(r'\b(\d{4})\s*[A-Z]{2}\b', address)
    return match.group(1) if match else None

def parse_price_level(price_str):
    """Convert price level string to numeric value."""
    if not price_str:
        return None
    # Count dollar signs or euro symbols
    if '€' in price_str:
        return price_str.count('€')
    elif '$' in price_str:
        return price_str.count('$')
    elif 'Moderate' in price_str or 'Mid-range' in price_str:
        return 2
    elif 'Expensive' in price_str or 'Upscale' in price_str:
        return 3
    elif 'Inexpensive' in price_str or 'Budget' in price_str:
        return 1
    return None

def analyze_districts():
    """Analyze restaurant distribution with deep insights."""
    
    # Load restaurant data
    with open('restaurants_data.json', 'r', encoding='utf-8') as f:
        restaurants = json.load(f)
    
    # Group by PC4
    districts = defaultdict(lambda: {
        'restaurants': [],
        'cuisines': Counter(),
        'ratings': [],
        'prices': [],
        'total': 0
    })
    
    # Overall statistics
    overall_cuisines = Counter()
    overall_ratings = []
    overall_prices = []
    
    for r in restaurants:
        pc4 = extract_pc4(r.get('address', ''))
        if not pc4:
            continue
            
        cuisine = r.get('cuisine', 'Unknown')
        rating = r.get('rating')
        price = parse_price_level(r.get('price_level'))
        
        districts[pc4]['restaurants'].append(r)
        districts[pc4]['total'] += 1
        
        if cuisine and cuisine != 'Unknown':
            districts[pc4]['cuisines'][cuisine] += 1
            overall_cuisines[cuisine] += 1
        
        if rating:
            districts[pc4]['ratings'].append(rating)
            overall_ratings.append(rating)
        
        if price:
            districts[pc4]['prices'].append(price)
            overall_prices.append(price)
    
    # Calculate citywide metrics
    total_restaurants = sum(overall_cuisines.values())
    avg_citywide_rating = statistics.mean(overall_ratings) if overall_ratings else 0
    avg_citywide_price = statistics.mean(overall_prices) if overall_prices else 0
    top_cuisines = overall_cuisines.most_common(15)
    
    print(f"Total restaurants analyzed: {total_restaurants}")
    print(f"Citywide avg rating: {avg_citywide_rating:.2f}")
    print(f"Citywide avg price level: {avg_citywide_price:.2f}")
    
    # Analyze each district
    recommendations = {}
    
    for pc4, data in districts.items():
        if data['total'] < 5:  # Skip districts with too few restaurants
            continue
        
        # Calculate district metrics
        avg_rating = statistics.mean(data['ratings']) if data['ratings'] else 0
        avg_price = statistics.mean(data['prices']) if data['prices'] else 0
        
        # Price distribution
        price_dist = Counter(data['prices'])
        budget_count = price_dist.get(1, 0)
        mid_count = price_dist.get(2, 0)
        upscale_count = price_dist.get(3, 0) + price_dist.get(4, 0)
        
        # Find cuisine gaps
        missing_cuisines = []
        underrepresented = []
        
        for cuisine, citywide_count in top_cuisines[:10]:
            expected_pct = citywide_count / total_restaurants
            district_count = data['cuisines'].get(cuisine, 0)
            district_pct = district_count / data['total'] if data['total'] > 0 else 0
            
            if district_count == 0:
                missing_cuisines.append(cuisine)
            elif district_pct < (expected_pct * 0.5):
                underrepresented.append(cuisine)
        
        # Market saturation analysis
        density = data['total']
        saturation = "Low" if density < 20 else "Medium" if density < 50 else "High"
        
        # Price gap analysis
        price_gaps = []
        total_with_price = sum(price_dist.values())
        if total_with_price > 0:
            budget_pct = (budget_count / total_with_price) * 100
            mid_pct = (mid_count / total_with_price) * 100
            upscale_pct = (upscale_count / total_with_price) * 100
            
            if budget_pct < 20:
                price_gaps.append("budget-friendly")
            if mid_pct < 30:
                price_gaps.append("mid-range")
            if upscale_pct < 15:
                price_gaps.append("upscale")
        
        # Generate comprehensive recommendation
        insights = []
        
        # Market opportunity
        if saturation == "Low":
            insights.append("🎯 Low competition - great market entry opportunity")
        elif saturation == "High":
            insights.append("⚠️ Saturated market - differentiation crucial")
        
        # Quality insight
        if avg_rating > avg_citywide_rating + 0.2:
            insights.append(f"⭐ High-quality area (avg {avg_rating:.1f}★)")
        elif avg_rating < avg_citywide_rating - 0.2:
            insights.append(f"📈 Quality gap - opportunity for excellence (avg {avg_rating:.1f}★)")
        
        # Price insights
        if price_gaps:
            insights.append(f"💰 Price gaps: {', '.join(price_gaps)}")
        
        if avg_price > avg_citywide_price + 0.3:
            insights.append("💎 Premium dining area")
        elif avg_price < avg_citywide_price - 0.3:
            insights.append("💵 Value-focused market")
        
        # Cuisine opportunities
        if missing_cuisines:
            top_missing = missing_cuisines[:2]
            insights.append(f"🍽️ Missing: {', '.join(top_missing)}")
        
        if underrepresented:
            insights.append(f"📊 Underserved: {', '.join(underrepresented[:2])}")
        
        # Top performers
        top_local = data['cuisines'].most_common(3)
        top_names = [f"{c[0]} ({c[1]})" for c in top_local]
        
        recommendations[pc4] = {
            'total_restaurants': data['total'],
            'avg_rating': round(avg_rating, 2),
            'avg_price_level': round(avg_price, 2),
            'saturation': saturation,
            'top_cuisines': [c[0] for c in top_local],
            'cuisine_counts': dict(top_local),
            'price_distribution': {
                'budget': budget_count,
                'mid_range': mid_count,
                'upscale': upscale_count
            },
            'missing_cuisines': missing_cuisines[:3],
            'insights': insights,
            'recommendation': ' • '.join(insights) if insights else 'Balanced market'
        }
    
    # Save recommendations
    with open('static/district_recommendations.json', 'w', encoding='utf-8') as f:
        json.dump(recommendations, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Generated deep analysis for {len(recommendations)} districts")
    print("✓ Saved to static/district_recommendations.json")
    
    # Print sample
    print("\nSample analysis:")
    for pc4 in list(recommendations.keys())[:3]:
        rec = recommendations[pc4]
        print(f"\nPC4 {pc4}:")
        print(f"  Restaurants: {rec['total_restaurants']}")
        print(f"  Avg Rating: {rec['avg_rating']}★")
        print(f"  Saturation: {rec['saturation']}")
        print(f"  Insights: {rec['recommendation'][:100]}...")
    
    return recommendations

if __name__ == "__main__":
    analyze_districts()
