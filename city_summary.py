#!/usr/bin/env python3
"""
City-wide summary generator for Amsterdam restaurant market.
Aggregates insights across all districts and generates strategic recommendations.
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from llm_analyzer import LLMAnalyzer


class CitySummaryGenerator:
    def __init__(self, cache_file='district_analyses_cache.json'):
        self.cache_file = cache_file
        self.llm = LLMAnalyzer()
        
    def generate_summary(self):
        """Generate comprehensive city-wide summary."""
        # Load cached analyses
        cache_path = Path(self.cache_file)
        if not cache_path.exists():
            return {"error": "No cached analyses found. Run batch_analyzer.py first."}
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        districts_data = cache.get('districts', {})
        
        if not districts_data:
            return {"error": "No district data available"}
        
        # Aggregate metrics
        summary = {
            'generated_at': cache.get('generated_at'),
            'total_districts': len(districts_data),
            'top_opportunities': self._get_top_opportunities(districts_data),
            'underserved_cuisines': self._get_underserved_cuisines(districts_data),
            'quality_saturation_analysis': self._analyze_quality_saturation(districts_data),
            'market_segments': self._analyze_market_segments(districts_data),
            'investment_priorities': self._get_investment_priorities(districts_data),
            'strategic_recommendations': self._generate_strategic_recommendations(districts_data)
        }
        
        return summary
    
    def _get_top_opportunities(self, districts_data, top_n=10):
        """Get top districts by market potential."""
        opportunities = []
        
        for pc4, data in districts_data.items():
            analytics = data['analytics']
            opp = analytics.get('growth_opportunities', {})
            overview = analytics.get('overview', {})
            
            opportunities.append({
                'pc4': pc4,
                'potential_score': opp.get('market_potential_score', 0),
                'restaurant_count': overview.get('total_restaurants', 0),
                'avg_rating': overview.get('avg_rating', 0),
                'saturation': analytics.get('competition_analysis', {}).get('market_saturation', 'N/A'),
                'positioning': analytics.get('market_positioning', {}).get('positioning', 'N/A'),
                'quality_gap': opp.get('quality_improvement_potential', 0),
                'underserved_count': len(opp.get('underserved_cuisines', []))
            })
        
        # Sort by potential score
        opportunities.sort(key=lambda x: x['potential_score'], reverse=True)
        return opportunities[:top_n]
    
    def _get_underserved_cuisines(self, districts_data):
        """Find cuisines that are underserved citywide."""
        # Count all underserved cuisines across districts
        underserved_counter = Counter()
        excluded_cuisines = ['cannabis store', 'coffee shop', 'coffeeshop']
        
        for data in districts_data.values():
            underserved = data['analytics'].get('growth_opportunities', {}).get('underserved_cuisines', [])
            for cuisine in underserved:
                if cuisine['cuisine'].lower() not in excluded_cuisines:
                    underserved_counter[cuisine['cuisine']] += 1
        
        # Get top underserved cuisines
        top_underserved = [
            {
                'cuisine': cuisine,
                'districts_missing': count,
                'opportunity_level': 'High' if count > 40 else 'Medium' if count > 20 else 'Low'
            }
            for cuisine, count in underserved_counter.most_common(15)
        ]
        
        return top_underserved
    
    def _analyze_quality_saturation(self, districts_data):
        """Analyze quality vs saturation matrix."""
        matrix = {
            'high_quality_low_saturation': [],  # Best opportunities
            'high_quality_high_saturation': [],  # Competitive markets
            'low_quality_low_saturation': [],   # Emerging markets
            'low_quality_high_saturation': []   # Challenging markets
        }
        
        for pc4, data in districts_data.items():
            analytics = data['analytics']
            avg_rating = analytics.get('overview', {}).get('avg_rating', 0)
            saturation = analytics.get('competition_analysis', {}).get('market_saturation', 'Medium')
            count = analytics.get('overview', {}).get('total_restaurants', 0)
            
            district_info = {
                'pc4': pc4,
                'avg_rating': avg_rating,
                'restaurant_count': count,
                'saturation': saturation
            }
            
            # Classify
            high_quality = avg_rating >= 4.3
            high_saturation = saturation == 'High'
            
            if high_quality and not high_saturation:
                matrix['high_quality_low_saturation'].append(district_info)
            elif high_quality and high_saturation:
                matrix['high_quality_high_saturation'].append(district_info)
            elif not high_quality and not high_saturation:
                matrix['low_quality_low_saturation'].append(district_info)
            else:
                matrix['low_quality_high_saturation'].append(district_info)
        
        # Sort each category
        for category in matrix:
            matrix[category].sort(key=lambda x: x['avg_rating'], reverse=True)
        
        return matrix
    
    def _analyze_market_segments(self, districts_data):
        """Analyze market by positioning segments."""
        segments = defaultdict(list)
        
        for pc4, data in districts_data.items():
            positioning = data['analytics'].get('market_positioning', {}).get('positioning', 'Unknown')
            overview = data['analytics'].get('overview', {})
            
            segments[positioning].append({
                'pc4': pc4,
                'restaurant_count': overview.get('total_restaurants', 0),
                'avg_rating': overview.get('avg_rating', 0)
            })
        
        # Calculate segment statistics
        segment_stats = {}
        for segment, districts in segments.items():
            segment_stats[segment] = {
                'district_count': len(districts),
                'total_restaurants': sum(d['restaurant_count'] for d in districts),
                'avg_rating': sum(d['avg_rating'] for d in districts) / len(districts) if districts else 0,
                'districts': sorted(districts, key=lambda x: x['restaurant_count'], reverse=True)[:5]
            }
        
        return segment_stats
    
    def _get_investment_priorities(self, districts_data):
        """Generate investment priority ranking."""
        priorities = []
        
        for pc4, data in districts_data.items():
            analytics = data['analytics']
            overview = analytics.get('overview', {})
            opp = analytics.get('growth_opportunities', {})
            comp = analytics.get('competition_analysis', {})
            
            # Calculate investment score
            potential = opp.get('market_potential_score', 0)
            quality_gap = opp.get('quality_improvement_potential', 0)
            entry_barriers = comp.get('entry_barriers', 'High')
            
            # Score calculation
            score = potential * 0.5  # Potential is most important
            score += quality_gap * 2  # Quality gap is opportunity
            score -= 2 if entry_barriers == 'High' else 1 if entry_barriers == 'Medium' else 0
            
            priorities.append({
                'pc4': pc4,
                'investment_score': round(score, 2),
                'potential_score': potential,
                'quality_gap': quality_gap,
                'entry_barriers': entry_barriers,
                'restaurant_count': overview.get('total_restaurants', 0),
                'recommendation': self._get_investment_recommendation(score, entry_barriers)
            })
        
        priorities.sort(key=lambda x: x['investment_score'], reverse=True)
        return priorities[:15]
    
    def _get_investment_recommendation(self, score, barriers):
        """Get investment recommendation based on score."""
        if score > 6 and barriers != 'High':
            return 'Strong Buy - High potential, manageable barriers'
        elif score > 4:
            return 'Buy - Good opportunity with moderate risk'
        elif score > 2:
            return 'Hold - Consider with caution'
        else:
            return 'Avoid - High risk, low potential'
    
    def _generate_strategic_recommendations(self, districts_data):
        """Generate AI-powered strategic recommendations."""
        # Prepare summary data for LLM
        top_opps = self._get_top_opportunities(districts_data, 5)
        underserved = self._get_underserved_cuisines(districts_data)[:5]
        
        prompt = f"""You are a restaurant market strategist analyzing Amsterdam's dining landscape.

