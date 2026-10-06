import sys
import os
import json
import re
import csv
import math
from collections import Counter
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
INPUT_JSON = "data/enschede_restaurants_data.json"
INPUT_CSV  = "data/enschede_restaurants_data.csv"
OUTPUT_DIR = "enschede_district_reports"
CACHE_FILE = "data/enschede_district_analyses_cache.json"

ENSCHEDE_DISTRICT_NAMES = {
    "7511": "Enschede Binnenstad / Oude Markt",
    "7512": "Enschede Centrum-Oost / De Heurne / Bothoven",
    "7513": "Enschede Horstlanden / Veldkamp / Getfert",
    "7514": "Enschede Boddenkamp / Walhof",
    "7521": "Enschede Twekkelerveld / Tubantia",
    "7522": "Enschede Kennispark / UT / Bolhaar",
    "7523": "Enschede Roombeek / Mekkelholt / Deppenbroek",
    "7524": "Enschede De Eschmarke Noord",
    "7531": "Enschede Ribbelt / Stokhorst",
    "7532": "Enschede Eilermark / Glanerbrug Noord",
    "7533": "Enschede Dolphia / De Eschmarke",
    "7534": "Enschede Glanerbrug Centrum",
    "7535": "Enschede Lonneker",
    "7541": "Enschede Hogeland",
    "7542": "Enschede Wesselerbrink Noord",
    "7543": "Enschede Wesselerbrink Zuid",
    "7544": "Enschede Helmerhoek",
    "7545": "Enschede Stadsveld / Pathmos",
    "7546": "Enschede Boswinkel / Ruwenbos",
    "7547": "Enschede Usselo",
    "7548": "Enschede Boekelo"
}

def parse_pc4(address: str, url: str = "") -> str:
    # Look for Dutch 4-digit postcode (75xx) in address or url
    m = re.search(r'\b(75\d{2})\b', address)
    if m:
        return m.group(1)
    if url:
        m_url = re.search(r'\b(75\d{2})\b', url)
        if m_url:
            return m_url.group(1)
    return "7511" # Default to Enschede Centrum if unspecified

def calculate_opportunity_score(count: int, avg_rating: float, total_reviews: int, cuisine_diversity: int) -> float:
    # High reviews + good rating + moderate count = high opportunity / demand
    count_factor = max(1.0, math.log10(count + 1))
    review_factor = max(1.0, math.log10(total_reviews + 10))
    rating_factor = avg_rating / 5.0
    
    score = (review_factor * 1.5 + rating_factor * 2.0 + cuisine_diversity * 0.3) / (count_factor * 0.8)
    return round(min(10.0, max(1.0, score)), 1)

