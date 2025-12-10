#!/usr/bin/env python3
"""
LLM integration for generating district analysis insights.
Supports Ollama and other local LLM services.
"""

import requests
import json
from typing import Dict, Optional
import os
import copy


class LLMAnalyzer:
    def __init__(self, model='llama3', base_url='http://localhost:11434'):
        """
        Initialize LLM analyzer.
        
        Args:
            model: Model name (e.g., 'llama3', 'mistral', 'phi')
            base_url: Ollama API base URL
        """
        self.model = model
        self.base_url = base_url
        self.api_url = f"{base_url}/api/generate"
    
    def generate_district_analysis(self, pc4: str, analytics_data: Dict) -> Optional[str]:
        """Generate AI analysis for a district."""
        # Filter out cannabis and coffee shops from analytics data before sending to LLM
        filtered_data = self._filter_sensitive_categories(analytics_data)
        
        prompt = self._create_analysis_prompt(pc4, filtered_data)
        
        try:
            response = self._call_llm(prompt)
            return response
        except Exception as e:
            print(f"Error generating analysis: {e}")
            return self._generate_fallback_analysis(pc4, filtered_data)

    def _filter_sensitive_categories(self, data):
        """Remove cannabis and coffee shop related data."""
        clean_data = copy.deepcopy(data)
        
        # Filter top cuisines
        if 'cuisine_analysis' in clean_data and 'top_cuisines' in clean_data['cuisine_analysis']:
            clean_data['cuisine_analysis']['top_cuisines'] = [
                c for c in clean_data['cuisine_analysis']['top_cuisines']
                if c['cuisine'].lower() not in ['cannabis store', 'coffee shop', 'coffeeshop']
            ]
            
        # Filter underserved cuisines
        if 'growth_opportunities' in clean_data and 'underserved_cuisines' in clean_data['growth_opportunities']:
            clean_data['growth_opportunities']['underserved_cuisines'] = [
                c for c in clean_data['growth_opportunities']['underserved_cuisines']
                if c['cuisine'].lower() not in ['cannabis store', 'coffee shop', 'coffeeshop']
            ]
            
        return clean_data
    
    def _create_analysis_prompt(self, pc4: str, data: Dict) -> str:
        """Create structured prompt for district analysis."""
        
        overview = data.get('overview', {})
        quality = data.get('quality_metrics', {})
        price = data.get('price_analysis', {})
        cuisine = data.get('cuisine_analysis', {})
        competition = data.get('competition_analysis', {})
        positioning = data.get('market_positioning', {})
        opportunities = data.get('growth_opportunities', {})
        benchmarks = data.get('benchmarks', {})
        
        # Extract metrics for cleaner f-string
        total_restaurants = overview.get('total_restaurants', 0)
        avg_rating = overview.get('avg_rating', 0)
        total_reviews = overview.get('total_reviews', 0)
        cuisine_count = overview.get('cuisines_count', 0)
        
        rating_dist = quality.get('rating_distribution', {})
        min_rating = rating_dist.get('min', 0)
        max_rating = rating_dist.get('max', 0)
        high_rated = quality.get('high_rated_count', 0)
        review_mean = quality.get('review_volume', {}).get('mean', 0)
        
        avg_price = price.get('average_price_level', 0)
        affordability = price.get('affordability_score', 0)
        price_dist = price.get('distribution', {})
        
        top_cuisine = cuisine.get('top_cuisines', [{}])[0].get('cuisine', 'N/A') if cuisine.get('top_cuisines') else 'N/A'
        is_concentrated = "High" if cuisine.get('concentration', {}).get('is_concentrated') else "Low"
        
        saturation = competition.get('market_saturation', 'N/A')
        intensity = competition.get('competitive_intensity', 'N/A')
        barriers = competition.get('entry_barriers', 'N/A')
        
        pos_category = positioning.get('positioning', 'N/A')
        qp_ratio = positioning.get('quality_price_ratio', 0)
        
        potential = opportunities.get('market_potential_score', 0)
        quality_gap = opportunities.get('quality_improvement_potential', 0)
        missing_count = len(opportunities.get('underserved_cuisines', []))
        
        rating_diff = benchmarks.get('vs_citywide', {}).get('rating_diff', 0)
        reviews_diff = benchmarks.get('vs_citywide', {}).get('reviews_diff', 0)
        
        # Pre-format variables to avoid f-string complexity
        review_mean_str = f"{review_mean:.0f}"
        rating_diff_str = f"{rating_diff:+.2f}"
        reviews_diff_str = f"{reviews_diff:+.0f}"
        
        prompt = f"""You are a restaurant market analyst providing insights for Amsterdam district {pc4}.

DATA OVERVIEW:
- Total Restaurants: {total_restaurants}
- Average Rating: {avg_rating}/5.0
- Total Reviews: {total_reviews:,}
- Cuisine Diversity: {cuisine_count} different cuisines

QUALITY METRICS:
- Rating Range: {min_rating} - {max_rating}
- High-Rated (4.5+): {high_rated} restaurants
- Review Engagement: {review_mean_str} avg reviews per restaurant

PRICE ANALYSIS:
- Average Price Level: {avg_price}/4.0
- Affordability Score: {affordability}/10
- Distribution: Budget {price_dist.get('budget', 0)}, Moderate {price_dist.get('moderate', 0)}, Upscale {price_dist.get('upscale', 0)}

CUISINE LANDSCAPE:
- Total Cuisines: {cuisine.get('total_cuisines', 0)}
- Diversity Index: {cuisine.get('diversity_index', 0)}
- Top Cuisine: {top_cuisine}
- Market Concentration: {is_concentrated}

COMPETITION:
- Market Saturation: {saturation}
- Competitive Intensity: {intensity}
- Entry Barriers: {barriers}

MARKET POSITIONING:
- Category: {pos_category}
- Quality/Price Ratio: {qp_ratio}

GROWTH OPPORTUNITIES:
- Market Potential Score: {potential}/10
- Quality Gap: {quality_gap}
- Missing Popular Cuisines: {missing_count}

BENCHMARKING:
- Rating vs Citywide: {rating_diff_str}
- Reviews vs Citywide: {reviews_diff_str}

TASK:
Provide a comprehensive 300-400 word analysis covering:
1. Market Overview (2-3 sentences on current state)
2. Competitive Landscape (strengths and challenges)
3. Business Opportunities (specific actionable insights)
4. Strategic Recommendations (for new or existing businesses)

Write in a professional, data-driven tone. Be specific and actionable."""

        return prompt
    
    def _call_llm(self, prompt: str, max_retries: int = 2) -> str:
        """Call Ollama API to generate response."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "num_predict": 500  # Ollama uses num_predict instead of max_tokens
            }
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                
                result = response.json()
                return result.get('response', '').strip()
                
            except requests.exceptions.ConnectionError:
                if attempt == max_retries - 1:
                    raise Exception("Cannot connect to Ollama. Make sure it's running: 'ollama serve'")
                continue
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise Exception("LLM request timed out")
                continue
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"LLM error: {str(e)}")
                continue
        
        return ""
    
    def _generate_fallback_analysis(self, pc4: str, data: Dict) -> str:
        """Generate simple rule-based analysis as fallback."""
        overview = data.get('overview', {})
        competition = data.get('competition_analysis', {})
        positioning = data.get('market_positioning', {})
        opportunities = data.get('growth_opportunities', {})
        
        count = overview.get('total_restaurants', 0)
        rating = overview.get('avg_rating', 0)
        saturation = competition.get('market_saturation', 'Medium')
        position = positioning.get('positioning', 'Budget Casual')
        potential = opportunities.get('market_potential_score', 5)
        
        analysis = f"""District {pc4} Market Analysis

