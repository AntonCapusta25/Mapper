// Static deployment - loads JSON files directly
const API_BASE = '';

// State
let allRestaurants = [];
let filteredRestaurants = [];
let stats = {};
let allFarms = [];
let filteredFarms = [];
let farmsStats = {};
let map;
let farmsMap;
let geoJsonLayer;
let farmsGeoJsonLayer;
let districtRecommendations = {};

// PC4 to Neighborhood Name Mapping
const pc4ToNeighborhood = {
    '1011': 'Burgwallen-Oude Zijde', '1012': 'Burgwallen-Oude Zijde', '1013': 'Grachtengordel-West',
    '1014': 'Haarlemmerbuurt', '1015': 'Grachtengordel-West', '1016': 'Grachtengordel-Zuid',
    '1017': 'Grachtengordel-Zuid', '1018': 'Weesperbuurt/Plantage', '1019': 'Oostelijke Eilanden',
    '1021': 'Indische Buurt', '1022': 'Indische Buurt', '1091': 'Weesperbuurt/Plantage',
    '1092': 'Oosterparkbuurt', '1093': 'Dapperbuurt', '1094': 'Oosterparkbuurt',
    '1095': 'Indische Buurt', '1096': 'Indische Buurt', '1097': 'Indische Buurt',
    '1098': 'IJburg', '1099': 'IJburg', '1051': 'Oud-West', '1052': 'Westerpark',
    '1053': 'De Baarsjes', '1054': 'Oud-West', '1055': 'Bos en Lommer', '1056': 'De Baarsjes',
    '1057': 'Bos en Lommer', '1058': 'Overtoomse Veld', '1059': 'Slotervaart', '1060': 'Slotermeer',
    '1061': 'Overtoomse Veld', '1062': 'Zuidas', '1063': 'Buitenveldert', '1064': 'Slotervaart',
    '1065': 'Osdorp', '1066': 'De Aker', '1067': 'Osdorp', '1068': 'Buitenveldert',
    '1069': 'Slotervaart', '1070': 'Zuid', '1071': 'Museumkwartier', '1072': 'Willemspark',
    '1073': 'Apollobuurt', '1074': 'Stadionbuurt', '1075': 'Scheldebuurt', '1076': 'Stadionbuurt',
    '1077': 'Prinses Irenebuurt', '1078': 'Rivierenbuurt', '1079': 'Buitenveldert',
    '1081': 'Buitenveldert', '1082': 'Buitenveldert', '1083': 'Buitenveldert',
    '1084': 'Buitenveldert', '1085': 'Buitenveldert', '1086': 'Buitenveldert',
    '1087': 'Buitenveldert', '1101': 'Zuidoost - Bijlmer', '1102': 'Zuidoost - Gaasperdam',
    '1103': 'Zuidoost - Venserpolder', '1104': 'Zuidoost - Gaasperdam', '1105': 'Zuidoost - Nellestein',
    '1106': 'Zuidoost - Holendrecht', '1107': 'Zuidoost - Reigersbos', '1108': 'Zuidoost - Gein',
    '1109': 'Zuidoost - Driemond', '1031': 'Noord - Buiksloterham', '1032': 'Noord - Tuindorp Oostzaan',
    '1033': 'Noord - Buiksloot', '1034': 'Noord - Buiksloot', '1035': 'Noord - Kadoelen',
    '1036': 'Noord - Nieuwendam', '1043': 'Nieuw-West - Geuzenveld',
    '1044': 'Nieuw-West - Slotermeer', '1045': 'Nieuw-West - Slotervaart', '1046': 'Nieuw-West - Slotermeer',
    '1047': 'Nieuw-West - Osdorp'
};

function getNeighborhoodName(pc4) {
    return pc4ToNeighborhood[pc4] || `Amsterdam ${pc4}`;
}

