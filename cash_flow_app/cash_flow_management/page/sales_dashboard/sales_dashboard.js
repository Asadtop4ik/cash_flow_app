// cash_flow_app/cash_flow_management/page/sales_dashboard/sales_dashboard.js

frappe.pages['sales-dashboard'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Sales Dashboard',
        single_column: true
    });

    new ModernSalesDashboard(page);
};

class ModernSalesDashboard {
    constructor(page) {
        this.page = page;
        this.wrapper = this.page.main;
        this.charts = {};
        this.data = {};
        this.selectedYears = this.getDefaultYears();

        this.createHTML();
        this.loadChartJS().then(() => {
            this.setup();
        });
    }

    getDefaultYears() {
        const currentYear = new Date().getFullYear();
        return [currentYear - 2, currentYear - 1, currentYear];
    }

    createHTML() {
        const html = `
            <style>
                /* ========== REMOVE FRAPPE DEFAULTS ========== */
                .page-wrapper,
                .page-content,
                .page-content .frappe-control,
                .page-card {
                    background: transparent !important;
                    padding: 0 !important;
                    margin: 0 !important;
                }

                .layout-main-section {
                    padding: 0 !important;
                }

                /* Full page dark background */
                body {
                    background: linear-gradient(135deg, #0a0e27 0%, #1a1134 50%, #0d1b2a 100%) !important;
                    overflow-x: hidden;
                }

                /* ========== NEON THEME + FIGMA LAYOUT ========== */
                * {
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }

                .dashboard-fullscreen {
                    background: linear-gradient(135deg, #0a0e27 0%, #1a1134 50%, #0d1b2a 100%);
                    padding: 20px;
                    min-height: 100vh;
                    width: 100%;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    margin-left: -15px;
                    margin-right: -15px;
                    margin-top: -15px;
                    padding-bottom: 50px;
                }

                /* Loading */
                .dashboard-loading {
                    position: fixed;
                    inset: 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #0a0e27 0%, #1a1134 100%);
                    z-index: 9999;
                    width: 100vw;
                    height: 100vh;
                    left: 0;
                    top: 0;
                }

                .loading-spinner {
                    width: 60px;
                    height: 60px;
                    border: 4px solid rgba(0, 255, 255, 0.2);
                    border-top-color: #00ffff;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    to { transform: rotate(360deg); }
                }

                .loading-text {
                    margin-top: 20px;
                    font-size: 18px;
                    color: #00ffff;
                    font-weight: 600;
                    text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
                }

                /* Year Filter - Below page title */
                .year-filter {
                    position: relative; /* Fixed emas, static */
                    background: linear-gradient(135deg, rgba(30, 41, 59, 0.98), rgba(45, 55, 72, 0.95));
                    border-radius: 12px;
                    padding: 15px 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(0, 255, 255, 0.4);
                    display: flex;
                    gap: 12px;
                    align-items: center;
                    justify-content: center;
                    border: 2px solid rgba(0, 255, 255, 0.4);
                    backdrop-filter: blur(10px);
                }

                .year-filter-label {
                    font-size: 13px;
                    font-weight: 700;
                    color: #00ffff;
                    text-transform: uppercase;
                    letter-spacing: 1.5px;
                    text-shadow: 0 0 10px rgba(0, 255, 255, 0.6);
                    margin-right: 15px;
                }

                .year-buttons-container {
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                    align-items: center;
                }

                .year-btn {
                    padding: 10px 18px;
                    border: 2px solid rgba(139, 92, 246, 0.6);
                    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8), rgba(45, 55, 72, 0.6));
                    color: #a78bfa;
                    border-radius: 10px;
                    cursor: pointer;
                    font-weight: 700;
                    font-size: 14px;
                    transition: all 0.3s ease;
                    min-width: 70px;
                    text-align: center;
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                }

                .year-btn:hover {
                    border-color: #00ffff;
                    background: linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(139, 92, 246, 0.2));
                    color: #00ffff;
                    transform: translateY(-3px);
                    box-shadow: 0 6px 20px rgba(0, 255, 255, 0.4);
                }

                .year-btn.active {
                    background: linear-gradient(135deg, #6366f1, #8b5cf6);
                    border-color: #00ffff;
                    color: white;
                    box-shadow: 0 6px 24px rgba(99, 102, 241, 0.6), 0 0 20px rgba(0, 255, 255, 0.5);
                    transform: translateY(-2px);
                }

                .year-btn.active::before {
                    content: '✓ ';
                    margin-right: 4px;
                }

                .year-selection-info {
                    font-size: 11px;
                    color: #94a3b8;
                    margin-left: 15px;
                    font-style: italic;
                }

                /* Top KPI Row - 7 cards */
                .kpi-row {
                    display: grid;
                    grid-template-columns: repeat(7, 1fr);
                    gap: 15px;
                    margin-bottom: 20px;
                    /* No padding-top needed - year filter is static now */
                }

                .kpi-card {
                    background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(45, 55, 72, 0.9));
                    border-radius: 16px;
                    padding: 25px 15px; /* More vertical padding */
                    text-align: center;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                    min-height: 120px; /* Ensure minimum height */
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                }

                .kpi-card::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(90deg, var(--card-color), transparent);
                }

                .kpi-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5);
                }

                .kpi-card.cyan { --card-color: #00ffff; }
                .kpi-card.green { --card-color: #00ff88; }
                .kpi-card.purple { --card-color: #a78bfa; }
                .kpi-card.orange { --card-color: #ff6b00; }
                .kpi-card.pink { --card-color: #d946ef; }

                .kpi-value {
                    font-size: 26px; /* Slightly smaller to fit better */
                    font-weight: 900;
                    color: var(--card-color);
                    margin-bottom: 10px;
                    text-shadow: 0 0 20px var(--card-color);
                    line-height: 1.2;
                }

                .kpi-label {
                    font-size: 11px;
                    color: #94a3b8;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    font-weight: 600;
                    line-height: 1.4;
                }

                /* Charts Grid - Figma Layout */
                .charts-grid {
                    display: grid;
                    grid-template-columns: repeat(12, 1fr);
                    grid-template-rows: repeat(6, 140px);
                    gap: 15px;
                }

                /* Chart positions matching Figma */
                .chart-1 {
                    grid-column: 1 / 7;
                    grid-row: 1 / 3;
                }

                .chart-2 {
                    grid-column: 1 / 7;
                    grid-row: 3 / 5;
                }

                .chart-3 {
                    grid-column: 1 / 4;
                    grid-row: 5 / 7;
                }

                .chart-4 {
                    grid-column: 4 / 7;
                    grid-row: 5 / 7;
                }

                .chart-5 {
                    grid-column: 7 / 10;
                    grid-row: 1 / 4;
                }

                .chart-6 {
                    grid-column: 10 / 13;
                    grid-row: 1 / 7;
                }

                .chart-container {
                    background: linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(45, 55, 72, 0.9));
                    border-radius: 16px;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
                    position: relative;
                }

                .chart-container::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: linear-gradient(90deg, #6366f1, #8b5cf6, #d946ef);
                    opacity: 0.6;
                }

                .chart-title {
                    font-size: 14px;
                    font-weight: 700;
                    color: #00ffff;
                    margin-bottom: 15px;
                    text-align: center;
                    text-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
                }

                .chart-body {
                    flex: 1;
                    position: relative;
                    min-height: 0;
                }

                .chart-body canvas {
                    width: 100% !important;
                    height: 100% !important;
                }

                /* Table Styles */
                .debt-table-wrapper {
                    overflow-y: auto;
                    max-height: 100%;
                }

                .debt-table {
                    width: 100%;
                    border-collapse: collapse;
                }

                .debt-table thead {
                    position: sticky;
                    top: 0;
                    background: rgba(0, 0, 0, 0.5);
                    backdrop-filter: blur(10px);
                    z-index: 10;
                }

                .debt-table th {
                    padding: 12px 10px;
                    text-align: left;
                    font-size: 11px;
                    color: #00ffff;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    border-bottom: 2px solid rgba(0, 255, 255, 0.3);
                }

                .debt-table td {
                    padding: 10px;
                    font-size: 12px;
                    color: #cbd5e1;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                }

                .debt-table tbody tr:hover {
                    background: rgba(0, 255, 255, 0.05);
                }

                .classification-badge {
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 8px;
                    font-size: 11px;
                    font-weight: 700;
                    text-transform: uppercase;
                }

                .classification-badge.class-a {
                    background: linear-gradient(135deg, #00ff88, #00d4aa);
                    color: #0a0e27;
                }

                .classification-badge.class-b {
                    background: linear-gradient(135deg, #6366f1, #8b5cf6);
                    color: white;
                }

                .classification-badge.class-c {
                    background: linear-gradient(135deg, #ff6b00, #ff8c42);
                    color: white;
                }

                .classification-badge.class-n-a {
                    background: rgba(148, 163, 184, 0.3);
                    color: #94a3b8;
                }

                /* Responsive */
                @media (max-width: 1600px) {
                    .kpi-row {
                        grid-template-columns: repeat(4, 1fr);
                    }

                    .charts-grid {
                        grid-template-columns: 1fr 1fr;
                        grid-template-rows: auto;
                    }

                    .chart-1, .chart-2, .chart-3, .chart-4, .chart-5, .chart-6 {
                        grid-column: auto;
                        grid-row: auto;
                        min-height: 300px;
                    }
                }

                @media (max-width: 768px) {
                    .kpi-row {
                        grid-template-columns: repeat(2, 1fr);
                    }

                    .charts-grid {
                        grid-template-columns: 1fr;
                    }

                    .year-filter {
                        flex-direction: column;
                        text-align: center;
                        padding: 15px;
                    }

                    .year-filter-label {
                        margin-right: 0;
                        margin-bottom: 10px;
                    }

                    .year-buttons-container {
                        justify-content: center;
                    }

                    .year-btn {
                        min-width: 65px;
                        padding: 8px 14px;
                        font-size: 13px;
                    }

                    .year-selection-info {
                        margin-left: 0;
                        margin-top: 8px;
                    }
                }
            </style>

            <!-- Loading -->
            <div class="dashboard-loading" id="dashboardLoading">
                <div class="loading-spinner"></div>
                <div class="loading-text">Ma'lumotlar yuklanmoqda...</div>
            </div>

            <!-- Main Content -->
            <div class="dashboard-fullscreen" id="dashboardContent" style="display: none;">
                <!-- Year Filter -->
                <div class="year-filter">
                    <span class="year-filter-label">📅 Yillarni tanlang</span>
                    <div class="year-buttons-container" id="yearButtons"></div>
                    <span class="year-selection-info" id="yearSelectionInfo">(3 tagacha tanlashingiz mumkin)</span>
                </div>

                <!-- KPI Cards -->
                <div class="kpi-row" id="kpiRow"></div>

                <!-- Charts Grid -->
                <div class="charts-grid">
                        <!-- Chart 1: Line Grapha Oylik Chiqim Summa Oyma oy -->
                        <div class="chart-container chart-1">
                            <div class="chart-title">Oylik Moliyaviy Tendensiyalar (Tikilgan Pul)</div>
                            <div class="chart-body">
                                <canvas id="chart1"></canvas>
                            </div>
                        </div>

                        <!-- Chart 2: Bar graph Klientlarda Kirim Bolgan Summa Oyma Oy -->
                        <div class="chart-container chart-2">
                            <div class="chart-title">Oylik Kirim (Klientlardan to'lovlar)</div>
                            <div class="chart-body">
                                <canvas id="chart2"></canvas>
                            </div>
                        </div>

                        <!-- Chart 3: Bar graph Shartnomalar soni oyma oy -->
                        <div class="chart-container chart-3">
                            <div class="chart-title">Oylik Shartnomalar Soni</div>
                            <div class="chart-body">
                                <canvas id="chart3"></canvas>
                            </div>
                        </div>

                        <!-- Chart 4: Pie Chart ROI ochun -->
                        <div class="chart-container chart-4">
                            <div class="chart-title">ROI Statistikasi</div>
                            <div class="chart-body">
                                <canvas id="chart4"></canvas>
                            </div>
                        </div>

                        <!-- Chart 5: Bar graph Oylik sof foyda -->
                        <div class="chart-container chart-5">
                            <div class="chart-title">Oylik Sof Foyda</div>
                            <div class="chart-body">
                                <canvas id="chart5"></canvas>
                            </div>
                        </div>

                        <!-- Chart 6: Spiska Qarzdor haqdorlarniki -->
                        <div class="chart-container chart-6">
                            <div class="chart-title">Klientlar Qarzdorligi</div>
                            <div class="chart-body">
                                <div class="debt-table-wrapper">
                                    <table class="debt-table">
                                        <thead>
                                            <tr>
                                                <th>Kategoriya</th>
                                                <th>Klient</th>
                                                <th>Qarz</th>
                                            </tr>
                                        </thead>
                                        <tbody id="debtTableBody"></tbody>
                                    </table>
                                </div>
                            </div>
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
        this.loadAvailableYears();
        this.loadData();
    }

    loadAvailableYears() {
        frappe.call({
            method: 'cash_flow_app.cash_flow_management.api.dashboard.get_available_years',
            callback: (r) => {
                if (r.message && r.message.length > 0) {
                    this.availableYears = r.message;
                } else {
                    this.availableYears = this.getDefaultYears();
                }
                this.renderYearFilter();
            }
        });
    }

    renderYearFilter() {
        const container = this.wrapper.find('#yearButtons');
        const infoSpan = this.wrapper.find('#yearSelectionInfo');
        container.empty();

        this.availableYears.forEach(year => {
            const isActive = this.selectedYears.includes(year);
            const btn = $(`<button class="year-btn ${isActive ? 'active' : ''}" data-year="${year}">${year}</button>`);
            btn.on('click', () => this.toggleYear(year));
            container.append(btn);
        });

        // Update info text
        const selectedCount = this.selectedYears.length;
        if (selectedCount === 3) {
            infoSpan.text('(Maksimum: 3/3 tanlangan)').css('color', '#ff6b00');
        } else {
            infoSpan.text(`(${selectedCount}/3 tanlangan)`).css('color', '#94a3b8');
        }
    }

    toggleYear(year) {
        const index = this.selectedYears.indexOf(year);

        if (index > -1) {
            if (this.selectedYears.length > 1) {
                this.selectedYears.splice(index, 1);
            } else {
                frappe.msgprint('Kamida bitta yil tanlanishi kerak');
                return;
            }
        } else {
            if (this.selectedYears.length < 3) {
                this.selectedYears.push(year);
                this.selectedYears.sort();
            } else {
                frappe.msgprint('Maksimum 3 ta yil tanlanishi mumkin');
                return;
            }
        }

        this.renderYearFilter();
        this.loadData();
    }

    loadData() {
        this.wrapper.find('#dashboardLoading').show();
        this.wrapper.find('#dashboardContent').hide();

        frappe.call({
            method: 'cash_flow_app.cash_flow_management.api.dashboard.get_dashboard_data',
            args: {
                year_filter: this.selectedYears
            },
            callback: (r) => {
                console.log('Dashboard Data:', r.message);
                if (r.message) {
                    this.data = r.message;
                    this.renderDashboard();
                    this.wrapper.find('#dashboardLoading').hide();
                    this.wrapper.find('#dashboardContent').show();
                } else {
                    frappe.msgprint('Ma\'lumot topilmadi');
                    this.wrapper.find('#dashboardLoading').hide();
                }
            },
            error: (err) => {
                console.error('Dashboard Error:', err);
                frappe.msgprint('Xatolik: ' + (err.message || 'Unknown'));
                this.wrapper.find('#dashboardLoading').hide();
            }
        });
    }

    renderDashboard() {
        this.renderKPICards();
        this.renderChart1();
        this.renderChart2();
        this.renderChart3();
        this.renderChart4();
        this.renderChart5();
        this.renderDebtTable();
    }

    renderKPICards() {
        const row = this.wrapper.find('#kpiRow');
        row.empty();

        const shareholders = this.data.shareholders || {};
        const debtSummary = this.data.debt_summary || {};
        const debtByClass = this.data.debt_by_classification || {};
        const contracts = this.data.active_contracts || {};

        console.log('KPI Data:', { shareholders, debtSummary, debtByClass, contracts });

        const cards = [
            {
                value: this.formatCurrency(shareholders.net_capital || 0),
                label: 'Tikilgan Pul',
                color: 'cyan'
            },
            {
                value: this.formatCurrency(debtSummary.total_debt || 0),
                label: 'Jami qarzdorlik',
                color: 'orange'
            },
            {
                value: this.formatCurrency(debtByClass.A?.debt || 0),
                label: 'Qarzdorlik A',
                color: 'green'
            },
            {
                value: this.formatCurrency(debtByClass.B?.debt || 0),
                label: 'Qarzdorlik B',
                color: 'purple'
            },
            {
                value: this.formatCurrency(debtByClass.C?.debt || 0),
                label: 'Qarzdorlik C',
                color: 'pink'
            },
            {
                value: contracts.active || 0,
                label: 'Aktiva Shartnoma',
                color: 'cyan'
            },
            {
                value: contracts.completed || 0,
                label: 'Yopilgan Shartnoma',
                color: 'green'
            }
        ];

        cards.forEach(card => {
            row.append(`
                <div class="kpi-card ${card.color}">
                    <div class="kpi-value">${card.value}</div>
                    <div class="kpi-label">${card.label}</div>
                </div>
            `);
        });
    }

    renderChart1() {
        const canvas = this.wrapper.find('#chart1')[0];
        if (!canvas) return;
        if (this.charts.chart1) this.charts.chart1.destroy();

        const data = this.data.monthly_finance || {};
        const datasets = [];
        const colors = ['#00ffff', '#8b5cf6', '#d946ef'];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);
            datasets.push({
                label: year,
                data: yearData,
                borderColor: colors[index],
                backgroundColor: `${colors[index]}20`,
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointHoverRadius: 6
            });
        });

        this.charts.chart1 = new Chart(canvas, {
            type: 'line',
            data: {
                labels: ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun', 'Iyul', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek'],
                datasets: datasets
            },
            options: this.getChartOptions()
        });
    }

    renderChart2() {
        const canvas = this.wrapper.find('#chart2')[0];
        if (!canvas) return;
        if (this.charts.chart2) this.charts.chart2.destroy();

        const data = this.data.monthly_revenue || {};
        const datasets = [];
        const colors = ['#00ff88', '#6366f1', '#ff6b00'];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);
            datasets.push({
                label: year,
                data: yearData,
                backgroundColor: colors[index],
                borderWidth: 0,
                borderRadius: 8
            });
        });

        this.charts.chart2 = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun', 'Iyul', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek'],
                datasets: datasets
            },
            options: this.getChartOptions()
        });
    }

    renderChart3() {
        const canvas = this.wrapper.find('#chart3')[0];
        if (!canvas) return;
        if (this.charts.chart3) this.charts.chart3.destroy();

        const data = this.data.monthly_contracts || {};
        const datasets = [];
        const colors = ['#a78bfa', '#00d4ff', '#d946ef'];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);
            datasets.push({
                label: year,
                data: yearData,
                backgroundColor: colors[index],
                borderWidth: 0,
                borderRadius: 8
            });
        });

        this.charts.chart3 = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun', 'Iyul', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek'],
                datasets: datasets
            },
            options: this.getChartOptions()
        });
    }

    renderChart4() {
        const canvas = this.wrapper.find('#chart4')[0];
        if (!canvas) return;
        if (this.charts.chart4) this.charts.chart4.destroy();

        const roiData = this.data.roi_data || {};

        this.charts.chart4 = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Foyda', 'Kapital'],
                datasets: [{
                    data: [roiData.total_interest || 0, roiData.total_finance || 0],
                    backgroundColor: ['#00ff88', '#6366f1'],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: '#e2e8f0',
                            font: { size: 11, weight: '600' },
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

    renderChart5() {
        const canvas = this.wrapper.find('#chart5')[0];
        if (!canvas) return;
        if (this.charts.chart5) this.charts.chart5.destroy();

        const data = this.data.monthly_profit || {};
        const datasets = [];
        const colors = ['#00ff88', '#d946ef', '#00d4ff'];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);
            datasets.push({
                label: year,
                data: yearData,
                backgroundColor: colors[index],
                borderWidth: 0,
                borderRadius: 8
            });
        });

        this.charts.chart5 = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun', 'Iyul', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek'],
                datasets: datasets
            },
            options: this.getChartOptions()
        });
    }

    renderDebtTable() {
        const tbody = this.wrapper.find('#debtTableBody');
        tbody.empty();

        const debtList = this.data.debt_list?.data || [];

        console.log('Debt List Data:', debtList);

        if (debtList.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="3" style="text-align: center; color: #94a3b8; padding: 30px;">
                        Ma'lumot topilmadi
                    </td>
                </tr>
            `);
            return;
        }

        debtList.forEach(item => {
            const classKey = (item.classification || 'N/A').toLowerCase().replace('/', '-').replace(' ', '-');
            tbody.append(`
                <tr>
                    <td><span class="classification-badge class-${classKey}">${item.classification}</span></td>
                    <td><strong>${item.customer_name}</strong></td>
                    <td style="font-weight: 700; color: #ff6b00;">${this.formatCurrency(item.debt)}</td>
                </tr>
            `);
        });
    }

    getChartOptions() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: '#e2e8f0',
                        font: { size: 11, weight: '600' },
                        usePointStyle: true,
                        padding: 12
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
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: { size: 10 }
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: { size: 10 }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        };
    }

    formatCurrency(value) {
        if (!value) return '$0';
        const num = parseFloat(value);

        if (num >= 1000000000) {
            return '$' + (num / 1000000000).toFixed(2) + 'B';
        }
        if (num >= 1000000) {
            return '$' + (num / 1000000).toFixed(2) + 'M';
        }
        if (num >= 1000) {
            return '$' + (num / 1000).toFixed(1) + 'K';
        }

        return '$' + num.toLocaleString('en-US', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }
}