MARKET OVERVIEW:
- Total Districts Analyzed: {len(districts_data)}
- Top 5 Opportunity Districts: {', '.join([f"{d['pc4']} (score: {d['potential_score']}/10)" for d in top_opps])}
- Top 5 Underserved Cuisines: {', '.join([c['cuisine'] for c in underserved])}

TASK:
Write a compelling, high-level executive summary of the Amsterdam restaurant market.
Focus on the **variety of opportunities** for new entrants.
The tone should be professional, encouraging, and visionary.

Structure:
1. **Market Vibrancy**: Describe the overall health and diversity of the scene.
2. **Strategic Opportunities**: Highlight the specific districts ({top_opps[0]['pc4']}, {top_opps[1]['pc4']}) where new concepts can thrive.
3. **Cuisine Gaps**: Mention the demand for specific cuisines ({underserved[0]['cuisine']}, {underserved[1]['cuisine']}) and how they can fill market needs.
4. **Investment Outlook**: Conclude with a strong statement on why now is a good time to invest.

Do NOT use bullet points. Write in fluid, engaging paragraphs. Total length: 300-400 words."""

        try:
            if self.llm.check_availability():
                recommendations = self.llm._call_llm(prompt)
            else:
                recommendations = self._generate_fallback_recommendations(top_opps, underserved)
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            recommendations = self._generate_fallback_recommendations(top_opps, underserved)
        
        return recommendations
    
    def _generate_fallback_recommendations(self, top_opps, underserved):
        """Generate detailed rule-based recommendations as fallback."""
        recs = "**Executive Summary: Amsterdam Restaurant Market Opportunities**\n\n"
        
        recs += "**Market Vibrancy & Outlook**\n"
        recs += "Amsterdam's dining scene is showing remarkable resilience and diversity. "
        recs += "The market is characterized by a strong mix of established culinary traditions and a growing appetite for international concepts. "
        recs += "While central districts remain competitive, we observe a significant shift of potential towards emerging neighborhoods where saturation is lower and demand for quality is rising.\n\n"
        
        recs += "**Strategic Opportunities**\n"
        recs += f"Our analysis identifies **District {top_opps[0]['pc4']}** and **District {top_opps[1]['pc4']}** as the prime targets for new ventures. "
        recs += f"These areas score highest in our market potential index ({top_opps[0]['potential_score']}/10 and {top_opps[1]['potential_score']}/10 respectively), "
        recs += "indicating a favorable balance of high demand and manageable competition. "
        recs += "Investors entering these markets now can establish a strong foothold before saturation increases.\n\n"
        
        recs += "**Cuisine Gaps & Concept Opportunities**\n"
        if underserved:
            recs += "There is a clear, data-backed demand for specific culinary experiences. "
            recs += f"**{underserved[0]['cuisine']}** and **{underserved[1]['cuisine']}** are significantly underserved citywide. "
            recs += "Concepts focusing on these cuisines, particularly when combined with a modern, quality-focused approach, have a higher probability of capturing immediate market share. "
            recs += "Authenticity and specialization are key differentiators in this landscape.\n\n"
        
        recs += "**Investment Verdict**\n"
        recs += "The current market conditions offer a unique window for strategic entry. "
        recs += "By targeting high-potential districts and filling specific cuisine gaps, new entrants can mitigate risks associated with the competitive central zones. "
        recs += "We recommend a focus on quality-driven concepts in these identified growth areas for maximum return on investment."
        
        return recs


if __name__ == "__main__":
    generator = CitySummaryGenerator()
    summary = generator.generate_summary()
    
    print(json.dumps(summary, indent=2))
