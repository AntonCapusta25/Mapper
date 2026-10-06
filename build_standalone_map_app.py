import json
import os
import re

OUTPUT_FILE = "enschede_map.html"
WEBAPP_FILE = "webapp/enschede.html"

# Load Enschede dataset
with open("data/enschede_restaurants_data.json", "r", encoding="utf-8") as f:
    enschede_data = json.load(f)

# Ensure lat/lng valid
clean_records = []
for r in enschede_data:
    lat, lng = r.get("latitude"), r.get("longitude")
    if not lat or not lng:
        url = r.get("url", "")
        m = re.search(r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
        if m:
            lat, lng = m.group(1), m.group(2)
        else:
            m = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', url)
            if m:
                lat, lng = m.group(1), m.group(2)
    
    if lat and lng:
        r["latitude"] = float(lat)
        r["longitude"] = float(lng)
        clean_records.append(r)

json_data_str = json.dumps(clean_records, ensure_ascii=False)

template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enschede Restaurants & Food Spots Map</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <!-- Leaflet CSS & JS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

    <style>
        :root {
            --primary: #ff3b30;
            --primary-hover: #e03126;
            --primary-wash: rgba(255, 59, 48, 0.08);
            --bg-main: #f5f5f7;
            --card-bg: #ffffff;
            --text-main: #1d1d1f;
            --text-secondary: #6e6e73;
            --border-color: #e5e5ea;
            --radius-md: 12px;
            --radius-sm: 8px;
            --font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: var(--font-family);
            background-color: var(--bg-main);
            color: var(--text-main);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }

        /* HEADER */
        header {
            background: #ffffff;
            border-bottom: 1px solid var(--border-color);
            padding: 1.25rem 2rem;
            position: sticky;
            top: 0;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        }

        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }

        .logo h1 {
            font-size: 1.4rem;
            font-weight: 800;
            color: var(--text-main);
            letter-spacing: -0.02em;
        }

        .logo p {
            font-size: 0.82rem;
            color: var(--text-secondary);
        }

        .stats-bar {
            display: flex;
            gap: 1.5rem;
        }

        .stat-item {
            text-align: center;
        }

        .stat-val {
            font-size: 1.25rem;
            font-weight: 800;
            color: var(--primary);
        }

        .stat-lbl {
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            color: var(--text-secondary);
        }

        /* LAYOUT */
        .main-container {
            max-width: 1400px;
            margin: 1.5rem auto;
            padding: 0 1.5rem;
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
        }

        /* CONTROLS CARD */
        .controls-card {
            background: #ffffff;
            border-radius: var(--radius-md);
            padding: 1.25rem 1.5rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        }

        .controls-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            align-items: end;
        }

        .control-group {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .control-group label {
            font-size: 0.78rem;
            font-weight: 700;
            color: var(--text-main);
        }

        .control-group input, .control-group select {
            padding: 0.6rem 0.8rem;
            border-radius: var(--radius-sm);
            border: 1px solid var(--border-color);
            font-size: 0.88rem;
            font-family: inherit;
            background: #ffffff;
            outline: none;
            transition: border-color 0.2s;
        }

        .control-group input:focus, .control-group select:focus {
            border-color: var(--primary);
        }

        /* MAP & LIST GRID */
        .view-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 900px) {
            .view-grid {
                grid-template-columns: 1fr;
            }
        }

        .map-card {
            background: #ffffff;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
            overflow: hidden;
            height: 650px;
            position: sticky;
            top: 90px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
        }

        #map {
            width: 100%;
            height: 100%;
        }

        .list-card {
            background: #ffffff;
            border-radius: var(--radius-md);
            border: 1px solid var(--border-color);
            padding: 1.25rem;
            height: 650px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .venue-card {
            background: #f9f9fb;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 1rem;
            transition: transform 0.15s, border-color 0.15s;
        }

        .venue-card:hover {
            border-color: var(--primary);
            transform: translateY(-2px);
        }

        .venue-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.5rem;
        }

        .venue-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text-main);
        }

        .badge-cuisine {
            display: inline-block;
            background: var(--primary-wash);
            color: var(--primary);
            font-size: 0.72rem;
            font-weight: 700;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            text-transform: capitalize;
        }

        .venue-meta {
            font-size: 0.82rem;
            color: var(--text-secondary);
            margin-top: 0.4rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.8rem;
        }

        .rating-badge {
            color: #d97706;
            font-weight: 700;
        }

        .venue-address {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 0.4rem;
        }

        .venue-actions {
            margin-top: 0.75rem;
            display: flex;
            gap: 0.5rem;
        }

        .btn-maps {
            display: inline-flex;
            align-items: center;
            background: var(--primary);
            color: #ffffff;
            text-decoration: none;
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.4rem 0.8rem;
            border-radius: var(--radius-sm);
            transition: background-color 0.2s;
        }

        .btn-maps:hover {
            background: var(--primary-hover);
        }

        .btn-website {
            display: inline-flex;
            align-items: center;
            background: #ffffff;
            border: 1px solid var(--border-color);
            color: var(--text-main);
            text-decoration: none;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.4rem 0.8rem;
            border-radius: var(--radius-sm);
        }

        .btn-website:hover {
            background: #f5f5f7;
        }
    </style>