def run_analysis():
    print("=" * 70)
    print("ENSCHEDE DISTRICT MARKET MAP & ANALYSIS GENERATOR")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs("data", exist_ok=True)

    records = []
    if os.path.exists(INPUT_JSON):
        with open(INPUT_JSON, "r", encoding="utf-8") as f:
            records = json.load(f)
    elif os.path.exists(INPUT_CSV):
        with open(INPUT_CSV, "r", encoding="utf-8") as f:
            records = list(csv.DictReader(f))

    print(f"Total mapped records loaded: {len(records)}")

    # Group by district PC4
    districts_data = {}
    for r in records:
        pc4 = parse_pc4(r.get("address", ""), r.get("url", ""))
        if pc4 not in districts_data:
            districts_data[pc4] = []
        districts_data[pc4].append(r)

    print(f"Districts identified: {len(districts_data)}")

    city_summary_districts = []
    cache_output = {
        "generated_at": datetime.now().isoformat(),
        "total_districts": len(districts_data),
        "total_restaurants": len(records),
        "districts": {}
    }

    for pc4, items in sorted(districts_data.items()):
        district_name = ENSCHEDE_DISTRICT_NAMES.get(pc4, f"Enschede District {pc4}")
        count = len(items)

        # Ratings
        ratings = []
        reviews_total = 0
        cuisines_list = []

        for item in items:
            try:
                rate_val = float(str(item.get("rating", "")).replace(",", "."))
                if 1.0 <= rate_val <= 5.0:
                    ratings.append(rate_val)
            except Exception:
                pass

            try:
                rev_val = int(str(item.get("reviews", "")).replace(",", ""))
                reviews_total += rev_val
            except Exception:
                pass

            c = item.get("cuisine", "").strip()
            if c:
                cuisines_list.append(c)

        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 4.2
        cuisine_counts = Counter(cuisines_list)
        top_cuisines = cuisine_counts.most_common(5)
        diversity_score = len(cuisine_counts)

        opp_score = calculate_opportunity_score(count, avg_rating, reviews_total, diversity_score)

        summary_entry = {
            "pc4": pc4,
            "name": district_name,
            "count": count,
            "avg_rating": avg_rating,
            "reviews_total": reviews_total,
            "opportunity_score": opp_score,
            "top_cuisines": top_cuisines
        }
        city_summary_districts.append(summary_entry)

        # Build Individual District Report Text
        report_content = f"""======================================================================
ENSCHEDE DISTRICT {pc4} ({district_name.upper()}) - MARKET ANALYSIS REPORT
======================================================================

OVERVIEW
----------------------------------------------------------------------
Total Restaurants & Eateries: {count}
Average Rating: {avg_rating}/5.0
Total Customer Reviews: {reviews_total:,}
Cuisine Diversity Index: {diversity_score} distinct cuisines
Market Opportunity Score: {opp_score}/10.0

TOP CUISINES & EATERIES IN {pc4}
----------------------------------------------------------------------
"""
        for c_name, c_cnt in top_cuisines:
            report_content += f"- {c_name}: {c_cnt} venue(s)\n"

        report_content += f"""
DETAILED DISTRICT MARKET ANALYSIS
----------------------------------------------------------------------
The restaurant and dining market in Enschede district {pc4} ({district_name}) features {count} active dining establishments with an average rating of {avg_rating}/5.0 and {reviews_total:,} total reviews on Google Maps.

Key Market Observations:
1. Market Density: District {pc4} has a {'high' if count >= 20 else 'moderate' if count >= 8 else 'boutique'} concentration of hospitality venues.
2. Demand & Engagement: Accumulated review volume ({reviews_total:,} reviews) indicates {'strong' if reviews_total > 5000 else 'steady'} consumer traffic.
3. Opportunity Index: Rated {opp_score}/10.0 based on customer satisfaction vs venue competition ratio.

FEATURED VENUES IN THIS DISTRICT
----------------------------------------------------------------------
"""
        for item in items[:10]:
            report_content += f"- {item.get('name', 'N/A')} | Cuisine: {item.get('cuisine', 'N/A')} | Rating: {item.get('rating', 'N/A')} ({item.get('reviews', '0')} reviews) | Phone: {item.get('phone', 'N/A')}\n"

        report_path = os.path.join(OUTPUT_DIR, f"district_{pc4}_analysis.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        cache_output["districts"][pc4] = summary_entry

    # Sort city summary by opportunity score descending
    city_summary_districts.sort(key=lambda x: x["opportunity_score"], reverse=True)

    # Build City-Wide Summary Report
    city_report_content = f"""======================================================================
ENSCHEDE RESTAURANT MARKET - CITY-WIDE MAP & DISTRICT ANALYSIS
======================================================================

Total Districts Analyzed: {len(districts_data)}
Total Restaurants & Eateries Mapped: {len(records)}
Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

TOP HIGHEST-POTENTIAL ENSCHEDE DISTRICTS
----------------------------------------------------------------------
"""
    for rank, d in enumerate(city_summary_districts[:10], 1):
        city_report_content += f"{rank}. District {d['pc4']} ({d['name']}): Potential {d['opportunity_score']}/10.0 ({d['count']} restaurants, {d['avg_rating']} avg rating, {d['reviews_total']:,} reviews)\n"

    city_report_content += f"""
FULL ENSCHEDE DISTRICT BREAKDOWN
----------------------------------------------------------------------
"""
    for d in city_summary_districts:
        city_report_content += f"• PC {d['pc4']} - {d['name']}: {d['count']} venues | Avg Rating: {d['avg_rating']} | Reviews: {d['reviews_total']:,} | Opp Score: {d['opportunity_score']}/10.0\n"

    summary_file = os.path.join(OUTPUT_DIR, "enschede_city_wide_summary.txt")
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(city_report_content)

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Analysis complete! Generated {len(districts_data)} district reports in '{OUTPUT_DIR}/'.")
    print(f"   City-Wide Summary: {summary_file}")
    print(f"   Cache File: {CACHE_FILE}")

if __name__ == "__main__":
    run_analysis()
