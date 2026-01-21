// F1 AI Strategy Platform - Professional Dashboard JavaScript

// Global state
let currentRaceData = null;
let availableRaces = [];
let whatIfState = {
    track_temperature: 1.0,
    pit_loss: 22.0,
    safety_car_probability: 0.0,
    deg_multiplier: 1.0,
    traffic_factor: 1.0,
};
let lastStrategyRecommendation = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    load2026Predictions();
});

// Initialize application
async function initializeApp() {
    try {
        await loadAvailableRaces();
    } catch (error) {
        console.error('Initialization error:', error);
        showNotification('Failed to load race data', 'error');
    }
}

// Setup event listeners
function setupEventListeners() {
    const yearSelect = document.getElementById('yearSelect');
    const raceSelect = document.getElementById('raceSelect');
    const loadRaceBtn = document.getElementById('loadRaceBtn');
    const runWhatIfBtn = document.getElementById('runWhatIfBtn');
    const compareDriversBtn = document.getElementById('compareDriversBtn');

    yearSelect.addEventListener('change', onYearChange);
    raceSelect.addEventListener('change', onRaceChange);
    loadRaceBtn.addEventListener('click', loadRaceAnalysis);
    runWhatIfBtn.addEventListener('click', (e) => {
        console.log('[BUTTON_CLICK] RUN WHAT-IF button clicked');
        runWhatIfSimulation(false);
    });
    compareDriversBtn.addEventListener('click', compareDrivers);

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => switchTab(e.target.dataset.tab));
    });

    setupWhatIfControls();
}

// Load available races from API
async function loadAvailableRaces() {
    try {
        const response = await fetch('/api/races');
        availableRaces = await response.json();
        
        populateYearSelect();
    } catch (error) {
        console.error('Error loading races:', error);
        throw error;
    }
}

// Bind what-if sliders and value labels
function setupWhatIfControls() {
    bindRangeControl('trackTempInput', 'trackTempValue', (v) => `${Number(v).toFixed(2)}x`, (v) => {
        whatIfState.track_temperature = Number(v);
    });
    bindRangeControl('pitLossInput', 'pitLossValue', (v) => `${Number(v).toFixed(1)}s`, (v) => {
        whatIfState.pit_loss = Number(v);
    });
    bindRangeControl('safetyCarInput', 'safetyCarValue', (v) => `${Math.round(Number(v) * 100)}%`, (v) => {
        whatIfState.safety_car_probability = Number(v);
    });
    bindRangeControl('degMultiplierInput', 'degMultiplierValue', (v) => `${Number(v).toFixed(2)}x`, (v) => {
        whatIfState.deg_multiplier = Number(v);
    });
    bindRangeControl('trafficInput', 'trafficValue', (v) => `${Number(v).toFixed(2)}x`, (v) => {
        whatIfState.traffic_factor = Number(v);
    });
}

function bindRangeControl(inputId, labelId, formatter, onChange) {
    const input = document.getElementById(inputId);
    const label = document.getElementById(labelId);
    if (!input || !label) return;

    const update = () => {
        label.textContent = formatter(input.value);
        if (onChange) onChange(input.value);
    };

    input.addEventListener('input', update);
    update();
}

// Populate year dropdown
function populateYearSelect() {
    const yearSelect = document.getElementById('yearSelect');
    const years = [...new Set(availableRaces.map(r => r.year))].sort((a, b) => b - a);
    
    yearSelect.innerHTML = '<option value="">Select Season</option>';
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearSelect.appendChild(option);
    });
}

// Handle year selection change
function onYearChange(event) {
    const year = event.target.value;
    const raceSelect = document.getElementById('raceSelect');
    const loadRaceBtn = document.getElementById('loadRaceBtn');
    const runWhatIfBtn = document.getElementById('runWhatIfBtn');
    const compareDriversBtn = document.getElementById('compareDriversBtn');
    
    if (!year) {
        raceSelect.innerHTML = '<option value="">Select season first</option>';
        loadRaceBtn.disabled = true;
        runWhatIfBtn.disabled = true;
        compareDriversBtn.disabled = true;
        return;
    }
    
    const racesForYear = availableRaces.filter(r => r.year === year);
    
    raceSelect.innerHTML = '<option value="">Select Grand Prix</option>';
    racesForYear.forEach(race => {
        const option = document.createElement('option');
        option.value = race.name.replace(/ /g, '_');
        option.textContent = race.name;
        option.dataset.year = race.year;
        raceSelect.appendChild(option);
    });
    
    loadRaceBtn.disabled = true;
}

