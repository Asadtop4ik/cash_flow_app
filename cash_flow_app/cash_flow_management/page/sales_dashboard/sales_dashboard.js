// cash_flow_app/cash_flow_management/page/sales_dashboard/sales_dashboard.js

frappe.pages['sales-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales Dashboard',
        single_column: true
    });

    // Initialize Dashboard
    new SalesDashboard(page);
};

class SalesDashboard {
    constructor(page) {
        this.page = page;
        this.wrapper = this.page.main;
        this.charts = {};
        this.data = {};

        // Create HTML structure
        this.createHTML();

        // Load Chart.js
        this.loadChartJS().then(() => {
            this.setup();
        });
    }

    createHTML() {
        const html = `
            <style>
                /* Reset & Base */
                * {
                    box-sizing: border-box;
                }

                .sales-dashboard-container {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    padding: 0;
                    margin: 0;
                    background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1729 100%);
                    overflow-y: auto;
                    overflow-x: hidden;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                }

                .dashboard-grid {
                    display: grid;
                    grid-template-columns: repeat(24, 1fr);
                    grid-auto-rows: minmax(60px, auto);
                    gap: 15px;
                    padding: 20px;
                    min-height: 100vh;
                }

                /* Widget Base Style */
                .widget {
                    background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(45, 55, 72, 0.9) 100%);
                    border-radius: 16px;
                    padding: 20px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4),
                                inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    position: relative;
                    overflow: hidden;
                    transition: all 0.3s ease;
                }

                .widget:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5),
                                0 0 40px rgba(99, 102, 241, 0.2);
                }

                .widget::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(90deg,
                        #6366f1 0%,
                        #8b5cf6 25%,
                        #d946ef 50%,
                        #00ffff 75%,
                        #00ff88 100%);
                    opacity: 0.6;
                }

                /* Loading State */
                .dashboard-loading {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
                    z-index: 9999;
                    color: #00ffff;
                }

                /* Header Widget */
                .widget-header {
                    grid-column: 1 / 25;
                    grid-row: 1 / 3;
                    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 25px 30px;
                }

                .widget-header::before {
                    background: none;
                }

                .header-left h1 {
                    font-size: 32px;
                    font-weight: 900;
                    margin: 0;
                    color: white;
                    text-shadow: 0 0 30px rgba(255, 255, 255, 0.4);
                }

                .header-left p {
                    margin: 5px 0 0 0;
                    opacity: 0.95;
                    font-size: 14px;
                }

                .header-right {
                    text-align: right;
                }

                .refresh-btn {
                    background: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    color: white;
                    padding: 10px 24px;
                    border-radius: 10px;
                    font-weight: 700;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    backdrop-filter: blur(10px);
                }

                .refresh-btn:hover {
                    background: rgba(255, 255, 255, 0.3);
                    transform: translateY(-2px);
                }

                /* KPI Widgets */
                .widget-kpi {
                    grid-row: span 2;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                }

                .kpi-icon {
                    width: 60px;
                    height: 60px;
                    border-radius: 16px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 28px;
                    margin-bottom: 15px;
                    position: relative;
                }

                .kpi-icon::after {
                    content: '';
                    position: absolute;
                    inset: -2px;
                    border-radius: 16px;
                    padding: 2px;
                    background: linear-gradient(135deg, currentColor, transparent);
                    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
                    -webkit-mask-composite: xor;
                    mask-composite: exclude;
                    opacity: 0.5;
                }

                .kpi-title {
                    font-size: 11px;
                    color: #94a3b8;
                    text-transform: uppercase;
                    letter-spacing: 1.2px;
                    margin: 0 0 8px 0;
                    font-weight: 600;
                }

                .kpi-value {
                    font-size: 28px;
                    font-weight: 900;
                    color: #ffffff;
                    margin: 0;
                    text-shadow: 0 0 20px currentColor;
                }

                .kpi-trend {
                    display: inline-block;
                    margin-top: 8px;
                    padding: 4px 10px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 700;
                }

                .kpi-trend.up {
                    background: rgba(0, 255, 136, 0.15);
                    color: #00ff88;
                }

                .kpi-trend.down {
                    background: rgba(255, 68, 102, 0.15);
                    color: #ff4466;
                }

                /* Color Variants */
                .kpi-cyan { color: #00ffff; }
                .kpi-cyan .kpi-icon { background: rgba(0, 255, 255, 0.15); }

                .kpi-green { color: #00ff88; }
                .kpi-green .kpi-icon { background: rgba(0, 255, 136, 0.15); }

                .kpi-purple { color: #a78bfa; }
                .kpi-purple .kpi-icon { background: rgba(167, 139, 250, 0.15); }

                .kpi-orange { color: #ff6b00; }
                .kpi-orange .kpi-icon { background: rgba(255, 107, 0, 0.15); }

                /* Chart Widgets */
                .widget-chart {
                    padding: 25px;
                }

                .chart-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                }

                .chart-title {
                    font-size: 16px;
                    font-weight: 700;
                    color: #ffffff;
                    margin: 0;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }

                .chart-title i {
                    color: #00ffff;
                    filter: drop-shadow(0 0 10px #00ffff);
                }

                .chart-body {
                    position: relative;
                }

                /* Donut Center */
                .donut-center {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    text-align: center;
                    pointer-events: none;
                }

                .donut-center h3 {
                    font-size: 36px;
                    font-weight: 900;
                    margin: 0;
                    color: #ffffff;
                    text-shadow: 0 0 20px #00ffff;
                }

                .donut-center p {
                    font-size: 12px;
                    color: #94a3b8;
                    margin: 5px 0 0 0;
                    text-transform: uppercase;
                }

                /* Progress Bars */
                .progress-item {
                    margin-bottom: 15px;
                }

                .progress-label {
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 8px;
                    font-size: 13px;
                }

                .progress-label-name {
                    color: #e2e8f0;
                    font-weight: 600;
                }

                .progress-label-value {
                    color: #00ffff;
                    font-weight: 700;
                }

                .progress-bar-container {
                    height: 8px;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 10px;
                    overflow: hidden;
                    position: relative;
                }

                .progress-bar {
                    height: 100%;
                    border-radius: 10px;
                    background: linear-gradient(90deg, #6366f1, #8b5cf6);
                    box-shadow: 0 0 10px currentColor;
                    transition: width 1s ease;
                    position: relative;
                }

                .progress-bar::after {
                    content: '';
                    position: absolute;
                    top: 0;
                    right: 0;
                    bottom: 0;
                    width: 30%;
                    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3));
                    animation: shimmer 2s infinite;
                }

                @keyframes shimmer {
                    0% { transform: translateX(-100%); }
                    100% { transform: translateX(100%); }
                }

                /* List Items */
                .list-item {
                    padding: 12px 15px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    background: rgba(0, 0, 0, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    transition: all 0.3s ease;
                }

                .list-item:hover {
                    background: rgba(0, 0, 0, 0.3);
                    border-color: rgba(0, 255, 255, 0.3);
                    transform: translateX(5px);
                }

                .list-item-name {
                    color: #e2e8f0;
                    font-weight: 600;
                    font-size: 13px;
                }

                .list-item-value {
                    color: #00ffff;
                    font-weight: 700;
                    font-size: 14px;
                }

                /* Mini Stats */
                .mini-stat {
                    text-align: center;
                    padding: 15px 10px;
                    border-radius: 10px;
                    background: rgba(0, 0, 0, 0.2);
                    margin-bottom: 10px;
                }

                .mini-stat-value {
                    font-size: 24px;
                    font-weight: 900;
                    color: #ffffff;
                    margin: 0;
                    text-shadow: 0 0 15px currentColor;
                }

                .mini-stat-label {
                    font-size: 11px;
                    color: #94a3b8;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    margin: 5px 0 0 0;
                }

                /* Table */
                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .data-table thead th {
                    background: rgba(0, 0, 0, 0.3);
                    color: #00ffff;
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    padding: 12px 10px;
                    text-align: left;
                    font-weight: 700;
                    border-bottom: 2px solid rgba(0, 255, 255, 0.3);
                }

                .data-table tbody tr {
                    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                    transition: all 0.3s ease;
                }

                .data-table tbody tr:hover {
                    background: rgba(0, 255, 255, 0.05);
                }

                .data-table tbody td {
                    padding: 10px;
                    font-size: 12px;
                    color: #cbd5e1;
                }

                .data-table tbody td a {
                    color: #00ffff;
                    text-decoration: none;
                    font-weight: 600;
                }

                .status-badge {
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 10px;
                    font-weight: 700;
                    text-transform: uppercase;
                    background: linear-gradient(135deg, #00ff88 0%, #00d4aa 100%);
                    color: #0a0e27;
                    display: inline-block;
                }

                /* Grid Positioning */
                .widget-earnings { grid-column: 1 / 5; }
                .widget-contracts { grid-column: 5 / 9; }
                .widget-paid { grid-column: 9 / 13; }
                .widget-outstanding { grid-column: 13 / 17; }
                .widget-monthly { grid-column: 17 / 21; }
                .widget-courses { grid-column: 21 / 25; }

                .widget-trends { grid-column: 1 / 13; grid-row: 3 / 7; }
                .widget-donut { grid-column: 13 / 17; grid-row: 3 / 7; }
                .widget-performance { grid-column: 17 / 25; grid-row: 3 / 7; }

                .widget-customers { grid-column: 1 / 9; grid-row: 7 / 11; }
                .widget-products { grid-column: 9 / 17; grid-row: 7 / 11; }
                .widget-team { grid-column: 17 / 25; grid-row: 7 / 11; }

                .widget-table { grid-column: 1 / 17; grid-row: 11 / 15; }
                .widget-stats { grid-column: 17 / 25; grid-row: 11 / 15; }

                /* Scrollbar */
                ::-webkit-scrollbar {
                    width: 8px;
                    height: 8px;
                }

                ::-webkit-scrollbar-track {
                    background: rgba(0, 0, 0, 0.2);
                }

                ::-webkit-scrollbar-thumb {
                    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                    border-radius: 4px;
                }

                /* Responsive */
                @media (max-width: 1600px) {
                    .dashboard-grid {
                        grid-template-columns: repeat(12, 1fr);
                    }
                    .widget-earnings, .widget-contracts, .widget-paid, .widget-outstanding { grid-column: span 3; }
                    .widget-monthly, .widget-courses { grid-column: span 3; }
                    .widget-trends { grid-column: 1 / 9; }
                    .widget-donut { grid-column: 9 / 13; }
                    .widget-performance { grid-column: 1 / 13; grid-row: 7 / 11; }
                    .widget-customers, .widget-products, .widget-team { grid-column: span 4; }
                    .widget-table { grid-column: 1 / 10; }
                    .widget-stats { grid-column: 10 / 13; }
                }
            </style>

            <div class="sales-dashboard-container">
                <div class="dashboard-loading" id="dashboardLoading">
                    <div class="spinner-border text-primary" role="status" style="width: 4rem; height: 4rem;"></div>
                    <p style="margin-top: 20px; font-size: 18px; font-weight: 600;">Ma'lumotlar yuklanmoqda...</p>
                </div>

                <div class="dashboard-grid" id="dashboardContent" style="display: none;">
                    <!-- Header -->
                    <div class="widget widget-header">
                        <div class="header-left">
                            <h1><i class="fa fa-chart-line"></i> Sales Dashboard</h1>
                            <p>Real-time biznes analitikasi va statistika</p>
                        </div>
                        <div class="header-right">
                            <button class="refresh-btn" id="refreshBtn">
                                <i class="fa fa-sync"></i> Yangilash
                            </button>
                            <p style="margin: 10px 0 0 0; font-size: 12px; opacity: 0.9;" id="lastUpdated">
                                Oxirgi: Hozir
                            </p>
                        </div>
                    </div>

                    <!-- KPI Cards -->
                    <div class="widget widget-kpi widget-earnings kpi-cyan">
                        <div class="kpi-icon"><i class="fa fa-dollar-sign"></i></div>
                        <h3 class="kpi-title">Total Earnings</h3>
                        <h2 class="kpi-value" id="totalEarnings">0</h2>
                        <span class="kpi-trend up" id="earningsTrend">+0%</span>
                    </div>

                    <div class="widget widget-kpi widget-contracts kpi-green">
                        <div class="kpi-icon"><i class="fa fa-file-contract"></i></div>
                        <h3 class="kpi-title">Shartnomalar</h3>
                        <h2 class="kpi-value" id="totalContracts">0</h2>
                        <p style="color: #94a3b8; font-size: 12px; margin-top: 8px;">Aktiv</p>
                    </div>

                    <div class="widget widget-kpi widget-paid kpi-purple">
                        <div class="kpi-icon"><i class="fa fa-check-circle"></i></div>
                        <h3 class="kpi-title">To'langan</h3>
                        <h2 class="kpi-value" id="totalPaid">0</h2>
                        <p style="color: #94a3b8; font-size: 12px; margin-top: 8px;" id="paidPercent">0%</p>
                    </div>

                    <div class="widget widget-kpi widget-outstanding kpi-orange">
                        <div class="kpi-icon"><i class="fa fa-clock"></i></div>
                        <h3 class="kpi-title">Kutilmoqda</h3>
                        <h2 class="kpi-value" id="outstanding">0</h2>
                        <p style="color: #94a3b8; font-size: 12px; margin-top: 8px;" id="unpaidPercent">0%</p>
                    </div>

                    <div class="widget widget-kpi widget-monthly kpi-purple">
                        <div class="kpi-icon"><i class="fa fa-calendar"></i></div>
                        <h3 class="kpi-title">Monthly</h3>
                        <h2 class="kpi-value" id="monthlyValue">Jan-Dec</h2>
                        <div style="display: flex; gap: 5px; flex-wrap: wrap; margin-top: 10px;" id="monthButtons"></div>
                    </div>

                    <div class="widget widget-kpi widget-courses kpi-cyan">
                        <div class="kpi-icon"><i class="fa fa-graduation-cap"></i></div>
                        <h3 class="kpi-title">Enrolled Courses</h3>
                        <h2 class="kpi-value" id="enrolledCourses">0</h2>
                        <p style="color: #94a3b8; font-size: 12px; margin-top: 8px;">Courses</p>
                    </div>

                    <!-- Main Trend Chart -->
                    <div class="widget widget-chart widget-trends">
                        <div class="chart-header">
                            <h4 class="chart-title"><i class="fa fa-chart-area"></i> Oylik Tendensiyalar</h4>
                        </div>
                        <div class="chart-body">
                            <canvas id="trendsChart" height="100"></canvas>
                        </div>
                    </div>

                    <!-- Donut Chart -->
                    <div class="widget widget-chart widget-donut">
                        <div class="chart-header">
                            <h4 class="chart-title"><i class="fa fa-chart-pie"></i> To'lov Statistikasi</h4>
                        </div>
                        <div class="chart-body">
                            <canvas id="donutChart" height="180"></canvas>
                            <div class="donut-center">
                                <h3 id="donutPercent">0%</h3>
                                <p>To'langan</p>
                            </div>
                        </div>
                    </div>

                    <!-- Performance Widget -->
                    <div class="widget widget-chart widget-performance">
                        <div class="chart-header">
                            <h4 class="chart-title"><i class="fa fa-chart-line"></i> Team Performance</h4>
                        </div>
                        <div class="chart-body" id="teamPerformance">
                            <!-- Will be populated -->
                        </div>
                    </div>

                    <!-- Top Customers -->
                    <div class="widget widget-chart widget-customers">
                        <div class="chart-header">
                            <h4 class="chart-title"><i class="fa fa-users"></i> Top Mijozlar</h4>
                        </div>
                        <div class="chart-body">
                            <canvas id="customersChart" height="120"></canvas>
                        </div>
                    </div>

                    <!-- Products -->
                    <div class="widget widget-chart widget-products">
                        <div class="chart-header">
                            <h4 class="chart-title"><i class="fa fa-box"></i> Top Mahsulotlar</h4>
                        </div>
                        <div class="chart-body">
                            <canvas id="productsChart" height="120"></canvas>
                        </div>
                    </div>

                    <!-- Team Stats -->
                    <div class="widget widget-chart widget-team">
                        <div class="chart-header">
                            <h4 class="chart-title"><i class="fa fa-user-friends"></i> Sales Team</h4>
                        </div>
                        <div class="chart-body" id="teamStats">
                            <!-- Will be populated -->
                        </div>
                    </div>

                    <!-- Recent Applications Table -->
                    <div class="widget widget-chart widget-table">
                        <div class="chart-header">
                            <h4 class="chart-title"><i class="fa fa-history"></i> So'nggi Shartnomalar</h4>
                        </div>
                        <div class="chart-body" style="overflow-x: auto;">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Mijoz</th>
                                        <th>Sana</th>
                                        <th>Summa</th>
                                        <th>Oylik</th>
                                        <th>Muddat</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody id="tableBody"></tbody>
                            </table>
                        </div>
                    </div>

                    <!-- Additional Stats -->
                    <div class="widget widget-chart widget-stats">
                        <div class="chart-header">
                            <h4 class="chart-title"><i class="fa fa-chart-bar"></i> Statistics</h4>
                        </div>
                        <div class="chart-body" id="additionalStats">
                            <!-- Will be populated -->
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.wrapper.html(html);
    }

    loadChartJS() {
        return new Promise((resolve) => {
            if (typeof Chart !== 'undefined') {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
            script.onload = resolve;
            document.head.appendChild(script);
        });
    }

    setup() {
        this.wrapper.find('#refreshBtn').on('click', () => this.loadData());
        this.loadData();
        setInterval(() => this.loadData(), 300000);
    }

    loadData() {
        this.wrapper.find('#dashboardLoading').show();
        this.wrapper.find('#dashboardContent').hide();

        frappe.call({
            method: 'cash_flow_app.cash_flow_management.api.dashboard.get_dashboard_data',
            callback: (r) => {
                if (r.message) {
                    this.data = r.message;
                    this.renderDashboard();
                    this.wrapper.find('#dashboardLoading').hide();
                    this.wrapper.find('#dashboardContent').css('display', 'grid');
                    this.updateLastRefreshTime();
                } else {
                    frappe.msgprint('Ma\'lumot topilmadi');
                    this.wrapper.find('#dashboardLoading').hide();
                }
            },
            error: (err) => {
                console.error('Dashboard Error:', err);
                frappe.msgprint('Xatolik: ' + (err.message || 'Unknown error'));
                this.wrapper.find('#dashboardLoading').hide();
            }
        });
    }

    renderDashboard() {
        this.renderKPICards();
        this.renderTrendsChart();
        this.renderDonutChart();
        this.renderCustomersChart();
        this.renderProductsChart();
        this.renderTeamPerformance();
        this.renderTeamStats();
        this.renderTable();
        this.renderAdditionalStats();
        this.renderMonthButtons();
    }

    renderKPICards() {
        const kpi = this.data.kpi || {};

        this.wrapper.find('#totalEarnings').text(this.formatCurrency(kpi.total_earnings || 0, true));
        this.wrapper.find('#totalContracts').text(kpi.total_contracts || 0);
        this.wrapper.find('#totalPaid').text(this.formatCurrency(kpi.total_paid || 0, true));
        this.wrapper.find('#outstanding').text(this.formatCurrency(kpi.outstanding_amount || 0, true));

        const growth = kpi.growth_percentage || 0;
        const trendEl = this.wrapper.find('#earningsTrend');
        trendEl.html('<i class="fa fa-arrow-' + (growth >= 0 ? 'up' : 'down') + '"></i> ' + Math.abs(growth) + '%');
        trendEl.toggleClass('up', growth >= 0).toggleClass('down', growth < 0);

        const paidPct = kpi.total_earnings > 0 ? ((kpi.total_paid / kpi.total_earnings) * 100).toFixed(1) : 0;
        this.wrapper.find('#paidPercent').text(paidPct + '%');
        this.wrapper.find('#unpaidPercent').text((100 - paidPct).toFixed(1) + '%');

        this.wrapper.find('#enrolledCourses').text(kpi.total_contracts || 0);
    }

    renderMonthButtons() {
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const container = this.wrapper.find('#monthButtons');
        container.empty();

        months.forEach(month => {
            container.append(`
                <div style="
                    padding: 4px 8px;
                    background: rgba(167, 139, 250, 0.2);
                    border: 1px solid rgba(167, 139, 250, 0.4);
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: 600;
                    color: #a78bfa;
                    cursor: pointer;
                ">${month}</div>
            `);
        });
    }

    renderTrendsChart() {
        const canvas = this.wrapper.find('#trendsChart')[0];
        if (!canvas) return;

        const data = this.data.monthly_trends || [];

        if (this.charts.trends) this.charts.trends.destroy();

        const ctx = canvas.getContext('2d');
        const gradient1 = ctx.createLinearGradient(0, 0, 0, 300);
        gradient1.addColorStop(0, 'rgba(139, 92, 246, 0.4)');
        gradient1.addColorStop(1, 'rgba(139, 92, 246, 0)');

        const gradient2 = ctx.createLinearGradient(0, 0, 0, 300);
        gradient2.addColorStop(0, 'rgba(0, 255, 136, 0.4)');
        gradient2.addColorStop(1, 'rgba(0, 255, 136, 0)');

        this.charts.trends = new Chart(canvas, {
            type: 'line',
            data: {
                labels: data.map(d => d.month),
                datasets: [{
                    label: 'Daromad',
                    data: data.map(d => d.revenue),
                    borderColor: '#8b5cf6',
                    backgroundColor: gradient1,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }, {
                    label: 'To\'lovlar',
                    data: data.map(d => d.payments),
                    borderColor: '#00ff88',
                    backgroundColor: gradient2,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#e2e8f0',
                            font: { size: 12, weight: '600' },
                            usePointStyle: true,
                            padding: 15
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#00ffff',
                        bodyColor: '#e2e8f0',
                        borderColor: 'rgba(0, 255, 255, 0.3)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                        ticks: { color: '#94a3b8', font: { size: 11 } }
                    },
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                        ticks: { color: '#94a3b8', font: { size: 11 } }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    renderDonutChart() {
        const canvas = this.wrapper.find('#donutChart')[0];
        if (!canvas) return;

        const stats = this.data.payment_statistics || {};

        if (this.charts.donut) this.charts.donut.destroy();

        this.wrapper.find('#donutPercent').text((stats.paid_percentage || 0) + '%');

        this.charts.donut = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['To\'langan', 'Kutilmoqda'],
                datasets: [{
                    data: [stats.paid || 50, stats.unpaid || 50],
                    backgroundColor: ['#00ff88', '#ff6b00'],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: '#e2e8f0',
                            font: { size: 12, weight: '600' },
                            padding: 12,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#00ffff',
                        bodyColor: '#e2e8f0',
                        padding: 12,
                        cornerRadius: 8
                    }
                }
            }
        });
    }

    renderCustomersChart() {
        const canvas = this.wrapper.find('#customersChart')[0];
        if (!canvas) return;

        const data = (this.data.top_customers || []).slice(0, 6);

        if (this.charts.customers) this.charts.customers.destroy();

        const colors = ['#00d4ff', '#6366f1', '#8b5cf6', '#d946ef', '#00ffff', '#00ff88'];

        this.charts.customers = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: data.map(d => d.customer_name),
                datasets: [{
                    data: data.map(d => d.total_value),
                    backgroundColor: colors,
                    borderWidth: 0,
                    borderRadius: 8
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#00ffff',
                        bodyColor: '#e2e8f0',
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#e2e8f0', font: { size: 11, weight: '600' } }
                    }
                }
            }
        });
    }

    renderProductsChart() {
        const canvas = this.wrapper.find('#productsChart')[0];
        if (!canvas) return;

        const data = (this.data.product_sales || []).slice(0, 6);

        if (this.charts.products) this.charts.products.destroy();

        const colors = ['#d946ef', '#8b5cf6', '#6366f1', '#00d4ff', '#00ffff', '#00ff88'];

        this.charts.products = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: data.map(d => d.item_name),
                datasets: [{
                    data: data.map(d => d.total_sales),
                    backgroundColor: colors,
                    borderWidth: 0,
                    borderRadius: 8
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#00ffff',
                        bodyColor: '#e2e8f0',
                        padding: 12,
                        cornerRadius: 8
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false },
                        ticks: { color: '#94a3b8', font: { size: 10 } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#e2e8f0', font: { size: 11, weight: '600' } }
                    }
                }
            }
        });
    }

    renderTeamPerformance() {
        const container = this.wrapper.find('#teamPerformance');
        container.empty();

        const teams = [
            { name: 'Hossam', value: 7.1, color: '#00ff88' },
            { name: 'Rovan', value: 5.7, color: '#6366f1' },
            { name: 'Beyablo', value: 3.5, color: '#d946ef' },
            { name: 'Haidy', value: 7.0, color: '#00d4ff' }
        ];

        teams.forEach(team => {
            const percent = (team.value / 10 * 100).toFixed(0);
            container.append(`
                <div class="progress-item">
                    <div class="progress-label">
                        <span class="progress-label-name">${team.name}</span>
                        <span class="progress-label-value">${team.value}B</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar" style="width: ${percent}%; background: ${team.color};"></div>
                    </div>
                </div>
            `);
        });
    }

    renderTeamStats() {
        const container = this.wrapper.find('#teamStats');
        container.empty();

        const customers = this.data.top_customers || [];

        customers.slice(0, 6).forEach(customer => {
            container.append(`
                <div class="list-item">
                    <span class="list-item-name">${customer.customer_name}</span>
                    <span class="list-item-value">${this.formatCurrency(customer.total_value, true)}</span>
                </div>
            `);
        });
    }

    renderTable() {
        const tbody = this.wrapper.find('#tableBody');
        tbody.empty();

        const data = (this.data.recent_applications || []).slice(0, 8);

        data.forEach(app => {
            tbody.append(`
                <tr>
                    <td><a href="/app/installment-application/${app.name}">${app.name}</a></td>
                    <td>${app.customer_name}</td>
                    <td>${app.transaction_date || '-'}</td>
                    <td><strong>${this.formatCurrency(app.total_amount, true)}</strong></td>
                    <td>${this.formatCurrency(app.monthly_payment, true)}</td>
                    <td>${app.installment_months} oy</td>
                    <td><span class="status-badge">${app.status}</span></td>
                </tr>
            `);
        });
    }

    renderAdditionalStats() {
        const container = this.wrapper.find('#additionalStats');
        container.empty();

        const kpi = this.data.kpi || {};

        const stats = [
            { label: 'Total Calls', value: '1,557', icon: 'phone' },
            { label: 'Avg Response', value: '2.2', icon: 'clock' },
            { label: 'Conversion', value: '34%', icon: 'chart-line' },
            { label: 'Satisfaction', value: '4.8', icon: 'star' }
        ];

        stats.forEach(stat => {
            container.append(`
                <div class="mini-stat" style="color: #00ffff;">
                    <h3 class="mini-stat-value"><i class="fa fa-${stat.icon}"></i> ${stat.value}</h3>
                    <p class="mini-stat-label">${stat.label}</p>
                </div>
            `);
        });
    }

    formatCurrency(value, short = false) {
        if (!value) return '0';
        const num = parseFloat(value);
        if (short && num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
        if (short && num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (short && num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toLocaleString('uz-UZ');
    }

    updateLastRefreshTime() {
        const now = new Date();
        this.wrapper.find('#lastUpdated').text('Oxirgi: ' + now.toLocaleTimeString('uz-UZ'));
    }
}
