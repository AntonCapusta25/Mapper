#!/usr/bin/env python3
"""
Enhanced district-level analytics for restaurant market research.
Provides comprehensive metrics per district with detailed insights.
"""

import json
import numpy as np
from collections import Counter, defaultdict
from scipy import stats
import re


class DistrictAnalytics:
    def __init__(self, data_file='restaurants_data.json'):
        """Initialize district analytics with restaurant data."""
        with open(data_file, 'r', encoding='utf-8') as f:
            self.restaurants = json.load(f)
        
        # Extract PC4 codes from addresses
        for r in self.restaurants:
            address = r.get('address') or ''
            if address:
                match = re.search(r'\b(\d{4})\s*[A-Z]{2}\b', address)
                r['pc4'] = match.group(1) if match else None
            else:
                r['pc4'] = None
        
        # Group restaurants by district
        self.districts = defaultdict(list)
        for r in self.restaurants:
            if r.get('pc4'):
                self.districts[r['pc4']].append(r)
    
    def get_district_summary(self):
        """Get summary metrics for all districts."""
        summaries = []
        
        for pc4, restaurants in self.districts.items():
            if len(restaurants) >= 3:  # Only include districts with 3+ restaurants
                summary = {
                    'pc4': pc4,
                    'restaurant_count': len(restaurants),
                    'avg_rating': self._calc_avg_rating(restaurants),
                    'total_reviews': sum(r.get('reviews') or 0 for r in restaurants),
                    'cuisine_diversity': self._calc_cuisine_diversity(restaurants),
                    'market_saturation': self._calc_saturation_level(len(restaurants))
                }
                summaries.append(summary)
        
        # Sort by restaurant count
        summaries.sort(key=lambda x: x['restaurant_count'], reverse=True)
        return summaries
    
    def get_detailed_analytics(self, pc4):
        """Get comprehensive analytics for a specific district."""
        if pc4 not in self.districts:
            return None
        
        restaurants = self.districts[pc4]
        
        if len(restaurants) < 3:
            return {'error': 'Insufficient data for this district'}
        
        analytics = {
            'pc4': pc4,
            'overview': self._calc_overview_metrics(restaurants),
            'quality_metrics': self._calc_quality_metrics(restaurants),
            'price_analysis': self._calc_price_analysis(restaurants),
            'cuisine_analysis': self._calc_cuisine_analysis(restaurants),
            'competition_analysis': self._calc_competition_metrics(restaurants),
            'market_positioning': self._calc_market_positioning(restaurants),
            'growth_opportunities': self._calc_growth_opportunities(pc4, restaurants),
            'benchmarks': self._calc_benchmarks(pc4, restaurants)
        }
        
        return analytics
    
    def _calc_overview_metrics(self, restaurants):
        """Calculate basic overview metrics."""
        return {
            'total_restaurants': len(restaurants),
            'avg_rating': self._calc_avg_rating(restaurants),
            'median_rating': self._calc_median_rating(restaurants),
            'total_reviews': sum(r.get('reviews') or 0 for r in restaurants),
            'avg_reviews': np.mean([r.get('reviews') or 0 for r in restaurants]),
            'cuisines_count': len(set(r.get('cuisine') for r in restaurants if r.get('cuisine')))
        }
    
    def _calc_quality_metrics(self, restaurants):
        """Calculate quality-related metrics."""
        ratings = [r['rating'] for r in restaurants if r.get('rating')]
        reviews = [r['reviews'] for r in restaurants if r.get('reviews') and r['reviews'] is not None]
        
        if not ratings:
            return {}
        
        return {
            'rating_distribution': {
                'mean': round(np.mean(ratings), 2),
                'median': round(np.median(ratings), 2),
                'std_dev': round(np.std(ratings), 2),
                'min': round(min(ratings), 2),
                'max': round(max(ratings), 2),
                'percentiles': {
                    '25th': round(np.percentile(ratings, 25), 2),
                    '75th': round(np.percentile(ratings, 75), 2),
                    '90th': round(np.percentile(ratings, 90), 2)
                }
            },
            'high_rated_count': len([r for r in ratings if r >= 4.5]),
            'low_rated_count': len([r for r in ratings if r < 3.5]),
            'review_volume': {
                'total': sum(reviews) if reviews else 0,
                'mean': round(np.mean(reviews), 1) if reviews else 0,
                'median': round(np.median(reviews), 1) if reviews else 0,
                'high_engagement': len([r for r in reviews if r >=100]) if reviews else 0
            }
        }
    
    def _calc_price_analysis(self, restaurants):
        """Analyze price levels in the district."""
        price_mapping = {'€': 1, '€€': 2, '€€€': 3, '€€€€': 4}
        prices = []
        
        for r in restaurants:
            price_level = r.get('price_level', '')
            if price_level in price_mapping:
                prices.append(price_mapping[price_level])
        
        if not prices:
            return {'available': False}
        
        price_counter = Counter(prices)
        
        return {
            'available': True,
            'average_price_level': round(np.mean(prices), 1),
            'median_price_level': int(np.median(prices)),
            'distribution': {
                'budget': price_counter.get(1, 0),
                'moderate': price_counter.get(2, 0),
                'upscale': price_counter.get(3, 0),
                'fine_dining': price_counter.get(4, 0)
            },
            'affordability_score': self._calc_affordability_score(prices)
        }
    
    def _calc_cuisine_analysis(self, restaurants):
        """Analyze cuisine diversity and distribution."""
        cuisines = [r['cuisine'] for r in restaurants if r.get('cuisine')]
        
        if not cuisines:
            return {}
        
        cuisine_counter = Counter(cuisines)
        total = len(cuisines)
        
        # Calculate Shannon diversity index
        shannon_index = -sum((count/total) * np.log(count/total) 
                            for count in cuisine_counter.values())
        
        return {
            'total_cuisines': len(cuisine_counter),
            'diversity_index': round(shannon_index, 2),
            'top_cuisines': [
                {'cuisine': c, 'count': count, 'percentage': round(count/total*100, 1)}
                for c, count in cuisine_counter.most_common(10)
            ],
            'concentration': {
                'top_3_share': round(sum(c for _, c in cuisine_counter.most_common(3))/total*100, 1),
                'is_concentrated': cuisine_counter.most_common(1)[0][1]/total > 0.3
            }
        }
    
    def _calc_competition_metrics(self, restaurants):
        """Calculate competition-related metrics."""
        count = len(restaurants)
        
        # Market saturation based on restaurant count
        saturation_level = 'High' if count > 50 else 'Medium' if count > 20 else 'Low'
        
        # Competition intensity (restaurants per cuisine on average)
        cuisines = [r['cuisine'] for r in restaurants if r.get('cuisine')]
        unique_cuisines = len(set(cuisines))
        avg_competitors_per_cuisine = count / unique_cuisines if unique_cuisines > 0 else 0
        
        return {
            'market_saturation': saturation_level,
            'saturation_score': min(count / 10, 10),  # 0-10 scale
            'total_restaurants': count,
            'avg_competitors_per_cuisine': round(avg_competitors_per_cuisine, 1),
            'competitive_intensity': 'High' if avg_competitors_per_cuisine > 5 else 'Medium' if avg_competitors_per_cuisine > 2 else 'Low',
            'entry_barriers': self._assess_entry_barriers(count, avg_competitors_per_cuisine)
        }
    
    def _calc_market_positioning(self, restaurants):
        """Analyze market positioning (quality vs price)."""
        ratings = [r['rating'] for r in restaurants if r.get('rating')]
        
        price_mapping = {'€': 1, '€€': 2, '€€€': 3, '€€€€': 4}
        prices = [price_mapping.get(r.get('price_level', ''), 2) for r in restaurants if r.get('price_level')]
        
        if not ratings or not prices:
            return {}
        
        avg_rating = np.mean(ratings)
        avg_price = np.mean(prices)
        
        # Classify positioning
        if avg_rating >= 4.3 and avg_price >= 2.5:
            positioning = 'Premium'
        elif avg_rating >= 4.3 and avg_price < 2.5:
            positioning = 'Value Premium'
        elif avg_rating < 4.0 and avg_price >= 2.5:
            positioning = 'Overpriced'
        else:
            positioning = 'Budget Casual'
        
        return {
            'positioning': positioning,
            'avg_rating': round(avg_rating, 2),
            'avg_price_level': round(avg_price, 1),
            'quality_price_ratio': round(avg_rating / avg_price, 2)
        }
    
    def _calc_growth_opportunities(self, pc4, restaurants):
        """Identify growth opportunities in the district."""
        # Get all cuisines in dataset
        all_cuisines = set(r['cuisine'] for r in self.restaurants if r.get('cuisine'))
        district_cuisines = set(r['cuisine'] for r in restaurants if r.get('cuisine'))
        
        # Find popular missing cuisines
        missing = all_cuisines - district_cuisines
        popular_missing = []
        
        for cuisine in missing:
            global_count = sum(1 for r in self.restaurants if r.get('cuisine') == cuisine)
            if global_count >= 10:  # Popular globally but missing here
                popular_missing.append({
                    'cuisine': cuisine,
                    'global_popularity': global_count
                })
        
        popular_missing.sort(key=lambda x: x['global_popularity'], reverse=True)
        
        # Quality gap
        avg_rating = self._calc_avg_rating(restaurants)
        quality_gap = 4.5 - avg_rating if avg_rating < 4.5 else 0
        
        return {
            'underserved_cuisines': popular_missing[:5],
            'quality_improvement_potential': round(quality_gap, 2),
            'has_quality_gap': quality_gap > 0.3,
            'market_potential_score': self._calc_market_potential(pc4, restaurants)
        }
    
    def _calc_benchmarks(self, pc4, restaurants):
        """Calculate benchmarks comparing to citywide averages."""
        # Citywide metrics
        all_ratings = [r['rating'] for r in self.restaurants if r.get('rating')]
        all_reviews = [r['reviews'] for r in self.restaurants if r.get('reviews')]
        
        # District metrics
        district_ratings = [r['rating'] for r in restaurants if r.get('rating')]
        district_reviews = [r['reviews'] for r in restaurants if r.get('reviews')]
        
        return {
            'vs_citywide': {
                'rating_diff': round(np.mean(district_ratings) - np.mean(all_ratings), 2) if district_ratings and all_ratings else 0,
                'reviews_diff': round(np.mean(district_reviews) - np.mean(all_reviews), 1) if district_reviews and all_reviews else 0,
                'rating_percentile': self._calc_percentile(np.mean(district_ratings), all_ratings) if district_ratings and all_ratings else 50
            }
        }
    
    # Helper methods
    def _calc_avg_rating(self, restaurants):
        ratings = [r['rating'] for r in restaurants if r.get('rating')]
        return round(np.mean(ratings), 2) if ratings else 0
    
    def _calc_median_rating(self, restaurants):
        ratings = [r['rating'] for r in restaurants if r.get('rating')]
        return round(np.median(ratings), 2) if ratings else 0
    
    def _calc_cuisine_diversity(self, restaurants):
        cuisines = [r['cuisine'] for r in restaurants if r.get('cuisine')]
        return len(set(cuisines)) if cuisines else 0
    
    def _calc_saturation_level(self, count):
        if count > 50:
            return 'High'
        elif count > 20:
            return 'Medium'
        else:
            return 'Low'
    
    def _calc_affordability_score(self, prices):
        """Calculate affordability score (lower is more affordable)."""
        avg_price = np.mean(prices)
        # Score from 0-10, where 1=very affordable, 4=very expensive
        return round((5 - avg_price) * 2, 1)
    
    def _assess_entry_barriers(self, count, avg_competitors):
        """Assess entry barriers for new restaurants."""
        if count > 50 or avg_competitors > 5:
            return 'High'
        elif count > 20 or avg_competitors > 3:
            return 'Medium'
        else:
            return 'Low'
    
    def _calc_market_potential(self, pc4, restaurants):
        """Calculate overall market potential score (0-10)."""
        count = len(restaurants)
        avg_rating = self._calc_avg_rating(restaurants)
        diversity = self._calc_cuisine_diversity(restaurants)
        
        # Lower saturation + lower quality + lower diversity = higher potential
        saturation_factor = max(0, 10 - count/5)  # Higher when fewer restaurants
        quality_factor = max(0, (4.5 - avg_rating) * 2)  # Higher when lower quality
        diversity_factor = max(0, 10 - diversity)  # Higher when less diverse
        
        score = (saturation_factor + quality_factor + diversity_factor) / 3
        return round(min(score, 10), 1)
    
    def _calc_percentile(self, value, all_values):
        """Calculate percentile of value in all_values."""
        return round(stats.percentileofscore(all_values, value), 0)


if __name__ == "__main__":
    # Test the analytics
    analytics = DistrictAnalytics()
    
    print("=" * 60)
    print("DISTRICT ANALYTICS TEST")
    print("=" * 60)
    
    # Get summary
    summaries = analytics.get_district_summary()
    print(f"\nTotal districts: {len(summaries)}")
    print(f"\nTop 5 districts by restaurant count:")
    for s in summaries[:5]:
        print(f"  {s['pc4']}: {s['restaurant_count']} restaurants, "
              f"{s['avg_rating']}⭐, {s['cuisine_diversity']} cuisines")
    
    # Get detailed analytics for top district
    if summaries:
        top_district = summaries[0]['pc4']
        details = analytics.get_detailed_analytics(top_district)
        print(f"\nDetailed analytics for {top_district}:")
        print(f"  Market position: {details.get('market_positioning', {}).get('positioning', 'N/A')}")
        print(f"  Competition: {details.get('competition_analysis', {}).get('competitive_intensity', 'N/A')}")
        print(f"  Potential score: {details.get('growth_opportunities', {}).get('market_potential_score', 0)}/10")