// DOM Elements
const restaurantsGrid = document.getElementById('restaurantsGrid');
const loadingState = document.getElementById('loadingState');
const emptyState = document.getElementById('emptyState');
const searchInput = document.getElementById('searchInput');
const cuisineFilter = document.getElementById('cuisineFilter');
const minRating = document.getElementById('minRating');
const sortBy = document.getElementById('sortBy');
const applyFiltersBtn = document.getElementById('applyFilters');
const resetFiltersBtn = document.getElementById('resetFilters');
const exportDataBtn = document.getElementById('exportData');
const resultsCount = document.getElementById('resultsCount');
const totalRestaurants = document.getElementById('totalRestaurants');
const avgRating = document.getElementById('avgRating');
const totalReviews = document.getElementById('totalReviews');

// Farms DOM Elements
const farmsGrid = document.getElementById('farmsGrid');
const farmsLoadingState = document.getElementById('farmsLoadingState');
const farmsEmptyState = document.getElementById('farmsEmptyState');
const farmsSearchInput = document.getElementById('farmsSearchInput');
const farmTypeFilter = document.getElementById('farmTypeFilter');
const farmsMinRating = document.getElementById('farmsMinRating');
const farmsSortBy = document.getElementById('farmsSortBy');
const farmsResultsCount = document.getElementById('farmsResultsCount');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadRestaurants();
    loadFarmsStats();
    loadFarms();
    initMap();
    setupEventListeners();
    setupTabSwitching();
});

// Tab Switching
function setupTabSwitching() {
    const tabs = document.querySelectorAll('.tab-btn');
    const views = document.querySelectorAll('.view-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetView = tab.dataset.tab;

            // Update tabs
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Update views
            views.forEach(v => v.style.display = 'none');
            const view = document.getElementById(targetView);
            if (view) view.style.display = 'block';

            // Update stats bar
            if (targetView === 'farms-view') {
                updateStatsDisplay('farms');
                if (farmsMap) farmsMap.invalidateSize();
                if (!farmsMap) initFarmsMap();
            } else if (targetView === 'map-view') {
                updateStatsDisplay('restaurants');
                if (map) map.invalidateSize();
            }
        });
    });
}

function updateStatsDisplay(type = 'restaurants') {
    if (type === 'farms') {
        totalRestaurants.textContent = farmsStats.total_farms || 0;
        avgRating.textContent = farmsStats.average_rating ? `${farmsStats.average_rating}⭐` : 'N/A';
        totalReviews.textContent = formatNumber(farmsStats.total_reviews || 0);
        document.querySelector('#totalRestaurants').parentElement.querySelector('.stat-label').textContent = 'Farms';
    } else {
        totalRestaurants.textContent = stats.total_restaurants || 0;
        avgRating.textContent = stats.average_rating ? `${stats.average_rating}⭐` : 'N/A';
        totalReviews.textContent = formatNumber(stats.total_reviews || 0);
        document.querySelector('#totalRestaurants').parentElement.querySelector('.stat-label').textContent = 'Restaurants';
    }
}

// Initialize Map
async function initMap() {
    map = L.map('map').setView([52.3676, 4.9041], 12);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    await loadRecommendations();
    await loadMapData();
}

// Initialize Farms Map
async function initFarmsMap() {
    if (farmsMap) return;

    farmsMap = L.map('farmsMap').setView([52.3676, 4.9041], 12);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(farmsMap);

    await loadFarmsMapData();
}

async function loadRecommendations() {
    try {
        const response = await fetch('./district_recommendations.json');
        if (response.ok) {
            districtRecommendations = await response.json();
        }
    } catch (error) { console.error('Error loading recommendations:', error); }
}

async function loadMapData() {
    try {
        const response = await fetch('./amsterdam_pc4.geojson');
        if (!response.ok) return;
        const geojson = await response.json();
        const statsByPC4 = computePC4Stats(allRestaurants);

        const enrichedFeatures = geojson.features.map(feature => {
            const pc4 = feature.properties.pc4;
            const stats = statsByPC4[pc4] || { count: 0, avg_rating: 0, top_cuisines: [] };
            return { ...feature, properties: { ...feature.properties, ...stats } };
        });

        if (geoJsonLayer) map.removeLayer(geoJsonLayer);
        geoJsonLayer = L.geoJSON({ type: "FeatureCollection", features: enrichedFeatures }, {
            style: styleFeature,
            onEachFeature: onEachFeature
        }).addTo(map);
    } catch (error) { console.error('Error loading map data:', error); }
}