**Market Overview:** This district contains {count} restaurants with an average rating of {rating}/5.0. """
        
        if saturation == 'High':
            analysis += "The market shows high saturation, indicating intense competition. "
        elif saturation == 'Low':
            analysis += "The market has room for growth with relatively low saturation. "
        else:
            analysis += "The market has moderate saturation levels. "
        
        analysis += f"The predominant market positioning is {position}.\n\n"
        
        analysis += f"""**Competitive Landscape:** """
        if potential > 7:
            analysis += "Strong opportunities exist due to lower competition and quality gaps. "
        elif potential > 4:
            analysis += "Moderate opportunities available for differentiated offerings. "
        else:
            analysis += "Highly competitive environment requiring strong differentiation. "
        
        missing_cuisines = opportunities.get('underserved_cuisines', [])
        if missing_cuisines:
            top_missing = missing_cuisines[0].get('cuisine', '')
            analysis += f"Notable gap in {top_missing} cuisine.\n\n"
        else:
            analysis += "\n\n"
        
        analysis += f"""**Business Opportunities:** """
        if opportunities.get('has_quality_gap'):
            analysis += "Quality improvement presents a significant opportunity. "
        if missing_cuisines:
            analysis += f"Consider introducing underserved cuisines. "
        
        analysis += f"""\n\n**Strategic Recommendations:** Focus on quality and unique positioning to stand out in this market."""
        
        return analysis
    
    def check_availability(self) -> bool:
        """Check if LLM service is available."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False


if __name__ == "__main__":
    # Test the LLM analyzer
    analyzer = LLMAnalyzer()
    
    print("=" * 60)
    print("LLM ANALYZER TEST")
    print("=" * 60)
    
    # Check availability
    if analyzer.check_availability():
        print("✓ Ollama is running and accessible")
    else:
        print("✗ Ollama is not running. Start it with: ollama serve")
        print("  Using fallback analysis mode")
    
    # Test with sample data
    sample_data = {
        'overview': {
            'total_restaurants': 45,
            'avg_rating': 4.2,
            'total_reviews': 12500,
            'cuisines_count': 15
        },
        'competition_analysis': {
            'market_saturation': 'Medium',
            'competitive_intensity': 'High'
        },
        'market_positioning': {
            'positioning': 'Value Premium'
        },
        'growth_opportunities': {
            'market_potential_score': 6.5,
            'has_quality_gap': False,
            'underserved_cuisines': [
                {'cuisine': 'Vietnamese', 'global_popularity': 25}
            ]
        }
    }
    
    print("\nGenerating analysis for test district 1012...")
    analysis = analyzer.generate_district_analysis('1012', sample_data)
    print("\n" + analysis)
