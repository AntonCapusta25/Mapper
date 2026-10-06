// API Base URL
const API_BASE = '';

// State
let allRestaurants = [];
let filteredRestaurants = [];
let stats = {};

// PC4 to Neighborhood Name Mapping
const pc4ToNeighborhood = {
    // Centrum
    '1011': 'Burgwallen-Oude Zijde',
    '1012': 'Burgwallen-Oude Zijde',
    '1013': 'Grachtengordel-West',
    '1014': 'Haarlemmerbuurt',
    '1015': 'Grachtengordel-West',
    '1016': 'Grachtengordel-Zuid',
    '1017': 'Grachtengordel-Zuid',
    '1018': 'Weesperbuurt/Plantage',
    '1019': 'Oostelijke Eilanden',
    // Oost
    '1021': 'Indische Buurt',
    '1022': 'Indische Buurt',
    '1091': 'Weesperbuurt/Plantage',
    '1092': 'Oosterparkbuurt',
    '1093': 'Dapperbuurt',
    '1094': 'Oosterparkbuurt',
    '1095': 'Indische Buurt',
    '1096': 'Indische Buurt',
    '1097': 'Indische Buurt',
    '1098': 'IJburg',
    '1099': 'IJburg',
    // West
    '1013': 'Grachtengordel-West',
    '1014': 'Haarlemmerbuurt',
    '1015': 'Grachtengordel-West',
    '1016': 'Grachtengordel-Zuid',
    '1051': 'Oud-West',
    '1052': 'Westerpark',
    '1053': 'De Baarsjes',
    '1054': 'Oud-West',
    '1055': 'Bos en Lommer',
    '1056': 'De Baarsjes',
    '1057': 'Bos en Lommer',
    '1058': 'Overtoomse Veld',
    '1059': 'Slotervaart',
    '1060': 'Slotermeer',
    '1061': 'Overtoomse Veld',
    '1062': 'Zuidas',
    '1063': 'Buitenveldert',
    '1064': 'Slotervaart',
    '1065': 'Osdorp',
    '1066': 'De Aker',
    '1067': 'Osdorp',
    '1068': 'Buitenveldert',
    '1069': 'Slotervaart',
    // Zuid
    '1070': 'Zuid',
    '1071': 'Museumkwartier',
    '1072': 'Willemspark',
    '1073': 'Apollobuurt',
    '1074': 'Stadionbuurt',
    '1075': 'Scheldebuurt',
    '1076': 'Stadionbuurt',
    '1077': 'Prinses Irenebuurt',
    '1078': 'Rivierenbuurt',
    '1079': 'Buitenveldert',
    '1081': 'Buitenveldert',
    '1082': 'Buitenveldert',
    '1083': 'Buitenveldert',
    '1084': 'Buitenveldert',
    '1085': 'Buitenveldert',
    '1086': 'Buitenveldert',
    '1087': 'Buitenveldert',
    // Zuidoost
    '1101': 'Zuidoost - Bijlmer',
    '1102': 'Zuidoost - Gaasperdam',
    '1103': 'Zuidoost - Venserpolder',
    '1104': 'Zuidoost - Gaasperdam',
    '1105': 'Zuidoost - Nellestein',
    '1106': 'Zuidoost - Holendrecht',
    '1107': 'Zuidoost - Reigersbos',
    '1108': 'Zuidoost - Gein',
    '1109': 'Zuidoost - Driemond',
    // Noord
    '1031': 'Noord - Buiksloterham',
    '1032': 'Noord - Tuindorp Oostzaan',
    '1033': 'Noord - Buiksloot',
    '1034': 'Noord - Buiksloot',
    '1035': 'Noord - Kadoelen',
    '1036': 'Noord - Nieuwendam',
    '1021': 'Noord - Overhoeks',
    // Nieuw-West
    '1043': 'Nieuw-West - Geuzenveld',
    '1044': 'Nieuw-West - Slotermeer',
    '1045': 'Nieuw-West - Slotervaart',
    '1046': 'Nieuw-West - Slotermeer',
    '1047': 'Nieuw-West - Osdorp',
    '1061': 'Nieuw-West - Overtoomse Veld',
    '1062': 'Nieuw-West - Zuidas',
    '1064': 'Nieuw-West - Slotervaart',
    '1065': 'Nieuw-West - Osdorp',
    '1066': 'Nieuw-West - De Aker',
    '1067': 'Nieuw-West - Osdorp',
    '1068': 'Nieuw-West - Buitenveldert',
    '1069': 'Nieuw-West - Slotervaart'
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

// Map State
let map;
let geoJsonLayer;
let districtRecommendations = {};

// Initialize Map
async function initMap() {
    // Center on Amsterdam
    map = L.map('map').setView([52.3676, 4.9041], 12);

    // Add dark tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // Load recommendations
    await loadRecommendations();
    await loadMapData();
}

// Load District Recommendations
async function loadRecommendations() {
    try {
        const response = await fetch('/static/district_recommendations.json');
        if (response.ok) {
            districtRecommendations = await response.json();
            console.log('Loaded recommendations for', Object.keys(districtRecommendations).length, 'districts');
        }
    } catch (error) {
        console.error('Error loading recommendations:', error);
    }
}

// Load Map Data
async function loadMapData() {
    try {
        // Fetch the base GeoJSON
        const response = await fetch('/static/amsterdam_pc4.geojson');
        if (!response.ok) {
            console.error("GeoJSON file not found");
            return;
        }

        const geojson = await response.json();

        // Compute statistics from current restaurant data
        const statsByPC4 = computePC4Stats(allRestaurants);

        // Enrich GeoJSON with stats
        const enrichedFeatures = geojson.features.map(feature => {
            const pc4 = feature.properties.pc4;
            const stats = statsByPC4[pc4] || {
                count: 0,
                avg_rating: 0,
                top_cuisines: []
            };

            return {
                ...feature,
                properties: {
                    ...feature.properties,
                    ...stats
                }
            };
        });

        renderMapData({
            type: "FeatureCollection",
            features: enrichedFeatures
        });
    } catch (error) {
        console.error('Error loading map data:', error);
    }
}

// Compute PC4 Statistics from Restaurant Data
function computePC4Stats(restaurants) {
    const stats = {};

    restaurants.forEach(r => {
        const address = r.address || '';
        // Extract 4-digit zip code
        const match = address.match(/\b(\d{4})\s*[A-Z]{2}\b/);
        if (match) {
            const pc4 = match[1];

            if (!stats[pc4]) {
                stats[pc4] = {
                    count: 0,
                    total_rating: 0,
                    cuisines: {}
                };
            }

            stats[pc4].count++;

            if (r.rating) {
                stats[pc4].total_rating += r.rating;
            }

            if (r.cuisine) {
                stats[pc4].cuisines[r.cuisine] = (stats[pc4].cuisines[r.cuisine] || 0) + 1;
            }
        }
    });

    // Calculate averages and top cuisines
    Object.keys(stats).forEach(pc4 => {
        const s = stats[pc4];
        s.avg_rating = s.count > 0 ? (s.total_rating / s.count).toFixed(2) : 0;

        // Get top 3 cuisines
        const sortedCuisines = Object.entries(s.cuisines)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 3)
            .map(c => c[0]);

        s.top_cuisines = sortedCuisines;
        delete s.cuisines;
        delete s.total_rating;
    });

    return stats;
}