async function loadFarmsMapData() {
    try {
        const response = await fetch('./amsterdam_pc4.geojson');
        if (!response.ok) return;
        const geojson = await response.json();
        const statsByPC4 = computePC4Stats(allFarms);

        const enrichedFeatures = geojson.features.map(feature => {
            const pc4 = feature.properties.pc4;
            const stats = statsByPC4[pc4] || { count: 0, avg_rating: 0, top_cuisines: [] };
            return { ...feature, properties: { ...feature.properties, ...stats } };
        });

        if (farmsGeoJsonLayer) farmsMap.removeLayer(farmsGeoJsonLayer);
        farmsGeoJsonLayer = L.geoJSON({ type: "FeatureCollection", features: enrichedFeatures }, {
            style: styleFarmsFeature,
            onEachFeature: onEachFarmsFeature
        }).addTo(farmsMap);
    } catch (error) { console.error('Error loading farms map data:', error); }
}

function computePC4Stats(items) {
    const stats = {};
    items.forEach(r => {
        const address = r.address || '';
        const match = address.match(/\b(\d{4})\s*[A-Z]{2}\b/);
        if (match) {
            const pc4 = match[1];
            if (!stats[pc4]) stats[pc4] = { count: 0, total_rating: 0, cuisines: {} };
            stats[pc4].count++;
            if (r.rating) stats[pc4].total_rating += r.rating;
            if (r.cuisine) stats[pc4].cuisines[r.cuisine] = (stats[pc4].cuisines[r.cuisine] || 0) + 1;
        }
    });

    Object.keys(stats).forEach(pc4 => {
        const s = stats[pc4];
        s.avg_rating = s.count > 0 ? (s.total_rating / s.count).toFixed(2) : 0;
        const sortedCuisines = Object.entries(s.cuisines).sort((a, b) => b[1] - a[1]).slice(0, 3).map(c => c[0]);
        s.top_cuisines = sortedCuisines;
        delete s.cuisines; delete s.total_rating;
    });
    return stats;
}

function styleFeature(feature) {
    return {
        fillColor: getColor(feature.properties.count),
        weight: 2, opacity: 1, color: 'white', dashArray: '3', fillOpacity: 0.7
    };
}

function styleFarmsFeature(feature) {
    return {
        fillColor: getFarmsColor(feature.properties.count),
        weight: 2, opacity: 1, color: 'white', dashArray: '3', fillOpacity: 0.7
    };
}

function getColor(d) {
    return d > 50 ? '#800026' : d > 20 ? '#BD0026' : d > 10 ? '#E31A1C' : d > 5 ? '#FC4E2A' : d > 2 ? '#FD8D3C' : d > 0 ? '#FEB24C' : '#FFEDA0';
}

function getFarmsColor(d) {
    return d > 50 ? '#006d2c' : d > 20 ? '#238b45' : d > 10 ? '#41ab5d' : d > 5 ? '#74c476' : d > 2 ? '#a1d99b' : d > 0 ? '#c7e9c0' : '#edf8e9';
}

function onEachFeature(feature, layer) {
    layer.on({ mouseover: highlightFeature, mouseout: resetHighlight, click: zoomToFeature });
}

function onEachFarmsFeature(feature, layer) {
    layer.on({ mouseover: highlightFarmsFeature, mouseout: resetFarmsHighlight, click: zoomToFarmsFeature });
}