// Handle race selection change
function onRaceChange(event) {
    const loadRaceBtn = document.getElementById('loadRaceBtn');
    const runWhatIfBtn = document.getElementById('runWhatIfBtn');
    const compareDriversBtn = document.getElementById('compareDriversBtn');
    const enabled = Boolean(event.target.value);
    loadRaceBtn.disabled = !enabled;
    runWhatIfBtn.disabled = !enabled;
    compareDriversBtn.disabled = !enabled;
}

// Load and analyze selected race
async function loadRaceAnalysis() {
    const yearSelect = document.getElementById('yearSelect');
    const raceSelect = document.getElementById('raceSelect');
    
    const year = yearSelect.value;
    const gpName = raceSelect.value;
    
    if (!year || !gpName) return;
    
    showLoading(true);
    
    try {
        // Load race data
        await loadRaceData(year, gpName);
        document.getElementById('runWhatIfBtn').disabled = false;
        document.getElementById('compareDriversBtn').disabled = false;
        populateDriverSelects(currentRaceData.drivers);
        
        // Load all analyses (don't fail if one fails)
        const results = await Promise.allSettled([
            loadTyreDegradation(year, gpName),
            loadPitStrategy(year, gpName),
            loadLapTimeModel(year, gpName)
        ]);

        // Run additional analyses that depend on base data
        await runWhatIfSimulation(true);
        loadRaceOutcomes(year, gpName);
        
        // Check if any succeeded
        const anySucceeded = results.some(r => r.status === 'fulfilled');
        
        if (anySucceeded) {
            // Show analysis sections
            document.getElementById('raceOverview').classList.remove('hidden');
            document.getElementById('analysisSection').classList.remove('hidden');
            
            const failedCount = results.filter(r => r.status === 'rejected').length;
            if (failedCount > 0) {
                showNotification(`Race loaded! (${failedCount} analysis partially unavailable)`, 'warning');
            } else {
                showNotification('Race analysis complete!', 'success');
            }
        } else {
            showNotification('Race data loaded but analysis failed', 'warning');
        }
    } catch (error) {
        console.error('Error loading race analysis:', error);
        showNotification('Failed to analyze race data', 'error');
    } finally {
        showLoading(false);
    }
}

// Load race data and update stats
async function loadRaceData(year, gpName) {
    const response = await fetch(`/api/race/${year}/${gpName}`);
    const data = await response.json();
    
    if (data.error) throw new Error(data.error);
    
    currentRaceData = data;
    updateRaceStats(data);
}

// Update race statistics cards
function updateRaceStats(data) {
    document.getElementById('totalLaps').textContent = data.total_laps.toLocaleString();
    document.getElementById('fastestLap').textContent = formatTime(data.fastest_lap.time);
    document.getElementById('fastestDriver').textContent = data.fastest_lap.driver;
    document.getElementById('driverCount').textContent = data.drivers.length;
    document.getElementById('compoundCount').textContent = data.compounds.length;
}

function populateDriverSelects(drivers) {
    const driverA = document.getElementById('driverASelect');
    const driverB = document.getElementById('driverBSelect');
    driverA.innerHTML = '';
    driverB.innerHTML = '';
    drivers.forEach((drv, idx) => {
        const optA = document.createElement('option');
        optA.value = drv;
        optA.textContent = drv;
        driverA.appendChild(optA);

        const optB = document.createElement('option');
        optB.value = drv;
        optB.textContent = drv;
        driverB.appendChild(optB.cloneNode(true));
    });
    // Default selections
    if (drivers.length >= 2) {
        driverA.value = drivers[0];
        driverB.value = drivers[1];
    }
}

// Load tyre degradation analysis
async function loadTyreDegradation(year, gpName) {
    const response = await fetch(`/api/tyre-degradation/${year}/${gpName}`);
    const data = await response.json();
    
    if (data.error) {
        console.error('Tyre degradation error:', data.error);
        renderNoDataMessage('tyreDegradationChart', 'Tyre degradation data not available for this race');
        return;
    }
    
    if (Object.keys(data).length === 0) {
        renderNoDataMessage('tyreDegradationChart', 'No tyre degradation data found');
        return;
    }
    
    renderTyreDegradationChart(data);
}