// Refresh map data when restaurants are loaded
function refreshMapData() {
    if (map && allRestaurants.length > 0) {
        loadMapData();
    }
}

// Render Map Data
function renderMapData(data) {
    if (geoJsonLayer) {
        map.removeLayer(geoJsonLayer);
    }

    geoJsonLayer = L.geoJSON(data, {
        style: styleFeature,
        onEachFeature: onEachFeature
    }).addTo(map);
}

// Style for Map Features
function styleFeature(feature) {
    return {
        fillColor: getColor(feature.properties.count),
        weight: 2,
        opacity: 1,
        color: 'white',
        dashArray: '3',
        fillOpacity: 0.7
    };
}

// Get Color based on count
function getColor(d) {
    return d > 50 ? '#800026' :
        d > 20 ? '#BD0026' :
            d > 10 ? '#E31A1C' :
                d > 5 ? '#FC4E2A' :
                    d > 2 ? '#FD8D3C' :
                        d > 0 ? '#FEB24C' :
                            '#FFEDA0';
}

// Interaction handlers
function onEachFeature(feature, layer) {
    layer.on({
        mouseover: highlightFeature,
        mouseout: resetHighlight,
        click: zoomToFeature
    });
}

function highlightFeature(e) {
    const layer = e.target;

    layer.setStyle({
        weight: 5,
        color: '#ffffff',
        dashArray: '',
        fillOpacity: 0.7
    });

    layer.bringToFront();

    // Show comprehensive district analysis
    const props = layer.feature.properties;
    const neighborhoodName = getNeighborhoodName(props.pc4);
    const rec = districtRecommendations[props.pc4];

    let tooltipContent = `
        <div style="min-width: 280px;">
            <strong style="font-size: 1.1em;">${neighborhoodName}</strong><br>
            <small style="color: #a0aec0;">PC4: ${props.pc4 || 'Unknown'}</small>
            <hr style="margin: 8px 0; border-color: rgba(255,255,255,0.1);">
    `;

    if (rec) {
        // Market Overview
        tooltipContent += `
            <div style="margin-bottom: 8px;">
                <strong>📊 Market Overview</strong><br>
                <small>
                    • Restaurants: ${rec.total_restaurants} (${rec.saturation} saturation)<br>
                    • Avg Rating: ${rec.avg_rating}⭐<br>
                </small>
            </div>
        `;

        // Top Cuisines
        if (rec.top_cuisines && rec.top_cuisines.length > 0) {
            const cuisineList = rec.top_cuisines.map((c, i) => {
                const count = rec.cuisine_counts ? rec.cuisine_counts[c] : '';
                return `${i + 1}. ${c}${count ? ` (${count})` : ''}`;
            }).join('<br>                    ');

            tooltipContent += `
                <div style="margin-bottom: 8px;">
                    <strong>🍽️ Top Cuisines</strong><br>
                    <small>
                        ${cuisineList}
                    </small>
                </div>
            `;
        }

        // Business Opportunities
        if (rec.recommendation) {
            tooltipContent += `
                <div style="background: rgba(67, 233, 123, 0.1); padding: 6px; border-radius: 4px; margin-top: 8px;">
                    <strong style="color: #43e97b;">💡 Opportunities</strong><br>
                    <small style="line-height: 1.4;">${rec.recommendation}</small>
                </div>
            `;
        }
    } else {
        // Fallback for districts without analysis
        tooltipContent += `
            <small>
                Restaurants: ${props.count}<br>
                Avg Rating: ${props.avg_rating || 'N/A'}⭐<br>
                Top: ${props.top_cuisines ? props.top_cuisines.join(', ') : 'None'}
            </small>
        `;
    }

    tooltipContent += `</div>`;

    layer.bindTooltip(tooltipContent, {
        maxWidth: 350,
        className: 'custom-tooltip'
    }).openTooltip();
}

function resetHighlight(e) {
    geoJsonLayer.resetStyle(e.target);
}

function zoomToFeature(e) {
    map.fitBounds(e.target.getBounds());
    // Optional: Filter list by this zip code
}

// Setup Event Listeners
function setupEventListeners() {
    applyFiltersBtn.addEventListener('click', applyFilters);
    resetFiltersBtn.addEventListener('click', resetFilters);
    exportDataBtn.addEventListener('click', exportToCSV);
    document.getElementById('reloadData').addEventListener('click', reloadData);

    // Real-time search
    if (searchInput) {
        searchInput.addEventListener('input', debounce(applyFilters, 300));
    }

    // Tab Switching
    const tabs = document.querySelectorAll('.tab-btn');
    const views = document.querySelectorAll('.view-section');

    console.log('Setting up tab switching. Found', tabs.length, 'tabs and', views.length, 'views');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            console.log('Tab clicked:', tab.getAttribute('data-tab'));

            // Remove active class from all tabs and views
            tabs.forEach(t => t.classList.remove('active'));
            views.forEach(v => {
                v.style.display = 'none';
                v.classList.remove('active');
            });

            // Add active class to clicked tab
            tab.classList.add('active');

            // Show corresponding view
            const viewId = tab.getAttribute('data-tab');
            const view = document.getElementById(viewId);

            if (view) {
                console.log('Showing view:', viewId);
                view.style.display = 'block';
                setTimeout(() => view.classList.add('active'), 10);

                // Load analytics if needed
                if (viewId === 'analytics-view' && !analyticsLoaded) {
                    console.log('Loading analytics...');
                    loadAnalytics();
                    analyticsLoaded = true;
                }

                // Load farms data if needed
                if (viewId === 'farms-view' && !farmsLoaded) {
                    console.log('Loading farms...');
                    loadFarmsStats();
                    loadFarms();
                    initFarmsMap();
                    farmsLoaded = true;
                }

                // Update stats bar based on active tab
                if (viewId === 'farms-view') {
                    updateStatsDisplay('farms');
                } else if (viewId === 'restaurants-view') {
                    updateStatsDisplay('restaurants');
                }

                // Resize map if switching to map view
                if (viewId === 'map-view' && map) {
                    setTimeout(() => map.invalidateSize(), 100);
                }

                // Resize farms map if switching back to farms view
                if (viewId === 'farms-view' && farmsMap) {
                    setTimeout(() => farmsMap.invalidateSize(), 100);
                }
            } else {
                console.error('View not found:', viewId);
            }
        });
    });
}