function highlightFeature(e) {
    const layer = e.target;
    layer.setStyle({ weight: 5, color: '#ffffff', dashArray: '', fillOpacity: 0.7 });
    layer.bringToFront();

    const props = layer.feature.properties;
    const neighborhoodName = getNeighborhoodName(props.pc4);

    let tooltipContent = `<div style="min-width: 280px;"><strong style="font-size: 1.1em;">${neighborhoodName}</strong><br><small style="color: #a0aec0;">PC4: ${props.pc4 || 'Unknown'}</small><hr style="margin: 8px 0; border-color: rgba(255,255,255,0.1);">`;
    tooltipContent += `<small>Restaurants: ${props.count}<br>Avg Rating: ${props.avg_rating || 'N/A'}⭐<br>Top: ${props.top_cuisines ? props.top_cuisines.join(', ') : 'None'}</small></div>`;

    layer.bindTooltip(tooltipContent, { maxWidth: 350, className: 'custom-tooltip' }).openTooltip();
}

function highlightFarmsFeature(e) {
    const layer = e.target;
    layer.setStyle({ weight: 5, color: '#ffffff', dashArray: '', fillOpacity: 0.7 });
    layer.bringToFront();

    const props = layer.feature.properties;
    const neighborhoodName = getNeighborhoodName(props.pc4);

    let tooltipContent = `<div style="min-width: 280px;"><strong style="font-size: 1.1em;">${neighborhoodName}</strong><br><small style="color: #a0aec0;">PC4: ${props.pc4 || 'Unknown'}</small><hr style="margin: 8px 0; border-color: rgba(255,255,255,0.1);">`;
    tooltipContent += `<small>Farms: ${props.count}<br>Avg Rating: ${props.avg_rating || 'N/A'}⭐<br>Top: ${props.top_cuisines ? props.top_cuisines.join(', ') : 'None'}</small></div>`;

    layer.bindTooltip(tooltipContent, { maxWidth: 350, className: 'custom-tooltip' }).openTooltip();
}

function resetHighlight(e) { geoJsonLayer.resetStyle(e.target); }
function resetFarmsHighlight(e) { farmsGeoJsonLayer.resetStyle(e.target); }
function zoomToFeature(e) { map.fitBounds(e.target.getBounds()); }
function zoomToFarmsFeature(e) { farmsMap.fitBounds(e.target.getBounds()); }

function setupEventListeners() {
    applyFiltersBtn.addEventListener('click', applyFilters);
    resetFiltersBtn.addEventListener('click', resetFilters);
    exportDataBtn.addEventListener('click', exportToCSV);
    document.getElementById('reloadData').addEventListener('click', reloadData);
    searchInput.addEventListener('input', debounce(applyFilters, 300));

    // Farms listeners
    document.getElementById('applyFarmsFilters').addEventListener('click', applyFarmsFilters);
    document.getElementById('resetFarmsFilters').addEventListener('click', resetFarmsFilters);
    document.getElementById('exportFarmsData').addEventListener('click', exportFarmsToCSV);
    document.getElementById('reloadFarmsData').addEventListener('click', reloadFarmsData);
}

async function reloadData() {
    await loadStats();
    await loadRestaurants();
}

async function reloadFarmsData() {
    await loadFarmsStats();
    await loadFarms();
}

async function loadStats() {
    try {
        const response = await fetch('./restaurants_data.json');
        const data = await response.json();
        const restaurants = Array.isArray(data) ? data : (data.restaurants || []);

        const ratings = restaurants.filter(r => r.rating).map(r => r.rating);
        const reviews = restaurants.filter(r => r.reviews).map(r => r.reviews);

        stats = {
            total_restaurants: restaurants.length,
            average_rating: ratings.length > 0 ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(2) : 0,
            total_reviews: reviews.reduce((a, b) => a + b, 0)
        };
        updateStatsDisplay('restaurants');
    } catch (error) { console.error('Error loading stats:', error); }
}

async function loadFarmsStats() {
    try {
        const response = await fetch('./farms_data.json');
        const data = await response.json();
        const farms = Array.isArray(data) ? data : (data.farms || []);

        const ratings = farms.filter(f => f.rating).map(f => f.rating);
        const reviews = farms.filter(f => f.reviews).map(f => f.reviews);

        farmsStats = {
            total_farms: farms.length,
            average_rating: ratings.length > 0 ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(2) : 0,
            total_reviews: reviews.reduce((a, b) => a + b, 0)
        };
    } catch (error) { console.error('Error loading farms stats:', error); }
}

