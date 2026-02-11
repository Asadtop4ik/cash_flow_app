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
        this.applyTheme(this.currentTheme, false); // Apply without animation on init

        this.loadChartJS().then(() => {
            this.setup();
        });
    }

    getDefaultYears() {
        const currentYear = new Date().getFullYear();
        return [currentYear - 2, currentYear - 1, currentYear];
    }

    /**
     * Load theme preference from localStorage
     */
    loadThemePreference() {
        try {
            const saved = localStorage.getItem('sales_dashboard_theme');
            return saved || 'dark'; // Default to dark theme
        } catch (e) {
            console.warn('localStorage not available:', e);
            return 'dark';
        }
    }

    /**
     * Save theme preference to localStorage
     */
    saveThemePreference(theme) {
        try {
            localStorage.setItem('sales_dashboard_theme', theme);
        } catch (e) {
            console.warn('Could not save theme preference:', e);
        }
    }

    /**
     * Create elegant emoji-based theme toggle with glassmorphism
     */
    createThemeToggle() {
        // Clear existing actions
        this.page.clear_actions();

        // Create custom toggle button container
        const toggleContainer = $(`
            <div class="theme-toggle-container">
                <button class="theme-toggle-btn" id="themeToggleBtn" title="${this.currentTheme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}">
                    <span class="theme-toggle-emoji">${this.currentTheme === 'dark' ? '☀️' : '🌙'}</span>
                </button>
            </div>
        `);

        // Inject into page actions area
        this.page.page_actions.prepend(toggleContainer);

        // Store reference
        this.themeToggleBtn = toggleContainer.find('#themeToggleBtn');

        // Bind click event
        this.themeToggleBtn.on('click', () => {
            this.toggleTheme();
        });
    }

    /**
     * Update theme toggle button appearance
     */
    updateThemeToggle() {
        if (!this.themeToggleBtn) return;

        const emoji = this.themeToggleBtn.find('.theme-toggle-emoji');

        // Update emoji
        emoji.text(this.currentTheme === 'dark' ? '☀️' : '🌙');

        // Update title
        this.themeToggleBtn.attr('title', this.currentTheme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode');
    }

    /**
     * Toggle between light and dark themes with full system sync
     */
    toggleTheme() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.currentTheme = newTheme;

        // Save preference to localStorage
        this.saveThemePreference(newTheme);

        // Sync with Frappe's global theme system
        if (typeof frappe !== 'undefined' && frappe.ui && frappe.ui.set_theme) {
            frappe.ui.set_theme(newTheme);
        }

        // Apply theme with smooth animation
        this.applyTheme(newTheme, true);

        // Update toggle button
        this.updateThemeToggle();

        // Re-render all charts with new theme colors
        if (this.data && Object.keys(this.data).length > 0) {
            // Slight delay for smooth visual transition
            setTimeout(() => {
                this.reRenderAllCharts();
            }, 150);
        }

        // Show elegant notification
        frappe.show_alert({
            message: `${newTheme === 'dark' ? '🌙 Dark' : '☀️ Light'} Mode Activated`,
            indicator: newTheme === 'dark' ? 'purple' : 'blue'
        }, 3);
    }

    /**
     * Apply theme to the entire dashboard with CSS variable updates
     */
    applyTheme(theme, animate = true) {
        const root = document.documentElement;

        // Add transition class if animating
        if (animate) {
            this.wrapper.addClass('theme-transitioning');
        }

        if (theme === 'dark') {
            // Dark Mode - Premium Neon Cockpit
            root.style.setProperty('--bg-color', '#000000');
            root.style.setProperty('--card-bg', '#0d0d0d');
            root.style.setProperty('--card-bg-elevated', '#121212');
            root.style.setProperty('--text-color', '#ffffff');
            root.style.setProperty('--text-muted', '#94a3b8');
            root.style.setProperty('--border-color', '#1f1f1f');
            root.style.setProperty('--subtle-fg', '#121212');
            root.style.setProperty('--grid-color', 'rgba(255, 255, 255, 0.05)');
            root.style.setProperty('--tooltip-bg', 'rgba(0, 0, 0, 0.95)');
            root.style.setProperty('--tooltip-border', '#8b5cf6');
            root.style.setProperty('--shadow-sm', '0 4px 20px rgba(0, 0, 0, 0.4)');
            root.style.setProperty('--shadow-lg', '0 8px 32px rgba(0, 0, 0, 0.6)');
            root.style.setProperty('--hover-overlay', 'rgba(139, 92, 246, 0.15)');

            // Toggle button specific
            root.style.setProperty('--toggle-bg', 'rgba(13, 13, 13, 0.8)');
            root.style.setProperty('--toggle-border', 'rgba(139, 92, 246, 0.3)');
            root.style.setProperty('--toggle-shadow', '0 4px 16px rgba(139, 92, 246, 0.2)');
            root.style.setProperty('--toggle-hover-bg', 'rgba(139, 92, 246, 0.15)');
            root.style.setProperty('--toggle-hover-shadow', '0 6px 24px rgba(139, 92, 246, 0.4)');
        } else {
            // Light Mode - Clean Office Productivity
            root.style.setProperty('--bg-color', '#ffffff');
            root.style.setProperty('--card-bg', '#f8f9fa');
            root.style.setProperty('--card-bg-elevated', '#ffffff');
            root.style.setProperty('--text-color', '#1a1a1a');
            root.style.setProperty('--text-muted', '#64748b');
            root.style.setProperty('--border-color', '#e5e7eb');
            root.style.setProperty('--subtle-fg', '#f3f4f6');
            root.style.setProperty('--grid-color', 'rgba(0, 0, 0, 0.06)');
            root.style.setProperty('--tooltip-bg', 'rgba(255, 255, 255, 0.98)');
            root.style.setProperty('--tooltip-border', '#6366f1');
            root.style.setProperty('--shadow-sm', '0 2px 8px rgba(0, 0, 0, 0.08)');
            root.style.setProperty('--shadow-lg', '0 4px 16px rgba(0, 0, 0, 0.12)');
            root.style.setProperty('--hover-overlay', 'rgba(99, 102, 241, 0.08)');

            // Toggle button specific
            root.style.setProperty('--toggle-bg', 'rgba(248, 249, 250, 0.9)');
            root.style.setProperty('--toggle-border', 'rgba(99, 102, 241, 0.2)');
            root.style.setProperty('--toggle-shadow', '0 2px 12px rgba(99, 102, 241, 0.15)');
            root.style.setProperty('--toggle-hover-bg', 'rgba(99, 102, 241, 0.1)');
            root.style.setProperty('--toggle-hover-shadow', '0 4px 20px rgba(99, 102, 241, 0.25)');
        }

        // Brand accent colors remain consistent across themes
        root.style.setProperty('--accent-cyan', '#00d4ff');
        root.style.setProperty('--accent-green', '#00ff88');
        root.style.setProperty('--accent-purple', '#8b5cf6');
        root.style.setProperty('--accent-orange', '#ff6b00');
        root.style.setProperty('--accent-pink', '#d946ef');

        // Remove transition class after animation completes
        if (animate) {
            setTimeout(() => {
                this.wrapper.removeClass('theme-transitioning');
            }, 300);
        }
    }

    /**
     * Re-render all charts with new theme colors
     */
    reRenderAllCharts() {
        if (this.data && Object.keys(this.data).length > 0) {
            this.renderChart1();
            this.renderChart2();
            this.renderChart3();
            this.renderChart4();
            this.renderChart5();
        }
    }

    /**
     * Get dynamic colors based on current theme
     */
    getThemeColors() {
        const root = document.documentElement;
        const computedStyle = getComputedStyle(root);

        return {
            // Core theme colors from CSS variables
            bgColor: computedStyle.getPropertyValue('--bg-color').trim(),
            cardBg: computedStyle.getPropertyValue('--card-bg').trim(),
            textColor: computedStyle.getPropertyValue('--text-color').trim(),
            textMuted: computedStyle.getPropertyValue('--text-muted').trim(),
            borderColor: computedStyle.getPropertyValue('--border-color').trim(),
            subtleFg: computedStyle.getPropertyValue('--subtle-fg').trim(),
            gridColor: computedStyle.getPropertyValue('--grid-color').trim(),
            tooltipBg: computedStyle.getPropertyValue('--tooltip-bg').trim(),
            tooltipBorder: computedStyle.getPropertyValue('--tooltip-border').trim(),

            // Brand accent colors
            accentPurple: computedStyle.getPropertyValue('--accent-purple').trim(),
            accentPink: computedStyle.getPropertyValue('--accent-pink').trim(),
            accentCyan: computedStyle.getPropertyValue('--accent-cyan').trim(),
            accentGreen: computedStyle.getPropertyValue('--accent-green').trim(),
            accentOrange: computedStyle.getPropertyValue('--accent-orange').trim()
        };
    }

    createHTML() {
        const html = `
            <style>
                /* ========== CSS CUSTOM PROPERTIES (Theme Variables) ========== */
                :root {
                    /* Theme colors - set dynamically by JavaScript */
                    --bg-color: #000000;
                    --card-bg: #0d0d0d;
                    --card-bg-elevated: #121212;
                    --text-color: #ffffff;
                    --text-muted: #94a3b8;
                    --border-color: #1f1f1f;
                    --subtle-fg: #121212;
                    --grid-color: rgba(255, 255, 255, 0.05);
                    --tooltip-bg: rgba(0, 0, 0, 0.95);
                    --tooltip-border: #8b5cf6;
                    --shadow-sm: 0 4px 20px rgba(0, 0, 0, 0.4);
                    --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.6);
                    --hover-overlay: rgba(139, 92, 246, 0.15);

                    /* Toggle button variables */
                    --toggle-bg: rgba(13, 13, 13, 0.8);
                    --toggle-border: rgba(139, 92, 246, 0.3);
                    --toggle-shadow: 0 4px 16px rgba(139, 92, 246, 0.2);
                    --toggle-hover-bg: rgba(139, 92, 246, 0.15);
                    --toggle-hover-shadow: 0 6px 24px rgba(139, 92, 246, 0.4);

                    /* Brand accent colors - consistent across themes */
                    --accent-cyan: #00d4ff;
                    --accent-green: #00ff88;
                    --accent-purple: #8b5cf6;
                    --accent-orange: #ff6b00;
                    --accent-pink: #d946ef;
                }

                /* ========== GLASSMORPHIC THEME TOGGLE BUTTON ========== */
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
                    backdrop-filter: blur(10px);
                    -webkit-backdrop-filter: blur(10px);
                    border: 1.5px solid var(--toggle-border);
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
                    padding: 1.5px;
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
                    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
                }

                .theme-toggle-btn:hover .theme-toggle-emoji {
                    transform: scale(1.15) rotate(15deg);
                    filter: drop-shadow(0 4px 8px rgba(139, 92, 246, 0.4));
                }

                /* Animation for emoji change */
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

                /* ========== SMOOTH THEME TRANSITIONS ========== */
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

                /* ========== FLUID LAYOUT ENGINE ========== */
                .dashboard-fullscreen {
                    background: var(--bg-color);
                    padding: 20px;
                    min-height: 100vh;
                    width: 100vw !important;
                    max-width: 100vw !important;
                    margin: 0 !important;
                    box-sizing: border-box;
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    position: relative;
                    left: 50%;
                    right: 50%;
                    margin-left: -50vw !important;
                    margin-right: -50vw !important;
                    padding-bottom: 50px;
                }

                /* Loading State */
                .dashboard-loading {
                    position: fixed;
                    inset: 0;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    background: var(--bg-color);
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
                    border-top-color: var(--accent-purple);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    to { transform: rotate(360deg); }
                }

                .loading-text {
                    margin-top: 20px;
                    font-size: 18px;
                    color: var(--text-color);
                    font-weight: 600;
                }

                /* ========== KPI CARDS (Theme-Aware) ========== */
                .kpi-row {
                    display: grid;
                    grid-template-columns: repeat(7, 1fr);
                    gap: 15px;
                    margin-bottom: 15px;
                }

                .kpi-card {
                    background: var(--card-bg);
                    border-radius: 16px;
                    padding: 25px 15px;
                    text-align: center;
                    box-shadow: var(--shadow-sm);
                    border: 1px solid var(--border-color);
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
                    height: 3px;
                    background: var(--card-color);
                }

                .kpi-card:hover {
                    transform: translateY(-5px);
                    box-shadow: var(--shadow-lg);
                    border-color: var(--card-color);
                    background: var(--card-bg-elevated);
                }

                .kpi-card.cyan { --card-color: var(--accent-cyan); }
                .kpi-card.green { --card-color: var(--accent-green); }
                .kpi-card.purple { --card-color: var(--accent-purple); }
                .kpi-card.orange { --card-color: var(--accent-orange); }
                .kpi-card.pink { --card-color: var(--accent-pink); }

                .kpi-value {
                    font-size: 26px;
                    font-weight: 900;
                    color: var(--card-color);
                    margin-bottom: 10px;
                    line-height: 1.2;
                }

                .kpi-label {
                    font-size: 11px;
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    font-weight: 600;
                    line-height: 1.4;
                }

                /* ========== YEAR FILTER (Theme-Aware) ========== */
                .year-filter {
                    position: relative;
                    background: var(--card-bg);
                    border-radius: 12px;
                    padding: 20px 25px;
                    margin-bottom: 20px;
                    box-shadow: var(--shadow-sm);
                    display: flex;
                    gap: 15px;
                    align-items: center;
                    justify-content: center;
                    border: 1px solid var(--border-color);
                    flex-wrap: wrap;
                }

                .year-filter-label {
                    font-size: 14px;
                    font-weight: 700;
                    color: var(--text-color);
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
                    color: var(--text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    font-weight: 600;
                }

                .year-select {
                    padding: 10px 35px 10px 15px;
                    background: var(--bg-color);
                    border: 2px solid var(--border-color);
                    color: var(--text-color);
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
                    border-color: var(--accent-purple);
                }

                .year-select:focus {
                    border-color: var(--accent-purple);
                    box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2);
                }

                .year-select option {
                    background: var(--card-bg);
                    color: var(--text-color);
                    padding: 10px;
                }

                .apply-years-btn {
                    padding: 12px 25px;
                    background: linear-gradient(135deg, var(--accent-purple), var(--accent-pink));
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

                /* ========== CHARTS GRID (Responsive) ========== */
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
                    background: var(--card-bg);
                    border-radius: 16px;
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    border: 1px solid var(--border-color);
                    box-shadow: var(--shadow-sm);
                    position: relative;
                }

                .chart-container::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 2px;
                    background: linear-gradient(90deg, var(--accent-purple), var(--accent-pink));
                    opacity: 0.6;
                }

                .chart-title {
                    font-size: 14px;
                    font-weight: 700;
                    color: var(--text-color);
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

                /* ROI Center Text */
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
                    color: var(--accent-purple);
                    line-height: 1;
                }

                /* ========== TABLE STYLES (Theme-Aware) ========== */
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
                    padding: 12px 10px;
                    text-align: left;
                    font-size: 11px;
                    color: var(--text-color);
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    border-bottom: 2px solid var(--border-color);
                }

                .debt-table td {
                    padding: 10px;
                    font-size: 12px;
                    color: var(--text-color);
                    border-bottom: 1px solid var(--border-color);
                }

                .debt-table tbody tr:hover {
                    background: var(--hover-overlay);
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
                    background: var(--subtle-fg);
                    color: var(--text-muted);
                }

                /* ========== RESPONSIVE BREAKPOINTS ========== */
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
                    .dashboard-fullscreen {
                        padding: 15px;
                    }

                    .kpi-row {
                        grid-template-columns: repeat(2, 1fr);
                        gap: 10px;
                    }

                    .charts-grid {
                        grid-template-columns: 1fr;
                        gap: 15px;
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
                    <!-- Chart 1: Monthly Finance -->
                    <div class="chart-container chart-1">
                        <div class="chart-title">Har Oylik Tikilgan Pul</div>
                        <div class="chart-body">
                            <canvas id="chart1"></canvas>
                        </div>
                    </div>

                    <!-- Chart 2: Monthly Revenue -->
                    <div class="chart-container chart-2">
                        <div class="chart-title">Oylik Kirim (Klientlardan to'lovlar)</div>
                        <div class="chart-body">
                            <canvas id="chart2"></canvas>
                        </div>
                    </div>

                    <!-- Chart 3: Monthly Contracts -->
                    <div class="chart-container chart-3">
                        <div class="chart-title">Oylik Shartnomalar Soni</div>
                        <div class="chart-body">
                            <canvas id="chart3"></canvas>
                        </div>
                    </div>

                    <!-- Chart 4: ROI Statistics -->
                    <div class="chart-container chart-4">
                        <div class="chart-title">ROI Statistikasi</div>
                        <div class="chart-body">
                            <canvas id="chart4"></canvas>
                            <div class="roi-center-text">
                                <div class="roi-percentage" id="roiPercentage">0%</div>
                            </div>
                        </div>
                    </div>

                    <!-- Chart 5: Monthly Profit -->
                    <div class="chart-container chart-5">
                        <div class="chart-title">Oylik Sof Foyda</div>
                        <div class="chart-body">
                            <canvas id="chart5"></canvas>
                        </div>
                    </div>

                    <!-- Chart 6: Debt Table -->
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
            { line: colors.accentPurple, gradientStart: 'rgba(139, 92, 246, 0.3)', gradientEnd: 'rgba(139, 92, 246, 0)' },
            { line: colors.accentPink, gradientStart: 'rgba(217, 70, 239, 0.3)', gradientEnd: 'rgba(217, 70, 239, 0)' },
            { line: colors.accentCyan, gradientStart: 'rgba(0, 212, 255, 0.3)', gradientEnd: 'rgba(0, 212, 255, 0)' }
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
                borderWidth: 3,
                fill: true,
                tension: 0.4,
                pointRadius: 6,
                pointHoverRadius: 8,
                pointBackgroundColor: lineColors[index % lineColors.length].line,
                pointBorderColor: colors.bgColor,
                pointBorderWidth: 2,
                pointHoverBackgroundColor: lineColors[index % lineColors.length].line,
                pointHoverBorderColor: colors.textColor,
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
                            color: colors.textColor,
                            font: { size: 11, weight: '600' },
                            usePointStyle: true,
                            padding: 12
                        }
                    },
                    tooltip: {
                        enabled: true,
                        backgroundColor: colors.tooltipBg,
                        titleColor: colors.textColor,
                        bodyColor: colors.textColor,
                        borderColor: colors.tooltipBorder,
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
                            color: colors.gridColor,
                            drawBorder: false
                        },
                        ticks: {
                            color: colors.textMuted,
                            font: { size: 10 },
                            callback: function(value) {
                                if (value >= 1000000) return (value / 1000000).toFixed(0) + 'M';
                                if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
                                return value;
                            }
                        }
                    },
                    x: {
                        grid: {
                            color: colors.gridColor,
                            drawBorder: false
                        },
                        ticks: {
                            color: colors.textMuted,
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

        const colors = this.getThemeColors();
        const data = this.data.monthly_revenue || {};
        const datasets = [];

        const barColors = [
            { main: colors.accentGreen, light: 'rgba(0, 255, 136, 0.8)' },
            { main: colors.accentPurple, light: 'rgba(139, 92, 246, 0.8)' },
            { main: colors.accentCyan, light: 'rgba(0, 212, 255, 0.8)' }
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

        const colors = this.getThemeColors();
        const data = this.data.monthly_contracts || {};
        const datasets = [];

        const barColors = [
            { main: colors.accentPurple, light: 'rgba(139, 92, 246, 0.8)' },
            { main: colors.accentPink, light: 'rgba(217, 70, 239, 0.8)' },
            { main: colors.accentCyan, light: 'rgba(0, 212, 255, 0.8)' }
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
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: colors.textColor,
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
                        backgroundColor: colors.tooltipBg,
                        titleColor: colors.textColor,
                        bodyColor: colors.textColor,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
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
                    <td colspan="3" style="text-align: center; padding: 30px;">
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
                        font: { size: 11, weight: '600' },
                        usePointStyle: true,
                        padding: 12
                    }
                },
                tooltip: {
                    backgroundColor: colors.tooltipBg,
                    titleColor: colors.textColor,
                    bodyColor: colors.textColor,
                    borderColor: colors.tooltipBorder,
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
                        color: colors.gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.textMuted,
                        font: { size: 10 },
                        callback: function(value) {
                            if (value >= 1000000) return (value / 1000000).toFixed(0) + 'M';
                            if (value >= 1000) return (value / 1000).toFixed(0) + 'K';
                            return value;
                        }
                    }
                },
                x: {
                    grid: {
                        color: colors.gridColor,
                        drawBorder: false
                    },
                    ticks: {
                        color: colors.textMuted,
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
