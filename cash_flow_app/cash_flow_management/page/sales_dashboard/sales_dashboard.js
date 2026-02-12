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

        // Initialize theme from localStorage or default to dark
        this.currentTheme = this.loadThemePreference();

        this.createHTML();
        this.createThemeToggle();
        this.applyTheme(this.currentTheme, false);

        this.loadChartJS().then(() => {
            this.setup();
        });
    }

    getDefaultYears() {
        const currentYear = new Date().getFullYear();
        return [currentYear - 2, currentYear - 1, currentYear];
    }

    loadThemePreference() {
        try {
            const saved = localStorage.getItem('sales_dashboard_theme');
            return saved || 'dark';
        } catch (e) {
            console.warn('localStorage not available:', e);
            return 'dark';
        }
    }

    saveThemePreference(theme) {
        try {
            localStorage.setItem('sales_dashboard_theme', theme);
        } catch (e) {
            console.warn('Could not save theme preference:', e);
        }
    }

    createThemeToggle() {
        this.page.clear_actions();

        const toggleContainer = $(`
            <div class="theme-toggle-container">
                <button class="theme-toggle-btn" id="themeToggleBtn" title="${this.currentTheme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}">
                    <span class="theme-toggle-emoji">${this.currentTheme === 'dark' ? '☀️' : '🌙'}</span>
                </button>
            </div>
        `);

        this.page.page_actions.prepend(toggleContainer);
        this.themeToggleBtn = toggleContainer.find('#themeToggleBtn');

        this.themeToggleBtn.on('click', () => {
            this.toggleTheme();
        });
    }

    updateThemeToggle() {
        if (!this.themeToggleBtn) return;

        const emoji = this.themeToggleBtn.find('.theme-toggle-emoji');
        emoji.text(this.currentTheme === 'dark' ? '☀️' : '🌙');
        this.themeToggleBtn.attr('title', this.currentTheme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode');
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.currentTheme = newTheme;

        this.saveThemePreference(newTheme);

        if (typeof frappe !== 'undefined' && frappe.ui && frappe.ui.set_theme) {
            frappe.ui.set_theme(newTheme);
        }

        this.applyTheme(newTheme, true);
        this.updateThemeToggle();

        if (this.data && Object.keys(this.data).length > 0) {
            setTimeout(() => {
                this.reRenderAllCharts();
            }, 150);
        }

        frappe.show_alert({
            message: `${newTheme === 'dark' ? '🌙 Dark' : '☀️ Light'} Mode Activated`,
            indicator: newTheme === 'dark' ? 'purple' : 'blue'
        }, 3);
    }

    applyTheme(theme, animate = true) {
        const root = document.documentElement;

        if (animate) {
            this.wrapper.addClass('theme-transitioning');
        }

        if (theme === 'dark') {
            // OBSIDIAN DARK THEME - Extracted from Reference
            root.style.setProperty('--bg-color', '#0a0a0a');
            root.style.setProperty('--bg-gradient', 'radial-gradient(ellipse at top, #0d0d0d, #0a0a0a)');
            root.style.setProperty('--card-bg', '#111111');
            root.style.setProperty('--card-bg-elevated', '#141414');
            root.style.setProperty('--text-color', '#f8fafc');
            root.style.setProperty('--text-muted', '#94a3b8');
            root.style.setProperty('--border-color', 'rgba(139, 92, 246, 0.15)');
            root.style.setProperty('--border-subtle', 'rgba(255, 255, 255, 0.05)');
            root.style.setProperty('--grid-color', 'rgba(255, 255, 255, 0.03)');
            root.style.setProperty('--tooltip-bg', 'rgba(17, 17, 17, 0.98)');
            root.style.setProperty('--tooltip-border', '#9333ea');
            root.style.setProperty('--shadow-sm', '0 2px 8px rgba(0, 0, 0, 0.4), 0 0 1px rgba(147, 51, 234, 0.2)');
            root.style.setProperty('--shadow-md', '0 4px 16px rgba(0, 0, 0, 0.5), 0 0 2px rgba(147, 51, 234, 0.3)');
            root.style.setProperty('--shadow-lg', '0 8px 32px rgba(0, 0, 0, 0.6), 0 0 4px rgba(147, 51, 234, 0.4)');
            root.style.setProperty('--hover-overlay', 'rgba(147, 51, 234, 0.08)');

            // Toggle button
            root.style.setProperty('--toggle-bg', 'rgba(17, 17, 17, 0.9)');
            root.style.setProperty('--toggle-border', 'rgba(147, 51, 234, 0.3)');
            root.style.setProperty('--toggle-shadow', '0 4px 16px rgba(147, 51, 234, 0.25)');
            root.style.setProperty('--toggle-hover-bg', 'rgba(147, 51, 234, 0.15)');
            root.style.setProperty('--toggle-hover-shadow', '0 6px 24px rgba(147, 51, 234, 0.4)');

            // Chart-specific colors
            root.style.setProperty('--chart-purple', '#9333ea');
            root.style.setProperty('--chart-pink', '#ec4899');
            root.style.setProperty('--chart-cyan', '#06b6d4');
            root.style.setProperty('--chart-green', '#10b981');
            root.style.setProperty('--chart-orange', '#f97316');
        } else {
            // CRYSTAL LIGHT THEME - Extracted from Reference
            root.style.setProperty('--bg-color', '#fafafa');
            root.style.setProperty('--bg-gradient', 'linear-gradient(to bottom, #ffffff, #fafafa)');
            root.style.setProperty('--card-bg', '#ffffff');
            root.style.setProperty('--card-bg-elevated', '#ffffff');
            root.style.setProperty('--text-color', '#0f172a');
            root.style.setProperty('--text-muted', '#64748b');
            root.style.setProperty('--border-color', 'rgba(99, 102, 241, 0.12)');
            root.style.setProperty('--border-subtle', 'rgba(0, 0, 0, 0.06)');
            root.style.setProperty('--grid-color', 'rgba(0, 0, 0, 0.04)');
            root.style.setProperty('--tooltip-bg', 'rgba(255, 255, 255, 0.98)');
            root.style.setProperty('--tooltip-border', '#6366f1');
            root.style.setProperty('--shadow-sm', '0 1px 3px rgba(0, 0, 0, 0.08), 0 0 1px rgba(0, 0, 0, 0.04)');
            root.style.setProperty('--shadow-md', '0 2px 8px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06)');
            root.style.setProperty('--shadow-lg', '0 4px 16px rgba(0, 0, 0, 0.12), 0 2px 4px rgba(0, 0, 0, 0.08)');
            root.style.setProperty('--hover-overlay', 'rgba(99, 102, 241, 0.06)');

            // Toggle button
            root.style.setProperty('--toggle-bg', 'rgba(255, 255, 255, 0.95)');
            root.style.setProperty('--toggle-border', 'rgba(99, 102, 241, 0.2)');
            root.style.setProperty('--toggle-shadow', '0 2px 12px rgba(99, 102, 241, 0.15)');
            root.style.setProperty('--toggle-hover-bg', 'rgba(99, 102, 241, 0.08)');
            root.style.setProperty('--toggle-hover-shadow', '0 4px 20px rgba(99, 102, 241, 0.25)');

            // Chart-specific colors
            root.style.setProperty('--chart-purple', '#6366f1');
            root.style.setProperty('--chart-pink', '#e11d48');
            root.style.setProperty('--chart-cyan', '#0ea5e9');
            root.style.setProperty('--chart-green', '#059669');
            root.style.setProperty('--chart-orange', '#ea580c');
        }

        // Brand accent colors - consistent
        root.style.setProperty('--accent-cyan', theme === 'dark' ? '#06b6d4' : '#0ea5e9');
        root.style.setProperty('--accent-green', theme === 'dark' ? '#10b981' : '#059669');
        root.style.setProperty('--accent-purple', theme === 'dark' ? '#9333ea' : '#6366f1');
        root.style.setProperty('--accent-orange', theme === 'dark' ? '#f97316' : '#ea580c');
        root.style.setProperty('--accent-pink', theme === 'dark' ? '#ec4899' : '#e11d48');

        if (animate) {
            setTimeout(() => {
                this.wrapper.removeClass('theme-transitioning');
            }, 300);
        }
    }

    reRenderAllCharts() {
        if (this.data && Object.keys(this.data).length > 0) {
            this.renderChart1();
            this.renderChart2();
            this.renderChart3();
            this.renderChart4();
            this.renderChart5();
        }
    }

    getThemeColors() {
        const root = document.documentElement;
        const computedStyle = getComputedStyle(root);

        return {
            bgColor: computedStyle.getPropertyValue('--bg-color').trim(),
            cardBg: computedStyle.getPropertyValue('--card-bg').trim(),
            textColor: computedStyle.getPropertyValue('--text-color').trim(),
            textMuted: computedStyle.getPropertyValue('--text-muted').trim(),
            borderColor: computedStyle.getPropertyValue('--border-color').trim(),
            gridColor: computedStyle.getPropertyValue('--grid-color').trim(),
            tooltipBg: computedStyle.getPropertyValue('--tooltip-bg').trim(),
            tooltipBorder: computedStyle.getPropertyValue('--tooltip-border').trim(),

            accentPurple: computedStyle.getPropertyValue('--accent-purple').trim(),
            accentPink: computedStyle.getPropertyValue('--accent-pink').trim(),
            accentCyan: computedStyle.getPropertyValue('--accent-cyan').trim(),
            accentGreen: computedStyle.getPropertyValue('--accent-green').trim(),
            accentOrange: computedStyle.getPropertyValue('--accent-orange').trim(),

            chartPurple: computedStyle.getPropertyValue('--chart-purple').trim(),
            chartPink: computedStyle.getPropertyValue('--chart-pink').trim(),
            chartCyan: computedStyle.getPropertyValue('--chart-cyan').trim(),
            chartGreen: computedStyle.getPropertyValue('--chart-green').trim(),
            chartOrange: computedStyle.getPropertyValue('--chart-orange').trim()
        };
    }

    createHTML() {
        const html = `
            <style>
                /* ========== EXECUTIVE TYPOGRAPHY ========== */
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

                :root {
                    /* Theme variables - dynamically set */
                    --bg-color: #0a0a0a;
                    --bg-gradient: radial-gradient(ellipse at top, #0d0d0d, #0a0a0a);
                    --card-bg: #111111;
                    --card-bg-elevated: #141414;
                    --text-color: #f8fafc;
                    --text-muted: #94a3b8;
                    --border-color: rgba(139, 92, 246, 0.15);
                    --border-subtle: rgba(255, 255, 255, 0.05);
                    --grid-color: rgba(255, 255, 255, 0.03);
                    --tooltip-bg: rgba(17, 17, 17, 0.98);
                    --tooltip-border: #9333ea;
                    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 1px rgba(147, 51, 234, 0.2);
                    --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.5), 0 0 2px rgba(147, 51, 234, 0.3);
                    --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.6), 0 0 4px rgba(147, 51, 234, 0.4);
                    --hover-overlay: rgba(147, 51, 234, 0.08);

                    --toggle-bg: rgba(17, 17, 17, 0.9);
                    --toggle-border: rgba(147, 51, 234, 0.3);
                    --toggle-shadow: 0 4px 16px rgba(147, 51, 234, 0.25);
                    --toggle-hover-bg: rgba(147, 51, 234, 0.15);
                    --toggle-hover-shadow: 0 6px 24px rgba(147, 51, 234, 0.4);

                    --chart-purple: #9333ea;
                    --chart-pink: #ec4899;
                    --chart-cyan: #06b6d4;
                    --chart-green: #10b981;
                    --chart-orange: #f97316;

                    --accent-cyan: #06b6d4;
                    --accent-green: #10b981;
                    --accent-purple: #9333ea;
                    --accent-orange: #f97316;
                    --accent-pink: #ec4899;
                }

                * {
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                    text-rendering: optimizeLegibility;
                }

                /* ========== GLASSMORPHIC THEME TOGGLE ========== */
                .theme-toggle-container {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    margin-right: 10px;
                }

                .theme-toggle-btn {
                    position: relative;
                    width: 48px;
                    height: 48px;
                    border-radius: 12px;
                    background: var(--toggle-bg);
                    backdrop-filter: blur(12px);
                    -webkit-backdrop-filter: blur(12px);
                    border: 0.5px solid var(--toggle-border);
                    box-shadow: var(--toggle-shadow);
                    cursor: pointer;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    outline: none;
                    overflow: hidden;
                }

                .theme-toggle-btn::before {
                    content: '';
                    position: absolute;
                    inset: 0;
                    border-radius: 12px;
                    padding: 0.5px;
                    background: linear-gradient(135deg, var(--accent-purple), var(--accent-pink));
                    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
                    -webkit-mask-composite: xor;
                    mask-composite: exclude;
                    opacity: 0;
                    transition: opacity 0.3s ease;
                }

                .theme-toggle-btn:hover {
                    background: var(--toggle-hover-bg);
                    box-shadow: var(--toggle-hover-shadow);
                    transform: translateY(-2px) scale(1.05);
                    border-color: var(--accent-purple);
                }

                .theme-toggle-btn:hover::before {
                    opacity: 1;
                }

                .theme-toggle-btn:active {
                    transform: translateY(0) scale(0.98);
                }

                .theme-toggle-emoji {
                    font-size: 24px;
                    line-height: 1;
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
                }

                .theme-toggle-btn:hover .theme-toggle-emoji {
                    transform: scale(1.15) rotate(15deg);
                    filter: drop-shadow(0 4px 8px rgba(147, 51, 234, 0.5));
                }

                @keyframes emojiPop {
                    0% {
                        transform: scale(0.8) rotate(-10deg);
                        opacity: 0;
                    }
                    50% {
                        transform: scale(1.2) rotate(5deg);
                    }
                    100% {
                        transform: scale(1) rotate(0deg);
                        opacity: 1;
                    }
                }

                .theme-toggle-emoji {
                    animation: emojiPop 0.4s cubic-bezier(0.4, 0, 0.2, 1);
                }

                /* ========== THEME TRANSITIONS ========== */
                .theme-transitioning,
                .theme-transitioning * {
                    transition: background-color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                                border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                                color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
                                box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
                }

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
                    max-width: none !important;
                }

                /* ========== ENTERPRISE LAYOUT ========== */
                .dashboard-fullscreen {
                    background: var(--bg-color);
                    background-image: var(--bg-gradient);
                    padding: 24px;
                    min-height: 100vh;
                    width: 100vw !important;
                    max-width: 100vw !important;
                    margin: 0 !important;
                    box-sizing: border-box;
                    position: relative;
                    left: 50%;
                    right: 50%;
                    margin-left: -50vw !important;
                    margin-right: -50vw !important;
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
                    background: var(--bg-color);
                    background-image: var(--bg-gradient);
                    z-index: 9999;
                    width: 100vw;
                    height: 100vh;
                    left: 0;
                    top: 0;
                }

                .loading-spinner {
                    width: 60px;
                    height: 60px;
                    border: 3px solid rgba(147, 51, 234, 0.2);
                    border-top-color: var(--accent-purple);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    to { transform: rotate(360deg); }
                }

                .loading-text {
                    margin-top: 20px;
                    font-size: 16px;
                    font-weight: 600;
                    color: var(--text-color);
                    letter-spacing: 0.5px;
                }

                /* ========== PREMIUM KPI CARDS ========== */
                .kpi-row {
                    display: grid;
                    grid-template-columns: repeat(7, 1fr);
                    gap: 16px;
                    margin-bottom: 20px;
                }

                .kpi-card {
                    background: var(--card-bg);
                    border-radius: 16px;
                    padding: 24px 16px;
                    text-align: center;
                    box-shadow: var(--shadow-sm);
                    border: 0.5px solid var(--border-color);
                    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
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
                    height: 2px;
                    background: linear-gradient(90deg, var(--card-color), transparent);
                }

                .kpi-card::after {
                    content: '';
                    position: absolute;
                    inset: 0;
                    background: radial-gradient(circle at top, var(--card-color-fade), transparent 70%);
                    opacity: 0;
                    transition: opacity 0.3s ease;
                }

                .kpi-card:hover {
                    transform: translateY(-4px);
                    box-shadow: var(--shadow-lg);
                    border-color: var(--card-color);
                    background: var(--card-bg-elevated);
                }

                .kpi-card:hover::after {
                    opacity: 0.08;
                }

                .kpi-card.cyan {
                    --card-color: var(--accent-cyan);
                    --card-color-fade: rgba(6, 182, 212, 0.2);
                }
                .kpi-card.green {
                    --card-color: var(--accent-green);
                    --card-color-fade: rgba(16, 185, 129, 0.2);
                }
                .kpi-card.purple {
                    --card-color: var(--accent-purple);
                    --card-color-fade: rgba(147, 51, 234, 0.2);
                }
                .kpi-card.orange {
                    --card-color: var(--accent-orange);
                    --card-color-fade: rgba(249, 115, 22, 0.2);
                }
                .kpi-card.pink {
                    --card-color: var(--accent-pink);
                    --card-color-fade: rgba(236, 72, 153, 0.2);
                }

                .kpi-value {
                    font-size: 28px;
                    font-weight: 800;
                    color: var(--card-color);
                    margin-bottom: 8px;
                    line-height: 1.2;
                    letter-spacing: -0.5px;
                }

                .kpi-label {
                    font-size: 10px;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 1.2px;
                    font-weight: 600;
                    line-height: 1.4;
                }

                /* ========== YEAR FILTER ========== */
                .year-filter {
                    position: relative;
                    background: var(--card-bg);
                    border-radius: 16px;
                    padding: 20px 28px;
                    margin-bottom: 20px;
                    box-shadow: var(--shadow-sm);
                    display: flex;
                    gap: 16px;
                    align-items: center;
                    justify-content: center;
                    border: 0.5px solid var(--border-color);
                    flex-wrap: wrap;
                }

                .year-filter-label {
                    font-size: 13px;
                    font-weight: 700;
                    color: var(--text-color);
                    text-transform: uppercase;
                    letter-spacing: 1.5px;
                    margin-right: 12px;
                }

                .year-selectors {
                    display: flex;
                    gap: 16px;
                    align-items: center;
                    flex-wrap: wrap;
                }

                .year-select-group {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }

                .year-select-label {
                    font-size: 10px;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.8px;
                    font-weight: 600;
                }

                .year-select {
                    padding: 10px 36px 10px 16px;
                    background: var(--bg-color);
                    border: 1px solid var(--border-subtle);
                    color: var(--text-color);
                    border-radius: 10px;
                    font-size: 14px;
                    font-weight: 700;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    outline: none;
                    min-width: 110px;
                    appearance: none;
                    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%239333ea' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
                    background-repeat: no-repeat;
                    background-position: right 12px center;
                }

                .year-select:hover {
                    border-color: var(--accent-purple);
                    background: var(--card-bg);
                }

                .year-select:focus {
                    border-color: var(--accent-purple);
                    box-shadow: 0 0 0 3px rgba(147, 51, 234, 0.15);
                }

                .year-select option {
                    background: var(--card-bg);
                    color: var(--text-color);
                    padding: 12px;
                }

                .apply-years-btn {
                    padding: 12px 28px;
                    background: linear-gradient(135deg, var(--accent-purple), var(--accent-pink));
                    border: none;
                    color: white;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 13px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    text-transform: uppercase;
                    letter-spacing: 1.2px;
                    box-shadow: 0 4px 16px rgba(147, 51, 234, 0.3);
                }

                .apply-years-btn:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(147, 51, 234, 0.5);
                }

                .apply-years-btn:active {
                    transform: translateY(0);
                }

                /* ========== ENTERPRISE CHARTS GRID ========== */
                .charts-grid {
                    display: grid;
                    grid-template-columns: repeat(12, 1fr);
                    grid-template-rows: repeat(6, 140px);
                    gap: 16px;
                }

                .chart-1 { grid-column: 1 / 7; grid-row: 1 / 3; }
                .chart-2 { grid-column: 1 / 7; grid-row: 3 / 5; }
                .chart-3 { grid-column: 1 / 4; grid-row: 5 / 7; }
                .chart-4 { grid-column: 4 / 7; grid-row: 5 / 7; }
                .chart-5 { grid-column: 7 / 10; grid-row: 1 / 4; }
                .chart-6 { grid-column: 10 / 13; grid-row: 1 / 7; }

                .chart-container {
                    background: var(--card-bg);
                    border-radius: 16px;
                    padding: 22px;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    border: 0.5px solid var(--border-color);
                    box-shadow: var(--shadow-sm);
                    position: relative;
                    transition: all 0.3s ease;
                }

                .chart-container:hover {
                    box-shadow: var(--shadow-md);
                    border-color: var(--border-subtle);
                }

                .chart-container::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 1px;
                    background: linear-gradient(90deg, var(--accent-purple), var(--accent-pink), transparent);
                    opacity: 0.4;
                }

                .chart-title {
                    font-size: 13px;
                    font-weight: 700;
                    color: var(--text-color);
                    margin-bottom: 16px;
                    text-align: center;
                    letter-spacing: 0.3px;
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

                /* ROI Center Text */
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
                    font-size: 36px;
                    font-weight: 900;
                    color: var(--accent-purple);
                    line-height: 1;
                    letter-spacing: -1px;
                    text-shadow: 0 2px 8px rgba(147, 51, 234, 0.3);
                }

                /* ========== PREMIUM TABLE ========== */
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
                    background: var(--card-bg);
                    z-index: 10;
                }

                .debt-table th {
                    padding: 14px 12px;
                    text-align: left;
                    font-size: 10px;
                    color: var(--text-muted);
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 1.2px;
                    border-bottom: 1px solid var(--border-subtle);
                }

                .debt-table td {
                    padding: 12px;
                    font-size: 13px;
                    color: var(--text-color);
                    border-bottom: 0.5px solid var(--border-subtle);
                    font-weight: 500;
                }

                .debt-table tbody tr {
                    transition: background 0.2s ease;
                }

                .debt-table tbody tr:hover {
                    background: var(--hover-overlay);
                }

                .classification-badge {
                    display: inline-block;
                    padding: 4px 10px;
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }

                .classification-badge.class-a {
                    background: var(--accent-green);
                    color: #000000;
                }

                .classification-badge.class-b {
                    background: var(--accent-purple);
                    color: #ffffff;
                }

                .classification-badge.class-c {
                    background: var(--accent-orange);
                    color: #ffffff;
                }

                .classification-badge.class-n-a {
                    background: var(--border-subtle);
                    color: var(--text-muted);
                }

                /* ========== RESPONSIVE ========== */
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
                        min-height: 320px;
                    }
                }

                @media (max-width: 768px) {
                    .dashboard-fullscreen {
                        padding: 16px;
                    }

                    .kpi-row {
                        grid-template-columns: repeat(2, 1fr);
                        gap: 12px;
                    }

                    .charts-grid {
                        grid-template-columns: 1fr;
                        gap: 16px;
                    }

                    .year-filter {
                        flex-direction: column;
                        padding: 16px;
                    }

                    .year-selectors {
                        flex-direction: column;
                        width: 100%;
                    }

                    .year-select-group,
                    .year-select,
                    .apply-years-btn {
                        width: 100%;
                    }

                    .theme-toggle-btn {
                        width: 44px;
                        height: 44px;
                    }

                    .theme-toggle-emoji {
                        font-size: 22px;
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
                <!-- KPI Cards -->
                <div class="kpi-row" id="kpiRow"></div>

                <!-- Year Filter -->
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
                    <div class="chart-container chart-1">
                        <div class="chart-title">Har Oylik Tikilgan Pul</div>
                        <div class="chart-body">
                            <canvas id="chart1"></canvas>
                        </div>
                    </div>

                    <div class="chart-container chart-2">
                        <div class="chart-title">Oylik Kirim (Klientlardan to'lovlar)</div>
                        <div class="chart-body">
                            <canvas id="chart2"></canvas>
                        </div>
                    </div>

                    <div class="chart-container chart-3">
                        <div class="chart-title">Oylik Shartnomalar Soni</div>
                        <div class="chart-body">
                            <canvas id="chart3"></canvas>
                        </div>
                    </div>

                    <div class="chart-container chart-4">
                        <div class="chart-title">ROI Statistikasi</div>
                        <div class="chart-body">
                            <canvas id="chart4"></canvas>
                            <div class="roi-center-text">
                                <div class="roi-percentage" id="roiPercentage">0%</div>
                            </div>
                        </div>
                    </div>

                    <div class="chart-container chart-5">
                        <div class="chart-title">Oylik Sof Foyda</div>
                        <div class="chart-body">
                            <canvas id="chart5"></canvas>
                        </div>
                    </div>

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
                    const currentYear = new Date().getFullYear();
                    this.availableYears = [];
                    for (let i = 0; i < 5; i++) {
                        this.availableYears.push(currentYear - i);
                    }
                }
                this.renderYearSelects();
                this.loadData();
            },
            error: () => {
                const currentYear = new Date().getFullYear();
                this.availableYears = [];
                for (let i = 0; i < 5; i++) {
                    this.availableYears.push(currentYear - i);
                }
                this.renderYearSelects();
                this.loadData();
            }
        });
    }

    renderYearSelects() {
        const select1 = this.wrapper.find('#yearSelect1');
        const select2 = this.wrapper.find('#yearSelect2');
        const select3 = this.wrapper.find('#yearSelect3');

        this.availableYears.forEach(year => {
            select1.append($(`<option value="${year}">${year}</option>`));
            select2.append($(`<option value="${year}">${year}</option>`));
            select3.append($(`<option value="${year}">${year}</option>`));
        });

        if (this.selectedYears.length >= 3) {
            select1.val(this.selectedYears[0]);
            select2.val(this.selectedYears[1]);
            select3.val(this.selectedYears[2]);
        } else if (this.availableYears.length >= 3) {
            select1.val(this.availableYears[2]);
            select2.val(this.availableYears[1]);
            select3.val(this.availableYears[0]);
            this.selectedYears = [this.availableYears[2], this.availableYears[1], this.availableYears[0]];
        }
    }

    applyYearSelection() {
        const year1 = this.wrapper.find('#yearSelect1').val();
        const year2 = this.wrapper.find('#yearSelect2').val();
        const year3 = this.wrapper.find('#yearSelect3').val();

        this.selectedYears = [year1, year2, year3]
            .filter(y => y !== '' && y !== null && y !== undefined)
            .map(y => parseInt(y))
            .filter(y => !isNaN(y));

        this.selectedYears.sort((a, b) => a - b);

        if (this.selectedYears.length === 0) {
            frappe.msgprint({
                title: 'Diqqat',
                indicator: 'orange',
                message: 'Iltimos, kamida bitta yilni tanlang!'
            });
            return;
        }

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

        const colors = this.getThemeColors();
        const data = this.data.monthly_finance || {};
        const datasets = [];

        const lineColors = [
            {
                line: colors.chartPurple,
                gradientStart: this.currentTheme === 'dark' ? 'rgba(147, 51, 234, 0.25)' : 'rgba(99, 102, 241, 0.2)',
                gradientEnd: 'rgba(147, 51, 234, 0)'
            },
            {
                line: colors.chartPink,
                gradientStart: this.currentTheme === 'dark' ? 'rgba(236, 72, 153, 0.25)' : 'rgba(225, 29, 72, 0.2)',
                gradientEnd: 'rgba(236, 72, 153, 0)'
            },
            {
                line: colors.chartCyan,
                gradientStart: this.currentTheme === 'dark' ? 'rgba(6, 182, 212, 0.25)' : 'rgba(14, 165, 233, 0.2)',
                gradientEnd: 'rgba(6, 182, 212, 0)'
            }
        ];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);
            const ctx = canvas.getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, lineColors[index % lineColors.length].gradientStart);
            gradient.addColorStop(1, lineColors[index % lineColors.length].gradientEnd);

            datasets.push({
                label: year,
                data: yearData,
                borderColor: lineColors[index % lineColors.length].line,
                backgroundColor: gradient,
                borderWidth: 2.5,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 6,
                pointBackgroundColor: lineColors[index % lineColors.length].line,
                pointBorderColor: colors.cardBg,
                pointBorderWidth: 2,
                pointHoverBorderWidth: 2
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
                            color: colors.textColor,
                            font: { size: 11, weight: '600', family: 'Inter' },
                            usePointStyle: true,
                            padding: 15,
                            boxWidth: 8,
                            boxHeight: 8
                        }
                    },
                    tooltip: {
                        enabled: true,
                        backgroundColor: colors.tooltipBg,
                        titleColor: colors.textColor,
                        bodyColor: colors.textColor,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 0.5,
                        padding: 12,
                        cornerRadius: 8,
                        displayColors: true,
                        boxWidth: 8,
                        boxHeight: 8,
                        boxPadding: 6,
                        titleFont: { size: 12, weight: '600', family: 'Inter' },
                        bodyFont: { size: 11, weight: '500', family: 'Inter' },
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
                            color: colors.gridColor,
                            drawBorder: false,
                            lineWidth: 0.5
                        },
                        ticks: {
                            color: colors.textMuted,
                            font: { size: 10, weight: '500', family: 'Inter' },
                            padding: 8,
                            callback: function(value) {
                                if (value >= 1000000) return (value / 1000000).toFixed(0) + 'M';
                                if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
                                return value;
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false,
                            drawBorder: false
                        },
                        ticks: {
                            color: colors.textMuted,
                            font: { size: 10, weight: '500', family: 'Inter' },
                            padding: 8
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

        const colors = this.getThemeColors();
        const data = this.data.monthly_revenue || {};
        const datasets = [];

        const barColors = [
            {
                main: colors.chartGreen,
                light: this.currentTheme === 'dark' ? 'rgba(16, 185, 129, 0.85)' : 'rgba(5, 150, 105, 0.8)'
            },
            {
                main: colors.chartPurple,
                light: this.currentTheme === 'dark' ? 'rgba(147, 51, 234, 0.85)' : 'rgba(99, 102, 241, 0.8)'
            },
            {
                main: colors.chartCyan,
                light: this.currentTheme === 'dark' ? 'rgba(6, 182, 212, 0.85)' : 'rgba(14, 165, 233, 0.8)'
            }
        ];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);
            const ctx = canvas.getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, barColors[index % barColors.length].light);
            gradient.addColorStop(1, barColors[index % barColors.length].main);

            datasets.push({
                label: year,
                data: yearData,
                backgroundColor: gradient,
                borderWidth: 0,
                borderRadius: 6,
                barPercentage: 0.7,
                categoryPercentage: 0.8
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

        const colors = this.getThemeColors();
        const data = this.data.monthly_contracts || {};
        const datasets = [];

        const barColors = [
            {
                main: colors.chartPurple,
                light: this.currentTheme === 'dark' ? 'rgba(147, 51, 234, 0.85)' : 'rgba(99, 102, 241, 0.8)'
            },
            {
                main: colors.chartPink,
                light: this.currentTheme === 'dark' ? 'rgba(236, 72, 153, 0.85)' : 'rgba(225, 29, 72, 0.8)'
            },
            {
                main: colors.chartCyan,
                light: this.currentTheme === 'dark' ? 'rgba(6, 182, 212, 0.85)' : 'rgba(14, 165, 233, 0.8)'
            }
        ];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);
            const ctx = canvas.getContext('2d');
            const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
            gradient.addColorStop(0, barColors[index % barColors.length].light);
            gradient.addColorStop(1, barColors[index % barColors.length].main);

            datasets.push({
                label: year,
                data: yearData,
                backgroundColor: gradient,
                borderWidth: 0,
                borderRadius: 6,
                barPercentage: 0.7,
                categoryPercentage: 0.8
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

        const colors = this.getThemeColors();
        const roiData = this.data.roi_data || {};
        const totalFinance = roiData.total_finance || 0;
        const totalInterest = roiData.total_interest || 0;

        const roiPercentage = totalFinance > 0 ? ((totalInterest / totalFinance) * 100).toFixed(1) : 0;
        this.wrapper.find('#roiPercentage').text(`${roiPercentage}%`);

        this.charts.chart4 = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Foyda', 'Kapital'],
                datasets: [{
                    data: [totalInterest, totalFinance],
                    backgroundColor: [colors.accentGreen, colors.accentPurple],
                    borderWidth: 0,
                    hoverOffset: 6
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
                            color: colors.textColor,
                            font: { size: 11, weight: '600', family: 'Inter' },
                            padding: 12,
                            usePointStyle: true,
                            boxWidth: 8,
                            boxHeight: 8,
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
                        backgroundColor: colors.tooltipBg,
                        titleColor: colors.textColor,
                        bodyColor: colors.textColor,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 0.5,
                        padding: 12,
                        cornerRadius: 8,
                        titleFont: { size: 12, weight: '600', family: 'Inter' },
                        bodyFont: { size: 11, weight: '500', family: 'Inter' },
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
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

        const colors = this.getThemeColors();
        const data = this.data.monthly_profit || {};
        const datasets = [];
        const barColors = [colors.accentGreen, colors.accentPink, colors.accentCyan];

        this.selectedYears.forEach((year, index) => {
            const yearData = data[year] || Array(12).fill(0);
            datasets.push({
                label: year,
                data: yearData,
                backgroundColor: barColors[index % barColors.length],
                borderWidth: 0,
                borderRadius: 6,
                barThickness: 'flex',
                maxBarThickness: 24
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

        if (debtList.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="3" style="text-align: center; padding: 30px; color: var(--text-muted);">
                        Ma'lumot topilmadi
                    </td>
                </tr>
            `);
            return;
        }

        const classificationOrder = { 'C': 1, 'B': 2, 'A': 3, 'N/A': 4 };

        const sortedDebtList = debtList.sort((a, b) => {
            const classA = (a.classification || 'N/A').toUpperCase();
            const classB = (b.classification || 'N/A').toUpperCase();
            const orderA = classificationOrder[classA] || 999;
            const orderB = classificationOrder[classB] || 999;

            if (orderA !== orderB) {
                return orderA - orderB;
            }

            return (b.debt || 0) - (a.debt || 0);
        });

        sortedDebtList.forEach(item => {
            const classKey = (item.classification || 'N/A').toLowerCase().replace('/', '-').replace(' ', '-');
            tbody.append(`
                <tr>
                    <td><span class="classification-badge class-${classKey}">${item.classification}</span></td>
                    <td><strong>${item.customer_name}</strong></td>
                    <td style="font-weight: 700; color: var(--accent-orange);">${this.formatCurrency(item.debt)}</td>
                </tr>
            `);
        });
    }

    getChartOptions() {
        const colors = this.getThemeColors();

        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: {
                        color: colors.textColor,
                        font: { size: 11, weight: '600', family: 'Inter' },
                        usePointStyle: true,
                        padding: 15,
                        boxWidth: 8,
                        boxHeight: 8
                    }
                },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.textColor,
                    bodyColor: colors.textColor,
                    borderColor: colors.tooltipBorder,
                    borderWidth: 0.5,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    boxWidth: 8,
                    boxHeight: 8,
                    boxPadding: 6,
                    titleFont: { size: 12, weight: '600', family: 'Inter' },
                    bodyFont: { size: 11, weight: '500', family: 'Inter' },
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
                        color: colors.gridColor,
                        drawBorder: false,
                        lineWidth: 0.5
                    },
                    ticks: {
                        color: colors.textMuted,
                        font: { size: 10, weight: '500', family: 'Inter' },
                        padding: 8,
                        callback: function(value) {
                            if (value >= 1000000) return (value / 1000000).toFixed(0) + 'M';
                            if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
                            return value;
                        }
                    }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.textMuted,
                        font: { size: 10, weight: '500', family: 'Inter' },
                        padding: 8
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
