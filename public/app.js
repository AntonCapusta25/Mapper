
// Static App.js for Deployment
const API_BASE = '';

// State
let allRestaurants = [];
let filteredRestaurants = [];
let stats = {};
let map;
let geoJsonLayer;
let districtRecommendations = {};
let chefsData = [];
let chefLayerGroup;

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
    '1036': 'Noord - Nieuwendam', '1021': 'Noord - Overhoeks', '1043': 'Nieuw-West - Geuzenveld',
    '1044': 'Nieuw-West - Slotermeer', '1045': 'Nieuw-West - Slotervaart', '1046': 'Nieuw-West - Slotermeer',
    '1047': 'Nieuw-West - Osdorp', '1061': 'Nieuw-West - Overtoomse Veld', '1062': 'Nieuw-West - Zuidas',
    '1064': 'Nieuw-West - Slotervaart', '1065': 'Nieuw-West - Osdorp', '1066': 'Nieuw-West - De Aker',
    '1067': 'Nieuw-West - Osdorp', '1068': 'Nieuw-West - Buitenveldert', '1069': 'Nieuw-West - Slotervaart'
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

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    loadRestaurants();
    initMap();
    setupEventListeners();
});

// Initialize Map
async function initMap() {
    map = L.map('map').setView([52.3676, 4.9041], 12);
    // Switch to Carto Positron (light_all) for a cleaner, brighter base map
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    chefLayerGroup = L.layerGroup().addTo(map);

    await loadRecommendations();
    await loadMapData();
    await loadChefsData();
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

function computePC4Stats(restaurants) {
    const stats = {};
    restaurants.forEach(r => {
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

function refreshMapData() {
    if (map && allRestaurants.length > 0) loadMapData();
}

function styleFeature(feature) {
    const count = feature.properties.count || 0;
    return {
        fillColor: getColor(count),
        weight: 1.5,
        opacity: count > 0 ? 1 : 0.3,
        color: '#ffffff',
        dashArray: '',
        fillOpacity: count > 0 ? 0.85 : 0.05,
        className: count > 0 ? 'amsterdam-active-district' : 'amsterdam-empty-district'
    };
}

function getColor(d) {
    return d > 50 ? '#9a3412' : // Deep burnt orange
           d > 20 ? '#c2410c' : // Rust orange
           d > 10 ? '#ea580c' : // Warm orange
           d > 5  ? '#f97316' : // Soft orange
           d > 2  ? '#fb923c' : // Creamy orange
           d > 0  ? '#fdba74' : // Peach orange
                    '#fff7ed';  // Warm white tint for empty
}

function onEachFeature(feature, layer) {
    layer.on({ mouseover: highlightFeature, mouseout: resetHighlight, click: zoomToFeature });
}

function highlightFeature(e) {
    const layer = e.target;
    layer.setStyle({ weight: 3, color: '#fff7ed', dashArray: '', fillOpacity: 0.85 });
    layer.bringToFront();

    const props = layer.feature.properties;
    const neighborhoodName = getNeighborhoodName(props.pc4);
    const rec = districtRecommendations[props.pc4];
    
    let tooltipContent = `<div style="min-width: 280px;"><strong style="font-size: 1.1em;">${neighborhoodName}</strong><br><small style="color: #a0aec0;">PC4: ${props.pc4 || 'Unknown'}</small><hr style="margin: 8px 0; border-color: rgba(255,255,255,0.1);">`;
    
    if (rec) {
        tooltipContent += `<div style="margin-bottom: 8px;"><strong>📊 Market Overview</strong><br><small>• Restaurants: ${rec.total_restaurants} (${rec.saturation} saturation)<br>• Avg Rating: ${rec.avg_rating}⭐<br></small></div>`;
        if (rec.top_cuisines && rec.top_cuisines.length > 0) {
            const cuisineList = rec.top_cuisines.map((c, i) => {
                const count = rec.cuisine_counts ? rec.cuisine_counts[c] : '';
                return `${i + 1}. ${c}${count ? ` (${count})` : ''}`;
            }).join('<br>                    ');
            tooltipContent += `<div style="margin-bottom: 8px;"><strong>🍽️ Top Cuisines</strong><br><small>${cuisineList}</small></div>`;
        }
        if (rec.recommendation) {
            tooltipContent += `<div style="background: rgba(67, 233, 123, 0.1); padding: 6px; border-radius: 4px; margin-top: 8px;"><strong style="color: #43e97b;">💡 Opportunities</strong><br><small style="line-height: 1.4;">${rec.recommendation}</small></div>`;
        }
    } else {
        tooltipContent += `<small>Restaurants: ${props.count}<br>Avg Rating: ${props.avg_rating || 'N/A'}⭐<br>Top: ${props.top_cuisines ? props.top_cuisines.join(', ') : 'None'}</small>`;
    }
    tooltipContent += `</div>`;
    
    layer.bindTooltip(tooltipContent, { maxWidth: 350, className: 'custom-tooltip' }).openTooltip();
}

function resetHighlight(e) { geoJsonLayer.resetStyle(e.target); }
function zoomToFeature(e) { map.fitBounds(e.target.getBounds()); }

function setupEventListeners() {
    applyFiltersBtn.addEventListener('click', applyFilters);
    resetFiltersBtn.addEventListener('click', resetFilters);
    exportDataBtn.addEventListener('click', exportToCSV);
    document.getElementById('reloadData').addEventListener('click', reloadData);
    searchInput.addEventListener('input', debounce(applyFilters, 300));

    const showChefsToggle = document.getElementById('showChefsToggle');
    if (showChefsToggle) {
        showChefsToggle.addEventListener('change', (e) => {
            if (e.target.checked) {
                if (map && !map.hasLayer(chefLayerGroup)) {
                    chefLayerGroup.addTo(map);
                }
            } else {
                if (map && map.hasLayer(chefLayerGroup)) {
                    map.removeLayer(chefLayerGroup);
                }
            }
        });
    }
}

async function reloadData() {
    const btn = document.getElementById('reloadData');
    const originalText = btn.textContent;
    btn.textContent = '🔄 Reloading...';
    btn.disabled = true;
    try {
        await loadStats();
        await loadRestaurants();
        refreshMapData();
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = `Loaded ${allRestaurants.length} restaurants!`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    } catch (error) { console.error('Error reloading data:', error); alert('Failed to reload data'); }
    finally { btn.textContent = originalText; btn.disabled = false; }
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
        updateStatsDisplay();
    } catch (error) { console.error('Error loading stats:', error); }
}

function updateStatsDisplay() {
    totalRestaurants.textContent = stats.total_restaurants || 0;
    avgRating.textContent = stats.average_rating ? `${stats.average_rating}⭐` : 'N/A';
    totalReviews.textContent = formatNumber(stats.total_reviews || 0);
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
        refreshMapData();
        hideLoading();
    } catch (error) { console.error('Error loading restaurants:', error); hideLoading(); showEmpty(); }
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

function resetFilters() {
    searchInput.value = ''; cuisineFilter.value = ''; minRating.value = ''; sortBy.value = 'rating';
    filteredRestaurants = allRestaurants;
    renderRestaurants();
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

function showLoading() { loadingState.style.display = 'block'; restaurantsGrid.style.display = 'none'; emptyState.style.display = 'none'; }
function hideLoading() { loadingState.style.display = 'none'; restaurantsGrid.style.display = 'grid'; }
function showEmpty() { emptyState.style.display = 'block'; restaurantsGrid.style.display = 'none'; }
function formatNumber(num) { if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'; if (num >= 1000) return (num / 1000).toFixed(1) + 'K'; return num.toString(); }
function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }
function debounce(func, wait) { let timeout; return function(...args) { clearTimeout(timeout); timeout = setTimeout(() => func(...args), wait); }; }

async function loadChefsData() {
    try {
        const response = await fetch('./chefs_data.json');
        if (!response.ok) return;
        chefsData = await response.json();
        renderChefMarkers();
    } catch (error) {
        console.error('Error loading chefs data:', error);
    }
}

function getChefEmoji(name) {
    const n = name.toLowerCase();
    
    // Country flags for specific cuisines / nationalities
    if (n.includes('indian') || n.includes('bombay') || n.includes('swetima') || n.includes('patel') || n.includes('sham') || n.includes('spices of india')) return '🇮🇳';
    if (n.includes('italian') || n.includes('vincenzo') || n.includes('renato') || n.includes('bottega') || n.includes('cucina') || n.includes('dante') || n.includes('aleksandr')) return '🇮🇹';
    if (n.includes('korean')) return '🇰🇷';
    if (n.includes('moroccan') || n.includes('marokkaanse')) return '🇲🇦';
    if (n.includes('ghana')) return '🇬🇭';
    if (n.includes('perzie') || n.includes('persia') || n.includes('arefe')) return '🇮🇷';
    if (n.includes('sushi') || n.includes('japanese')) return '🇯🇵';
    if (n.includes('sierra leone')) return '🇸🇱';
    if (n.includes('turkish') || n.includes('turkuaz')) return '🇹🇷';
    if (n.includes('vietnamese') || n.includes('xóm')) return '🇻🇳';
    if (n.includes('bangla') || n.includes('bangaliana')) return '🇧🇩';
    if (n.includes('iraqi') || n.includes('iraq')) return '🇮🇶';
    if (n.includes('kosh') || n.includes('egypt')) return '🇪🇬';
    if (n.includes('beirut') || n.includes('lebanese') || n.includes('lebanon')) return '🇱🇧';
    if (n.includes('dominicana')) return '🇩🇴';
    if (n.includes('alakondre') || n.includes('suriname')) return '🇸🇷';
    if (n.includes('handi') || n.includes('ammi') || n.includes('pakistani')) return '🇵🇰';
    if (n.includes('yuhan') || n.includes('indonesian')) return '🇮🇩';
    if (n.includes('caribbean')) return '🇯🇲';
    if (n.includes('thai')) return '🇹🇭';
    
    // Specific food categories
    if (n.includes('healthy') || n.includes('nourish') || n.includes('herbain')) return '🥗';
    if (n.includes('desi') || n.includes('masala') || n.includes('biryani') || n.includes('deshi') || n.includes('curry')) return '🍛';
    if (n.includes('pizza') || n.includes('forno') || n.includes('pasta') || n.includes('piadina') || n.includes('foldo') || n.includes('tiramisu')) return '🍕';
    if (n.includes('bakes') || n.includes('bakery') || n.includes('cake') || n.includes('cakery') || n.includes('sweet') || n.includes('swirl') || n.includes('pastry') || n.includes('cookie') || n.includes('treats') || n.includes('desserts') || n.includes('pastry')) return '🍰';
    if (n.includes('tacos') || n.includes('mexican') || n.includes('quesadilla') || n.includes('cali') || n.includes('agave') || n.includes('comal')) return '🌮';
    if (n.includes('asian') || n.includes('soup') || n.includes('ramen') || n.includes('noodle')) return '🥢';
    if (n.includes('middle eastern') || n.includes('almatbakh')) return '🥙';
    if (n.includes('african') || n.includes('adinkra')) return '🍲';
    
    return '👨‍🍳';
}

function renderChefMarkers() {
    if (!chefLayerGroup) return;
    chefLayerGroup.clearLayers();
    
    chefsData.forEach(chef => {
        if (!chef.lat || !chef.lng) return;
        
        // Filter chefs to display those in/near Amsterdam
        const isAmsterdam = (chef.city || '').toLowerCase().includes('amsterdam') || 
                            (chef.address || '').toLowerCase().includes('amsterdam') ||
                            (chef.postal_code && /^(10|110)/.test(chef.postal_code.trim().replace(/\s+/g, '')));
        
        if (!isAmsterdam) return;
        
        const emoji = getChefEmoji(chef.name);
        const chefIcon = L.divIcon({
            className: 'chef-marker-container',
            html: `
                <div class="chef-marker-pulse"></div>
                <div class="chef-avatar-marker">${emoji}</div>
            `,
            iconSize: [46, 46],
            iconAnchor: [23, 23],
            popupAnchor: [0, -23]
        });
        
        const popupContent = `
            <div class="chef-tooltip-card">
                <div class="chef-tooltip-header">
                    <span class="chef-tooltip-badge">${emoji} Chef Partner</span>
                    <h3>${escapeHtml(chef.name)}</h3>
                </div>
                <div class="chef-tooltip-body">
                    <div class="chef-tooltip-row">
                        <span class="chef-tooltip-icon">📍</span>
                        <span>${escapeHtml(chef.address || 'Amsterdam, Netherlands')}</span>
                    </div>
                    ${chef.phone ? `
                    <div class="chef-tooltip-row">
                        <span class="chef-tooltip-icon">📞</span>
                        <span>${escapeHtml(chef.phone)}</span>
                    </div>` : ''}
                    ${chef.email ? `
                    <div class="chef-tooltip-row">
                        <span class="chef-tooltip-icon">✉️</span>
                        <span>${escapeHtml(chef.email)}</span>
                    </div>` : ''}
                </div>
            </div>
        `;
        
        const marker = L.marker([chef.lat, chef.lng], { icon: chefIcon });
        marker.bindPopup(popupContent, { className: 'chef-popup' });
        chefLayerGroup.addLayer(marker);
    });
}