// Analytics State
let analyticsLoaded = false;
let farmsLoaded = false;
let analyticsData = null;
let ratingChart = null;
let reviewChart = null;

// Load Analytics Data
async function loadAnalytics() {
    try {
        const response = await fetch(`${API_BASE}/api/analytics`);
        analyticsData = await response.json();
        renderAnalytics();
        analyticsLoaded = true;

        // Also load districts list and setup city summary
        await loadDistrictsList();
        setupAnalyticsViewToggle();
        loadCitySummary(); // Load city summary by default
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

// Render Analytics Dashboard
function renderAnalytics() {
    if (!analyticsData) return;

    renderMetrics();
    renderCharts();
    renderGaps();
    renderSaturation();
}

// Render Key Metrics
function renderMetrics() {
    const container = document.getElementById('analyticsMetrics');
    const trends = analyticsData.trends;
    const regression = analyticsData.regression;

    const metrics = [
        {
            label: 'Avg Rating',
            value: trends.rating_distribution.mean + '⭐'
        },
        {
            label: 'Avg Reviews',
            value: Math.round(trends.review_distribution.mean)
        },
        {
            label: 'Rating/Review Corr.',
            value: regression.rating_vs_reviews.correlation.toFixed(2)
        },
        {
            label: 'Market Growth',
            value: 'High' // Placeholder based on data
        }
    ];

    container.innerHTML = metrics.map(m => `
        <div class="metric-item">
            <div class="metric-value">${m.value}</div>
            <div class="metric-label">${m.label}</div>
        </div>
    `).join('');
}

// Render Charts
function renderCharts() {
    const cuisinePerf = analyticsData.regression.cuisine_performance;

    // 1. Rating Chart
    const ratingCtx = document.getElementById('cuisineRatingChart').getContext('2d');
    if (ratingChart) ratingChart.destroy();

    ratingChart = new Chart(ratingCtx, {
        type: 'bar',
        data: {
            labels: cuisinePerf.slice(0, 10).map(c => c.cuisine),
            datasets: [{
                label: 'Average Rating',
                data: cuisinePerf.slice(0, 10).map(c => c.avg_rating),
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: false,
                    min: 3.5,
                    grid: { color: 'rgba(255, 255, 255, 0.1)' },
                    ticks: { color: '#a0aec0' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#a0aec0' }
                }
            }
        }
    });

    // 2. Review Chart
    const reviewCtx = document.getElementById('cuisineReviewChart').getContext('2d');
    if (reviewChart) reviewChart.destroy();

    const topReviewed = analyticsData.trends.top_cuisines_by_engagement;

    reviewChart = new Chart(reviewCtx, {
        type: 'doughnut',
        data: {
            labels: topReviewed.slice(0, 6).map(c => c.cuisine),
            datasets: [{
                data: topReviewed.slice(0, 6).map(c => c.total_reviews),
                backgroundColor: [
                    '#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: '#a0aec0' }
                }
            }
        }
    });
}

// Render Market Gaps
function renderGaps() {
    const container = document.getElementById('marketGaps');
    const gaps = analyticsData.gaps.underserved_cuisines.slice(0, 6);

    container.innerHTML = gaps.map(gap => `
        <div class="gap-card">
            <h4>${getNeighborhoodName(gap.pc4)}</h4>
            <p>Opportunity Score: ${gap.opportunity_score}/10</p>
            <div class="gap-tags">
                ${gap.missing_cuisines.map(c => `<span class="gap-tag">Missing: ${c}</span>`).join('')}
            </div>
        </div>
    `).join('');
}

// Render Saturation Table
function renderSaturation() {
    const tbody = document.querySelector('#saturationTable tbody');
    const saturation = analyticsData.saturation.by_district.slice(0, 10);

    tbody.innerHTML = saturation.map(item => `
        <tr>
            <td>
                <strong>${getNeighborhoodName(item.pc4)}</strong>
                <br><small style="color: #718096;">${item.pc4}</small>
            </td>
            <td>${item.restaurant_count}</td>
            <td>
                <span style="
                    padding: 4px 8px; 
                    border-radius: 4px; 
                    background: ${item.saturation_level === 'High' ? 'rgba(245, 87, 108, 0.2)' : 'rgba(67, 233, 123, 0.2)'};
                    color: ${item.saturation_level === 'High' ? '#f5576c' : '#43e97b'};
                    font-size: 0.875rem;
                    font-weight: 600;
                ">
                    ${item.saturation_level}
                </span>
            </td>
            <td>
                <div style="
                    width: 100%; 
                    height: 6px; 
                    background: rgba(255,255,255,0.1); 
                    border-radius: 3px;
                    overflow: hidden;
                ">
                    <div style="
                        width: ${item.competition_score * 10}%; 
                        height: 100%; 
                        background: var(--accent-gradient);
                    "></div>
                </div>
            </td>
        </tr>
    `).join('');
}

// District Analytics State
let districtsData = null;
let currentDistrictPC4 = null;

// Load Districts List
async function loadDistrictsList() {
    try {
        const response = await fetch(`${API_BASE}/api/analytics/districts`);
        const data = await response.json();
        districtsData = data.districts;

        const selector = document.getElementById('districtSelect');
        if (selector) {
            selector.innerHTML = '<option value="">-- Select District --</option>';

            districtsData.forEach(district => {
                const option = document.createElement('option');
                option.value = district.pc4;
                option.textContent = `${getNeighborhoodName(district.pc4)} (${district.pc4}) - ${district.restaurant_count} restaurants`;
                selector.appendChild(option);
            });

            selector.addEventListener('change', (e) => {
                if (e.target.value) {
                    loadDistrictAnalytics(e.target.value);
                } else {
                    showCitywideAnalytics();
                }
            });
        }
    } catch (error) {
        console.error('Error loading districts:', error);
    }
}

// Load District Analytics
async function loadDistrictAnalytics(pc4) {
    currentDistrictPC4 = pc4;
    document.getElementById('districtDetailView').style.display = 'block';
    document.getElementById('citywideAnalytics').style.display = 'none';

    const aiInsightsContainer = document.getElementById('aiInsights');
    aiInsightsContainer.innerHTML = '<div class="loading"><div class="spinner"></div><p>Generating AI insights...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/api/analytics/district/${pc4}`);
        const data = await response.json();
        renderDistrictAnalytics(data);
    } catch (error) {
        console.error('Error loading district analytics:', error);
        aiInsightsContainer.innerHTML = '<p style="color: #ff6b6b;">Error loading analytics.</p>';
    }
}

// Render District Analytics (helper function to render each section)
function renderMetricList(data, mapping) {
    return `<div class="metric-list">${Object.entries(mapping).map(([label, getValue]) => {
        const value = typeof getValue === 'function' ? getValue(data) : data[getValue];
        return `<div class="metric-row"><span class="metric-label">${label}:</span><span class="metric-value">${value !== undefined ? value : 'N/A'}</span></div>`;
    }).join('')}</div>`;
}

// Render All District Analytics
function renderDistrictAnalytics(data) {
    // AI Insights
    const aiInsightsContainer = document.getElementById('aiInsights');
    if (data.ai_insights) {
        aiInsightsContainer.innerHTML = `<div class="ai-text">${data.ai_insights.split('\n\n').map(p => `<p>${p.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')}</p>`).join('')}</div>`;
    }

    // Overview
    const overview = data.overview || {};
    document.getElementById('districtOverview').innerHTML = renderMetricList(overview, {
        'Total Restaurants': 'total_restaurants',
        'Average Rating': d => `${d.avg_rating || 0}⭐`,
        'Median Rating': d => `${d.median_rating || 0}⭐`,
        'Total Reviews': d => (d.total_reviews || 0).toLocaleString(),
        'Avg Reviews/Restaurant': d => Math.round(d.avg_reviews || 0),
        'Cuisine Diversity': d => `${d.cuisines_count || 0} cuisines`
    });

    // Quality
    const quality = data.quality_metrics || {};
    const rd = quality.rating_distribution || {};
    document.getElementById('districtQuality').innerHTML = renderMetricList({ ...quality, ...rd }, {
        'Rating Range': d => `${d.min || 0} - ${d.max || 0}`,
        'Std Deviation': 'std_dev',
        'High-Rated (4.5+)': d => `${d.high_rated_count || 0} restaurants`,
        'Low-Rated (<3.5)': d => `${d.low_rated_count || 0} restaurants`,
        'High Engagement (100+)': d => `${d.review_volume?.high_engagement || 0} restaurants`
    });

    // Price
    const price = data.price_analysis || {};
    if (price.available) {
        const dist = price.distribution || {};
        document.getElementById('districtPrice').innerHTML = renderMetricList({ ...price, ...dist }, {
            'Avg Price Level': d => `${d.average_price_level || 0}/4`,
            'Affordability Score': d => `${d.affordability_score || 0}/10`,
            'Budget (€)': 'budget',
            'Moderate (€€)': 'moderate',
            'Upscale (€€€)': 'upscale',
            'Fine Dining (€€€€)': 'fine_dining'
        });
    } else {
        document.getElementById('districtPrice').innerHTML = '<p>Price data not available</p>';
    }

    // Cuisine
    const cuisine = data.cuisine_analysis || {};
    const topCuisines = cuisine.top_cuisines || [];
    document.getElementById('districtCuisine').innerHTML = renderMetricList(cuisine, {
        'Total Cuisines': 'total_cuisines',
        'Diversity Index': 'diversity_index',
        'Top 3 Share': d => `${d.concentration?.top_3_share || 0}%`,
        'Concentrated': d => d.concentration?.is_concentrated ? 'Yes' : 'No'
    }) + `<div style="margin-top:1rem;"><strong>Top Cuisines:</strong><ol style="margin-top:0.5rem;">${topCuisines.slice(0, 5).map(c => `<li>${c.cuisine} - ${c.count} (${c.percentage}%)</li>`).join('')}</ol></div>`;

    // Competition
    const comp = data.competition_analysis || {};
    document.getElementById('districtCompetition').innerHTML = renderMetricList(comp, {
        'Market Saturation': d => `<span class="badge badge-${(d.market_saturation || '').toLowerCase()}">${d.market_saturation}</span>`,
        'Saturation Score': d => `${d.saturation_score || 0}/10`,
        'Competitive Intensity': 'competitive_intensity',
        'Avg Competitors/Cuisine': 'avg_competitors_per_cuisine',
        'Entry Barriers': 'entry_barriers'
    });

    // Positioning
    const pos = data.market_positioning || {};
    document.getElementById('districtPositioning').innerHTML = renderMetricList(pos, {
        'Category': d => `<strong>${d.positioning || 'N/A'}</strong>`,
        'Avg Rating': d => `${d.avg_rating || 0}⭐`,
        'Avg Price Level': d => `${d.avg_price_level || 0}/4`,
        'Quality/Price Ratio': 'quality_price_ratio'
    });

    // Opportunities
    const opp = data.growth_opportunities || {};
    const underserved = opp.underserved_cuisines || [];
    document.getElementById('districtOpportunities').innerHTML = renderMetricList(opp, {
        'Market Potential Score': d => `<strong>${d.market_potential_score || 0}/10</strong>`,
        'Quality Gap': 'quality_improvement_potential',
        'Has Quality Opportunity': d => d.has_quality_gap ? 'Yes ✓' : 'No'
    }) + (underserved.length > 0 ? `<div style="margin-top:1rem;"><strong>Underserved Cuisines:</strong><ul style="margin-top:0.5rem;">${underserved.map(c => `<li>${c.cuisine} (${c.global_popularity} citywide)</li>`).join('')}</ul></div>` : '<p style="margin-top:1rem;">No significant cuisine gaps.</p>');

    // Benchmarks
    const bench = data.benchmarks?.vs_citywide || {};
    document.getElementById('districtBenchmarks').innerHTML = renderMetricList(bench, {
        'Rating vs Citywide': d => `${d.rating_diff >= 0 ? '+' : ''}${d.rating_diff || 0}`,
        'Reviews vs Citywide': d => `${d.reviews_diff >= 0 ? '+' : ''}${Math.round(d.reviews_diff || 0)}`,
        'Rating Percentile': d => `${d.rating_percentile || 50}th percentile`
    });

    // Setup regenerate button
    const regenerateBtn = document.getElementById('regenerateInsights');
    if (regenerateBtn) {
        regenerateBtn.onclick = () => regenerateInsights(currentDistrictPC4);
    }
}

// Regenerate Insights
async function regenerateInsights(pc4) {
    const aiInsightsContainer = document.getElementById('aiInsights');
    aiInsightsContainer.innerHTML = '<div class="loading"><div class="spinner"></div><p>Regenerating insights...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/api/analytics/district/${pc4}/regenerate`, { method: 'POST' });
        const data = await response.json();

        if (data.insights) {
            aiInsightsContainer.innerHTML = `<div class="ai-text">${data.insights.split('\n\n').map(p => `<p>${p.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>')}</p>`).join('')}</div>`;
        }
    } catch (error) {
        console.error('Error regenerating insights:', error);
        aiInsightsContainer.innerHTML = '<p style="color: #ff6b6b;">Error regenerating insights.</p>';
    }
}

// Show Citywide Analytics
function showCitywideAnalytics() {
    document.getElementById('districtDetailView').style.display = 'none';
    document.getElementById('citywideAnalytics').style.display = 'grid';
    currentDistrictPC4 = null;
}

// City Summary State
let citySummaryData = null;
let citySummaryLoaded = false;

// View Toggle Handlers
function setupAnalyticsViewToggle() {
    const toggleBtns = document.querySelectorAll('.view-toggle-btn');
    const citySummaryView = document.getElementById('citySummaryView');
    const districtAnalysisView = document.getElementById('districtAnalysisView');

    toggleBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.getAttribute('data-view');

            // Update active button
            toggleBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Toggle views
            if (view === 'city') {
                citySummaryView.style.display = 'block';
                districtAnalysisView.style.display = 'none';

                // Load city summary if not loaded
                if (!citySummaryLoaded) {
                    loadCitySummary();
                }
            } else {
                citySummaryView.style.display = 'none';
                districtAnalysisView.style.display = 'block';
            }
        });
    });
}