async function loadRestaurants() {
    showLoading();
    try {
        const response = await fetch('./restaurants_data.json');
        const data = await response.json();
        allRestaurants = Array.isArray(data) ? data : (data.restaurants || []);
        filteredRestaurants = allRestaurants;
        await loadCuisines();
        renderRestaurants();
        if (map) loadMapData();
        hideLoading();
    } catch (error) { console.error('Error loading restaurants:', error); hideLoading(); showEmpty(); }
}

async function loadFarms() {
    showFarmsLoading();
    try {
        const response = await fetch('./farms_data.json');
        const data = await response.json();
        allFarms = Array.isArray(data) ? data : (data.farms || []);
        filteredFarms = allFarms;
        await loadFarmTypes();
        renderFarms();
        hideFarmsLoading();
    } catch (error) { console.error('Error loading farms:', error); hideFarmsLoading(); showFarmsEmpty(); }
}

async function loadCuisines() {
    try {
        const cuisines = new Set();
        allRestaurants.forEach(r => { if (r.cuisine) cuisines.add(r.cuisine); });
        const sortedCuisines = Array.from(cuisines).sort();
        cuisineFilter.innerHTML = '<option value="">All Cuisines</option>';
        sortedCuisines.forEach(cuisine => {
            const option = document.createElement('option');
            option.value = cuisine;
            option.textContent = cuisine;
            cuisineFilter.appendChild(option);
        });
    } catch (error) { console.error('Error loading cuisines:', error); }
}

async function loadFarmTypes() {
    try {
        const types = new Set();
        allFarms.forEach(f => { if (f.cuisine) types.add(f.cuisine); });
        const sortedTypes = Array.from(types).sort();
        farmTypeFilter.innerHTML = '<option value="">All Types</option>';
        sortedTypes.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            farmTypeFilter.appendChild(option);
        });
    } catch (error) { console.error('Error loading farm types:', error); }
}

async function applyFilters() {
    const search = searchInput.value.trim().toLowerCase();
    const cuisine = cuisineFilter.value.toLowerCase();
    const rating = parseFloat(minRating.value);
    const sort = sortBy.value;

    showLoading();

    try {
        let filtered = [...allRestaurants];
        if (search) {
            filtered = filtered.filter(r =>
                (r.name || '').toLowerCase().includes(search) ||
                (r.address || '').toLowerCase().includes(search) ||
                (r.cuisine || '').toLowerCase().includes(search)
            );
        }
        if (rating) filtered = filtered.filter(r => r.rating && r.rating >= rating);
        if (cuisine) filtered = filtered.filter(r => r.cuisine && r.cuisine.toLowerCase().includes(cuisine));

        if (sort === 'rating') filtered.sort((a, b) => (b.rating || 0) - (a.rating || 0));
        else if (sort === 'reviews') filtered.sort((a, b) => (b.reviews || 0) - (a.reviews || 0));
        else if (sort === 'name') filtered.sort((a, b) => (a.name || '').localeCompare(b.name || ''));

        filteredRestaurants = filtered;
        renderRestaurants();
        hideLoading();
    } catch (error) { console.error('Error applying filters:', error); hideLoading(); }
}

