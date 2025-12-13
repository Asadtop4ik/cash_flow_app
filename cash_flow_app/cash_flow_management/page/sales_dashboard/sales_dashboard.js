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

                /* Full page dark background - TINIQ QORA */
                body {
                    background: #000000 !important;
                    overflow-x: hidden;
                }

                /* ========== NEON THEME + FIGMA LAYOUT ========== */
                * {
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }

                .dashboard-fullscreen {
                    background: #000000;
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
                    background: #000000;
                    z-index: 9999;
                    width: 100vw;
                    height: 100vh;
                    left: 0;
                    top: 0;
                }

                .loading-spinner {
                    width: 60px;
                    height: 60px;
                    border: 4px solid rgba(139, 92, 246, 0.2);
                    border-top-color: #8b5cf6;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    to { transform: rotate(360deg); }
                }

                .loading-text {
                    margin-top: 20px;
                    font-size: 18px;
                    color: #ffffff;
                    font-weight: 600;
                }

                /* Top KPI Row - 7 cards - XIRA QORA */
                .kpi-row {
                    display: grid;
                    grid-template-columns: repeat(7, 1fr);
                    gap: 15px;
                    margin-bottom: 15px;
                }

                .kpi-card {
                    background: #0d0d0d;
                    border-radius: 16px;
                    padding: 25px 15px;
                    text-align: center;
                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
                    border: 1px solid #1a1a1a;
                    transition: all 0.3s ease;
                    position: relative;
                    overflow: hidden;
                    min-height: 120px;
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
                    background: var(--card-color);
                }

                .kpi-card:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
                    border-color: var(--card-color);
                    background: #121212;
                }

                .kpi-card.cyan { --card-color: #00d4ff; }
                .kpi-card.green { --card-color: #00ff88; }
                .kpi-card.purple { --card-color: #8b5cf6; }
                .kpi-card.orange { --card-color: #ff6b00; }
                .kpi-card.pink { --card-color: #d946ef; }

                .kpi-value {
                    font-size: 26px;
                    font-weight: 900;
                    color: var(--card-color);
                    margin-bottom: 10px;
                    line-height: 1.2;
                }

                .kpi-label {
                    font-size: 11px;
                    color: #ffffff;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    font-weight: 600;
                    line-height: 1.4;
                }

                /* Chart 4 ROI - O'rtada matn uchun */
                .chart-4 .chart-body {
                    position: relative;
                }

                .roi-center-text {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    text-align: center;
                    pointer-events: none;
                    z-index: 10;
                }

                .roi-percentage {
                    font-size: 32px;
                    font-weight: 900;
                    color: #8b5cf6;
                    line-height: 1;
                }

                /* Year Filter - KPI qatoridan keyin - XIRA QORA */
                .year-filter {
                    position: relative;
                    background: #0d0d0d;
                    border-radius: 12px;
                    padding: 20px 25px;
                    margin-bottom: 20px;
                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
                    display: flex;
                    gap: 15px;
                    align-items: center;
                    justify-content: center;
                    border: 1px solid #1a1a1a;
                    flex-wrap: wrap;
                }

                .year-filter-label {
                    font-size: 14px;
                    font-weight: 700;
                    color: #ffffff;
                    text-transform: uppercase;
                    letter-spacing: 1.5px;
                    margin-right: 10px;
                }

                .year-selectors {
                    display: flex;
                    gap: 15px;
                    align-items: center;
                    flex-wrap: wrap;
                }

                .year-select-group {
                    display: flex;
                    flex-direction: column;
                    gap: 5px;
                }

                .year-select-label {
                    font-size: 11px;
                    color: #999999;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    font-weight: 600;
                }

                .year-select {
                    padding: 10px 35px 10px 15px;
                    background: #000000;
                    border: 2px solid #1a1a1a;
                    color: #ffffff;
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 700;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    outline: none;
                    min-width: 100px;
                    appearance: none;
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%238b5cf6' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
                    background-repeat: no-repeat;
                    background-position: right 10px center;
                }

                .year-select:hover {
                    border-color: #8b5cf6;
                    background: #0d0d0d;
                }

                .year-select:focus {
                    border-color: #8b5cf6;
                    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2);
                }

                .year-select option {
                    background: #000000;
                    color: #ffffff;
                    padding: 10px;
                }

                /* Bo'sh option uchun alohida stil */
                .year-select option[value=""] {
                    color: #666666;
                    font-style: italic;
                }

                .apply-years-btn {
                    padding: 12px 25px;
                    background: linear-gradient(135deg, #8b5cf6, #d946ef);
                    border: none;
                    color: white;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
                }

                .apply-years-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 16px rgba(139, 92, 246, 0.6);
                }

                .apply-years-btn:active {
                    transform: translateY(0);
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

                /* Chart 5 maxsus stillar - oddiy vertikal barlar */
                .chart-5 .chart-body {
                    padding: 10px;
                }

                .chart-6 {
                    grid-column: 10 / 13;
                    grid-row: 1 / 7;
                }

                .chart-container {
                    background: #0d0d0d;
                    border-radius: 16px;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    border: 1px solid #1a1a1a;
                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
                    position: relative;
                }

                .chart-container::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(90deg, #8b5cf6, #d946ef);
                    opacity: 0.6;
                }

                .chart-title {
                    font-size: 14px;
                    font-weight: 700;
                    color: #ffffff;
                    margin-bottom: 15px;
                    text-align: center;
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
                    background: #000000;
                    z-index: 10;
                }

                .debt-table th {
                    padding: 12px 10px;
                    text-align: left;
                    font-size: 11px;
                    color: #ffffff;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    border-bottom: 2px solid #1a1a1a;
                }

                .debt-table td {
                    padding: 10px;
                    font-size: 12px;
                    color: #ffffff;
                    border-bottom: 1px solid #121212;
                }

                .debt-table tbody tr:hover {
                    background: rgba(139, 92, 246, 0.1);
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
                    background: #00ff88;
                    color: #000000;
                }

                .classification-badge.class-b {
                    background: #8b5cf6;
                    color: #ffffff;
                }

                .classification-badge.class-c {
                    background: #ff6b00;
                    color: #ffffff;
                }

                .classification-badge.class-n-a {
                    background: #333333;
                    color: #999999;
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
                        padding: 15px;
                    }

                    .year-filter-label {
                        margin-right: 0;
                        margin-bottom: 10px;
                    }

                    .year-selectors {
                        flex-direction: column;
                        width: 100%;
                    }

                    .year-select-group {
                        width: 100%;
                    }

                    .year-select {
                        width: 100%;
                    }

                    .apply-years-btn {
                        width: 100%;
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
                <!-- KPI Cards - Eng tepada -->
                <div class="kpi-row" id="kpiRow"></div>

                <!-- Year Filter - KPI qatoridan keyin -->
                <div class="year-filter">
                    <span class="year-filter-label">📅 Yillarni tanlang</span>
                    <div class="year-selectors">
                        <div class="year-select-group">
                            <label class="year-select-label">Yil 1</label>
                            <select class="year-select" id="yearSelect1">
                                <option value="">Tanlanmagan</option>
                            </select>
                        </div>
                        <div class="year-select-group">
                            <label class="year-select-label">Yil 2</label>
                            <select class="year-select" id="yearSelect2">
                                <option value="">Tanlanmagan</option>
                            </select>
                        </div>
                        <div class="year-select-group">
                            <label class="year-select-label">Yil 3</label>
                            <select class="year-select" id="yearSelect3">
                                <option value="">Tanlanmagan</option>
                            </select>
                        </div>
                        <button class="apply-years-btn" id="applyYearsBtn">
                            <i class="fa fa-check"></i> Qo'llash
                        </button>
                    </div>
                </div>

                <!-- Charts Grid -->
                <div class="charts-grid">
                        <!-- Chart 1: Line Grapha Oylik Chiqim Summa Oyma oy -->
                        <div class="chart-container chart-1">
                            <div class="chart-title">Har Oylik Tikilgan Pul</div>
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
                                <div class="roi-center-text">
                                    <div class="roi-percentage" id="roiPercentage">0%</div>
                                </div>
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
        this.wrapper.find('#applyYearsBtn').on('click', () => this.applyYearSelection());
    }

    loadAvailableYears() {
        frappe.call({
            method: 'cash_flow_app.cash_flow_management.api.dashboard.get_available_years',
            callback: (r) => {
                if (r.message && r.message.length > 0) {
                    this.availableYears = r.message;
                } else {
                    // Fallback: generate last 5 years
                    const currentYear = new Date().getFullYear();
                    this.availableYears = [];
                    for (let i = 0; i < 5; i++) {
                        this.availableYears.push(currentYear - i);
                    }
                }
                this.renderYearSelects();
                // Avtomatik ma'lumot yuklash
                this.loadData();
            },
            error: () => {
                // Fallback on error
                const currentYear = new Date().getFullYear();
                this.availableYears = [];
                for (let i = 0; i < 5; i++) {
                    this.availableYears.push(currentYear - i);
                }
                this.renderYearSelects();
                // Avtomatik ma'lumot yuklash
                this.loadData();
            }
        });
    }

    renderYearSelects() {
        const select1 = this.wrapper.find('#yearSelect1');
        const select2 = this.wrapper.find('#yearSelect2');
        const select3 = this.wrapper.find('#yearSelect3');

        // Bo'sh optiondan keyin yillarni qo'shish
        this.availableYears.forEach(year => {
            const option1 = $(`<option value="${year}">${year}</option>`);
            const option2 = $(`<option value="${year}">${year}</option>`);
            const option3 = $(`<option value="${year}">${year}</option>`);

            select1.append(option1);
            select2.append(option2);
            select3.append(option3);
        });

        // Default qiymatlarni o'rnatish
        if (this.selectedYears.length >= 3) {
            select1.val(this.selectedYears[0]);
            select2.val(this.selectedYears[1]);
            select3.val(this.selectedYears[2]);
        } else if (this.availableYears.length >= 3) {
            // Agar selectedYears bo'sh bo'lsa, so'nggi 3 yilni tanlash
            select1.val(this.availableYears[2]); // 3rd newest
            select2.val(this.availableYears[1]); // 2nd newest
            select3.val(this.availableYears[0]); // newest
            this.selectedYears = [this.availableYears[2], this.availableYears[1], this.availableYears[0]];
        }
    }

    applyYearSelection() {
        const year1 = this.wrapper.find('#yearSelect1').val();
        const year2 = this.wrapper.find('#yearSelect2').val();
        const year3 = this.wrapper.find('#yearSelect3').val();

        // Faqat tanlangan yillarni olish (bo'sh bo'lmaganlarini)
        this.selectedYears = [year1, year2, year3]
            .filter(y => y !== '' && y !== null && y !== undefined)
            .map(y => parseInt(y))
            .filter(y => !isNaN(y));

        this.selectedYears.sort((a, b) => a - b); // Sort ascending

        console.log('Selected years:', this.selectedYears);

        if (this.selectedYears.length === 0) {
            frappe.msgprint({
                title: 'Diqqat',
                indicator: 'orange',
                message: 'Iltimos, kamida bitta yilni tanlang!'
            });
            return;
        }

        // Reload data with new years
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
        const colors = [
            { line: '#8b5cf6', gradientStart: 'rgba(139, 92, 246, 0.3)', gradientEnd: 'rgba(139, 92, 246, 0)' },
            { line: '#d946ef', gradientStart: 'rgba(217, 70, 239, 0.3)', gradientEnd: 'rgba(217, 70, 239, 0)' },
            { line: '#00d4ff', gradientStart: 'rgba(0, 212, 255, 0.3)', gradientEnd: 'rgba(0, 212, 255, 0)' }
        ];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);

            // Gradient yaratish
            const ctx = canvas.getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, colors[index % colors.length].gradientStart);
            gradient.addColorStop(1, colors[index % colors.length].gradientEnd);

            datasets.push({
                label: year,
                data: yearData,
                borderColor: colors[index % colors.length].line,
                backgroundColor: gradient,
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBackgroundColor: colors[index % colors.length].line,
                pointBorderColor: '#000000',
                pointBorderWidth: 2,
                pointHoverBackgroundColor: colors[index % colors.length].line,
                pointHoverBorderColor: '#ffffff',
                pointHoverBorderWidth: 3
            });
        });

        this.charts.chart1 = new Chart(canvas, {
            type: 'line',
            data: {
                labels: ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun', 'Iyul', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek'],
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            color: '#ffffff',
                            font: { size: 11, weight: '600' },
                            usePointStyle: true,
                            padding: 12
                        }
                    },
                    tooltip: {
                        enabled: true,
                        backgroundColor: '#000000',
                        titleColor: '#ffffff',
                        bodyColor: '#ffffff',
                        borderColor: '#8b5cf6',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.y;
                                const formattedValue = value >= 1000000
                                    ? (value / 1000000).toFixed(2) + 'M'
                                    : value >= 1000
                                    ? (value / 1000).toFixed(1) + 'K'
                                    : value.toFixed(0);
                                return `${context.dataset.label}: $${formattedValue}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#121212',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#999999',
                            font: { size: 10 },
                            callback: function(value) {
                                if (value >= 1000000) {
                                    return (value / 1000000).toFixed(0) + 'M';
                                }
                                if (value >= 1000) {
                                    return (value / 1000).toFixed(0) + 'K';
                                }
                                return value;
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: '#121212',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#999999',
                            font: { size: 10 }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });
    }

    renderChart2() {
        const canvas = this.wrapper.find('#chart2')[0];
        if (!canvas) return;
        if (this.charts.chart2) this.charts.chart2.destroy();

        const data = this.data.monthly_revenue || {};
        const datasets = [];
        const colors = [
            { main: '#10b981', light: '#34d399' },  // Emerald green
            { main: '#8b5cf6', light: '#a78bfa' },  // Purple
            { main: '#06b6d4', light: '#22d3ee' }   // Cyan
        ];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);

            // Gradient yaratish
            const ctx = canvas.getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, colors[index % colors.length].light);
            gradient.addColorStop(1, colors[index % colors.length].main);

            datasets.push({
                label: year,
                data: yearData,
                backgroundColor: gradient,
                borderWidth: 0,
                borderRadius: 6,
                barPercentage: 0.6,
                categoryPercentage: 0.7
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
        const colors = [
            { main: '#8b5cf6', light: '#a78bfa' },  // Purple
            { main: '#ec4899', light: '#f472b6' },  // Pink
            { main: '#06b6d4', light: '#22d3ee' }   // Cyan
        ];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);

            // Gradient yaratish
            const ctx = canvas.getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, colors[index % colors.length].light);
            gradient.addColorStop(1, colors[index % colors.length].main);

            datasets.push({
                label: year,
                data: yearData,
                backgroundColor: gradient,
                borderWidth: 0,
                borderRadius: 6,
                barPercentage: 0.6,
                categoryPercentage: 0.7
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
        const totalFinance = roiData.total_finance || 0;
        const totalInterest = roiData.total_interest || 0;
        const total = totalFinance + totalInterest;

        // ROI foizini hisoblash
        const roiPercentage = totalFinance > 0 ? ((totalInterest / totalFinance) * 100).toFixed(1) : 0;

        // Faqat foizni yangilash
        this.wrapper.find('#roiPercentage').text(`${roiPercentage}%`);

        this.charts.chart4 = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Foyda', 'Kapital'],
                datasets: [{
                    data: [totalInterest, totalFinance],
                    backgroundColor: ['#00ff88', '#6366f1'],
                    borderWidth: 0,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%', // Qalinroq
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: '#e2e8f0',
                            font: { size: 11, weight: '600' },
                            padding: 12,
                            usePointStyle: true,
                            generateLabels: function(chart) {
                                const data = chart.data;
                                if (data.labels.length && data.datasets.length) {
                                    return data.labels.map((label, i) => {
                                        const value = data.datasets[0].data[i];
                                        const formattedValue = value >= 1000000
                                            ? (value / 1000000).toFixed(1) + 'M'
                                            : value >= 1000
                                            ? (value / 1000).toFixed(1) + 'K'
                                            : value.toFixed(0);

                                        return {
                                            text: `${label}: $${formattedValue}`,
                                            fillStyle: data.datasets[0].backgroundColor[i],
                                            hidden: false,
                                            index: i
                                        };
                                    });
                                }
                                return [];
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#00ffff',
                        bodyColor: '#e2e8f0',
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: $${(value / 1000000).toFixed(2)}M (${percentage}%)`;
                            }
                        }
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

        // Faqat tanlangan yillar uchun barlar ko'rsatish
        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);
            datasets.push({
                label: year,
                data: yearData,
                backgroundColor: colors[index % colors.length],
                borderWidth: 0,
                borderRadius: 8,
                barThickness: 'flex',
                maxBarThickness: 30
            });
        });

        this.charts.chart5 = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyun', 'Iyul', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek'],
                datasets: datasets
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
                        cornerRadius: 8,
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.y;
                                const formattedValue = value >= 1000000
                                    ? (value / 1000000).toFixed(2) + 'M'
                                    : value >= 1000
                                    ? (value / 1000).toFixed(1) + 'K'
                                    : value.toFixed(0);
                                return `${context.dataset.label}: $${formattedValue}`;
                            }
                        }
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
                            font: { size: 10 },
                            callback: function(value) {
                                if (value >= 1000000) {
                                    return (value / 1000000).toFixed(0) + 'M';
                                }
                                if (value >= 1000) {
                                    return (value / 1000).toFixed(0) + 'K';
                                }
                                return value;
                            }
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
            }
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

        // Toifalar bo'yicha saralash funksiyasi
        const classificationOrder = { 'C': 1, 'B': 2, 'A': 3, 'N/A': 4 };

        // Avval toifa bo'yicha, keyin qarz miqdori bo'yicha saralash
        const sortedDebtList = debtList.sort((a, b) => {
            const classA = (a.classification || 'N/A').toUpperCase();
            const classB = (b.classification || 'N/A').toUpperCase();

            // Toifalarni solishtirish
            const orderA = classificationOrder[classA] || 999;
            const orderB = classificationOrder[classB] || 999;

            if (orderA !== orderB) {
                return orderA - orderB; // C (1), B (2), A (3) tartibida
            }

            // Agar toifalar bir xil bo'lsa, qarz miqdori bo'yicha kamayish tartibida
            return (b.debt || 0) - (a.debt || 0);
        });

        // Saralangan ma'lumotlarni jadvalga qo'shish
        sortedDebtList.forEach(item => {
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
                        color: '#ffffff',
                        font: { size: 11, weight: '600' },
                        usePointStyle: true,
                        padding: 12
                    }
                },
                tooltip: {
                    backgroundColor: '#000000',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: '#8b5cf6',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#121212',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#999999',
                        font: { size: 10 }
                    }
                },
                x: {
                    grid: {
                        color: '#121212',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#999999',
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
