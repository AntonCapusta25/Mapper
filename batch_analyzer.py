#!/usr/bin/env python3
"""
Batch analyzer for generating AI insights for all Amsterdam districts.
Pre-generates and caches analyses for instant access.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from district_analytics import DistrictAnalytics
from llm_analyzer import LLMAnalyzer


class BatchAnalyzer:
    def __init__(self, data_file='restaurants_data.json', cache_file='district_analyses_cache.json'):
        self.data_file = data_file
        self.cache_file = cache_file
        self.district_analytics = DistrictAnalytics(data_file)
        self.llm = LLMAnalyzer()
        
    def generate_all_analyses(self, rate_limit_seconds=1):
        """Generate AI insights for all districts and cache them."""
        print("=" * 70)
        print("BATCH DISTRICT ANALYSIS - AI INSIGHTS GENERATION")
        print("=" * 70)
        
        # Get all districts
        districts_summary = self.district_analytics.get_district_summary()
        total_districts = len(districts_summary)
        
        print(f"\nTotal districts to process: {total_districts}")
        print(f"Estimated time: ~{total_districts * 8 / 60:.1f} minutes")
        print(f"Rate limit: {rate_limit_seconds} second(s) between requests\n")
        
        # Check if LLM is available
        if not self.llm.check_availability():
            print("⚠️  WARNING: Ollama is not running. Using fallback analysis.")
            print("   Start Ollama with: ollama serve")
            use_llm = False
        else:
            print("✓ Ollama is running and ready")
            use_llm = True
        
        # Load existing cache if available
        cache = self._load_cache()
        
        # Process each district
        results = {
            'generated_at': datetime.now().isoformat(),
            'total_districts': total_districts,
            'llm_used': use_llm,
            'districts': {}
        }
        
        start_time = time.time()
        
        for idx, district_summary in enumerate(districts_summary, 1):
            pc4 = district_summary['pc4']
            
            print(f"\n[{idx}/{total_districts}] Processing {pc4}...")
            
            try:
                # Get detailed analytics
                analytics_data = self.district_analytics.get_detailed_analytics(pc4)
                
                if analytics_data and 'error' not in analytics_data:
                    # Generate AI insights
                    print(f"  → Generating AI insights...")
                    insight_start = time.time()
                    
                    if use_llm:
                        try:
                            insights = self.llm.generate_district_analysis(pc4, analytics_data)
                        except Exception as e:
                            print(f"  ⚠️  LLM error: {e}, using fallback")
                            insights = self.llm._generate_fallback_analysis(pc4, analytics_data)
                    else:
                        insights = self.llm._generate_fallback_analysis(pc4, analytics_data)
                    
                    insight_time = time.time() - insight_start
                    
                    # Store in results
                    results['districts'][pc4] = {
                        'analytics': analytics_data,
                        'ai_insights': insights,
                        'generated_at': datetime.now().isoformat(),
                        'generation_time_seconds': round(insight_time, 2)
                    }
                    
                    print(f"  ✓ Complete ({insight_time:.1f}s) - {len(insights)} characters")
                    
                    # Rate limiting
                    if idx < total_districts:
                        time.sleep(rate_limit_seconds)
                else:
                    print(f"  ✗ Skipped - insufficient data")
                    
            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue
        
        total_time = time.time() - start_time
        
        # Save cache
        print(f"\n{'=' * 70}")
        print(f"BATCH PROCESSING COMPLETE")
        print(f"{'=' * 70}")
        print(f"Total time: {total_time / 60:.1f} minutes")
        print(f"Districts processed: {len(results['districts'])}/{total_districts}")
        print(f"Average time per district: {total_time / len(results['districts']):.1f}s")
        
        self._save_cache(results)
        print(f"\n✓ Cache saved to: {self.cache_file}")
        
        # Export text reports
        self._export_text_reports(results)
        
        return results
    
    def _load_cache(self):
        """Load existing cache if available."""
        cache_path = Path(self.cache_file)
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def _save_cache(self, data):
        """Save cache to file."""
        # Convert numpy types before saving
        from server import convert_numpy_types
        data = convert_numpy_types(data)
        
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _export_text_reports(self, results):
        """Export text reports for presentations."""
        print(f"\n{'=' * 70}")
        print("EXPORTING TEXT REPORTS")
        print(f"{'=' * 70}")
        
        # Create reports directory
        reports_dir = Path('district_reports')
        reports_dir.mkdir(exist_ok=True)
        
        # Export individual district reports
        for pc4, data in results['districts'].items():
            report_file = reports_dir / f"district_{pc4}_analysis.txt"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write(f"AMSTERDAM DISTRICT {pc4} - MARKET ANALYSIS REPORT\n")
                f.write("=" * 70 + "\n\n")
                
                # Overview
                overview = data['analytics']['overview']
                f.write("OVERVIEW\n")
                f.write("-" * 70 + "\n")
                f.write(f"Total Restaurants: {overview['total_restaurants']}\n")
                f.write(f"Average Rating: {overview['avg_rating']}/5.0\n")
                f.write(f"Total Reviews: {overview['total_reviews']:,}\n")
                f.write(f"Cuisine Diversity: {overview['cuisines_count']} cuisines\n\n")
                
                # AI Insights
                f.write("AI-GENERATED MARKET ANALYSIS\n")
                f.write("-" * 70 + "\n")
                f.write(data['ai_insights'])
                f.write("\n\n")
                
                # Key Metrics
                f.write("DETAILED METRICS\n")
                f.write("-" * 70 + "\n\n")
                
                # Competition
                comp = data['analytics']['competition_analysis']
                f.write(f"Market Saturation: {comp['market_saturation']}\n")
                f.write(f"Competitive Intensity: {comp['competitive_intensity']}\n")
                f.write(f"Entry Barriers: {comp['entry_barriers']}\n\n")
                
                # Market Positioning
                pos = data['analytics']['market_positioning']
                f.write(f"Market Position: {pos.get('positioning', 'N/A')}\n")
                f.write(f"Quality/Price Ratio: {pos.get('quality_price_ratio', 'N/A')}\n\n")
                
                # Growth Opportunities
                opp = data['analytics']['growth_opportunities']
                f.write(f"Market Potential Score: {opp['market_potential_score']}/10\n")
                f.write(f"Quality Gap: {opp['quality_improvement_potential']}\n")
                
                underserved = opp.get('underserved_cuisines', [])
                if underserved:
                    f.write(f"\nUnderserved Cuisines:\n")
                    for cuisine in underserved[:5]:
                        f.write(f"  - {cuisine['cuisine']} ({cuisine['global_popularity']} citywide)\n")
                
                f.write("\n" + "=" * 70 + "\n")
                f.write(f"Report generated: {data['generated_at']}\n")
                f.write("=" * 70 + "\n")
        
        print(f"✓ Exported {len(results['districts'])} individual district reports")
        
        # Export summary report
        summary_file = reports_dir / "city_wide_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("AMSTERDAM RESTAURANT MARKET - CITY-WIDE SUMMARY\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Total Districts Analyzed: {len(results['districts'])}\n")
            f.write(f"Analysis Date: {results['generated_at']}\n")
            f.write(f"LLM Used: {'Yes' if results['llm_used'] else 'No (Fallback)'}\n\n")
            
            # Top opportunities
            f.write("TOP 10 HIGHEST-POTENTIAL DISTRICTS\n")
            f.write("-" * 70 + "\n")
            
            # Sort by market potential
            sorted_districts = sorted(
                results['districts'].items(),
                key=lambda x: x[1]['analytics']['growth_opportunities']['market_potential_score'],
                reverse=True
            )
            
            for idx, (pc4, data) in enumerate(sorted_districts[:10], 1):
                score = data['analytics']['growth_opportunities']['market_potential_score']
                count = data['analytics']['overview']['total_restaurants']
                rating = data['analytics']['overview']['avg_rating']
                f.write(f"{idx}. District {pc4}: Potential {score}/10 ")
                f.write(f"({count} restaurants, {rating} avg rating)\n")
            
            f.write("\n" + "=" * 70 + "\n")
        
        print(f"✓ Exported city-wide summary report")
        print(f"\nReports directory: {reports_dir.absolute()}")


if __name__ == "__main__":
    print("\nStarting batch analysis...\n")
    
    analyzer = BatchAnalyzer()
    results = analyzer.generate_all_analyses(rate_limit_seconds=0.5)
    
    print(f"\n{'=' * 70}")
    print("ALL DONE!")
    print(f"{'=' * 70}")
    print(f"\nCache file: district_analyses_cache.json")
    print(f"Reports directory: district_reports/")
    print(f"\nYou can now:")
    print("  1. View individual district reports in district_reports/")
    print("  2. Read city-wide summary in district_reports/city_wide_summary.txt")
    print("  3. Access cached data via API endpoints")