async function applyFarmsFilters() {
    const search = farmsSearchInput.value.trim().toLowerCase();
    const type = farmTypeFilter.value;
    const rating = parseFloat(farmsMinRating.value);
    const sort = farmsSortBy.value;

    showFarmsLoading();

    try {
        let filtered = [...allFarms];
        if (search) {
            filtered = filtered.filter(f =>
                (f.name || '').toLowerCase().includes(search) ||
                (f.address || '').toLowerCase().includes(search)
            );
        }
        if (type) filtered = filtered.filter(f => f.cuisine === type);
        if (rating) filtered = filtered.filter(f => f.rating && f.rating >= rating);

        if (sort === 'rating') filtered.sort((a, b) => (b.rating || 0) - (a.rating || 0));
        else if (sort === 'reviews') filtered.sort((a, b) => (b.reviews || 0) - (a.reviews || 0));
        else if (sort === 'name') filtered.sort((a, b) => (a.name || '').localeCompare(b.name || ''));

        filteredFarms = filtered;
        renderFarms();
        hideFarmsLoading();
    } catch (error) { console.error('Error applying farms filters:', error); hideFarmsLoading(); }
}

function resetFilters() {
    searchInput.value = ''; cuisineFilter.value = ''; minRating.value = ''; sortBy.value = 'rating';
    filteredRestaurants = allRestaurants;
    renderRestaurants();
}

function resetFarmsFilters() {
    farmsSearchInput.value = ''; farmTypeFilter.value = ''; farmsMinRating.value = ''; farmsSortBy.value = 'rating';
    filteredFarms = allFarms;
    renderFarms();
}

function renderRestaurants() {
    resultsCount.textContent = filteredRestaurants.length;
    if (filteredRestaurants.length === 0) { showEmpty(); return; }
    restaurantsGrid.innerHTML = '';
    emptyState.style.display = 'none';
    filteredRestaurants.forEach(restaurant => {
        const card = createRestaurantCard(restaurant);
        restaurantsGrid.appendChild(card);
    });
}

function renderFarms() {
    farmsResultsCount.textContent = filteredFarms.length;
    if (filteredFarms.length === 0) { showFarmsEmpty(); return; }
    farmsGrid.innerHTML = '';
    farmsEmptyState.style.display = 'none';
    filteredFarms.forEach(farm => {
        const card = createFarmCard(farm);
        farmsGrid.appendChild(card);
    });
}

