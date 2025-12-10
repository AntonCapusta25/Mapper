# Amsterdam Restaurants Scraper

A comprehensive Google Maps scraper for Amsterdam restaurants with a beautiful web interface.

## Features

- 🔍 **Smart Scraping**: Extracts detailed restaurant information from Google Maps
- 🎨 **Modern UI**: Beautiful dark-themed interface with glassmorphism effects
- 🔎 **Advanced Filtering**: Filter by cuisine, rating, and search by name/address
- 📊 **Statistics**: View aggregate data about restaurants
- 📥 **Export**: Download filtered results as CSV
- 🗺️ **Maps Integration**: Direct links to Google Maps for each restaurant

## Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd amsterdam-restaurants-scraper
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Step 1: Scrape Restaurant Data

Run the scraper to collect restaurant data from Google Maps:

```bash
python scraper.py
```

This will:
- Open Google Maps in a headless Chrome browser
- Search for "restaurants in Amsterdam"
- Scroll through results to load more restaurants
- Extract detailed information for each restaurant
- Save data to `restaurants_data.json`

**Configuration**: Edit `config.json` to customize:
- `search_query`: Change the search term
- `max_results`: Maximum number of restaurants to scrape
- `scroll_pause_time`: Delay between scrolls (seconds)
- `headless`: Run browser in headless mode (true/false)

### Step 2: Start the Web Server

Launch the FastAPI server to view results:

```bash
python server.py
```

Or use uvicorn directly:

```bash
uvicorn server:app --reload
```

### Step 3: View Results

Open your browser and navigate to:
- **Main App**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Data Extracted

For each restaurant, the scraper collects:

- ✅ Name
- ✅ Rating (stars)
- ✅ Number of reviews
- ✅ Address
- ✅ Phone number
- ✅ Website
- ✅ Cuisine type
- ✅ Price level
- ✅ Coordinates (latitude/longitude)

## API Endpoints

### GET `/api/restaurants`

Get all restaurants with optional filtering:

**Query Parameters**:
- `search`: Search by name, address, or cuisine
- `min_rating`: Minimum rating (0-5)
- `max_rating`: Maximum rating (0-5)
- `cuisine`: Filter by cuisine type
- `sort_by`: Sort by `rating`, `reviews`, or `name`
- `limit`: Limit number of results

**Example**:
```
GET /api/restaurants?min_rating=4.0&cuisine=Italian&sort_by=rating
```

### GET `/api/restaurants/stats`

Get statistics about the restaurant data:

**Response**:
```json
{
  "total_restaurants": 100,
  "average_rating": 4.2,
  "total_reviews": 45000,
  "cuisines": [...],
  "rating_distribution": {...}
}
```

### GET `/api/restaurants/cuisines`

Get list of all unique cuisines.

### POST `/api/reload`

Reload restaurant data from the JSON file.

## Web Interface Features

### Search & Filter
- Real-time search across name, address, and cuisine
- Filter by cuisine type
- Filter by minimum rating
- Sort by rating, reviews, or name

### Restaurant Cards
- Beautiful card design with hover effects
- Rating badges
- Contact information
- Direct links to Google Maps and websites
- Cuisine tags

### Export
- Export filtered results to CSV
- Includes all restaurant data
- Filename includes current date

## Troubleshooting

### Scraper Issues

**Problem**: Chrome driver not found
- **Solution**: The script uses `webdriver-manager` which automatically downloads the correct ChromeDriver

**Problem**: No restaurants found
- **Solution**: Check your internet connection and ensure Google Maps is accessible

**Problem**: Getting blocked by Google
- **Solution**: Increase `request_delay` in `config.json` to add more delay between requests

### Server Issues

**Problem**: `restaurants_data.json` not found
- **Solution**: Run `python scraper.py` first to generate the data file

**Problem**: Port 8000 already in use
- **Solution**: Change the port in `server.py` or kill the process using port 8000

## Important Notes

⚠️ **Terms of Service**: Web scraping Google Maps may violate their Terms of Service. This tool is intended for educational and personal research purposes only.

⚠️ **Rate Limiting**: The scraper includes delays to avoid overwhelming Google's servers. Adjust `request_delay` in `config.json` if needed.

⚠️ **Production Use**: For production applications, consider using the official [Google Places API](https://developers.google.com/maps/documentation/places/web-service/overview).

## Technology Stack

- **Backend**: Python, Selenium, FastAPI, Uvicorn
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Data Storage**: JSON
- **Browser Automation**: Chrome WebDriver

## License

This project is for educational purposes only. Use responsibly and in accordance with Google's Terms of Service.

## Support

For issues or questions, please check:
1. The troubleshooting section above
2. API documentation at http://localhost:8000/docs
3. Console logs in the browser developer tools