// Load City Summary
async function loadCitySummary() {
    try {
        const response = await fetch(`${API_BASE}/api/analytics/city-summary`);
        citySummaryData = await response.json();

        renderCitySummary(citySummaryData);
        citySummaryLoaded = true;
    } catch (error) {
        console.error('Error loading city summary:', error);
    }
}

// Render City Summary
function renderCitySummary(data) {
    renderStrategicRecommendations(data.strategic_recommendations);
    renderTopOpportunities(data.top_opportunities);
    renderUnderservedCuisines(data.underserved_cuisines);
    renderInvestmentPriorities(data.investment_priorities);
    renderQualitySaturationMatrix(data.quality_saturation_analysis);
}

// Render Strategic Recommendations
function renderStrategicRecommendations(recommendations) {
    const container = document.getElementById('strategicRecommendations');

    if (!recommendations) {
        container.innerHTML = '<p>No recommendations available</p>';
        return;
    }

    // Format recommendations (preserve markdown-like formatting)
    const formatted = recommendations
        .split('\n\n')
        .map(para => `<p>${para.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</p>`)
        .join('');

    container.innerHTML = formatted;
}

// Render Top Opportunities
function renderTopOpportunities(opportunities) {
    const container = document.getElementById('topOpportunities');

    if (!opportunities || opportunities.length === 0) {
        container.innerHTML = '<p>No opportunities data available</p>';
        return;
    }

    container.innerHTML = opportunities.map((opp, idx) => `
        <div class="opportunity-item">
            <div class="opportunity-rank">${idx + 1}</div>
            <div class="opportunity-details">
                <div class="opportunity-header">
                    <strong>District ${opp.pc4}</strong>
                    <span class="opportunity-score">${opp.potential_score}/10</span>
                </div>
                <div class="opportunity-meta">
                    ${opp.restaurant_count} restaurants • ${opp.avg_rating}⭐ • ${opp.saturation} saturation
                </div>
                <div class="opportunity-tags">
                    ${opp.quality_gap > 0.3 ? '<span class="tag tag-quality">Quality Gap</span>' : ''}
                    ${opp.underserved_count > 0 ? `<span class="tag tag-cuisine">${opp.underserved_count} Underserved</span>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

// Render Underserved Cuisines
function renderUnderservedCuisines(cuisines) {
    const container = document.getElementById('underservedCuisines');

    if (!cuisines || cuisines.length === 0) {
        container.innerHTML = '<p>No underserved cuisines data available</p>';
        return;
    }

    container.innerHTML = cuisines.slice(0, 10).map((cuisine, idx) => `
        <div class="cuisine-item">
            <div class="cuisine-rank">${idx + 1}</div>
            <div class="cuisine-details">
                <strong>${cuisine.cuisine}</strong>
                <div class="cuisine-meta">
                    Missing in ${cuisine.districts_missing} districts
                    <span class="opportunity-badge badge-${cuisine.opportunity_level.toLowerCase()}">${cuisine.opportunity_level}</span>
                </div>
            </div>
        </div>
    `).join('');
}

// Render Investment Priorities
function renderInvestmentPriorities(priorities) {
    const container = document.getElementById('investmentPriorities');

    if (!priorities || priorities.length === 0) {
        container.innerHTML = '<p>No investment priorities data available</p>';
        return;
    }

    container.innerHTML = `
        <table class="investment-table">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>District</th>
                    <th>Investment Score</th>
                    <th>Potential</th>
                    <th>Entry Barriers</th>
                    <th>Recommendation</th>
                </tr>
            </thead>
            <tbody>
                ${priorities.slice(0, 10).map((p, idx) => `
                    <tr>
                        <td>${idx + 1}</td>
                        <td><strong>${p.pc4}</strong></td>
                        <td><span class="score-badge">${p.investment_score}</span></td>
                        <td>${p.potential_score}/10</td>
                        <td><span class="badge badge-${p.entry_barriers.toLowerCase()}">${p.entry_barriers}</span></td>
                        <td class="recommendation-cell">${p.recommendation}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Render Quality vs Saturation Matrix
function renderQualitySaturationMatrix(matrix) {
    const container = document.getElementById('qualitySaturationMatrix');

    if (!matrix) {
        container.innerHTML = '<p>No matrix data available</p>';
        return;
    }

    container.innerHTML = `
        <div class="matrix-quadrants">
            <div class="matrix-quadrant quadrant-best">
                <h4>🌟 Best Opportunities</h4>
                <p class="quadrant-desc">High Quality, Low Saturation</p>
                <div class="quadrant-count">${matrix.high_quality_low_saturation.length} districts</div>
                <div class="quadrant-list">
                    ${matrix.high_quality_low_saturation.slice(0, 5).map(d =>
        `<div class="quadrant-item">${d.pc4} (${d.avg_rating}⭐, ${d.restaurant_count} restaurants)</div>`
    ).join('')}
                </div>
            </div>
            
            <div class="matrix-quadrant quadrant-competitive">
                <h4>⚔️ Competitive Markets</h4>
                <p class="quadrant-desc">High Quality, High Saturation</p>
                <div class="quadrant-count">${matrix.high_quality_high_saturation.length} districts</div>
                <div class="quadrant-list">
                    ${matrix.high_quality_high_saturation.slice(0, 5).map(d =>
        `<div class="quadrant-item">${d.pc4} (${d.avg_rating}⭐, ${d.restaurant_count} restaurants)</div>`
    ).join('')}
                </div>
            </div>
            
            <div class="matrix-quadrant quadrant-emerging">
                <h4>🌱 Emerging Markets</h4>
                <p class="quadrant-desc">Lower Quality, Low Saturation</p>
                <div class="quadrant-count">${matrix.low_quality_low_saturation.length} districts</div>
                <div class="quadrant-list">
                    ${matrix.low_quality_low_saturation.slice(0, 5).map(d =>
        `<div class="quadrant-item">${d.pc4} (${d.avg_rating}⭐, ${d.restaurant_count} restaurants)</div>`
    ).join('')}
                </div>
            </div>
            
            <div class="matrix-quadrant quadrant-challenging">
                <h4>⚠️ Challenging Markets</h4>
                <p class="quadrant-desc">Lower Quality, High Saturation</p>
                <div class="quadrant-count">${matrix.low_quality_high_saturation.length} districts</div>
                <div class="quadrant-list">
                    ${matrix.low_quality_high_saturation.slice(0, 5).map(d =>
        `<div class="quadrant-item">${d.pc4} (${d.avg_rating}⭐, ${d.restaurant_count} restaurants)</div>`
    ).join('')}
                </div>
            </div>
        </div>
    `;
}


// Reload Data from Server
async function reloadData() {
    const btn = document.getElementById('reloadData');
    const originalText = btn.textContent;
    btn.textContent = '🔄 Reloading...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/reload`, { method: 'POST' });
        const data = await response.json();

        await loadStats();
        await loadRestaurants();
        refreshMapData(); // Update map

        // Show toast or alert
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = `Loaded ${data.total_restaurants} restaurants!`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);

    } catch (error) {
        console.error('Error reloading data:', error);
        alert('Failed to reload data');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Load Statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE}/api/restaurants/stats`);
        stats = await response.json();

        updateStatsDisplay();
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Update Stats Display
function updateStatsDisplay(type = 'restaurants') {
    if (type === 'farms') {
        // Update with farms stats
        totalRestaurants.textContent = farmsStats.total_farms || 0;
        avgRating.textContent = farmsStats.average_rating ? `${farmsStats.average_rating}⭐` : 'N/A';
        totalReviews.textContent = formatNumber(farmsStats.total_reviews || 0);

        // Update labels
        document.querySelector('#totalRestaurants').parentElement.querySelector('.stat-label').textContent = 'Farms';
    } else {
        // Update with restaurants stats
        totalRestaurants.textContent = stats.total_restaurants || 0;
        avgRating.textContent = stats.average_rating ? `${stats.average_rating}⭐` : 'N/A';
        totalReviews.textContent = formatNumber(stats.total_reviews || 0);

        // Update labels
        document.querySelector('#totalRestaurants').parentElement.querySelector('.stat-label').textContent = 'Restaurants';
    }
}

// Load Restaurants
async function loadRestaurants() {
    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/restaurants`);
        const data = await response.json();

        allRestaurants = data.restaurants;
        filteredRestaurants = allRestaurants;

        await loadCuisines();
        renderRestaurants();
        refreshMapData(); // Update map with new data
        hideLoading();
    } catch (error) {
        console.error('Error loading restaurants:', error);
        hideLoading();
        showEmpty();
    }
}