// Render "no data" message
function renderNoDataMessage(elementId, message) {
    const element = document.getElementById(elementId);
    element.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #A0A0A0; font-size: 1.1rem;">${message}</div>`;
}

// Render tyre degradation chart with Plotly
function renderTyreDegradationChart(data) {
    const traces = [];
    const compoundColors = {
        'SOFT': '#FF0000',
        'MEDIUM': '#FFD700',
        'HARD': '#FFFFFF',
        'INTERMEDIATE': '#00FF00',
        'WET': '#0000FF'
    };
    
    Object.entries(data).forEach(([compound, values]) => {
        traces.push({
            x: values.x,
            y: values.y,
            mode: 'lines',
            name: compound,
            line: {
                color: compoundColors[compound] || '#888888',
                width: 3
            }
        });
    });
    
    const layout = {
        title: {
            text: '',
            font: { color: '#E8E8E8' }
        },
        xaxis: {
            title: 'Tyre Life (Laps)',
            color: '#E8E8E8',
            gridcolor: '#38383F'
        },
        yaxis: {
            title: 'Lap Time Increase (seconds)',
            color: '#E8E8E8',
            gridcolor: '#38383F'
        },
        paper_bgcolor: '#1C1C28',
        plot_bgcolor: '#1C1C28',
        font: { color: '#E8E8E8' },
        showlegend: true,
        legend: {
            font: { color: '#E8E8E8' },
            bgcolor: 'rgba(46, 46, 58, 0.8)'
        }
    };
    
    Plotly.newPlot('tyreDegradationChart', traces, layout, {
        responsive: true,
        displayModeBar: false
    });
}

// Load pit strategy optimization
async function loadPitStrategy(year, gpName) {
    const response = await fetch(`/api/pit-strategy/${year}/${gpName}`);
    const data = await response.json();
    
    if (data.error) {
        console.error('Pit strategy error:', data.error);
        document.getElementById('strategyDetails').innerHTML = 
            `<p class="loading-text" style="color: #FF6B6B;">Strategy optimization unavailable: ${data.error}</p>`;
        renderNoDataMessage('raceSimChart', 'Strategy simulation not available');
        return;
    }
    
    renderStrategyDetails(data);
    renderRaceSimulation(data);
}

// Run advanced strategy simulation with what-if inputs
async function runWhatIfSimulation(silent = false) {
    if (!currentRaceData) {
        console.warn('[RUN_WHATIF] No race data loaded');
        return;
    }
    const year = document.getElementById('yearSelect').value;
    const gpName = document.getElementById('raceSelect').value;
    if (!year || !gpName) {
        console.warn('[RUN_WHATIF] Missing year or gpName', {year, gpName});
        return;
    }

    console.log('[RUN_WHATIF] Starting simulation', {year, gpName, whatIfState});
    
    const payload = {
        track_temperature: whatIfState.track_temperature,
        pit_loss: whatIfState.pit_loss,
        safety_car_probability: whatIfState.safety_car_probability,
        deg_multiplier: whatIfState.deg_multiplier,
        traffic_factor: whatIfState.traffic_factor,
    };

    try {
        const url = `/api/strategy/simulate/${year}/${gpName}`;
        console.log('[RUN_WHATIF] POST to', url, payload);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        console.log('[RUN_WHATIF] Response status:', response.status);
        
        const data = await response.json();
        if (data.error) {
            console.error('[RUN_WHATIF] Error in response:', data.error);
            throw new Error(data.error);
        }

        console.log('[RUN_WHATIF] Got', data.strategies.length, 'strategies and recommendation');
        renderStrategyTable(data.strategies);
        renderAIVerdict(data.recommendation);
        renderStrategyExplain(data.recommendation);
        lastStrategyRecommendation = data.recommendation;

        // Auto-switch to Pit Strategy tab to show results
        console.log('[RUN_WHATIF] Switching to Pit Strategy tab');
        switchTab('strategy');

        if (!silent) {
            showNotification('What-if simulation updated');
        }
    } catch (error) {
        console.error('[RUN_WHATIF] Error:', error);
        if (!silent) showNotification('Failed to run simulation', 'error');
    }
}

