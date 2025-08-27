// Enhanced Sales Analytics JavaScript

class SalesAnalytics {
    constructor() {
        this.charts = {};
        this.refreshInterval = null;
        this.isInitialized = false;
        this.init();
    }

    init() {
        this.initializeCharts();
        this.setupEventListeners();
        this.startAutoRefresh();
        this.isInitialized = true;
    }

    initializeCharts() {
        // Initialize sales chart
        const salesCtx = document.getElementById('salesChart');
        if (salesCtx) {
            this.charts.sales = this.createSalesChart(salesCtx);
        }

        // Initialize orders chart
        const ordersCtx = document.getElementById('ordersChart');
        if (ordersCtx) {
            this.charts.orders = this.createOrdersChart(ordersCtx);
        }
    }

    createSalesChart(ctx) {
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Ventas ($)',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: this.getChartOptions('Evolución de Ventas')
        });
    }

    createOrdersChart(ctx) {
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Pedidos',
                    data: [],
                    backgroundColor: 'rgba(16, 185, 129, 0.8)',
                    borderColor: '#10b981',
                    borderWidth: 1,
                    borderRadius: 4,
                    borderSkipped: false
                }]
            },
            options: this.getChartOptions('Cantidad de Pedidos')
        });
    }

    getChartOptions(title) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    labels: {
                        color: '#f1f5f9',
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#f1f5f9',
                    borderColor: '#334155',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            if (context.dataset.label === 'Ventas ($)') {
                                return `Ventas: $${context.parsed.y.toLocaleString()}`;
                            }
                            return `${context.dataset.label}: ${context.parsed.y}`;
                        }
                    }
                },
                title: {
                    display: true,
                    text: title,
                    color: '#f1f5f9',
                    font: { size: 16, weight: '600' }
                }
            },
            scales: {
                x: {
                    grid: {
                        color: '#334155',
                        borderColor: '#334155'
                    },
                    ticks: { color: '#94a3b8' }
                },
                y: {
                    grid: {
                        color: '#334155',
                        borderColor: '#334155'
                    },
                    ticks: {
                        color: '#94a3b8',
                        callback: function(value) {
                            if (title.includes('Ventas')) {
                                return '$' + value.toLocaleString();
                            }
                            return value;
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart'
            }
        };
    }

    setupEventListeners() {
        // Chart filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleFilterClick(e));
        });

        // Analytics cards hover effects
        document.querySelectorAll('.analytics-card').forEach(card => {
            card.addEventListener('mouseenter', () => this.handleCardHover(card, true));
            card.addEventListener('mouseleave', () => this.handleCardHover(card, false));
        });

        // Order items hover effects
        document.querySelectorAll('.order-item').forEach(item => {
            item.addEventListener('mouseenter', () => this.handleOrderHover(item, true));
            item.addEventListener('mouseleave', () => this.handleOrderHover(item, false));
        });
    }

    handleFilterClick(e) {
        const btn = e.target;
        const period = btn.dataset.period;
        
        // Update active state
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Update charts
        this.updateChartsForPeriod(period);
    }

    handleCardHover(card, isHovering) {
        if (isHovering) {
            card.style.transform = 'translateY(-4px) scale(1.02)';
            card.style.boxShadow = '0 20px 40px rgba(0, 0, 0, 0.4)';
        } else {
            card.style.transform = 'translateY(0) scale(1)';
            card.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.3)';
        }
    }

    handleOrderHover(item, isHovering) {
        if (isHovering) {
            item.style.transform = 'translateX(8px)';
            item.style.borderLeft = '3px solid #3b82f6';
            item.style.background = 'rgba(59, 130, 246, 0.05)';
        } else {
            item.style.transform = 'translateX(0)';
            item.style.borderLeft = 'none';
            item.style.background = 'transparent';
        }
    }

    updateChartsForPeriod(period) {
        // Show loading state
        this.showLoadingState();
        
        // Simulate API call (replace with actual API call)
        setTimeout(() => {
            this.fetchChartData(period);
        }, 500);
    }

    async fetchChartData(period) {
        try {
            // Replace with actual API endpoint
            const response = await fetch(`/admin/api/sales-data/?period=${period}`);
            const data = await response.json();
            
            this.updateCharts(data);
        } catch (error) {
            console.error('Error fetching chart data:', error);
            // Fallback to demo data
            this.updateChartsWithDemoData(period);
        } finally {
            this.hideLoadingState();
        }
    }

    updateChartsWithDemoData(period) {
        // Generate demo data based on period
        const days = parseInt(period);
        const labels = [];
        const salesData = [];
        const ordersData = [];
        
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' }));
            
            // Generate realistic demo data
            salesData.push(Math.floor(Math.random() * 1000) + 100);
            ordersData.push(Math.floor(Math.random() * 20) + 1);
        }
        
        this.updateCharts({ labels, sales: salesData, orders: ordersData });
    }

    updateCharts(data) {
        if (this.charts.sales) {
            this.charts.sales.data.labels = data.labels;
            this.charts.sales.data.datasets[0].data = data.sales;
            this.charts.sales.update('active');
        }
        
        if (this.charts.orders) {
            this.charts.orders.data.labels = data.labels;
            this.charts.orders.data.datasets[0].data = data.orders;
            this.charts.orders.update('active');
        }
    }

    showLoadingState() {
        const containers = document.querySelectorAll('.chart-container');
        containers.forEach(container => {
            const overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = '<div class="loading-spinner"></div>';
            container.style.position = 'relative';
            container.appendChild(overlay);
        });
    }

    hideLoadingState() {
        const overlays = document.querySelectorAll('.loading-overlay');
        overlays.forEach(overlay => overlay.remove());
    }

    startAutoRefresh() {
        // Refresh data every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.refreshData();
        }, 300000);
    }

    async refreshData() {
        try {
            // Get current active period
            const activeBtn = document.querySelector('.filter-btn.active');
            const period = activeBtn ? activeBtn.dataset.period : '30';
            
            // Refresh data
            await this.fetchChartData(period);
            
            // Show refresh indicator
            this.showRefreshIndicator();
        } catch (error) {
            console.error('Error refreshing data:', error);
        }
    }

    showRefreshIndicator() {
        // Create or update refresh indicator
        let indicator = document.querySelector('.refresh-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'live-indicator refresh-indicator';
            indicator.innerHTML = `
                <div class="pulse-dot"></div>
                <span>Datos actualizados</span>
            `;
            
            const header = document.querySelector('.analytics-header');
            header.appendChild(indicator);
        }
        
        // Hide after 3 seconds
        setTimeout(() => {
            if (indicator) {
                indicator.remove();
            }
        }, 3000);
    }

    // Public method to destroy instance
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.destroy) {
                chart.destroy();
            }
        });
        
        this.isInitialized = false;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize sales analytics
    window.salesAnalytics = new SalesAnalytics();
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            switch(e.key) {
                case 'r':
                    e.preventDefault();
                    if (window.salesAnalytics) {
                        window.salesAnalytics.refreshData();
                    }
                    break;
                case '1':
                    e.preventDefault();
                    document.querySelector('[data-period="7"]')?.click();
                    break;
                case '2':
                    e.preventDefault();
                    document.querySelector('[data-period="30"]')?.click();
                    break;
                case '3':
                    e.preventDefault();
                    document.querySelector('[data-period="90"]')?.click();
                    break;
            }
        }
    });
    
    // Add help tooltip
    const helpTooltip = document.createElement('div');
    helpTooltip.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(15, 23, 42, 0.9);
        color: #f1f5f9;
        padding: 12px 16px;
        border-radius: 8px;
        font-size: 12px;
        border: 1px solid #334155;
        z-index: 1000;
        max-width: 300px;
    `;
    helpTooltip.innerHTML = `
        <strong>Atajos de teclado:</strong><br>
        Ctrl+R: Actualizar datos<br>
        Ctrl+1: 7 días<br>
        Ctrl+2: 30 días<br>
        Ctrl+3: 90 días
    `;
    
    // Hide tooltip after 10 seconds
    setTimeout(() => {
        helpTooltip.remove();
    }, 10000);
    
    document.body.appendChild(helpTooltip);
});

// Export for global access
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SalesAnalytics;
}