</head>
<body>

    <!-- HEADER -->
    <header>
        <div class="header-content">
            <div class="logo">
                <h1>Enschede Restaurants & Food Spots</h1>
                <p>Interactive spatial map & cuisine analytics</p>
            </div>
            <div style="display: flex; gap: 0.5rem; align-items: center; background: #f5f5f7; padding: 4px; border-radius: 999px; border: 1px solid var(--border-color);">
                <a href="index.html" style="padding: 0.4rem 0.9rem; border-radius: 999px; font-weight: 600; font-size: 0.82rem; text-decoration: none; color: var(--text-main);">🏛️ Amsterdam</a>
                <a href="enschede.html" style="padding: 0.4rem 0.9rem; border-radius: 999px; font-weight: 700; font-size: 0.82rem; text-decoration: none; background: var(--primary); color: #ffffff; box-shadow: 0 2px 6px rgba(255,59,48,0.3);">📍 Enschede</a>
            </div>
            <div class="stats-bar">
                <div class="stat-item">
                    <div class="stat-val" id="stat-count">0</div>
                    <div class="stat-lbl">Mapped Venues</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val" id="stat-rating">0.0</div>
                    <div class="stat-lbl">Avg Rating</div>
                </div>
                <div class="stat-item">
                    <div class="stat-val" id="stat-reviews">0</div>
                    <div class="stat-lbl">Total Reviews</div>
                </div>
            </div>
        </div>
    </header>

    <!-- MAIN CONTAINER -->
    <div class="main-container">
        <!-- FILTERS -->
        <div class="controls-card">
            <div class="controls-grid">
                <div class="control-group">
                    <label for="searchInput">Search Venue or Address</label>
                    <input type="text" id="searchInput" placeholder="Type restaurant name or street...">
                </div>
                <div class="control-group">
                    <label for="cuisineSelect">Cuisine / Category</label>
                    <select id="cuisineSelect">
                        <option value="">All Cuisines</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="ratingSelect">Min Rating</label>
                    <select id="ratingSelect">
                        <option value="0">Any Rating</option>
                        <option value="4.5">4.5+ Stars</option>
                        <option value="4.0">4.0+ Stars</option>
                        <option value="3.5">3.5+ Stars</option>
                    </select>
                </div>
                <div class="control-group">
                    <label for="sortSelect">Sort By</label>
                    <select id="sortSelect">
                        <option value="reviews">Most Reviews</option>
                        <option value="rating">Highest Rating</option>
                        <option value="name">Name (A-Z)</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- MAP & LIST GRID -->
        <div class="view-grid">
            <div class="map-card">
                <div id="map"></div>
            </div>
            <div class="list-card" id="venue-list">
                <!-- Venue cards dynamically rendered -->
            </div>
        </div>
    </div>

    <script>
        const RAW_DATA = __JSON_DATA__;

        let map = null;
        let markersGroup = null;
        let currentFilteredData = [...RAW_DATA];

        document.addEventListener('DOMContentLoaded', () => {
            initCuisineOptions();
            initMap();
            applyFilters();

            document.getElementById('searchInput').addEventListener('input', applyFilters);
            document.getElementById('cuisineSelect').addEventListener('change', applyFilters);
            document.getElementById('ratingSelect').addEventListener('change', applyFilters);
            document.getElementById('sortSelect').addEventListener('change', applyFilters);
        });

        function initCuisineOptions() {
            const cuisineSelect = document.getElementById('cuisineSelect');
            const cuisines = new Set();

            RAW_DATA.forEach(r => {
                if (r.cuisine) cuisines.add(r.cuisine.trim());
            });

            const sortedCuisines = Array.from(cuisines).sort();
            sortedCuisines.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c;
                opt.textContent = c;
                cuisineSelect.appendChild(opt);
            });
        }

        function initMap() {
            map = L.map('map').setView([52.2215, 6.8937], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '© OpenStreetMap'
            }).addTo(map);

            markersGroup = L.layerGroup().addTo(map);
        }

        function applyFilters() {
            const search = document.getElementById('searchInput').value.toLowerCase().trim();
            const cuisine = document.getElementById('cuisineSelect').value;
            const minRating = parseFloat(document.getElementById('ratingSelect').value) || 0;
            const sortBy = document.getElementById('sortSelect').value;

            currentFilteredData = RAW_DATA.filter(r => {
                const matchSearch = !search || (r.name && r.name.toLowerCase().includes(search)) || (r.address && r.address.toLowerCase().includes(search));
                const matchCuisine = !cuisine || r.cuisine === cuisine;
                const rRating = parseFloat(r.rating) || 0;
                const matchRating = rRating >= minRating;
                return matchSearch && matchCuisine && matchRating;
            });

            // Sort
            if (sortBy === 'rating') {
                currentFilteredData.sort((a, b) => (parseFloat(b.rating) || 0) - (parseFloat(a.rating) || 0));
            } else if (sortBy === 'reviews') {
                currentFilteredData.sort((a, b) => (parseInt(b.reviews) || 0) - (parseInt(a.reviews) || 0));
            } else if (sortBy === 'name') {
                currentFilteredData.sort((a, b) => a.name.localeCompare(b.name));
            }

            updateStats();
            updateMapPins();
            renderListings();
        }

        function updateStats() {
            document.getElementById('stat-count').textContent = currentFilteredData.length;

            let totalRev = 0;
            let ratingSum = 0;
            let ratingCount = 0;

            currentFilteredData.forEach(r => {
                totalRev += parseInt(r.reviews) || 0;
                const rVal = parseFloat(r.rating);
                if (rVal > 0) {
                    ratingSum += rVal;
                    ratingCount++;
                }
            });

            const avgR = ratingCount > 0 ? (ratingSum / ratingCount).toFixed(2) : '0.0';
            document.getElementById('stat-rating').textContent = avgR;
            document.getElementById('stat-reviews').textContent = totalRev.toLocaleString();
        }

        function updateMapPins() {
            markersGroup.clearLayers();
            const bounds = [];

            currentFilteredData.forEach(r => {
                if (r.latitude && r.longitude) {
                    bounds.push([r.latitude, r.longitude]);

                    const popupHtml = `
                        <div style="font-family: var(--font-family); font-size: 13px;">
                            <strong style="font-size: 14px; color: var(--text-main);">${r.name}</strong><br>
                            <span style="color: var(--primary); font-weight: 600;">${r.cuisine || 'Restaurant'}</span><br>
                            ⭐ <strong>${r.rating || 'N/A'}</strong> (${r.reviews || 0} reviews)<br>
                            <span style="color: #6e6e73; font-size: 11px;">${r.address || ''}</span><br>
                            <div style="margin-top: 6px;">
                                ${r.url ? `<a href="${r.url}" target="_blank" style="color: #ff3b30; font-weight: 700; font-size: 11px;">Open Google Maps</a>` : ''}
                            </div>
                        </div>
                    `;

                    L.marker([r.latitude, r.longitude]).bindPopup(popupHtml).addTo(markersGroup);
                }
            });

            if (bounds.length > 0) {
                map.fitBounds(bounds, { padding: [30, 30] });
            }
        }

        function renderListings() {
            const container = document.getElementById('venue-list');
            if (currentFilteredData.length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 40px; color: #888;">No restaurants match your filter criteria.</div>';
                return;
            }

            container.innerHTML = currentFilteredData.slice(0, 150).map(r => `
                <div class="venue-card">
                    <div class="venue-header">
                        <div class="venue-title">${r.name}</div>
                        <span class="badge-cuisine">${r.cuisine || 'Food Spot'}</span>
                    </div>
                    <div class="venue-meta">
                        <span class="rating-badge">★ ${r.rating || 'N/A'}</span>
                        <span>(${r.reviews || 0} reviews)</span>
                        ${r.phone ? `<span>📞 ${r.phone}</span>` : ''}
                    </div>
                    <div class="venue-address">${r.address || ''}</div>
                    <div class="venue-actions">
                        ${r.url ? `<a href="${r.url}" target="_blank" class="btn-maps">Google Maps</a>` : ''}
                        ${r.website ? `<a href="${r.website}" target="_blank" class="btn-website">Website</a>` : ''}
                    </div>
                </div>
            `).join('');
        }
    </script>
</body>
</html>
"""

html_content = template.replace("__JSON_DATA__", json_data_str)

output_files = [
    "enschede_map.html",
    "enschede.html",
    "public/enschede.html",
    "public/enschede_map.html",
    "deploy/enschede.html",
    "deploy/enschede_map.html",
    "webapp/enschede.html",
    "webapp/enschede_map.html"
]

for filepath in output_files:
    folder = os.path.dirname(filepath)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated: {filepath} ({round(os.path.getsize(filepath)/1024, 1)} KB)")