// Render strategy details
function renderStrategyDetails(data) {
    const container = document.getElementById('strategyDetails');
    
    const html = `
        <div class="strategy-item">
            <span class="strategy-label">Number of Stops</span>
            <span class="strategy-value">${data.num_stops}</span>
        </div>
        <div class="strategy-item">
            <span class="strategy-label">Pit Laps</span>
            <span class="strategy-value">${data.pit_laps.join(', ')}</span>
        </div>
        <div class="strategy-item">
            <span class="strategy-label">Compounds</span>
            <span class="strategy-value">${data.compounds.join(' → ')}</span>
        </div>
        <div class="strategy-item">
            <span class="strategy-label">Total Race Time</span>
            <span class="strategy-value">${formatTime(data.total_time)}</span>
        </div>
    `;
    
    container.innerHTML = html;
}

function renderStrategyTable(strategies = []) {
    console.log('[RENDER_TABLE] Called with', strategies.length, 'strategies');
    const container = document.getElementById('strategyTable');
    if (!container) {
        console.error('[RENDER_TABLE] Container strategyTable NOT FOUND');
        return;
    }

    if (!strategies || strategies.length === 0) {
        console.log('[RENDER_TABLE] No strategies, showing placeholder');
        container.innerHTML = '<p class="loading-text">No strategies evaluated yet.</p>';
        return;
    }

    console.log('[RENDER_TABLE] Rendering', strategies.length, 'strategies');
    const rows = strategies.map((s) => `
        <div class="strategy-row">
            <div>
                <div class="label">Label</div>
                <div class="value">${s.label || '-'} (${s.variant})</div>
            </div>
            <div>
                <div class="label">Stops</div>
                <div class="value">${s.pit_laps.length}</div>
            </div>
            <div>
                <div class="label">Pit Laps</div>
                <div class="value">${s.pit_laps.join(', ')}</div>
            </div>
            <div>
                <div class="label">Compounds</div>
                <div class="value">${s.compounds.join(' → ')}</div>
            </div>
            <div>
                <div class="label">Total</div>
                <div class="value">${formatTime(s.total_time)}</div>
            </div>
            <div>
                <div class="label">Gain vs Best</div>
                <div class="value">${s.time_gain !== null && s.time_gain !== undefined ? `${s.time_gain.toFixed(2)}s` : '—'}</div>
            </div>
        </div>
    `);

    console.log('[RENDER_TABLE] Rendered, HTML length:', rows.join('').length);
    container.innerHTML = rows.join('');
    console.log('[RENDER_TABLE] ✓ Complete');
}

function renderAIVerdict(recommendation) {
    console.log('[RENDER_VERDICT] Called, recommendation:', recommendation ? 'YES' : 'NULL');
    const container = document.getElementById('aiVerdict');
    if (!container) {
        console.error('[RENDER_VERDICT] Container aiVerdict NOT FOUND');
        return;
    }
    if (!recommendation || !recommendation.recommended) {
        console.log('[RENDER_VERDICT] No recommendation data');
        container.innerHTML = '<p class="loading-text">Run a simulation to get a verdict.</p>';
        return;
    }

    console.log('[RENDER_VERDICT] Rendering with compounds:', recommendation.recommended.compounds);

    const rec = recommendation.recommended;
    const explanationList = recommendation.explanation || [];
    const explainHtml = explanationList.map((item) => `<li>${item}</li>`).join('');

    container.innerHTML = `
        <div class="verdict-title">${rec.compounds.join(' → ')} (${rec.pit_laps.length} stops)</div>
        <div class="strategy-item">
            <span class="strategy-label">Pit Windows</span>
            <span class="strategy-value">${rec.optimal_windows.map(w => `${w[0]}-${w[1]}`).join(', ')}</span>
        </div>
        <div class="strategy-item">
            <span class="strategy-label">Total Time</span>
            <span class="strategy-value">${formatTime(rec.total_time)}</span>
        </div>
        <div class="strategy-item">
            <span class="strategy-label">Confidence</span>
            <span class="strategy-value">${(recommendation.confidence * 100).toFixed(1)}%</span>
        </div>
        <ul class="explain-list">${explainHtml}</ul>
    `;
    console.log('[RENDER_VERDICT] ✓ Complete');
}

