from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from typing import Optional, List
import uvicorn
from analytics import RestaurantAnalytics
from district_analytics import DistrictAnalytics
from llm_analyzer import LLMAnalyzer
import numpy as np
from pathlib import Path


# Helper to convert numpy types to Python types
def convert_numpy_types(obj):
    """Recursively convert numpy types to Python native types."""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj



app = FastAPI(title="Amsterdam Restaurants API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data storage
RESTAURANTS_FILE = "restaurants_data.json"
FARMS_FILE = "farms_data.json"
restaurants_data = []
farms_data = []


def load_restaurants():
    """Load restaurant data from JSON file."""
    global restaurants_data
    
    if os.path.exists(RESTAURANTS_FILE):
        with open(RESTAURANTS_FILE, 'r', encoding='utf-8') as f:
            restaurants_data = json.load(f)
        print(f"Loaded {len(restaurants_data)} restaurants from {RESTAURANTS_FILE}")
    else:
        print(f"Warning: {RESTAURANTS_FILE} not found. Run scraper.py first.")
        restaurants_data = []


def load_farms():
    """Load farms data from JSON file."""
    global farms_data
    
    if os.path.exists(FARMS_FILE):
        with open(FARMS_FILE, 'r', encoding='utf-8') as f:
            farms_data = json.load(f)
        print(f"Loaded {len(farms_data)} farms from {FARMS_FILE}")
    else:
        print(f"Warning: {FARMS_FILE} not found. Run scraper.py --type farms first.")
        farms_data = []


@app.on_event("startup")
async def startup_event():
    """Load data on startup."""
    load_restaurants()
    load_farms()


@app.get("/")
async def read_root():
    """Serve the main HTML page."""
    return FileResponse("static/index.html")


@app.get("/api/restaurants")
async def get_restaurants(
    search: Optional[str] = Query(None, description="Search by restaurant name"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    max_rating: Optional[float] = Query(None, ge=0, le=5, description="Maximum rating"),
    cuisine: Optional[str] = Query(None, description="Filter by cuisine type"),
    sort_by: Optional[str] = Query("rating", description="Sort by: rating, reviews, name"),
    limit: Optional[int] = Query(None, ge=1, description="Limit number of results")
):
    """
    Get restaurants with optional filtering and sorting.
    """
    filtered_restaurants = restaurants_data.copy()
    
    # Apply search filter
    if search:
        search_lower = search.lower()
        filtered_restaurants = [
            r for r in filtered_restaurants
            if search_lower in r.get('name', '').lower() or
               search_lower in r.get('address', '').lower() or
               search_lower in r.get('cuisine', '').lower()
        ]
    
    # Apply rating filters
    if min_rating is not None:
        filtered_restaurants = [
            r for r in filtered_restaurants
            if r.get('rating') is not None and r.get('rating') >= min_rating
        ]
    
    if max_rating is not None:
        filtered_restaurants = [
            r for r in filtered_restaurants
            if r.get('rating') is not None and r.get('rating') <= max_rating
        ]
    
    # Apply cuisine filter
    if cuisine:
        cuisine_lower = cuisine.lower()
        filtered_restaurants = [
            r for r in filtered_restaurants
            if r.get('cuisine') and cuisine_lower in r.get('cuisine', '').lower()
        ]
    
    # Sort results
    if sort_by == "rating":
        filtered_restaurants.sort(key=lambda x: x.get('rating') or 0, reverse=True)
    elif sort_by == "reviews":
        filtered_restaurants.sort(key=lambda x: x.get('reviews') or 0, reverse=True)
    elif sort_by == "name":
        filtered_restaurants.sort(key=lambda x: x.get('name', '').lower())
    
    # Apply limit
    if limit:
        filtered_restaurants = filtered_restaurants[:limit]
    
    return {
        "total": len(filtered_restaurants),
        "restaurants": filtered_restaurants
    }


@app.get("/api/restaurants/stats")
async def get_stats():
    """Get statistics about the restaurant data."""
    if not restaurants_data:
        return {
            "total_restaurants": 0,
            "average_rating": 0,
            "total_reviews": 0,
            "cuisines": []
        }
    
    # Calculate statistics
    ratings = [r.get('rating') for r in restaurants_data if r.get('rating') is not None]
    reviews = [r.get('reviews') for r in restaurants_data if r.get('reviews') is not None]
    cuisines = {}
    
    for restaurant in restaurants_data:
        cuisine = restaurant.get('cuisine')
        if cuisine:
            cuisines[cuisine] = cuisines.get(cuisine, 0) + 1
    
    # Sort cuisines by count
    sorted_cuisines = sorted(cuisines.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "total_restaurants": len(restaurants_data),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
        "total_reviews": sum(reviews) if reviews else 0,
        "cuisines": [{"name": c[0], "count": c[1]} for c in sorted_cuisines[:10]],
        "rating_distribution": {
            "5_stars": len([r for r in ratings if r >= 4.5]),
            "4_stars": len([r for r in ratings if 3.5 <= r < 4.5]),
            "3_stars": len([r for r in ratings if 2.5 <= r < 3.5]),
            "below_3": len([r for r in ratings if r < 2.5])
        }
    }


@app.get("/api/restaurants/cuisines")
async def get_cuisines():
    """Get list of all unique cuisines."""
    cuisines = set()
    
    for restaurant in restaurants_data:
        cuisine = restaurant.get('cuisine')
        if cuisine:
            cuisines.add(cuisine)
    
    return {
        "cuisines": sorted(list(cuisines))
    }


@app.get("/api/map-data")
async def get_map_data():
    """Get GeoJSON with restaurant statistics per zip code."""
    try:
        # Load PC4 GeoJSON
        geojson_path = "static/amsterdam_pc4.geojson"
        if not os.path.exists(geojson_path):
            return {"error": "GeoJSON not found"}
            
        with open(geojson_path, 'r') as f:
            geojson = json.load(f)
            
        # Aggregate data by zip code (first 4 digits)
        stats_by_pc4 = {}
        
        for r in restaurants_data:
            address = r.get('address', '')
            # Extract 4-digit zip code using regex
            import re
            match = re.search(r'\b(\d{4})\s*[A-Z]{2}\b', address)
            if match:
                pc4 = match.group(1)
                
                if pc4 not in stats_by_pc4:
                    stats_by_pc4[pc4] = {
                        "count": 0,
                        "avg_rating": 0,
                        "total_rating": 0,
                        "cuisines": {}
                    }
                
                stats = stats_by_pc4[pc4]
                stats["count"] += 1
                
                if r.get('rating'):
                    stats["total_rating"] += r['rating']
                    
                cuisine = r.get('cuisine')
                if cuisine:
                    stats["cuisines"][cuisine] = stats["cuisines"].get(cuisine, 0) + 1
        
        # Calculate averages and top cuisines
        for pc4, stats in stats_by_pc4.items():
            if stats["count"] > 0:
                stats["avg_rating"] = round(stats["total_rating"] / stats["count"], 2)
                
            # Get top 3 cuisines
            sorted_cuisines = sorted(stats["cuisines"].items(), key=lambda x: x[1], reverse=True)
            stats["top_cuisines"] = [c[0] for c in sorted_cuisines[:3]]
            del stats["cuisines"] # Remove full list to save space
            del stats["total_rating"]

        # Filter GeoJSON to only include Amsterdam area (roughly 1000-1119)
        # and enrich with stats
        amsterdam_features = []
        for feature in geojson['features']:
            pc4 = feature['properties'].get('pc4')
            if pc4 and 1000 <= int(pc4) <= 1119: # Amsterdam range
                if pc4 in stats_by_pc4:
                    feature['properties'].update(stats_by_pc4[pc4])
                else:
                    feature['properties'].update({
                        "count": 0,
                        "avg_rating": 0,
                        "top_cuisines": []
                    })
                amsterdam_features.append(feature)
                
        return {
            "type": "FeatureCollection",
            "features": amsterdam_features
        }
        
    except Exception as e:
        print(f"Error generating map data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reload")
async def reload_data():
    """Reload restaurant data from file."""
    load_restaurants()
    return {
        "message": "Data reloaded successfully",
        "total_restaurants": len(restaurants_data)
    }


# ============================================================
# FARMS ENDPOINTS
# ============================================================

@app.get("/api/farms")
async def get_farms(
    search: str = "",
    type: str = "",
    min_rating: float = 0,
    sort: str = "rating"
):
    """Get farms with optional filtering and sorting."""
    filtered = farms_data.copy()
    
    # Apply filters
    if search:
        search_lower = search.lower()
        filtered = [
            f for f in filtered
            if (search_lower in f.get('name', '').lower() or
                search_lower in f.get('address', '').lower())
        ]
    
    if type:
        filtered = [f for f in filtered if f.get('cuisine', '') == type]
    
    if min_rating > 0:
        filtered = [f for f in filtered if f.get('rating', 0) >= min_rating]
    
    # Apply sorting
    if sort == 'rating':
        filtered.sort(key=lambda x: x.get('rating') or 0, reverse=True)
    elif sort == 'reviews':
        filtered.sort(key=lambda x: x.get('reviews') or 0, reverse=True)
    elif sort == 'name':
        filtered.sort(key=lambda x: x.get('name', '').lower())
    
    return {
        "total": len(filtered),
        "farms": filtered
    }


@app.get("/api/farms/stats")
async def get_farms_stats():
    """Get statistics about the farms data."""
    if not farms_data:
        return {
            "total_farms": 0,
            "average_rating": 0,
            "total_reviews": 0,
            "types": []
        }
    
    # Calculate statistics
    ratings = [f.get('rating') for f in farms_data if f.get('rating') is not None]
    reviews = [f.get('reviews') for f in farms_data if f.get('reviews') is not None]
    types = {}
    
    for farm in farms_data:
        farm_type = farm.get('cuisine')  # Using cuisine field for farm type
        if farm_type:
            types[farm_type] = types.get(farm_type, 0) + 1
    
    # Sort types by count
    sorted_types = sorted(types.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "total_farms": len(farms_data),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else 0,
        "total_reviews": sum(reviews) if reviews else 0,
        "types": [{"name": t[0], "count": t[1]} for t in sorted_types[:10]],
        "rating_distribution": {
            "5_stars": len([r for r in ratings if r >= 4.5]),
            "4_stars": len([r for r in ratings if 3.5 <= r < 4.5]),
            "3_stars": len([r for r in ratings if 2.5 <= r < 3.5]),
            "below_3": len([r for r in ratings if r < 2.5])
        }
    }


@app.get("/api/farms/map-data")
async def get_farms_map_data():
    """Get GeoJSON with farm statistics per PC4 postal code."""
    try:
        # Load Amsterdam PC4 GeoJSON (covers major cities)
        geojson_path = "static/amsterdam_pc4.geojson"
        if not os.path.exists(geojson_path):
            return {"error": "GeoJSON not found"}
            
        with open(geojson_path, 'r') as f:
            geojson = json.load(f)
            
        # Aggregate data by PC4 (4-digit postal code)
        stats_by_pc4 = {}
        
        for farm in farms_data:
            address = farm.get('address')
            
            # Skip if no address
            if not address:
                continue
            
            # Extract 4-digit postal code using regex
            import re
            match = re.search(r'\b(\d{4})\s*[A-Z]{2}\b', address)
            if match:
                pc4 = match.group(1)
                
                if pc4 not in stats_by_pc4:
                    stats_by_pc4[pc4] = {
                        "count": 0,
                        "avg_rating": 0,
                        "total_rating": 0,
                        "types": {}
                    }
                
                stats_by_pc4[pc4]["count"] += 1
                
                # Add rating
                rating = farm.get('rating')
                if rating:
                    stats_by_pc4[pc4]["total_rating"] += rating
                
                # Add type
                farm_type = farm.get('cuisine', 'Unknown')
                if farm_type:
                    stats_by_pc4[pc4]["types"][farm_type] = stats_by_pc4[pc4]["types"].get(farm_type, 0) + 1
        
        # Calculate averages and top types
        for pc4, stats in stats_by_pc4.items():
            if stats["count"] > 0 and stats["total_rating"] > 0:
                stats["avg_rating"] = round(stats["total_rating"] / stats["count"], 2)
            
            # Get top 3 types
            if stats["types"]:
                sorted_types = sorted(stats["types"].items(), key=lambda x: x[1], reverse=True)
                stats["top_types"] = [t[0] for t in sorted_types[:3]]
            else:
                stats["top_types"] = []
            
            del stats["total_rating"]
            del stats["types"]
        
        # Add statistics to GeoJSON features
        for feature in geojson['features']:
            pc4 = feature['properties'].get('pc4')
            if pc4 and pc4 in stats_by_pc4:
                feature['properties'].update(stats_by_pc4[pc4])
            else:
                feature['properties'].update({
                    "count": 0,
                    "avg_rating": 0,
                    "top_types": []
                })
        
        return geojson
        
    except Exception as e:
        print(f"Error loading farms map data: {e}")
        return {"error": str(e)}


@app.post("/api/farms/reload")
async def reload_farms_data():
    """Reload farms data from file."""
    load_farms()
    return {
        "message": "Farms data reloaded successfully",
        "total_farms": len(farms_data)
    }


@app.get("/api/analytics")
async def get_analytics():
    """Get all analytics data."""
    # Initialize with the same file used by server
    analytics = RestaurantAnalytics(RESTAURANTS_FILE)
    return analytics.get_all_analytics()


@app.get("/api/analytics/districts")
async def get_districts_summary():
    """Get summary analytics for all districts."""
    district_analytics = DistrictAnalytics(RESTAURANTS_FILE)
    districts = district_analytics.get_district_summary()
    return {
        "districts": convert_numpy_types(districts)
    }


@app.get("/api/analytics/district/{pc4}")
async def get_district_analytics(pc4: str):
    """Get detailed analytics for a specific district."""
    # Try to load from cache first
    cache_file = Path('district_analyses_cache.json')
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            if pc4 in cache.get('districts', {}):
                cached_data = cache['districts'][pc4]
                # Return cached analytics and insights
                result = cached_data['analytics'].copy()
                result['ai_insights'] = cached_data['ai_insights']
                result['cached'] = True
                result['generated_at'] = cached_data['generated_at']
                return convert_numpy_types(result)
    
    # Fallback to live generation if not in cache
    district_analytics = DistrictAnalytics(RESTAURANTS_FILE)
    analytics_data = district_analytics.get_detailed_analytics(pc4)
    
    if analytics_data is None or 'error' in analytics_data:
        raise HTTPException(status_code=404, detail="District not found or insufficient data")
    
    # Try to generate LLM insights
    llm = LLMAnalyzer()
    insights = None
    
    try:
        if llm.check_availability():
            insights = llm.generate_district_analysis(pc4, analytics_data)
        else:
            # Use fallback analysis
            insights = llm._generate_fallback_analysis(pc4, analytics_data)
    except Exception as e:
        print(f"Error generating insights: {e}")
        insights = llm._generate_fallback_analysis(pc4, analytics_data)
    
    analytics_data['ai_insights'] = insights
    analytics_data['cached'] = False
    
    # Convert numpy types to Python native types for JSON serialization
    analytics_data = convert_numpy_types(analytics_data)
    
    return analytics_data


@app.post("/api/analytics/district/{pc4}/regenerate")
async def regenerate_district_insights(pc4: str):
    """Regenerate LLM insights for a district."""
    district_analytics = DistrictAnalytics(RESTAURANTS_FILE)
    analytics_data = district_analytics.get_detailed_analytics(pc4)
    
    if analytics_data is None or 'error' in analytics_data:
        raise HTTPException(status_code=404, detail="District not found or insufficient data")
    
    llm = LLMAnalyzer()
    
    try:
        insights = llm.generate_district_analysis(pc4, analytics_data)
        return {"insights": insights, "success": True}
    except Exception as e:
        # Return fallback
        insights = llm._generate_fallback_analysis(pc4, analytics_data)
        return {"insights": insights, "success": False, "error": str(e)}


@app.get("/api/analytics/city-summary")
async def get_city_summary():
    """Get city-wide summary with strategic recommendations."""
    from city_summary import CitySummaryGenerator
    
    generator = CitySummaryGenerator()
    summary = generator.generate_summary()
    
    return convert_numpy_types(summary)


# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Amsterdam Restaurants API Server")
    print("=" * 60)
    print("\nServer will be available at:")
    print("  - Main App: http://localhost:8000")
    print("  - API Docs: http://localhost:8000/docs")
    print("\n" + "=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