function createRestaurantCard(restaurant) {
    const card = document.createElement('div');
    card.className = 'restaurant-card';
    const rating = restaurant.rating ? restaurant.rating.toFixed(1) : 'N/A';
    const reviews = restaurant.reviews ? formatNumber(restaurant.reviews) : '0';
    const mapsUrl = restaurant.latitude && restaurant.longitude
        ? `https://www.google.com/maps/search/?api=1&query=${restaurant.latitude},${restaurant.longitude}`
        : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(restaurant.name + ' Amsterdam')}`;

    card.innerHTML = `
        <div class="card-header"><div><h3 class="restaurant-name">${escapeHtml(restaurant.name)}</h3></div>${restaurant.rating ? `<div class="rating-badge">⭐ ${rating}</div>` : ''}</div>
        <div class="card-info">
            <div class="info-row"><span class="info-icon">📍</span><span>${escapeHtml(restaurant.address || 'Address not available')}</span></div>
            <div class="info-row"><span class="info-icon">📞</span><span>${escapeHtml(restaurant.phone || 'Phone not available')}</span></div>
            <div class="info-row"><span class="info-icon">💬</span><span>${reviews} reviews</span></div>
            <div class="info-row"><span class="info-icon">💰</span><span>${escapeHtml(restaurant.price_level || 'Price not available')}</span></div>
            <div class="info-row"><span class="cuisine-tag">${escapeHtml(restaurant.cuisine || 'Cuisine not specified')}</span></div>
        </div>
        <div class="card-footer">
            <a href="${mapsUrl}" target="_blank" class="card-btn">🗺️ View on Maps</a>
            ${restaurant.website ? `<a href="${escapeHtml(restaurant.website)}" target="_blank" class="card-btn">🌐 Website</a>` : ''}
        </div>`;
    return card;
}

function createFarmCard(farm) {
    const card = document.createElement('div');
    card.className = 'restaurant-card';
    const rating = farm.rating ? farm.rating.toFixed(1) : 'N/A';
    const reviews = farm.reviews ? formatNumber(farm.reviews) : '0';
    const mapsUrl = farm.latitude && farm.longitude
        ? `https://www.google.com/maps/search/?api=1&query=${farm.latitude},${farm.longitude}`
        : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(farm.name)}`;

    card.innerHTML = `
        <div class="card-header"><div><h3 class="restaurant-name">${escapeHtml(farm.name)}</h3></div>${farm.rating ? `<div class="rating-badge">⭐ ${rating}</div>` : ''}</div>
        <div class="card-info">
            <div class="info-row"><span class="info-icon">📍</span><span>${escapeHtml(farm.address || 'Address not available')}</span></div>
            <div class="info-row"><span class="info-icon">📞</span><span>${escapeHtml(farm.phone || 'Phone not available')}</span></div>
            <div class="info-row"><span class="info-icon">💬</span><span>${reviews} reviews</span></div>
            <div class="info-row"><span class="cuisine-tag">🌾 ${escapeHtml(farm.cuisine || 'Type not specified')}</span></div>
        </div>
        <div class="card-footer">
            <a href="${mapsUrl}" target="_blank" class="card-btn">🗺️ View on Maps</a>
            ${farm.website ? `<a href="${escapeHtml(farm.website)}" target="_blank" class="card-btn">🌐 Website</a>` : ''}
        </div>`;
    return card;
}

function exportToCSV() {
    if (filteredRestaurants.length === 0) { alert('No restaurants to export!'); return; }
    const headers = ['Name', 'Rating', 'Reviews', 'Address', 'Phone', 'Cuisine', 'Price Level', 'Website', 'Latitude', 'Longitude'];
    const csvContent = [headers.join(','), ...filteredRestaurants.map(r => [
        `"${(r.name || '').replace(/"/g, '""')}"`, r.rating || '', r.reviews || '', `"${(r.address || '').replace(/"/g, '""')}"`,
        `"${(r.phone || '').replace(/"/g, '""')}"`, `"${(r.cuisine || '').replace(/"/g, '""')}"`, `"${(r.price_level || '').replace(/"/g, '""')}"`,
        `"${(r.website || '').replace(/"/g, '""')}"`, r.latitude || '', r.longitude || ''
    ].join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `amsterdam-restaurants-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
}

function exportFarmsToCSV() {
    if (filteredFarms.length === 0) { alert('No farms to export!'); return; }
    const headers = ['Name', 'Rating', 'Reviews', 'Address', 'Phone', 'Type', 'Website', 'Latitude', 'Longitude'];
    const csvContent = [headers.join(','), ...filteredFarms.map(f => [
        `"${(f.name || '').replace(/"/g, '""')}"`, f.rating || '', f.reviews || '', `"${(f.address || '').replace(/"/g, '""')}"`,
        `"${(f.phone || '').replace(/"/g, '""')}"`, `"${(f.cuisine || '').replace(/"/g, '""')}"`,
        `"${(f.website || '').replace(/"/g, '""')}"`, f.latitude || '', f.longitude || ''
    ].join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `amsterdam-farms-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
}

function showLoading() { loadingState.style.display = 'block'; restaurantsGrid.style.display = 'none'; emptyState.style.display = 'none'; }
function hideLoading() { loadingState.style.display = 'none'; restaurantsGrid.style.display = 'grid'; }
function showEmpty() { emptyState.style.display = 'block'; restaurantsGrid.style.display = 'none'; }
function showFarmsLoading() { farmsLoadingState.style.display = 'block'; farmsGrid.style.display = 'none'; farmsEmptyState.style.display = 'none'; }
function hideFarmsLoading() { farmsLoadingState.style.display = 'none'; farmsGrid.style.display = 'grid'; }
function showFarmsEmpty() { farmsEmptyState.style.display = 'block'; farmsGrid.style.display = 'none'; }
function formatNumber(num) { if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'; if (num >= 1000) return (num / 1000).toFixed(1) + 'K'; return num.toString(); }
function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }
function debounce(func, wait) { let timeout; return function (...args) { clearTimeout(timeout); timeout = setTimeout(() => func(...args), wait); }; }