// Load Cuisines for Filter
async function loadCuisines() {
    try {
        const response = await fetch(`${API_BASE}/api/restaurants/cuisines`);
        const data = await response.json();

        cuisineFilter.innerHTML = '<option value="">All Cuisines</option>';

        data.cuisines.forEach(cuisine => {
            const option = document.createElement('option');
            option.value = cuisine;
            option.textContent = cuisine;
            cuisineFilter.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading cuisines:', error);
    }
}

// Apply Filters
async function applyFilters() {
    const search = searchInput.value.trim();
    const cuisine = cuisineFilter.value;
    const rating = minRating.value;
    const sort = sortBy.value;

    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (cuisine) params.append('cuisine', cuisine);
    if (rating) params.append('min_rating', rating);
    if (sort) params.append('sort_by', sort);

    showLoading();

    try {
        const response = await fetch(`${API_BASE}/api/restaurants?${params}`);
        const data = await response.json();

        filteredRestaurants = data.restaurants;
        renderRestaurants();
        hideLoading();
    } catch (error) {
        console.error('Error applying filters:', error);
        hideLoading();
    }
}

// Reset Filters
function resetFilters() {
    searchInput.value = '';
    cuisineFilter.value = '';
    minRating.value = '';
    sortBy.value = 'rating';

    filteredRestaurants = allRestaurants;
    renderRestaurants();
}

// Render Restaurants
function renderRestaurants() {
    resultsCount.textContent = filteredRestaurants.length;

    if (filteredRestaurants.length === 0) {
        showEmpty();
        return;
    }

    restaurantsGrid.innerHTML = '';
    emptyState.style.display = 'none';

    filteredRestaurants.forEach(restaurant => {
        const card = createRestaurantCard(restaurant);
        restaurantsGrid.appendChild(card);
    });
}

// Create Restaurant Card
function createRestaurantCard(restaurant) {
    const card = document.createElement('div');
    card.className = 'restaurant-card';

    const rating = restaurant.rating ? restaurant.rating.toFixed(1) : 'N/A';
    const reviews = restaurant.reviews ? formatNumber(restaurant.reviews) : '0';
    const address = restaurant.address || 'Address not available';
    const phone = restaurant.phone || 'Phone not available';
    const cuisine = restaurant.cuisine || 'Cuisine not specified';
    const priceLevel = restaurant.price_level || 'Price not available';

    // Create Google Maps link
    const mapsUrl = restaurant.latitude && restaurant.longitude
        ? `https://www.google.com/maps/search/?api=1&query=${restaurant.latitude},${restaurant.longitude}`
        : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(restaurant.name + ' Amsterdam')}`;

    card.innerHTML = `
        <div class="card-header">
            <div>
                <h3 class="restaurant-name">${escapeHtml(restaurant.name)}</h3>
            </div>
            ${restaurant.rating ? `<div class="rating-badge">⭐ ${rating}</div>` : ''}
        </div>
        
        <div class="card-info">
            <div class="info-row">
                <span class="info-icon">📍</span>
                <span>${escapeHtml(address)}</span>
            </div>
            
            <div class="info-row">
                <span class="info-icon">📞</span>
                <span>${escapeHtml(phone)}</span>
            </div>
            
            <div class="info-row">
                <span class="info-icon">💬</span>
                <span>${reviews} reviews</span>
            </div>
            
            <div class="info-row">
                <span class="info-icon">💰</span>
                <span>${escapeHtml(priceLevel)}</span>
            </div>
            
            <div class="info-row">
                <span class="cuisine-tag">${escapeHtml(cuisine)}</span>
            </div>
        </div>
        
        <div class="card-footer">
            <a href="${mapsUrl}" target="_blank" class="card-btn">
                🗺️ View on Maps
            </a>
            ${restaurant.website ? `
                <a href="${escapeHtml(restaurant.website)}" target="_blank" class="card-btn">
                    🌐 Website
                </a>
            ` : ''}
        </div>
    `;

    return card;
}

// Export to CSV
function exportToCSV() {
    if (filteredRestaurants.length === 0) {
        alert('No restaurants to export!');
        return;
    }

    const headers = ['Name', 'Rating', 'Reviews', 'Address', 'Phone', 'Cuisine', 'Price Level', 'Website', 'Latitude', 'Longitude'];

    const csvContent = [
        headers.join(','),
        ...filteredRestaurants.map(r => [
            `"${(r.name || '').replace(/"/g, '""')}"`,
            r.rating || '',
            r.reviews || '',
            `"${(r.address || '').replace(/"/g, '""')}"`,
            `"${(r.phone || '').replace(/"/g, '""')}"`,
            `"${(r.cuisine || '').replace(/"/g, '""')}"`,
            `"${(r.price_level || '').replace(/"/g, '""')}"`,
            `"${(r.website || '').replace(/"/g, '""')}"`,
            r.latitude || '',
            r.longitude || ''
        ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `amsterdam-restaurants-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Utility Functions
function showLoading() {
    loadingState.style.display = 'block';
    restaurantsGrid.style.display = 'none';
    emptyState.style.display = 'none';
}

function hideLoading() {
    loadingState.style.display = 'none';
    restaurantsGrid.style.display = 'grid';
}

function showEmpty() {
    emptyState.style.display = 'block';
    restaurantsGrid.style.display = 'none';
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================================
// FARMS FUNCTIONALITY
// ============================================================

// Farms State
let allFarms = [];
let filteredFarms = [];
let farmsStats = {};
let farmsMap;
let farmsGeoJsonLayer;

// Farms DOM Elements
const farmsGrid = document.getElementById('farmsGrid');
const farmsLoadingState = document.getElementById('farmsLoadingState');
const farmsEmptyState = document.getElementById('farmsEmptyState');
const farmsResultsCount = document.getElementById('farmsResultsCount');
const farmsSearchInput = document.getElementById('farmsSearchInput');
const farmTypeFilter = document.getElementById('farmTypeFilter');
const farmsMinRating = document.getElementById('farmsMinRating');
const farmsSortBy = document.getElementById('farmsSortBy');

// Initialize Farms Map
function initFarmsMap() {
    if (farmsMap) return; // Already initialized

    farmsMap = L.map('farmsMap').setView([52.2, 5.5], 7); // Centered on Netherlands

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '©OpenStreetMap, ©CartoDB',
        maxZoom: 19
    }).addTo(farmsMap);

    // Add a legend with green colors
    const legend = L.control({ position: 'bottomright' });
    legend.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'info legend');
        const grades = [0, 5, 10, 20, 50, 100, 200];
        const labels = [];
        let from, to;

        for (let i = 0; i < grades.length; i++) {
            from = grades[i];
            to = grades[i + 1];

            labels.push(
                '<i style="background:' + getFarmsColor(from + 1) + '"></i> ' +
                from + (to ? '&ndash;' + to : '+'));
        }

        div.innerHTML = '<h4>Farms by District</h4>' + labels.join('<br>');
        return div;
    };
    legend.addTo(farmsMap);

    loadFarmsMapData();
}

// Get Green Color for Farms based on count (darker green = more farms)
function getFarmsColor(d) {
    return d > 200 ? '#00441b' :  // Very dark green
        d > 100 ? '#006d2c' :      // Dark green
            d > 50 ? '#238b45' :    // Medium-dark green
                d > 20 ? '#41ab5d' : // Medium green
                    d > 10 ? '#74c476' : // Light-medium green
                        d > 5 ? '#a1d99b' :  // Light green
                            d > 0 ? '#c7e9c0' :  // Very light green
                                '#f7fcf5';        // Almost white green
}

// Style Farms Feature
function styleFarmsFeature(feature) {
    return {
        fillColor: getFarmsColor(feature.properties.count),
        weight: 1,
        opacity: 1,
        color: '#2d5016',  // Dark green border
        fillOpacity: 0.7
    };
}

// Load Farms Map Data
async function loadFarmsMapData() {
    try {
        const response = await fetch(`${API_BASE}/api/farms/map-data`);
        const data = await response.json();
        renderFarmsMapData(data);
    } catch (error) {
        console.error('Error loading farms map data:', error);
    }
}

// Render Farms Map Data
function renderFarmsMapData(data) {
    if (farmsGeoJsonLayer) {
        farmsMap.removeLayer(farmsGeoJsonLayer);
    }

    farmsGeoJsonLayer = L.geoJSON(data, {
        style: styleFarmsFeature,
        onEachFeature: onEachFarmsFeature
    }).addTo(farmsMap);
}

// Interaction handlers for farms map
function onEachFarmsFeature(feature, layer) {
    layer.on({
        mouseover: highlightFarmsFeature,
        mouseout: resetFarmsHighlight,
        click: zoomToFeature
    });
}

function highlightFarmsFeature(e) {
    const layer = e.target;
    const props = layer.feature.properties;

    layer.setStyle({
        weight: 3,
        color: '#fff',
        fillOpacity: 0.9
    });

    const pc4 = props.pc4 || 'Unknown';
    const neighborhood = getNeighborhoodName(pc4);
    const count = props.count || 0;
    const avgRating = props.avg_rating || 0;
    const topTypes = props.top_types || [];

    const popupContent = `
        <div style="min-width: 200px;">
            <h3 style="margin: 0 0 10px 0; color: #41ab5d;">${neighborhood}</h3>
            <p style="margin: 5px 0;"><strong>Postal Code:</strong> ${pc4}</p>
            <p style="margin: 5px 0;"><strong>Farms:</strong> ${count}</p>
            <p style="margin: 5px 0;"><strong>Avg Rating:</strong> ${avgRating ? avgRating.toFixed(1) : 'N/A'}⭐</p>
            ${topTypes.length > 0 ? `<p style="margin: 5px 0;"><strong>Top Types:</strong> ${topTypes.join(', ')}</p>` : ''}
        </div>
    `;

    layer.bindPopup(popupContent).openPopup();
}

function resetFarmsHighlight(e) {
    farmsGeoJsonLayer.resetStyle(e.target);
}

// Load Farms Statistics
async function loadFarmsStats() {
    try {
        const response = await fetch(`${API_BASE}/api/farms/stats`);
        farmsStats = await response.json();
        console.log('Farms stats loaded:', farmsStats);

        // Update display if we're on the farms view
        const farmsView = document.getElementById('farms-view');
        if (farmsView && farmsView.classList.contains('active')) {
            updateStatsDisplay('farms');
        }
    } catch (error) {
        console.error('Error loading farms stats:', error);
    }
}

// Load Farms
async function loadFarms() {
    console.log('loadFarms() called');
    showFarmsLoading();

    try {
        const response = await fetch(`${API_BASE}/api/farms`);
        const data = await response.json();
        console.log('Farms data received:', data);

        allFarms = data.farms;
        filteredFarms = allFarms;
        console.log('allFarms set to:', allFarms.length, 'farms');

        // Populate farm type filter
        populateFarmTypeFilter();

        renderFarms();
        hideFarmsLoading();
    } catch (error) {
        console.error('Error loading farms:', error);
        hideFarmsLoading();
        showFarmsEmpty();
    }
}

// Populate Farm Type Filter
function populateFarmTypeFilter() {
    const types = new Set();
    allFarms.forEach(farm => {
        if (farm.cuisine) {
            types.add(farm.cuisine);
        }
    });

    const sortedTypes = Array.from(types).sort();

    // Clear existing options except "All Types"
    farmTypeFilter.innerHTML = '<option value="">All Types</option>';

    // Add farm types
    sortedTypes.forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        farmTypeFilter.appendChild(option);
    });

    console.log('Populated', sortedTypes.length, 'farm types');
}

// Apply Farms Filters
async function applyFarmsFilters() {
    const search = farmsSearchInput.value.trim();
    const farmType = farmTypeFilter.value;
    const rating = farmsMinRating.value;
    const sort = farmsSortBy.value;

    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (farmType) params.append('type', farmType);
    if (rating) params.append('min_rating', rating);
    if (sort) params.append('sort', sort);

    showFarmsLoading();

    try {
        const response = await fetch(`${API_BASE}/api/farms?${params.toString()}`);
        const data = await response.json();

        filteredFarms = data.farms;
        renderFarms();
        hideFarmsLoading();
    } catch (error) {
        console.error('Error applying farms filters:', error);
        hideFarmsLoading();
    }
}

// Reset Farms Filters
function resetFarmsFilters() {
    farmsSearchInput.value = '';
    farmTypeFilter.value = '';
    farmsMinRating.value = '';
    farmsSortBy.value = 'rating';
    applyFarmsFilters();
}

// Render Farms
function renderFarms() {
    farmsResultsCount.textContent = filteredFarms.length;

    if (filteredFarms.length === 0) {
        showFarmsEmpty();
        return;
    }

    farmsGrid.innerHTML = '';
    farmsEmptyState.style.display = 'none';

    filteredFarms.forEach(farm => {
        const card = createFarmCard(farm);
        farmsGrid.appendChild(card);
    });
}

// Create Farm Card
function createFarmCard(farm) {
    const card = document.createElement('div');
    card.className = 'restaurant-card';

    const rating = farm.rating ? farm.rating.toFixed(1) : 'N/A';
    const reviews = farm.reviews ? formatNumber(farm.reviews) : '0';
    const address = farm.address || 'Address not available';
    const phone = farm.phone || 'Phone not available';
    const farmType = farm.cuisine || 'Type not specified';

    // Create Google Maps link
    const mapsUrl = farm.latitude && farm.longitude
        ? `https://www.google.com/maps/search/?api=1&query=${farm.latitude},${farm.longitude}`
        : `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(farm.name + ' Amsterdam')}`;

    card.innerHTML = `
        <div class="card-header">
            <div>
                <h3 class="restaurant-name">${escapeHtml(farm.name)}</h3>
            </div>
            ${farm.rating ? `<div class="rating-badge">⭐ ${rating}</div>` : ''}
        </div>
        
        <div class="card-info">
            <div class="info-row">
                <span class="info-icon">📍</span>
                <span>${escapeHtml(address)}</span>
            </div>
            
            <div class="info-row">
                <span class="info-icon">📞</span>
                <span>${escapeHtml(phone)}</span>
            </div>
            
            <div class="info-row">
                <span class="info-icon">💬</span>
                <span>${reviews} reviews</span>
            </div>
            
            <div class="info-row">
                <span class="cuisine-tag">🌾 ${escapeHtml(farmType)}</span>
            </div>
        </div>
        
        <div class="card-footer">
            <a href="${mapsUrl}" target="_blank" class="card-btn">
                🗺️ View on Maps
            </a>
            ${farm.website ? `
                <a href="${escapeHtml(farm.website)}" target="_blank" class="card-btn">
                    🌐 Website
                </a>
            ` : ''}
        </div>
    `;

    return card;
}

