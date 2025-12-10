#!/usr/bin/env python3
"""
Analytics engine for restaurant market research.
Provides regression analysis, market saturation metrics, and gap identification.
"""

import json
import numpy as np
from collections import Counter, defaultdict
from scipy import stats
import re


class RestaurantAnalytics:
    def __init__(self, data_file='restaurants_data.json'):
        """Initialize analytics with restaurant data."""
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
    
    def regression_analysis(self):
        """Perform regression analysis on restaurant data."""
        results = {}
        
        # 1. Rating vs Reviews correlation
        restaurants_with_data = [r for r in self.restaurants 
                                if r.get('rating') and r.get('reviews')]
        
        if len(restaurants_with_data) > 10:
            ratings = [r['rating'] for r in restaurants_with_data]
            reviews = [r['reviews'] for r in restaurants_with_data]
            
            # Log transform reviews for better linear relationship
            log_reviews = np.log1p(reviews)
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(log_reviews, ratings)
            
            results['rating_vs_reviews'] = {
                'correlation': r_value,
                'r_squared': r_value ** 2,
                'p_value': p_value,
                'slope': slope,
                'intercept': intercept,
                'interpretation': self._interpret_correlation(r_value),
                'sample_size': len(restaurants_with_data)
            }
        
        # 2. Cuisine performance analysis
        cuisine_stats = defaultdict(lambda: {'ratings': [], 'reviews': []})
        for r in self.restaurants:
            if r.get('cuisine') and r.get('rating'):
                cuisine_stats[r['cuisine']]['ratings'].append(r['rating'])
                if r.get('reviews'):
                    cuisine_stats[r['cuisine']]['reviews'].append(r['reviews'])
        
        cuisine_performance = []
        for cuisine, data in cuisine_stats.items():
            if len(data['ratings']) >= 5:  # At least 5 restaurants
                cuisine_performance.append({
                    'cuisine': cuisine,
                    'avg_rating': np.mean(data['ratings']),
                    'median_rating': np.median(data['ratings']),
                    'count': len(data['ratings']),
                    'avg_reviews': np.mean(data['reviews']) if data['reviews'] else 0,
                    'std_dev': np.std(data['ratings'])
                })
        
        cuisine_performance.sort(key=lambda x: x['avg_rating'], reverse=True)
        results['cuisine_performance'] = cuisine_performance[:20]  # Top 20
        
        # 3. District performance analysis
        district_stats = defaultdict(lambda: {'ratings': [], 'count': 0})
        for r in self.restaurants:
            if r.get('pc4') and r.get('rating'):
                district_stats[r['pc4']]['ratings'].append(r['rating'])
                district_stats[r['pc4']]['count'] += 1
        
        district_performance = []
        for pc4, data in district_stats.items():
            if data['count'] >= 3:
                district_performance.append({
                    'pc4': pc4,
                    'avg_rating': np.mean(data['ratings']),
                    'count': data['count'],
                    'std_dev': np.std(data['ratings'])
                })
        
        district_performance.sort(key=lambda x: x['avg_rating'], reverse=True)
        results['district_performance'] = district_performance
        
        return results
    
    def market_saturation_analysis(self):
        """Analyze market saturation by district and cuisine."""
        saturation = {}
        
        # 1. Overall district saturation
        district_counts = Counter(r['pc4'] for r in self.restaurants if r.get('pc4'))
        
        saturation_levels = []
        for pc4, count in district_counts.items():
            if count >= 5:
                level = 'High' if count > 50 else 'Medium' if count > 20 else 'Low'
                saturation_levels.append({
                    'pc4': pc4,
                    'restaurant_count': count,
                    'saturation_level': level,
                    'competition_score': min(count / 10, 10)  # 0-10 scale
                })
        
        saturation_levels.sort(key=lambda x: x['restaurant_count'], reverse=True)
        saturation['by_district'] = saturation_levels
        
        # 2. Cuisine saturation
        cuisine_counts = Counter(r['cuisine'] for r in self.restaurants if r.get('cuisine'))
        
        total_restaurants = len(self.restaurants)
        cuisine_saturation = []
        for cuisine, count in cuisine_counts.most_common(30):
            market_share = (count / total_restaurants) * 100
            saturation_level = 'Oversaturated' if market_share > 5 else 'Saturated' if market_share > 2 else 'Moderate'
            
            cuisine_saturation.append({
                'cuisine': cuisine,
                'count': count,
                'market_share': round(market_share, 2),
                'saturation_level': saturation_level
            })
        
        saturation['by_cuisine'] = cuisine_saturation
        
        # 3. District-Cuisine matrix (find gaps)
        district_cuisine_matrix = defaultdict(lambda: defaultdict(int))
        for r in self.restaurants:
            if r.get('pc4') and r.get('cuisine'):
                district_cuisine_matrix[r['pc4']][r['cuisine']] += 1
        
        saturation['district_cuisine_matrix'] = {
            pc4: dict(cuisines) for pc4, cuisines in district_cuisine_matrix.items()
        }
        
        return saturation
    
    def market_gap_analysis(self):
        """Identify market gaps and opportunities."""
        gaps = {}
        
        # 1. Underserved cuisines by district
        all_cuisines = set(r['cuisine'] for r in self.restaurants if r.get('cuisine'))
        district_cuisines = defaultdict(set)
        district_counts = Counter()
        
        for r in self.restaurants:
            if r.get('pc4') and r.get('cuisine'):
                district_cuisines[r['pc4']].add(r['cuisine'])
                district_counts[r['pc4']] += 1
        
        underserved_opportunities = []
        for pc4, cuisines in district_cuisines.items():
            if district_counts[pc4] >= 10:  # Only districts with decent activity
                missing_cuisines = all_cuisines - cuisines
                # Focus on popular cuisines that are missing
                popular_missing = [c for c in missing_cuisines 
                                 if sum(1 for r in self.restaurants 
                                       if r.get('cuisine') == c) >= 10]
                
                if popular_missing:
                    underserved_opportunities.append({
                        'pc4': pc4,
                        'missing_cuisines': popular_missing[:5],  # Top 5
                        'current_variety': len(cuisines),
                        'opportunity_score': len(popular_missing)
                    })
        
        underserved_opportunities.sort(key=lambda x: x['opportunity_score'], reverse=True)
        gaps['underserved_cuisines'] = underserved_opportunities[:15]
        
        # 2. Quality gaps (low-rated districts)
        district_ratings = defaultdict(list)
        for r in self.restaurants:
            if r.get('pc4') and r.get('rating'):
                district_ratings[r['pc4']].append(r['rating'])
        
        quality_gaps = []
        for pc4, ratings in district_ratings.items():
            if len(ratings) >= 5:
                avg_rating = np.mean(ratings)
                if avg_rating < 4.0:  # Below 4.0 is an opportunity
                    quality_gaps.append({
                        'pc4': pc4,
                        'avg_rating': round(avg_rating, 2),
                        'restaurant_count': len(ratings),
                        'opportunity': 'High-quality restaurant needed',
                        'potential_impact': round((4.5 - avg_rating) * 10, 1)
                    })
        
        quality_gaps.sort(key=lambda x: x['potential_impact'], reverse=True)
        gaps['quality_gaps'] = quality_gaps[:10]
        
        # 3. Review volume gaps (low engagement areas)
        district_reviews = defaultdict(list)
        for r in self.restaurants:
            if r.get('pc4') and r.get('reviews'):
                district_reviews[r['pc4']].append(r['reviews'])
        
        engagement_gaps = []
        for pc4, reviews in district_reviews.items():
            if len(reviews) >= 5:
                avg_reviews = np.mean(reviews)
                if avg_reviews < 100:  # Low engagement
                    engagement_gaps.append({
                        'pc4': pc4,
                        'avg_reviews': round(avg_reviews, 1),
                        'restaurant_count': len(reviews),
                        'opportunity': 'Marketing and community engagement needed'
                    })
        
        engagement_gaps.sort(key=lambda x: x['avg_reviews'])
        gaps['engagement_gaps'] = engagement_gaps[:10]
        
        # 4. Emerging opportunities (high rating, low competition)
        cuisine_opportunities = []
        cuisine_stats = defaultdict(lambda: {'ratings': [], 'count': 0})
        
        for r in self.restaurants:
            if r.get('cuisine') and r.get('rating'):
                cuisine_stats[r['cuisine']]['ratings'].append(r['rating'])
                cuisine_stats[r['cuisine']]['count'] += 1
        
        for cuisine, data in cuisine_stats.items():
            if 5 <= data['count'] <= 30:  # Not too saturated, not too rare
                avg_rating = np.mean(data['ratings'])
                if avg_rating >= 4.2:  # High quality
                    cuisine_opportunities.append({
                        'cuisine': cuisine,
                        'avg_rating': round(avg_rating, 2),
                        'current_count': data['count'],
                        'opportunity': 'High demand, low supply',
                        'growth_potential': 'High'
                    })
        
        cuisine_opportunities.sort(key=lambda x: x['avg_rating'], reverse=True)
        gaps['emerging_cuisines'] = cuisine_opportunities[:10]
        
        return gaps
    
    def trend_analysis(self):
        """Analyze trends in the restaurant market."""
        trends = {}
        
        # 1. Rating distribution
        ratings = [r['rating'] for r in self.restaurants if r.get('rating')]
        if ratings:
            trends['rating_distribution'] = {
                'mean': round(np.mean(ratings), 2),
                'median': round(np.median(ratings), 2),
                'std_dev': round(np.std(ratings), 2),
                'percentiles': {
                    '25th': round(np.percentile(ratings, 25), 2),
                    '50th': round(np.percentile(ratings, 50), 2),
                    '75th': round(np.percentile(ratings, 75), 2),
                    '90th': round(np.percentile(ratings, 90), 2)
                },
                'histogram': self._create_histogram(ratings, bins=10)
            }
        
        # 2. Review volume distribution
        reviews = [r['reviews'] for r in self.restaurants if r.get('reviews')]
        if reviews:
            trends['review_distribution'] = {
                'mean': round(np.mean(reviews), 1),
                'median': round(np.median(reviews), 1),
                'total': sum(reviews),
                'percentiles': {
                    '25th': round(np.percentile(reviews, 25), 1),
                    '50th': round(np.percentile(reviews, 50), 1),
                    '75th': round(np.percentile(reviews, 75), 1),
                    '90th': round(np.percentile(reviews, 90), 1)
                }
            }
        
        # 3. Top growing cuisines (by review volume)
        cuisine_reviews = defaultdict(int)
        for r in self.restaurants:
            if r.get('cuisine') and r.get('reviews'):
                cuisine_reviews[r['cuisine']] += r['reviews']
        
        top_cuisines = sorted(cuisine_reviews.items(), key=lambda x: x[1], reverse=True)[:15]
        trends['top_cuisines_by_engagement'] = [
            {'cuisine': c, 'total_reviews': r} for c, r in top_cuisines
        ]
        
        return trends
    
    def _interpret_correlation(self, r_value):
        """Interpret correlation coefficient."""
        abs_r = abs(r_value)
        if abs_r >= 0.7:
            strength = "Strong"
        elif abs_r >= 0.4:
            strength = "Moderate"
        elif abs_r >= 0.2:
            strength = "Weak"
        else:
            strength = "Very weak"
        
        direction = "positive" if r_value > 0 else "negative"
        return f"{strength} {direction} correlation"
    
    def _create_histogram(self, data, bins=10):
        """Create histogram data."""
        hist, bin_edges = np.histogram(data, bins=bins)
        return {
            'counts': hist.tolist(),
            'bins': bin_edges.tolist()
        }
    
    def get_all_analytics(self):
        """Get all analytics in one call."""
        return {
            'regression': self.regression_analysis(),
            'saturation': self.market_saturation_analysis(),
            'gaps': self.market_gap_analysis(),
            'trends': self.trend_analysis()
        }


if __name__ == "__main__":
    # Test the analytics
    analytics = RestaurantAnalytics()
    results = analytics.get_all_analytics()
    
    print("=" * 60)
    print("ANALYTICS SUMMARY")
    print("=" * 60)
    print(f"\nRegression Analysis:")
    print(f"  Rating vs Reviews R²: {results['regression']['rating_vs_reviews']['r_squared']:.3f}")
    print(f"\nTop 5 Cuisines by Rating:")
    for c in results['regression']['cuisine_performance'][:5]:
        print(f"  {c['cuisine']}: {c['avg_rating']:.2f} ({c['count']} restaurants)")
    print(f"\nMarket Gaps Found: {len(results['gaps']['underserved_cuisines'])} districts")
    print(f"Quality Gaps: {len(results['gaps']['quality_gaps'])} districts")
