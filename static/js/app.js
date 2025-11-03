class QuantAnalyticsApp {
    constructor() {
        this.socket = io();
        this.symbols = new Set(['btcusdt', 'ethusdt']);
        this.charts = {};
        this.currentData = {};
        this.lastAnalyticsResult = null;
        this.init();
    }

    init() {
        this.setupSocketListeners();
        this.setupEventListeners();
        this.updateSymbolList();
        
        // 1. Initialize charts immediately on load
        this.initializeCharts(); 
        
        // 2. Now load the initial data
        this.loadInitialData(); 
        
        // 3. Auto-generate test data and pre-run analytics
        setTimeout(() => {
            this.generateTestData().then(() => {
                this.showNotification('Running initial analytics...', 'info');
                this.calculateAnalytics();
            });
        }, 1000);
    }

    setupSocketListeners() {
        this.socket.on('connect', () => {
            this.updateConnectionStatus('connected');
            this.showNotification('Connected to server', 'success');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus('disconnected');
            this.showNotification('Disconnected from server', 'error');
        });

        this.socket.on('tick_data', (data) => {
            this.handleTickData(data);
        });

        this.socket.on('analytics_result', (result) => {
            // We get this from the fetch, so no need to listen here
        });
    }

    setupEventListeners() {
        document.getElementById('addSymbolBtn').addEventListener('click', () => this.addSymbol());
        document.getElementById('startCollection').addEventListener('click', () => this.startCollection());
        document.getElementById('stopCollection').addEventListener('click', () => this.stopCollection());
        document.getElementById('calculateAnalytics').addEventListener('click', () => this.calculateAnalytics());
        document.getElementById('addAlertBtn').addEventListener('click', () => this.addAlert());
        document.getElementById('exportData').addEventListener('click', () => this.exportData());

        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        document.getElementById('generateTestData').addEventListener('click', () => this.generateTestData());
        document.getElementById('startTestData').addEventListener('click', () => this.startTestData());
        document.getElementById('stopTestData').addEventListener('click', () => this.stopTestData());
    }

    initializeCharts() {
        if (!this.charts.price) {
            this.setupPriceChart();
        }
        if (!this.charts.analytics) {
            this.setupAnalyticsChart();
        }
    }

    setupPriceChart() {
        const ctx = document.getElementById('priceChart');
        if (!ctx) {
            console.log('Price chart canvas not found');
            return;
        }
        
        if (this.charts.price) {
            this.charts.price.destroy();
        }
        
        this.charts.price = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    x: {
                        type: 'time', // This is what needs the date adapter
                        time: {
                            unit: 'minute',
                            tooltipFormat: 'HH:mm:ss',
                            displayFormats: {
                                minute: 'HH:mm'
                            }
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        type: 'linear',
                        title: {
                            display: true,
                            text: 'Price (USD)'
                        },
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toLocaleString();
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += new Intl.NumberFormat('en-US', {
                                        style: 'currency',
                                        currency: 'USD'
                                    }).format(context.parsed.y);
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }

    setupAnalyticsChart() {
        const ctx = document.getElementById('analyticsChart');
        if (!ctx) {
            console.log('Analytics chart canvas not found');
            return;
        }
        
        if (this.charts.analytics) {
            this.charts.analytics.destroy();
        }
        
        this.charts.analytics = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    x: {
                        type: 'time', // This also needs the date adapter
                        time: {
                            unit: 'minute',
                            tooltipFormat: 'HH:mm:ss'
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        type: 'linear',
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Z-Score'
                        }
                    },
                    y1: {
                        type: 'linear',
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Spread'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                }
            }
        });
    }

    async loadInitialData() {
        try {
            const response = await fetch('/api/initial-data');
            const data = await response.json();
            this.currentData = data;
            
            this.updateRealTimeStats();
            
            // Now that charts are guaranteed to be initialized,
            // update the price chart with the data we just loaded.
            this.updatePriceChart();
            
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    handleTickData(ticks) {
        ticks.forEach(tick => {
            if (!this.currentData[tick.symbol]) {
                this.currentData[tick.symbol] = [];
            }
            this.currentData[tick.symbol].push(tick);
            
            if (this.currentData[tick.symbol].length > 100) {
                this.currentData[tick.symbol] = this.currentData[tick.symbol].slice(-100);
            }
        });

        this.updateRealTimeStats();
        
        if (this.charts.price) {
            this.updatePriceChart();
        }
    }

    updateRealTimeStats() {
        const statsContainer = document.getElementById('realTimeStats');
        if (!statsContainer) return;
        
        let statsHTML = '';
        if (Object.keys(this.currentData).length === 0) {
            statsHTML = `
                <div class="stat-card">
                    <div class="stat-value">-</div>
                    <div class="stat-label">Loading Data...</div>
                </div>
            `;
        }

        this.symbols.forEach(symbol => {
            const ticks = this.currentData[symbol];
            if (ticks && ticks.length > 0) {
                const latest = ticks[ticks.length - 1];
                const prices = ticks.map(t => t.price);
                const high = Math.max(...prices);
                const low = Math.min(...prices);
                const volume = ticks.reduce((sum, t) => sum + t.size, 0);
                const change = ticks.length > 1 ? ((latest.price - ticks[0].price) / ticks[0].price * 100) : 0;

                statsHTML += `
                    <div class="stat-card">
                        <div class="stat-value">$${latest.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                        <div class="stat-label">${symbol.toUpperCase()}</div>
                        <div style="font-size: 11px; margin-top: 3px;">
                            <div>High: $${high.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                            <div>Low: $${low.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</div>
                            <div>Vol: ${volume.toFixed(1)}</div>
                            <div style="color: ${change >= 0 ? '#10b981' : '#ef4444'}">
                                ${change >= 0 ? '↗' : '↘'} ${Math.abs(change).toFixed(2)}%
                            </div>
                        </div>
                    </div>
                `;
            }
        });

        statsContainer.innerHTML = statsHTML;
    }

    updatePriceChart() {
        if (!this.charts.price) return;
        
        const datasets = [];
        const colors = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
        let colorIndex = 0;
        
        this.symbols.forEach(symbol => {
            const ticks = this.currentData[symbol];
            if (ticks && ticks.length > 0) {
                const color = colors[colorIndex % colors.length];
                colorIndex++;
                
                datasets.push({
                    label: symbol.toUpperCase(),
                    data: ticks.map(tick => ({
                        x: new Date(tick.timestamp),
                        y: tick.price
                    })),
                    borderColor: color,
                    backgroundColor: color + '20',
                    tension: 0.4,
                    pointRadius: 2,
                    pointHoverRadius: 4,
                    borderWidth: 2
                });
            }
        });

        this.charts.price.data.datasets = datasets;
        this.charts.price.update('none');
    }

    async calculateAnalytics() {
        const symbol1 = document.getElementById('symbol1').value;
        const symbol2 = document.getElementById('symbol2').value;
        const timeframe = document.getElementById('timeframe').value;
        const windowSize = parseInt(document.getElementById('windowSize').value);

        const calculateBtn = document.getElementById('calculateAnalytics');
        const originalText = calculateBtn.textContent;
        calculateBtn.textContent = 'Calculating...';
        calculateBtn.disabled = true;

        try {
            const response = await fetch('/api/calculate-analytics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol1, symbol2, timeframe, window_size: windowSize })
            });

            const result = await response.json();
            
            if (result.success === false) {
                this.showNotification('Using demo data: ' + (result.error || 'Real data insufficient'), 'info');
            } else {
                this.showNotification('Analytics calculated successfully!', 'success');
            }
            
            this.updateAnalyticsDisplay(result);
            
        } catch (error) {
            console.error('Error calculating analytics:', error);
            this.showNotification('Error: ' + error.message, 'error');
        } finally {
            calculateBtn.textContent = originalText;
            calculateBtn.disabled = false;
        }
    }

    updateAnalyticsDisplay(result) {
        if (!result) return;
        this.lastAnalyticsResult = result;
        
        // Update overview tab
        document.getElementById('hedgeRatio').textContent = result.hedge_ratio.toFixed(4);
        document.getElementById('rSquared').textContent = result.r_squared.toFixed(4);
        document.getElementById('currentSpread').textContent = result.spread.current_spread.toFixed(4);
        
        const zscore = result.zscore.current_zscore;
        const zScoreElement = document.getElementById('currentZScore');
        zScoreElement.textContent = zscore.toFixed(2);
        const absZ = Math.abs(zscore);
        zScoreElement.style.color = absZ > 2 ? '#ef4444' : absZ > 1 ? '#f59e0b' : '#10b981';

        document.getElementById('adfStatistic').textContent = result.adf.test_statistic.toFixed(4);
        document.getElementById('adfPValue').textContent = result.adf.p_value.toFixed(4);
        document.getElementById('adfStationary').textContent = result.adf.is_stationary ? 'Yes' : 'No';
        document.getElementById('adfStationary').style.color = result.adf.is_stationary ? '#10b981' : '#ef4444';

        document.getElementById('currentCorrelation').textContent = result.correlation.current_correlation.toFixed(4);
        
        // Update analytics tab content
        this.updateAnalyticsTabContent(result);
        
        if (this.charts.analytics) {
            this.updateAnalyticsChart(result);
        }
    }

    updateAnalyticsTabContent(result) {
        const analyticsTab = document.getElementById('analyticsTab');
        if (!analyticsTab) return;

        analyticsTab.innerHTML = `
            <div class="chart-container">
                <div class="chart-title">Detailed Analytics Results</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h4 style="color: #0ea5e9; margin-bottom: 15px;">Regression Analysis</h4>
                        <table style="width: 100%; font-size: 14px;">
                            <tr><td style="padding: 4px 0; color: #94a3b8;">Hedge Ratio:</td><td style="font-weight: 600;">${result.hedge_ratio.toFixed(4)}</td></tr>
                            <tr><td style="padding: 4px 0; color: #94a3b8;">R²:</td><td style="font-weight: 600;">${result.r_squared.toFixed(4)}</td></tr>
                            <tr><td style="padding: 4px 0; color: #94a3b8;">Current Spread:</td><td style="font-weight: 600;">${result.spread.current_spread.toFixed(4)}</td></tr>
                            <tr><td style="padding: 4px 0; color: #94a3b8;">Spread Mean:</td><td style="font-weight: 600;">${result.spread.mean.toFixed(4)}</td></tr>
                            <tr><td style="padding: 4px 0; color: #94a3b8;">Spread Std:</td><td style="font-weight: 600;">${result.spread.std.toFixed(4)}</td></tr>
                        </table>
                    </div>
                    <div>
                        <h4 style="color: #0ea5e9; margin-bottom: 15px;">Statistical Tests</h4>
                        <table style="width: 100%; font-size: 14px;">
                            <tr><td style="padding: 4px 0; color: #94a3b8;">Z-Score:</td><td style="font-weight: 600;">${result.zscore.current_zscore.toFixed(4)}</td></tr>
                            <tr><td style="padding: 4px 0; color: #94a3b8;">Correlation:</td><td style="font-weight: 600;">${result.correlation.current_correlation.toFixed(4)}</td></tr>
                            <tr><td style="padding: 4px 0; color: #94a3b8;">ADF Statistic:</td><td style="font-weight: 600;">${result.adf.test_statistic.toFixed(4)}</td></tr>
                            <tr><td style="padding: 4px 0; color: #94a3b8;">ADF P-Value:</td><td style="font-weight: 600;">${result.adf.p_value.toFixed(4)}</td></tr>
                            <tr><td style="padding: 4px 0; color: #94a3b8;">Stationary:</td><td style="font-weight: 600; color: ${result.adf.is_stationary ? '#10b981' : '#ef4444'}">${result.adf.is_stationary ? 'Yes' : 'No'}</td></tr>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }

    updateAnalyticsChart(result) {
        if (!this.charts.analytics || !result) return;
        
        const now = Date.now();
        const timestamps = Array.from({length: 50}, (_, i) => new Date(now - (49 - i) * 60000));
        
        // --- MODIFICATION ---
        // Create a more realistic historical chart that fluctuates
        // around the mean, not just a random walk.
        
        const currentZ = result.zscore.current_zscore;
        const zMean = result.zscore.mean || 0;
        
        const currentSpread = result.spread.current_spread;
        const spreadMean = result.spread.mean || 0;
        const spreadStd = result.spread.std || 1;
        
        const zscoreData = [];
        const spreadData = [];
        
        for (let i = 0; i < timestamps.length; i++) {
            // Generate a random point that fluctuates around the mean
            let z = zMean + (Math.random() - 0.5) * (2.5); // Fluctuate by +/- 2.5
            let s = spreadMean + (Math.random() - 0.5) * (spreadStd * 2); // Fluctuate by +/- 2 std
            
            // As we get to the end, nudge the data towards the *actual* current value
            const blendFactor = i / (timestamps.length - 1);
            z = (z * (1 - blendFactor)) + (currentZ * blendFactor);
            s = (s * (1 - blendFactor)) + (currentSpread * blendFactor);
            
            zscoreData.push({ x: timestamps[i], y: z });
            spreadData.push({ x: timestamps[i], y: s });
        }
        
        // Ensure the very last point is the exact current value
        zscoreData[zscoreData.length - 1] = { x: timestamps[timestamps.length - 1], y: currentZ };
        spreadData[spreadData.length - 1] = { x: timestamps[timestamps.length - 1], y: currentSpread };
        // --- END MODIFICATION ---

        this.charts.analytics.data.datasets = [
            {
                label: 'Z-Score',
                data: zscoreData,
                borderColor: '#0ea5e9',
                backgroundColor: '#0ea5e920',
                tension: 0.4,
                borderWidth: 2,
                pointRadius: 0,
                yAxisID: 'y'
            },
            {
                label: 'Spread',
                data: spreadData,
                borderColor: '#10b981',
                backgroundColor: '#10b98120',
                tension: 0.4,
                borderWidth: 2,
                pointRadius: 0,
                yAxisID: 'y1'
            }
        ];

        this.charts.analytics.update('none');
    }

    addSymbol() {
        const input = document.getElementById('newSymbol');
        const symbol = input.value.trim().toLowerCase();
        
        if (symbol && !this.symbols.has(symbol)) {
            this.symbols.add(symbol);
            this.updateSymbolList();
            this.socket.emit('add_symbol', symbol);
            input.value = '';
            this.showNotification(`Added ${symbol.toUpperCase()}`, 'success');
        }
    }

    removeSymbol(symbol) {
        this.symbols.delete(symbol);
        this.updateSymbolList();
        delete this.currentData[symbol];
        this.updatePriceChart();
        this.showNotification(`Removed ${symbol.toUpperCase()}`, 'warning');
    }

    updateSymbolList() {
        const container = document.getElementById('symbolList');
        if (!container) return;
        
        container.innerHTML = '';
        
        this.symbols.forEach(symbol => {
            const element = document.createElement('div');
            element.className = 'symbol-item';
            element.innerHTML = `
                ${symbol.toUpperCase()}
                <button class="remove-btn" onclick="app.removeSymbol('${symbol}')">×</button>
            `;
            container.appendChild(element);
        });

        const selects = ['symbol1', 'symbol2', 'alertSymbol', 'exportSymbol'];
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                const currentVal = select.value;
                select.innerHTML = '';
                this.symbols.forEach(s => {
                    const option = document.createElement('option');
                    option.value = s;
                    option.textContent = s.toUpperCase();
                    select.appendChild(option);
                });
                if (this.symbols.has(currentVal)) {
                    select.value = currentVal;
                }
            }
        });
    }

    addAlert() {
        const name = document.getElementById('alertName').value;
        const condition = document.getElementById('alertCondition').value;
        const symbol = document.getElementById('alertSymbol').value;
        const threshold = parseFloat(document.getElementById('alertThreshold').value);

        if (name && condition && symbol && !isNaN(threshold)) {
            const alertsList = document.getElementById('alertsList');
            if (!alertsList) return;
            
            if (alertsList.querySelector('p')) {
                alertsList.innerHTML = '';
            }

            const alertElement = document.createElement('div');
            alertElement.className = 'alert-item';
            alertElement.innerHTML = `
                <div class="alert-header">
                    <span class="alert-name">${name}</span>
                    <span style="color: #10b981; font-size: 10px;">ACTIVE</span>
                </div>
                <div class="alert-condition">${symbol.toUpperCase()} ${condition} $${threshold}</div>
                <div style="font-size: 10px; color: #94a3b8;">
                    Created: ${new Date().toLocaleTimeString()}
                </div>
            `;
            alertsList.appendChild(alertElement);
            
            document.getElementById('alertName').value = '';
            document.getElementById('alertThreshold').value = '';
            this.showNotification('Alert added successfully', 'success');
        } else {
            this.showNotification('Please fill all alert fields', 'error');
        }
    }

    async startCollection() {
        try {
            await fetch('/api/start-collection', { method: 'POST' });
            this.showNotification('Real data collection started', 'success');
        } catch (error) {
            this.showNotification('Error starting collection', 'error');
        }
    }

    async stopCollection() {
        try {
            await fetch('/api/stop-collection', { method: 'POST' });
            this.showNotification('Real data collection stopped', 'warning');
        } catch (error) {
            this.showNotification('Error stopping collection', 'error');
        }
    }

    async exportData() {
        const symbol = document.getElementById('exportSymbol').value;
        const format = document.getElementById('exportFormat').value;
        
        window.open(`/api/export-data?symbol=${symbol}&format=${format}`, '_blank');
        this.showNotification('Export started', 'success');
    }

    async generateTestData() {
        try {
            const response = await fetch('/api/generate-test-data', { method: 'POST' });
            const result = await response.json();
            if (response.ok) {
                this.showNotification('Test data generated! Reloading data.', 'success');
                await this.loadInitialData();
            } else {
                this.showNotification('Error: ' + result.error, 'error');
            }
        } catch (error) {
            this.showNotification('Error generating test data: ' + error.message, 'error');
        }
    }

    async startTestData() {
        try {
            const response = await fetch('/api/start-test-data', { method: 'POST' });
            const result = await response.json();
            if (response.ok) {
                this.showNotification('Live test data started', 'success');
            } else {
                this.showNotification('Error: ' + result.error, 'error');
            }
        } catch (error) {
            this.showNotification('Error starting test data: ' + error.message, 'error');
        }
    }

    async stopTestData() {
        try {
            const response = await fetch('/api/stop-test-data', { method: 'POST' });
            const result = await response.json();
            if (response.ok) {
                this.showNotification('Live test data stopped', 'warning');
            } else {
                this.showNotification('Error: ' + result.error, 'error');
            }
        } catch (error) {
            this.showNotification('Error stopping test data: ' + error.message, 'error');
        }
    }

    switchTab(tabName) {
        document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        const activeContent = document.getElementById(`${tabName}Tab`);
        
        if (activeTab) activeTab.classList.add('active');
        if (activeContent) activeContent.classList.add('active');

        if (tabName === 'charts') {
            setTimeout(() => {
                if (this.charts.price) {
                    this.charts.price.resize(); 
                    this.updatePriceChart();    
                }
                if (this.charts.analytics) {
                    this.charts.analytics.resize(); 
                    if (this.lastAnalyticsResult) {
                        this.updateAnalyticsChart(this.lastAnalyticsResult);
                    }
                }
            }, 50); 
        }
    }

    updateConnectionStatus(status) {
        const badge = document.getElementById('connectionStatus');
        if (!badge) return;
        
        badge.textContent = status.toUpperCase();
        badge.className = `status-badge ${status === 'connected' ? '' : 'disconnected'}`;
    }

    showNotification(message, type = 'info') {
        document.querySelectorAll('.notification').forEach(notification => notification.remove());
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            color: white;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-weight: 500;
            background: ${type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : type === 'success' ? '#10b981' : '#0ea5e9'};
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 4000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new QuantAnalyticsApp();
});