// Export Farms to CSV
function exportFarmsToCSV() {
    if (filteredFarms.length === 0) {
        alert('No farms to export!');
        return;
    }

    const headers = ['Name', 'Rating', 'Reviews', 'Address', 'Phone', 'Type', 'Website', 'Latitude', 'Longitude'];

    const csvContent = [
        headers.join(','),
        ...filteredFarms.map(f => [
            `"${(f.name || '').replace(/"/g, '""')}"`,
            f.rating || '',
            f.reviews || '',
            `"${(f.address || '').replace(/"/g, '""')}"`,
            `"${(f.phone || '').replace(/"/g, '""')}"`,
            `"${(f.cuisine || '').replace(/"/g, '""')}"`,
            `"${(f.website || '').replace(/"/g, '""')}"`,
            f.latitude || '',
            f.longitude || ''
        ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', `amsterdam-farms-${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Reload Farms Data
async function reloadFarmsData() {
    const btn = document.getElementById('reloadFarmsData');
    const originalText = btn.textContent;
    btn.textContent = '🔄 Reloading...';
    btn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/farms/reload`, { method: 'POST' });
        const data = await response.json();

        await loadFarmsStats();
        await loadFarms();
        loadFarmsMapData();

        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = `Loaded ${data.total_farms} farms!`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);

    } catch (error) {
        console.error('Error reloading farms data:', error);
        alert('Failed to reload farms data');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Farms Utility Functions
function showFarmsLoading() {
    farmsLoadingState.style.display = 'block';
    farmsGrid.style.display = 'none';
    farmsEmptyState.style.display = 'none';
}

function hideFarmsLoading() {
    farmsLoadingState.style.display = 'none';
    farmsGrid.style.display = 'grid';
}

function showFarmsEmpty() {
    farmsEmptyState.style.display = 'block';
    farmsGrid.style.display = 'none';
}

// Setup Farms Event Listeners
function setupFarmsEventListeners() {
    document.getElementById('applyFarmsFilters')?.addEventListener('click', applyFarmsFilters);
    document.getElementById('resetFarmsFilters')?.addEventListener('click', resetFarmsFilters);
    document.getElementById('exportFarmsData')?.addEventListener('click', exportFarmsToCSV);
    document.getElementById('reloadFarmsData')?.addEventListener('click', reloadFarmsData);

    // Enter key support
    farmsSearchInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') applyFarmsFilters();
    });
}

// Initialize farms when tab is activated
document.addEventListener('DOMContentLoaded', () => {
    setupFarmsEventListeners();
});