function renderStrategyExplain(recommendation) {
    console.log('[RENDER_EXPLAIN] Called');
    const container = document.getElementById('strategyExplain');
    if (!container) {
        console.error('[RENDER_EXPLAIN] Container strategyExplain NOT FOUND');
        return;
    }
    if (!recommendation || !recommendation.explanation) {
        console.log('[RENDER_EXPLAIN] No explanation data');
        container.innerHTML = '<p class="loading-text">Run a strategy simulation to view rationale.</p>';
        return;
    }

    console.log('[RENDER_EXPLAIN] Rendering', recommendation.explanation.length, 'points');

    const listItems = recommendation.explanation.map((item) => `<li>${item}</li>`).join('');
    container.innerHTML = `
        <div class="metric-card">
            <div class="metric-label">Recommended</div>
            <div class="metric-value">${recommendation.recommended.compounds.join(' → ')} @ laps ${recommendation.recommended.pit_laps.join(', ')}</div>
        </div>
        <ul class="explain-list">${listItems}</ul>
    `;
}

async function loadExplainability(year, gpName) {
    try {
        const response = await fetch(`/api/explainability/${year}/${gpName}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        if (data.feature_importance) renderFeatureImportance(data.feature_importance);
        if (data.strategy_explanation) renderStrategyExplain(data.strategy_explanation);
    } catch (error) {
        console.error('Explainability error:', error);
    }
}

// Render race simulation chart
function renderRaceSimulation(data) {
    const trace = {
        x: Array.from({ length: data.lap_times.length }, (_, i) => i + 1),
        y: data.lap_times,
        mode: 'lines+markers',
        name: 'Lap Time',
        line: {
            color: '#E10600',
            width: 2
        },
        marker: {
            color: data.pit_laps.map((pitLap, i) => 
                data.lap_times.map((_, idx) => idx + 1).includes(pitLap) ? '#FFD700' : '#E10600'
            ),
            size: 6
        }
    };
    
    const layout = {
        xaxis: {
            title: 'Lap Number',
            color: '#E8E8E8',
            gridcolor: '#38383F'
        },
        yaxis: {
            title: 'Lap Time (seconds)',
            color: '#E8E8E8',
            gridcolor: '#38383F'
        },
        paper_bgcolor: '#1C1C28',
        plot_bgcolor: '#1C1C28',
        font: { color: '#E8E8E8' },
        showlegend: false
    };
    
    Plotly.newPlot('raceSimChart', [trace], layout, {
        responsive: true,
        displayModeBar: false
    });
}

// Load lap time model results
async function loadLapTimeModel(year, gpName) {
    const response = await fetch(`/api/lap-time-prediction/${year}/${gpName}`);
    const data = await response.json();
    
    if (data.error) {
        console.error('Lap time model error:', data.error);
        document.getElementById('lapTimeResults').innerHTML = 
            `<p class="loading-text" style="color: #FF6B6B;">Model training failed: ${data.error}</p>`;
        return;
    }
    
    renderModelResults(data);
    await loadLapTimeForecast(year, gpName);
    await loadExplainability(year, gpName);
}

// Render model results
function renderModelResults(data) {
    const container = document.getElementById('lapTimeResults');
    
    const html = `
        <div class="metric-card">
            <div>
                <div class="metric-label">Mean Absolute Error (MAE)</div>
                <div style="font-size: 0.85rem; color: #A0A0A0; margin-top: 0.25rem;">
                    Random Forest Regression Model
                </div>
            </div>
            <div class="metric-value">${data.mae.toFixed(3)}s</div>
        </div>
        <div class="metric-card" style="border-left-color: #1E90FF;">
            <div class="metric-label">Training Samples</div>
            <div class="metric-value" style="color: #1E90FF;">${data.num_samples.toLocaleString()}</div>
        </div>
        <div class="metric-card" style="border-left-color: #FFD700;">
            <div class="metric-label">Model Status</div>
            <div class="metric-value" style="color: #FFD700; font-size: 1.2rem;">✓ Trained</div>
        </div>
    `;
    
    container.innerHTML = html;
}

async function loadLapTimeForecast(year, gpName) {
    try {
        const payload = {
            horizon: 6,
            track_temperature: whatIfState.track_temperature,
            traffic_factor: whatIfState.traffic_factor,
        };
        const response = await fetch(`/api/lap-time-forecast/${year}/${gpName}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        renderLapTimeForecast(data);
        renderFeatureImportance(data.feature_importance);
    } catch (error) {
        console.error('Lap time forecast error:', error);
        document.getElementById('lapTimeForecast').innerHTML = '<p class="loading-text" style="color: #FF6B6B;">Forecast unavailable.</p>';
    }
}

function renderLapTimeForecast(data) {
    const container = document.getElementById('lapTimeForecast');
    if (!container) return;

    if (!data.forecast) {
        container.innerHTML = '<p class="loading-text">No forecast available.</p>';
        return;
    }

    const items = data.forecast.map((f) => `
        <div class="forecast-item">
            <div>
                <div class="label">Lap +${f.lap_ahead}</div>
                <div class="value">${formatTime(f.prediction)}</div>
            </div>
            <div style="text-align: right;">
                <div class="label">Confidence</div>
                <div class="value">${formatTime(f.lower)} - ${formatTime(f.upper)}</div>
            </div>
        </div>
    `);

    container.innerHTML = `
        <div class="metric-card">
            <div class="metric-label">Forecast Horizon</div>
            <div class="metric-value">${data.horizon} laps</div>
        </div>
        ${items.join('')}
    `;
}

function renderFeatureImportance(importances) {
    const container = document.getElementById('featureImportance');
    if (!container || !importances) return;
    const entries = Object.entries(importances)
        .sort((a, b) => b[1] - a[1])
        .map(([key, val]) => `
            <div class="forecast-item" style="border-left-color: #FFD700;">
                <div class="label">${key}</div>
                <div class="value">${(val * 100).toFixed(1)}%</div>
            </div>
        `);
    container.innerHTML = entries.join('');
}

// Load 2026 predictions
async function load2026Predictions() {
    try {
        const response = await fetch('/api/2026-predictions');
        const data = await response.json();
        
        if (data.error) throw new Error(data.error);
        
        renderTeamPredictions(data.teams);
        renderDegradationTrends(data.degradation_trends);
    } catch (error) {
        console.error('Error loading 2026 predictions:', error);
    }
}

// Render team predictions
function renderTeamPredictions(teams) {
    const container = document.getElementById('teamPredictions');
    
    let html = '';
    Object.entries(teams).forEach(([team, data]) => {
        html += `
            <div class="team-card">
                <div class="team-name">${team}</div>
                <div class="team-metric">
                    <span class="team-metric-label">Avg Pit Stops</span>
                    <span class="team-metric-value">${data.avg_pit_stops}</span>
                </div>
                <div class="team-metric">
                    <span class="team-metric-label">Preferred Compounds</span>
                    <span class="team-metric-value">${data.preferred_compounds.join(', ')}</span>
                </div>
                <div class="team-metric">
                    <span class="team-metric-label">Aggressive Score</span>
                    <span class="team-metric-value">${data.aggressive_score}/10</span>
                </div>
                <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #38383F; font-size: 0.85rem; color: #A0A0A0;">
                    ${data.reasoning}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// Render degradation trends
function renderDegradationTrends(trends) {
    const container = document.getElementById('degradationTrends');
    
    const compoundColors = {
        'SOFT': '#FF0000',
        'MEDIUM': '#FFD700',
        'HARD': '#FFFFFF',
        'INTERMEDIATE': '#00FF00',
        'WET': '#0000FF'
    };
    
    let html = '';
    Object.entries(trends).forEach(([compound, multiplier]) => {
        const percentage = ((multiplier - 1) * 100).toFixed(1);
        const color = compoundColors[compound] || '#888888';
        
        html += `
            <div class="compound-bar">
                <span class="compound-name" style="color: ${color};">${compound}</span>
                <span class="compound-value" style="color: ${color};">
                    ${multiplier.toFixed(2)}x 
                    <span style="font-size: 0.85rem; color: #A0A0A0;">
                        (${percentage > 0 ? '+' : ''}${percentage}%)
                    </span>
                </span>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function loadRaceOutcomes(year, gpName) {
    try {
        const response = await fetch(`/api/outcomes/${year}/${gpName}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        renderRaceOutcomes(data);
    } catch (error) {
        console.error('Outcome load error:', error);
    }
}

function renderRaceOutcomes(data) {
    const container = document.getElementById('raceOutcomes');
    if (!container) return;
    if (!data.win_probability) {
        container.innerHTML = '<p class="loading-text">Outcome simulation unavailable.</p>';
        return;
    }

    const winList = Object.entries(data.win_probability)
        .sort((a, b) => b[1] - a[1])
        .map(([drv, prob]) => {
            const reasons = data.explanation && data.explanation[drv] 
                ? data.explanation[drv].join(' • ') 
                : 'Monte Carlo simulation';
            
            // Color-code based on probability
            let barColor = '#1E90FF';  // Default blue
            if (prob > 0.4) barColor = '#FFD700';  // Gold for favorites
            else if (prob > 0.2) barColor = '#00D448';  // Green for contenders
            
            return `
                <div class="compound-bar" style="border-left: 3px solid ${barColor};">
                    <div>
                        <span class="compound-name">${drv}</span>
                        <div style="font-size: 0.75rem; color: #A0A0A0; margin-top: 0.25rem;">${reasons}</div>
                    </div>
                    <span class="compound-value" style="color: ${barColor};">${(prob * 100).toFixed(1)}%</span>
                </div>
            `;
        });

    const metadataHtml = data.metadata ? `
        <div style="font-size: 0.85rem; color: #A0A0A0; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid #38383F;">
            ${data.metadata.simulations?.toLocaleString() || '2000'} Monte Carlo simulations • 
            ${data.metadata.features_available || 0}/${data.metadata.total_drivers || 0} drivers with data
        </div>
    ` : '';

    container.innerHTML = `
        <div class="metric-card" style="border-left-color:#FFD700;">
            <div class="metric-label">Win Probabilities (Robust Monte Carlo)</div>
            <div style="font-size: 0.85rem; color: #A0A0A0; margin-top: 0.25rem;">
                Accounts for pace, pit stops, safety cars, traffic, and reliability
            </div>
        </div>
        ${winList.join('')}
        ${metadataHtml}
    `;
}

async function compareDrivers() {
    const year = document.getElementById('yearSelect').value;
    const gpName = document.getElementById('raceSelect').value;
    const driverA = document.getElementById('driverASelect').value;
    const driverB = document.getElementById('driverBSelect').value;
    if (!year || !gpName || !driverA || !driverB) return;

    try {
        const response = await fetch('/api/driver-comparison', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ year, gp_name: gpName, driver_a: driverA, driver_b: driverB })
        });
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        renderDriverComparison(data);
    } catch (error) {
        console.error('Driver comparison error:', error);
        showNotification('Driver comparison failed', 'error');
    }
}

function renderDriverComparison(data) {
    const container = document.getElementById('driverComparison');
    if (!container) return;
    if (!data.drivers) {
        container.innerHTML = '<p class="loading-text">No comparison data.</p>';
        return;
    }

    const [a, b] = Object.keys(data.drivers);
    const cards = Object.entries(data.drivers).map(([driver, stats]) => `
        <div class="driver-card">
            <div class="strategy-label">${driver}</div>
            <div class="strategy-value">Avg Pace: ${stats.average_pace ? formatTime(stats.average_pace) : '—'}</div>
            <div class="strategy-value">Stints: ${stats.stint_count}</div>
            <div class="strategy-value">Deg Slope: ${stats.degradation_slope ? stats.degradation_slope[0].toFixed(3) : '—'}</div>
        </div>
    `);

    const delta = data.pace_delta ? `${data.pace_delta.toFixed(3)}s` : '—';

    container.innerHTML = `
        <div class="forecast-item" style="border-left-color:#FFD700;">
            <div class="label">Pace Delta (A - B)</div>
            <div class="value">${delta}</div>
        </div>
        <div class="driver-comparison">${cards.join('')}</div>
    `;
}

// Tab switching
function switchTab(tabName) {
    console.log('[SWITCH_TAB] Switching to tab:', tabName);
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === tabName);
    });
    console.log('[SWITCH_TAB] ✓ Tab switched to', tabName);
}

// Utility: Show loading overlay
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.classList.toggle('hidden', !show);
}

// Utility: Format time in seconds to MM:SS.mmm
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(3);
    return mins > 0 ? `${mins}:${secs.padStart(6, '0')}` : `${secs}s`;
}

// Utility: Show notification (simple implementation)
function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // Could be enhanced with a toast notification system
}
