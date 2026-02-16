/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * FINANCIAL CONTROL TOWER - PRODUCTION OPTIMIZED v4
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Single-file Frappe v15 Custom Page — zero external dependencies.
 * Mounts a Vue 3 reactive dashboard using Frappe's bundled Vue.
 *
 * v4 OPTIMIZATIONS:
 *   - Chart heights compressed to 250-280px for above-the-fold visibility
 *   - Monthly Investment: Interactive Area Chart with gradient fill, crosshair, expanding dots
 *   - Collections: Grouped Bar Chart (Expected vs Actual) with dynamic bar width scaling
 *   - X-axis labels: auto-rotation/skipping for 12+ months of data
 *   - All chart text uses CSS variables for Light/Dark mode compatibility
 *   - All UI labels in strict Uzbek
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ★★★ CONFIGURE THIS — your actual dotted Python module path ★★★
const API_BASE = 'cash_flow_app.cash_flow_management.api.financial_control_tower_api';

// ─────────────────────────────────────────────────────────────────────────────
// PAGE BOOTSTRAP
// ─────────────────────────────────────────────────────────────────────────────

frappe.pages['financial-control-to'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: '',
		single_column: true
	});

	$(wrapper).find('.page-head').hide();

	// ─── FIX 1: Force full-width layout ──────────────────────────────
	$(wrapper).find('.page-container').css('max-width', '100%');
	$(wrapper).find('.container').css('max-width', '100%');
	$(wrapper).find('.page-body').css('max-width', '100%');
	_injectOnce('fct-fullwidth', 'style', {}, `
		[data-page-container="financial-control-to"] .container,
		[data-page-container="financial-control-to"] .page-container,
		[data-page-container="financial-control-to"] .page-body,
		.page-container[data-page-container="financial-control-to"] {
			max-width: 100% !important;
			width: 100% !important;
			padding-left: 0 !important;
			padding-right: 0 !important;
		}
		#fct-mount {
			width: 100% !important;
		}
	`);

	_injectOnce('fct-font', 'link', {
		rel: 'stylesheet',
		href: 'https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap'
	});

	_injectOnce('fct-css', 'style', {}, FCT_STYLES);

	const mountEl = document.createElement('div');
	mountEl.id = 'fct-mount';
	page.main[0].innerHTML = '';
	page.main[0].appendChild(mountEl);

	const _initVueApp() {
		const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = frappe.Vue;

	const app = createApp({
		template: PAGE_TEMPLATE,
		setup() {
			// ═══════════════════════════════════════════════════════════════
			// REACTIVE STATE
			// ═══════════════════════════════════════════════════════════════
			const current_view = ref('general');
			const loading = ref(false);
			const loadingPeriodic = ref(false);
			const error = ref(null);
			const isDark = ref(false);
			const lastRefresh = ref(null);

			const kpis = ref({});
			const roi = ref({});
			const tiers = ref({ A: [], B: [], C: [] });

			const periodic = ref({ monthly_investment: [], collection_efficiency: [], net_profit: [], contract_count: [] });
			const dateFrom = ref(_monthsAgo(12));
			const dateTo = ref(_today());

			const tip = reactive({ show: false, x: 0, y: 0, title: '', rows: [] });
			const tierSearch = reactive({ A: '', B: '', C: '' });

			// Crosshair state for area chart
			const crosshair = reactive({ show: false, x: 0, idx: -1 });

			// ═══════════════════════════════════════════════════════════════
			// CHART DIMENSIONS — COMPRESSED for above-the-fold
			// Height reduced from 300 → 260 (range 250-280)
			// ═══════════════════════════════════════════════════════════════
			const CHART_W = 720;
			const CHART_H = 280;
			const PAD = { t: 20, r: 24, b: 65, l: 62 };
			// Extra bottom padding (65) to accommodate rotated labels

			// ─── Tier metadata
			const tierMeta = [
				{ key: 'A', title: 'Tier A — Yaxshi', sub: 'A toifadagi mijozlar', accent: '#34d399', accentBg: 'rgba(52,211,153,.12)', icon: '✓' },
				{ key: 'B', title: 'Tier B — O\'rtacha', sub: 'B toifadagi mijozlar', accent: '#fbbf24', accentBg: 'rgba(251,191,36,.12)', icon: '⚡' },
				{ key: 'C', title: 'Tier C — Xavfli', sub: 'C toifadagi mijozlar', accent: '#f87171', accentBg: 'rgba(248,113,113,.12)', icon: '⚠' }
			];

			const presets = [
				{ label: '3O', m: 3 }, { label: '6O', m: 6 },
				{ label: '1Y', m: 12 }, { label: '2Y', m: 24 },
				{ label: 'YB', ytd: true }
			];

			// ═══════════════════════════════════════════════════════════════
			// COMPUTED: KPI Cards
			// ═══════════════════════════════════════════════════════════════
			const kpiCards = computed(() => {
				const k = kpis.value;
				return [
					{ id: 'invested',  label: 'Tikilgan Pul',          val: k.invested_capital,  icon: 'M12 2v20M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6',  color: '#818cf8', isCount: false },
					{ id: 'debt',      label: 'Jami Qarzdorlik',       val: k.total_debt,        icon: 'M13 17h8m0 0V9m0 8l-8-8-4 4-6-6',                            color: '#fb7185', isCount: false },
					{ id: 'debt_a',    label: 'Qarzdorlik A',          val: k.debt_a,            icon: 'M9 12l2 2 4-4',                                              color: '#34d399', isCount: false },
					{ id: 'debt_b',    label: 'Qarzdorlik B',          val: k.debt_b,            icon: 'M12 9v4m0 4h.01',                                            color: '#fbbf24', isCount: false },
					{ id: 'debt_c',    label: 'Qarzdorlik C',          val: k.debt_c,            icon: 'M6 18L18 6M6 6l12 12',                                       color: '#f87171', isCount: false },
					{ id: 'active',    label: 'Aktiv Shartnomalar',    val: k.active_contracts,  icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', color: '#38bdf8', isCount: true },
					{ id: 'closed',    label: 'Yopilgan Shartnomalar', val: k.closed_contracts,  icon: 'M5 13l4 4L19 7',                                             color: '#a78bfa', isCount: true }
				];
			});

			// ═══════════════════════════════════════════════════════════════
			// COMPUTED: ROI Donut
			// ═══════════════════════════════════════════════════════════════
			const donut = computed(() => {
				const cd = roi.value.chart_data || {};
				const total = cd.total || 1;
				const interest = cd.interest || 0;
				const C = 2 * Math.PI * 76;
				const iLen = (interest / total) * C;
				return {
					pct: Math.round(roi.value.roi_percentage || 0),
					interest: roi.value.total_interest || 0,
					principal: roi.value.invested_capital || 0,
					iDash: `${iLen} ${C - iLen}`,
					pDash: `${C - iLen} ${iLen}`,
					iOff: 0,
					pOff: -iLen
				};
			});

			// ═══════════════════════════════════════════════════════════════
			// COMPUTED: Health
			// ═══════════════════════════════════════════════════════════════
			const health = computed(() => {
				const d = kpis.value.total_debt || 0;
				if (d === 0) return { label: 'A\'lo', color: '#34d399' };
				const r = (kpis.value.debt_c || 0) / d;
				if (r > .3) return { label: 'Kritik', color: '#f87171' };
				if (r > .15) return { label: 'Xavfli', color: '#fb923c' };
				if (r > .05) return { label: 'O\'rtacha', color: '#fbbf24' };
				return { label: 'Yaxshi', color: '#34d399' };
			});

			// ═══════════════════════════════════════════════════════════════
			// COMPUTED: Filtered Tier Rows
			// ═══════════════════════════════════════════════════════════════
			const filteredTiers = computed(() => {
				const result = {};
				for (const key of ['A', 'B', 'C']) {
					const rows = tiers.value[key] || [];
					const q = (tierSearch[key] || '').toLowerCase().trim();
					result[key] = q
						? rows.filter(r => (r.customer_name || '').toLowerCase().includes(q) || (r.customer || '').toLowerCase().includes(q))
						: rows;
				}
				return result;
			});

			// ═══════════════════════════════════════════════════════════════
			// CHART MATH — AREA CHART (Investment)
			// Includes: gradient area fill, crosshair zones, label skip logic
			// ═══════════════════════════════════════════════════════════════

			function _calcLabelSkip(count) {
				// Dynamically skip X-axis labels when data is dense
				if (count <= 6) return 1;       // show all
				if (count <= 12) return 2;      // show every 2nd
				if (count <= 18) return 3;      // show every 3rd
				return Math.ceil(count / 8);    // show ~8 labels max
			}

			function _shouldRotateLabels(count) {
				return count > 8;
			}

			function _scale(data, key) {
				if (!data?.length) return { pts: [], yTicks: [], path: '', area: '', labelSkip: 1, rotateLabels: false };
				const pw = CHART_W - PAD.l - PAD.r;
				const ph = CHART_H - PAD.t - PAD.b;
				const vals = data.map(d => d[key] || 0);
				const mx = Math.max(...vals, 1);

				const pts = data.map((d, i) => {
					const x = PAD.l + (data.length === 1 ? pw / 2 : (i / (data.length - 1)) * pw);
					const y = PAD.t + ph - ((d[key] || 0) / mx) * ph;
					return { x, y, val: d[key] || 0, label: d.label || '' };
				});

				const yTicks = [];
				for (let i = 0; i <= 4; i++) {
					const v = (mx / 4) * i;
					yTicks.push({ v, y: PAD.t + ph - (v / mx) * ph });
				}

				const path = pts.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join('');
				const by = CHART_H - PAD.b;
				const area = `M${pts[0].x.toFixed(1)},${by} ${pts.map(p => `L${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')} L${pts[pts.length - 1].x.toFixed(1)},${by}Z`;

				const labelSkip = _calcLabelSkip(data.length);
				const rotateLabels = _shouldRotateLabels(data.length);

				return { pts, yTicks, path, area, labelSkip, rotateLabels };
			}

			// ═══════════════════════════════════════════════════════════════
			// CHART MATH — GROUPED BAR CHART (Collections)
			// Dynamic bar width scaling for 1-24+ months
			// ═══════════════════════════════════════════════════════════════

			function _dualScale(data) {
				if (!data?.length) return { bars: [], yTicks: [], labels: [], labelSkip: 1, rotateLabels: false };

				const pw = CHART_W - PAD.l - PAD.r;
				const ph = CHART_H - PAD.t - PAD.b;
				const mx = Math.max(...data.map(d => Math.max(d.expected || 0, d.actual || 0)), 1);

				// Dynamic bar width calculation
				// Total available width per group = pw / data.length
				// Each group has 2 bars + gaps
				const groupSlot = pw / data.length;
				const barGap = Math.max(2, Math.min(4, groupSlot * 0.06));
				const groupPadding = Math.max(4, Math.min(groupSlot * 0.2, 16));
				const usableGroupWidth = groupSlot - groupPadding;
				const barWidth = Math.max(4, Math.min(28, (usableGroupWidth - barGap) / 2));

				const totalGroupWidth = (barWidth * 2) + barGap;

				const bars = [];
				const labels = [];

				data.forEach((d, i) => {
					const centerX = PAD.l + (i + 0.5) * groupSlot;
					const groupX = centerX - totalGroupWidth / 2;

					// Expected bar (blue)
					const expHeight = Math.max(1, ((d.expected || 0) / mx) * ph);
					const expY = PAD.t + ph - expHeight;
					bars.push({
						type: 'expected',
						x: groupX,
						y: expY,
						width: barWidth,
						height: expHeight,
						value: d.expected || 0,
						label: d.label || '',
						color: '#60a5fa',
						index: i
					});

					// Actual bar (green)
					const actHeight = Math.max(1, ((d.actual || 0) / mx) * ph);
					const actY = PAD.t + ph - actHeight;
					bars.push({
						type: 'actual',
						x: groupX + barWidth + barGap,
						y: actY,
						width: barWidth,
						height: actHeight,
						value: d.actual || 0,
						label: d.label || '',
						color: '#34d399',
						index: i
					});

					labels.push({
						x: centerX,
						label: d.label || '',
						efficiency: d.efficiency_pct || 0
					});
				});

				const yTicks = [];
				for (let i = 0; i <= 4; i++) {
					const v = (mx / 4) * i;
					yTicks.push({ v, y: PAD.t + ph - (v / mx) * ph });
				}

				const labelSkip = _calcLabelSkip(data.length);
				const rotateLabels = _shouldRotateLabels(data.length);

				return { bars, yTicks, labels, labelSkip, rotateLabels };
			}

			const investChart = computed(() => _scale(periodic.value.monthly_investment, 'amount'));
			const collChart = computed(() => _dualScale(periodic.value.collection_efficiency));

			// ═══════════════════════════════════════════════════════════════
			// CHART MATH — SINGLE BAR CHART (Net Profit & Contract Count)
			// ═══════════════════════════════════════════════════════════════

			function _singleBarScale(data, key, color) {
				if (!data?.length) return { bars: [], yTicks: [], labelSkip: 1, rotateLabels: false };

				const pw = CHART_W - PAD.l - PAD.r;
				const ph = CHART_H - PAD.t - PAD.b;
				const vals = data.map(d => d[key] || 0);
				const mx = Math.max(...vals, 1);

				// Dynamic bar width calculation for single bar chart
				const groupSlot = pw / data.length;
				const groupPadding = Math.max(6, Math.min(groupSlot * 0.3, 20));
				const barWidth = Math.max(8, Math.min(40, groupSlot - groupPadding));

				const bars = [];

				data.forEach((d, i) => {
					const centerX = PAD.l + (i + 0.5) * groupSlot;
					const barX = centerX - barWidth / 2;

					const barHeight = Math.max(1, ((d[key] || 0) / mx) * ph);
					const barY = PAD.t + ph - barHeight;

					bars.push({
						x: barX,
						y: barY,
						width: barWidth,
						height: barHeight,
						value: d[key] || 0,
						label: d.label || '',
						color: color,
						index: i
					});
				});

				const yTicks = [];
				for (let i = 0; i <= 4; i++) {
					const v = (mx / 4) * i;
					yTicks.push({ v, y: PAD.t + ph - (v / mx) * ph });
				}

				const labelSkip = _calcLabelSkip(data.length);
				const rotateLabels = _shouldRotateLabels(data.length);

				return { bars, yTicks, labelSkip, rotateLabels };
			}

			const netProfitChart = computed(() => _singleBarScale(periodic.value.net_profit, 'amount', '#10b981'));
			const contractCountChart = computed(() => _singleBarScale(periodic.value.contract_count, 'count', '#6366f1'));

			// ═══════════════════════════════════════════════════════════════
			// DATA FETCHING
			// ═══════════════════════════════════════════════════════════════

			async function fetchGeneral() {
				loading.value = true;
				error.value = null;
				try {
					const r = await frappe.call({ method: `${API_BASE}.get_intelligence_data`, freeze: false });
					const d = r.message;
					if (d?.success) {
						kpis.value = d.kpis || {};
						roi.value = d.roi || {};
						tiers.value = d.tiers || { A: [], B: [], C: [] };
						lastRefresh.value = new Date().toLocaleTimeString();
					} else {
						error.value = d?.error || 'Ma\'lumot olishda xatolik';
					}
				} catch (e) {
					error.value = e.message || 'Tarmoq xatosi';
				} finally {
					loading.value = false;
				}
			}

			async function fetchPeriodic() {
				loadingPeriodic.value = true;
				error.value = null;
				try {
					const r = await frappe.call({
						method: `${API_BASE}.get_periodic_data`,
						args: { from_date: dateFrom.value, to_date: dateTo.value },
						freeze: false
					});
					const d = r.message;
					if (d?.success) {
						periodic.value = {
							monthly_investment: d.monthly_investment || [],
							collection_efficiency: d.collection_efficiency || [],
							net_profit: d.net_profit || [],
							contract_count: d.contract_count || []
						};
					} else {
						error.value = d?.error || 'Davriy ma\'lumot olishda xatolik';
					}
				} catch (e) {
					error.value = e.message || 'Tarmoq xatosi';
				} finally {
					loadingPeriodic.value = false;
				}
			}

			function refresh() {
				if (current_view.value === 'general') fetchGeneral();
				else fetchPeriodic();
			}

			function applyPreset(p) {
				dateFrom.value = p.ytd ? `${new Date().getFullYear()}-01-01` : _monthsAgo(p.m);
				dateTo.value = _today();
				fetchPeriodic();
			}

			function switchView(v) {
				current_view.value = v;
				if (v === 'periodic' && !periodic.value.monthly_investment?.length) {
					fetchPeriodic();
				}
			}

			// ═══════════════════════════════════════════════════════════════
			// TOOLTIP & CROSSHAIR
			// ═══════════════════════════════════════════════════════════════

			function showTip(ev, title, rows) {
				const rect = document.getElementById('fct-mount')?.getBoundingClientRect();
				let tx = ev.clientX + 14;
				let ty = ev.clientY - 20;
				// Keep tooltip within viewport
				if (tx + 200 > window.innerWidth) tx = ev.clientX - 200;
				if (ty < 10) ty = ev.clientY + 20;
				tip.show = true;
				tip.x = tx;
				tip.y = ty;
				tip.title = title;
				tip.rows = rows;
			}
			function hideTip() {
				tip.show = false;
				crosshair.show = false;
			}

			function tipInvest(ev, pt, idx) {
				crosshair.show = true;
				crosshair.x = pt.x;
				crosshair.idx = idx;
				showTip(ev, pt.label, [
					{ k: 'Sana', v: pt.label, c: 'var(--fct-tx-1)' },
					{ k: 'Summa', v: fmt(pt.val), c: '#818cf8' }
				]);
			}

			function hideInvestTip() {
				hideTip();
				crosshair.show = false;
				crosshair.idx = -1;
			}

			function tipCollBar(ev, bar) {
				const d = periodic.value.collection_efficiency;
				const monthData = d?.[bar.index];
				if (!monthData) return;
				showTip(ev, bar.label, [
					{ k: 'Kutilgan', v: fmt(monthData.expected), c: '#60a5fa' },
					{ k: 'Haqiqiy', v: fmt(monthData.actual), c: '#34d399' },
					{ k: 'Samaradorlik', v: monthData.efficiency_pct + '%', c: monthData.efficiency_pct >= 90 ? '#34d399' : monthData.efficiency_pct >= 70 ? '#fbbf24' : '#f87171' }
				]);
			}

			function tipColl(ev, idx) {
				const d = periodic.value.collection_efficiency;
				if (!d?.[idx]) return;
				const r = d[idx];
				showTip(ev, r.label, [
					{ k: 'Kutilgan', v: fmt(r.expected), c: '#60a5fa' },
					{ k: 'Haqiqiy', v: fmt(r.actual), c: '#34d399' },
					{ k: 'Samaradorlik', v: r.efficiency_pct + '%', c: r.efficiency_pct >= 90 ? '#34d399' : r.efficiency_pct >= 70 ? '#fbbf24' : '#f87171' }
				]);
			}

			function tipNetProfit(ev, bar) {
				showTip(ev, bar.label, [
					{ k: 'Sana', v: bar.label, c: 'var(--fct-tx-1)' },
					{ k: 'Sof Foyda', v: fmt(bar.value), c: '#10b981' }
				]);
			}

			function tipContractCount(ev, bar) {
				showTip(ev, bar.label, [
					{ k: 'Sana', v: bar.label, c: 'var(--fct-tx-1)' },
					{ k: 'Soni', v: bar.value + ' ta shartnoma', c: '#6366f1' }
				]);
			}

			// ═══════════════════════════════════════════════════════════════
			// THEME
			// ═══════════════════════════════════════════════════════════════

			function toggleDark() {
				isDark.value = !isDark.value;
				try { localStorage.setItem('fct_dark', isDark.value ? '1' : '0'); } catch(e) {}
			}

			// ═══════════════════════════════════════════════════════════════
			// FORMATTERS
			// ═══════════════════════════════════════════════════════════════

			function fmt(v) {
				const n = parseFloat(v) || 0;
				if (Math.abs(n) >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
				if (Math.abs(n) >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
				if (Math.abs(n) >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'K';
				return '$' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
			}

			function fmtAxis(v) {
				const n = parseFloat(v) || 0;
				if (n >= 1e6) return '$' + (n / 1e6).toFixed(1) + 'M';
				if (n >= 1e3) return '$' + (n / 1e3).toFixed(0) + 'K';
				return '$' + n.toFixed(0);
			}

			function fmtFull(v) {
				const n = parseFloat(v) || 0;
				return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
			}

			function fmtCount(v) {
				const n = parseInt(v) || 0;
				return n.toLocaleString('en-US');
			}

			function overdueCls(d) {
				if (d <= 30) return 'fct-pill-g';
				if (d <= 90) return 'fct-pill-y';
				return 'fct-pill-r';
			}

			function effCls(p) {
				if (p >= 90) return '#34d399';
				if (p >= 70) return '#fbbf24';
				return '#f87171';
			}

			// ═══════════════════════════════════════════════════════════════
			// LIFECYCLE
			// ═══════════════════════════════════════════════════════════════

			onMounted(() => {
				const frappeTheme = document.documentElement.getAttribute('data-theme');
				const stored = (() => { try { return localStorage.getItem('fct_dark'); } catch(e) { return null; } })();
				if (stored !== null) {
					isDark.value = stored === '1';
				} else {
					isDark.value = frappeTheme === 'dark' || window.matchMedia('(prefers-color-scheme: dark)').matches;
				}

				fetchGeneral();
				fetchPeriodic();

				frappe.realtime.on('fct_data_changed', (data) => {
					console.log('📊 FCT: Real-time update', data);
					frappe.show_alert({
						message: __(`${data.doctype} ${data.docname} — ${data.method === 'on_submit' ? 'tasdiqlandi' : 'bekor qilindi'}. Dashboard yangilanmoqda...`),
						indicator: 'green'
					}, 5);
					fetchGeneral();
					fetchPeriodic();
				});

				const _autoTimer = setInterval(() => {
					if (!document.hidden) {
						if (current_view.value === 'general') fetchGeneral();
						else fetchPeriodic();
					}
				}, 60000);

				const _onVisible = () => {
					if (!document.hidden) {
						fetchGeneral();
						fetchPeriodic();
					}
				};
				document.addEventListener('visibilitychange', _onVisible);

				if (cur_page?.page?.wrapper) {
					$(cur_page.page.wrapper).on('remove', () => {
						clearInterval(_autoTimer);
						frappe.realtime.off('fct_data_changed');
						document.removeEventListener('visibilitychange', _onVisible);
					});
				}
			});

			// ═══════════════════════════════════════════════════════════════
			// EXPOSE
			// ═══════════════════════════════════════════════════════════════

			return {
				current_view, loading, loadingPeriodic, error, isDark, lastRefresh,
				kpis, roi, tiers, periodic,
				dateFrom, dateTo, tip, tierSearch, crosshair,
				kpiCards, donut, health, filteredTiers,
				CHART_W, CHART_H, PAD,
				investChart, collChart, netProfitChart, contractCountChart,
				tierMeta, presets,
				refresh, fetchPeriodic, applyPreset, switchView,
				toggleDark,
				showTip, hideTip, tipInvest, hideInvestTip, tipColl, tipCollBar, tipNetProfit, tipContractCount,
				fmt, fmtAxis, fmtFull, fmtCount, overdueCls, effCls
			};
		}
	});

		app.mount('#fct-mount');
	}

	// Frappe v15+ has Vue 3 bundled - check multiple sources
	const VueLib = window.Vue || frappe.Vue || (typeof Vue !== 'undefined' ? Vue : null);

	if (VueLib) {
		// Make Vue available globally for the app
		window.Vue = VueLib;
		_initVueApp();
	} else {
		// Fallback: try loading from CDN
		const vueScript = document.createElement('script');
		vueScript.src = 'https://unpkg.com/vue@3/dist/vue.global.prod.js';
		vueScript.onload = function() {
			window.Vue = window.Vue || Vue;
			_initVueApp();
		};
		vueScript.onerror = function() {
			// Last resort: show manual error with debug info
			page.main[0].innerHTML = `
				<div style="padding:2rem;color:#f87171;font-family:sans-serif;">
					<h3>Vue yuklanmadi</h3>
					<p>Tarmoqni tekshiring yoki qo'llab-quvvatlash xizmatiga murojaat qiling.</p>
					<details style="margin-top:1rem;font-size:12px;color:#888;">
						<summary>Debug Info</summary>
						<pre>window.Vue: ${typeof window.Vue}
frappe.Vue: ${typeof frappe?.Vue}
Vue global: ${typeof Vue}</pre>
					</details>
				</div>
			`;
		};
		document.head.appendChild(vueScript);
	}
};

// ─────────────────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────────────────

function _today() { return new Date().toISOString().slice(0, 10); }
function _monthsAgo(n) { const d = new Date(); d.setMonth(d.getMonth() - n); return d.toISOString().slice(0, 10); }

function _injectOnce(id, tag, attrs, content) {
	if (document.getElementById(id)) return;
	const el = document.createElement(tag);
	el.id = id;
	Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
	if (content) el.textContent = content;
	document.head.appendChild(el);
}


// ═══════════════════════════════════════════════════════════════════════════════
// PAGE_TEMPLATE — Complete Vue 3 Template (v4 — Production Optimized)
// ═══════════════════════════════════════════════════════════════════════════════

const PAGE_TEMPLATE = `
<div class="fct" :class="{ 'fct--dark': isDark }">

  <!-- ╔═══════════════════════════════════════════════════════════════════════╗
       ║ HEADER                                                              ║
       ╚═══════════════════════════════════════════════════════════════════════╝ -->
  <header class="fct-hd">
    <div class="fct-hd__inner">
      <div class="fct-hd__brand">
        <div class="fct-hd__logo">
          <svg viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="url(#fctGr)"/>
            <path d="M7 20V8" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
            <path d="M7 20h14" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
            <path d="M10 16l3.5-6 3 3.5L21 8" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="10" cy="16" r="1.5" fill="#fff"/>
            <circle cx="13.5" cy="10" r="1.5" fill="#fff"/>
            <circle cx="16.5" cy="13.5" r="1.5" fill="#fff"/>
            <circle cx="21" cy="8" r="1.5" fill="#fff"/>
            <defs><linearGradient id="fctGr" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs>
          </svg>
        </div>
        <div>
          <h1 class="fct-hd__title">Moliyaviy Boshqaruv Markazi</h1>
          <div class="fct-hd__meta">
            <span class="fct-hd__pill" v-if="!loading && !loadingPeriodic">
              <span class="fct-hd__dot fct-hd__dot--live"></span> Jonli
            </span>
            <span class="fct-hd__pill fct-hd__pill--load" v-else>
              <span class="fct-hd__dot fct-hd__dot--load"></span> Sinxronlanmoqda…
            </span>
            <span class="fct-hd__ts" v-if="lastRefresh">{{ lastRefresh }}</span>
          </div>
        </div>
      </div>

      <nav class="fct-hd__nav">
        <button class="fct-hd__tab" :class="{ 'fct-hd__tab--on': current_view === 'general' }" @click="switchView('general')">
          <svg viewBox="0 0 20 20" width="15" height="15" fill="currentColor"><path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zm0 6a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zm10 0a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"/></svg>
          <span>Umumiy Ma'lumotlar</span>
        </button>
        <button class="fct-hd__tab" :class="{ 'fct-hd__tab--on': current_view === 'periodic' }" @click="switchView('periodic')">
          <svg viewBox="0 0 20 20" width="15" height="15" fill="currentColor"><path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z"/><path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z"/></svg>
          <span>Davriy Statistika</span>
        </button>
      </nav>

      <div class="fct-hd__actions">
        <button class="fct-hd__btn" @click="refresh()" :disabled="loading || loadingPeriodic" title="Ma'lumotni yangilash">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" :class="{ 'fct-spin': loading || loadingPeriodic }">
            <path d="M21 2v6h-6M3 12a9 9 0 0115-6.7L21 8M3 22v-6h6M21 12a9 9 0 01-15 6.7L3 16" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <button class="fct-hd__btn" @click="toggleDark()" :title="isDark ? 'Yorug\\' rejimga o\\'tish' : 'Qorong\\'u rejimga o\\'tish'">
          <svg v-if="isDark" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2">
            <circle cx="12" cy="12" r="4.5"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41" stroke-linecap="round"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2">
            <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  </header>

  <!-- ERROR BAR -->
  <div v-if="error" class="fct-err">
    <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
    <span>{{ error }}</span>
    <button class="fct-err__btn" @click="refresh()">Qayta urinish</button>
    <button class="fct-err__x" @click="error = null">&times;</button>
  </div>

  <!-- ╔═══════════════════════════════════════════════════════════════════════╗
       ║ MAIN CONTENT                                                        ║
       ╚═══════════════════════════════════════════════════════════════════════╝ -->
  <main class="fct-body">

    <transition name="fct-fade">
      <div v-if="loading && current_view === 'general'" class="fct-loader">
        <div class="fct-loader__ring"></div>
        <p>Moliyaviy ma'lumotlar yuklanmoqda…</p>
      </div>
    </transition>

    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <!--  VIEW 1: UMUMIY MA'LUMOTLAR                                       -->
    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <section v-show="current_view === 'general'" class="fct-v fct-v--gen">

      <!-- KPI Cards -->
      <div class="fct-kpis">
        <div v-for="(c, i) in kpiCards" :key="c.id" class="fct-kpi" :style="{ '--kpi-accent': c.color, 'animation-delay': (i * 40) + 'ms' }">
          <div class="fct-kpi__head">
            <span class="fct-kpi__label">{{ c.label }}</span>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" :stroke="c.color" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="fct-kpi__icon">
              <path :d="c.icon"/>
            </svg>
          </div>
          <div class="fct-kpi__val">{{ c.isCount ? fmtCount(c.val) : fmt(c.val) }}</div>
          <div class="fct-kpi__bar"><div class="fct-kpi__barfill"></div></div>
        </div>
      </div>

      <!-- ROI + Portfolio Summary -->
      <div class="fct-duo">
        <!-- ROI Donut -->
        <div class="fct-card fct-roi">
          <div class="fct-card__hd">
            <h2 class="fct-card__title">ROI Statistikasi</h2>
          </div>
          <div class="fct-roi__body">
            <div class="fct-roi__donut">
              <svg viewBox="0 0 200 200" class="fct-roi__svg">
                <circle cx="100" cy="100" r="76" fill="none" :stroke="isDark ? '#1e293b' : '#e2e8f0'" stroke-width="20"/>
                <circle cx="100" cy="100" r="76" fill="none" stroke="url(#fctRoiGr)" stroke-width="20" stroke-linecap="round"
                  :stroke-dasharray="donut.iDash" :stroke-dashoffset="donut.iOff" transform="rotate(-90 100 100)" class="fct-roi__arc"/>
                <circle cx="100" cy="100" r="76" fill="none" :stroke="isDark ? '#334155' : '#94a3b8'" stroke-width="20" stroke-linecap="round"
                  :stroke-dasharray="donut.pDash" :stroke-dashoffset="donut.pOff" transform="rotate(-90 100 100)" class="fct-roi__arc" style="opacity:.5"/>
                <defs>
                  <linearGradient id="fctRoiGr" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#34d399"/><stop offset="100%" stop-color="#059669"/>
                  </linearGradient>
                </defs>
              </svg>
              <div class="fct-roi__center">
                <span class="fct-roi__pct">{{ donut.pct }}%</span>
                <span class="fct-roi__lbl">ROI</span>
              </div>
            </div>
            <div class="fct-roi__legend">
              <div class="fct-roi__li"><span class="fct-roi__dot" style="background:#34d399"></span><span>Foiz daromad</span><strong>{{ fmt(donut.interest) }}</strong></div>
              <div class="fct-roi__li"><span class="fct-roi__dot" style="background:#94a3b8"></span><span>Asosiy mablag'</span><strong>{{ fmt(donut.principal) }}</strong></div>
            </div>
          </div>
        </div>

        <!-- Portfolio Summary -->
        <div class="fct-card fct-summary">
          <div class="fct-card__hd">
            <h2 class="fct-card__title">Umumiy Ma'lumotlar</h2>
            <span class="fct-health" :style="{ color: health.color, borderColor: health.color + '44', background: health.color + '14' }">{{ health.label }}</span>
          </div>
          <div class="fct-summary__grid">
            <div class="fct-summary__row">
              <span>Jami shartnomalar</span><strong>{{ kpis.total_contracts || 0 }}</strong>
            </div>
            <div class="fct-summary__row">
              <span>Aktiv shartnomalar</span><strong style="color:#34d399">{{ kpis.active_contracts || 0 }}</strong>
            </div>
            <div class="fct-summary__row">
              <span>Yopilgan</span><strong style="color:#60a5fa">{{ kpis.closed_contracts || 0 }}</strong>
            </div>
            <div class="fct-summary__hr"></div>
            <div class="fct-summary__row">
              <span><span class="fct-summary__dot" style="background:#34d399"></span>Tier A</span><strong style="color:#34d399">{{ fmt(kpis.debt_a) }}</strong>
            </div>
            <div class="fct-summary__row">
              <span><span class="fct-summary__dot" style="background:#fbbf24"></span>Tier B</span><strong style="color:#fbbf24">{{ fmt(kpis.debt_b) }}</strong>
            </div>
            <div class="fct-summary__row">
              <span><span class="fct-summary__dot" style="background:#f87171"></span>Tier C</span><strong style="color:#f87171">{{ fmt(kpis.debt_c) }}</strong>
            </div>
            <div class="fct-summary__hr"></div>
            <div class="fct-summary__row fct-summary__row--em">
              <span>Tikilgan Pul</span><strong>{{ fmtFull(kpis.invested_capital) }}</strong>
            </div>
            <div class="fct-summary__row fct-summary__row--em">
              <span>Jami qarzdorlik</span><strong style="color:#fb7185">{{ fmtFull(kpis.total_debt) }}</strong>
            </div>
          </div>
        </div>
      </div>

      <!-- CUSTOMER TIER GRID -->
      <div class="fct-tier-grid">
        <div v-for="tm in tierMeta" :key="tm.key" class="fct-card fct-tier-col" :style="{ '--tier-accent': tm.accent }">
          <div class="fct-tier-col__hd">
            <div class="fct-tier__badge" :style="{ background: tm.accentBg, color: tm.accent }">{{ tm.icon }}</div>
            <div class="fct-tier__info">
              <h3 class="fct-tier__title">{{ tm.title }}</h3>
              <p class="fct-tier__sub">{{ tm.sub }} &middot; {{ (tiers[tm.key] || []).length }} mijoz</p>
            </div>
          </div>
          <div class="fct-tier-col__search">
            <svg viewBox="0 0 20 20" width="14" height="14" fill="currentColor" class="fct-tier__searchico">
              <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
            </svg>
            <input type="text" v-model="tierSearch[tm.key]" placeholder="Qidirish…" class="fct-tier__input fct-tier__input--full"/>
          </div>
          <div class="fct-tier-col__list" v-if="filteredTiers[tm.key]?.length">
            <div v-for="row in filteredTiers[tm.key]" :key="row.customer" class="fct-cust-row"
                 @mouseenter="showTip($event, row.customer_name, [
                   { k: 'Jami hisob', v: fmt(row.total_billed), c: '#60a5fa' },
                   { k: 'To\\'langan', v: fmt(row.total_paid), c: '#34d399' },
                   { k: 'Qoldiq qarz', v: fmt(row.total_debt), c: tm.accent },
                   { k: 'Shartnomalar', v: String(row.contract_count || 0), c: 'var(--fct-tx-1)' }
                 ])"
                 @mouseleave="hideTip()">
              <div class="fct-cust-row__info">
                <span class="fct-cust-row__name">{{ row.customer_name }}</span>
                <span class="fct-cust-row__id">{{ row.customer }} · {{ row.contract_count || 0 }} shartnoma</span>
              </div>
              <div class="fct-cust-row__debt" :style="{ color: tm.accent }">{{ fmt(row.total_debt) }}</div>
            </div>
          </div>
          <div v-else class="fct-tier__empty">
            <p v-if="tierSearch[tm.key]">"{{ tierSearch[tm.key] }}" bo'yicha natija topilmadi</p>
            <p v-else>Bu toifada mijoz yo'q</p>
          </div>
          <div class="fct-tier-col__foot" v-if="(tiers[tm.key] || []).length">
            <span>Jami</span>
            <strong :style="{ color: tm.accent }">{{ fmt( (tiers[tm.key] || []).reduce((s, r) => s + (r.total_debt || 0), 0) ) }}</strong>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <!--  VIEW 2: DAVRIY STATISTIKA                                        -->
    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <section v-show="current_view === 'periodic'" class="fct-v fct-v--per">

      <!-- Date Controls -->
      <div class="fct-dates">
        <div class="fct-dates__fields">
          <div class="fct-dates__f">
            <label>Boshlanish</label>
            <input type="date" v-model="dateFrom" class="fct-dates__input"/>
          </div>
          <div class="fct-dates__f">
            <label>Tugash</label>
            <input type="date" v-model="dateTo" class="fct-dates__input"/>
          </div>
          <button class="fct-dates__go" @click="fetchPeriodic()" :disabled="loadingPeriodic">
            <svg viewBox="0 0 20 20" width="14" height="14" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clip-rule="evenodd"/></svg>
            Qo'llash
          </button>
        </div>
        <div class="fct-dates__presets">
          <button v-for="p in presets" :key="p.label" class="fct-dates__pre" @click="applyPreset(p)">{{ p.label }}</button>
        </div>
      </div>

      <!-- Loading bar -->
      <div v-if="loadingPeriodic" class="fct-pbar"><div class="fct-pbar__fill"></div></div>

      <!-- ═══════════════════════════════════════════════════════════════
           CHARTS: Side by side on wide screens, stacked on narrow
           Both charts compressed to 260px viewBox height
           ═══════════════════════════════════════════════════════════════ -->
      <div class="fct-charts-duo">

        <!-- ─── MONTHLY INVESTMENT: Interactive Area Chart ────────────── -->
        <div class="fct-card fct-chart-card">
          <div class="fct-card__hd">
            <h2 class="fct-card__title">Oylik Investitsiya</h2>
            <span class="fct-card__badge" style="color:#818cf8; background:rgba(129,140,248,.12)">Sarflangan kapital</span>
          </div>
          <div class="fct-chart__body">
            <svg v-if="investChart.pts.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H" preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
              <defs>
                <!-- Multi-stop gradient for rich area fill -->
                <linearGradient id="fctInvGr" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="#818cf8" stop-opacity="0.35"/>
                  <stop offset="40%" stop-color="#818cf8" stop-opacity="0.15"/>
                  <stop offset="100%" stop-color="#818cf8" stop-opacity="0.02"/>
                </linearGradient>
                <!-- Glow filter for hover dot -->
                <filter id="fctDotGlow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="3" result="blur"/>
                  <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                </filter>
              </defs>

              <!-- Horizontal grid lines -->
              <line v-for="(t,i) in investChart.yTicks" :key="'ig'+i"
                :x1="PAD.l" :y1="t.y" :x2="CHART_W - PAD.r" :y2="t.y"
                class="fct-chart__grid"/>

              <!-- Y-axis labels -->
              <text v-for="(t,i) in investChart.yTicks" :key="'il'+i"
                :x="PAD.l - 8" :y="t.y + 3.5"
                class="fct-chart__ylab">{{ fmtAxis(t.v) }}</text>

              <!-- X-axis labels with skip/rotate logic -->
              <text v-for="(p,i) in investChart.pts" :key="'ix'+i"
                v-show="i % investChart.labelSkip === 0"
                :x="p.x" :y="CHART_H - PAD.b + (investChart.rotateLabels ? 18 : 16)"
                class="fct-chart__xlab"
                :class="{ 'fct-chart__xlab--rotated': investChart.rotateLabels }"
                :transform="investChart.rotateLabels ? 'rotate(-45 ' + p.x + ' ' + (CHART_H - PAD.b + 18) + ')' : ''">{{ p.label }}</text>

              <!-- Area fill (gradient) -->
              <path :d="investChart.area" fill="url(#fctInvGr)" class="fct-chart__area"/>

              <!-- Main line -->
              <path :d="investChart.path" fill="none" stroke="#818cf8" stroke-width="2.5"
                stroke-linecap="round" stroke-linejoin="round" class="fct-chart__line"/>

              <!-- Vertical crosshair guide line (shows on hover) -->
              <line v-if="crosshair.show"
                :x1="crosshair.x" :y1="PAD.t"
                :x2="crosshair.x" :y2="CHART_H - PAD.b"
                class="fct-chart__crosshair"/>

              <!-- Data points: normal state -->
              <circle v-for="(p,i) in investChart.pts" :key="'ip'+i"
                :cx="p.x" :cy="p.y"
                :r="crosshair.idx === i ? 7 : 4"
                fill="#818cf8"
                :stroke="isDark ? '#12151e' : '#fff'" stroke-width="2.5"
                :filter="crosshair.idx === i ? 'url(#fctDotGlow)' : ''"
                class="fct-chart__dot"
                :class="{ 'fct-chart__dot--active': crosshair.idx === i }"/>

              <!-- Invisible hover zones per data point -->
              <rect v-for="(p,i) in investChart.pts" :key="'ih'+i"
                :x="i === 0 ? PAD.l : (investChart.pts[i-1].x + p.x) / 2"
                :y="PAD.t"
                :width="i === 0 ? (investChart.pts.length > 1 ? (investChart.pts[1].x - p.x) / 2 + (p.x - PAD.l) : CHART_W - PAD.l - PAD.r) : (i === investChart.pts.length - 1 ? (CHART_W - PAD.r) - (investChart.pts[i-1].x + p.x) / 2 : (investChart.pts[Math.min(i+1, investChart.pts.length-1)].x - investChart.pts[Math.max(i-1, 0)].x) / 2)"
                :height="CHART_H - PAD.t - PAD.b"
                fill="transparent"
                @mouseenter="tipInvest($event, p, i)"
                @mouseleave="hideInvestTip()"
                style="cursor:crosshair"/>
            </svg>
            <div v-else class="fct-chart__empty">Tanlangan davr uchun investitsiya ma'lumoti yo'q</div>
          </div>
        </div>

        <!-- ─── ACTUAL vs EXPECTED: Grouped Bar Chart ─────────────────── -->
        <div class="fct-card fct-chart-card">
          <div class="fct-card__hd">
            <h2 class="fct-card__title">Haqiqiy va Kutilgan Yig'imlar</h2>
            <div class="fct-chart__legend">
              <span><span class="fct-chart__lsym fct-chart__lsym--bar" style="background:#60a5fa"></span>Kutilgan</span>
              <span><span class="fct-chart__lsym fct-chart__lsym--bar" style="background:#34d399"></span>Haqiqiy</span>
            </div>
          </div>
          <div class="fct-chart__body">
            <svg v-if="collChart.bars?.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H" preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
              <!-- Horizontal grid -->
              <line v-for="(t,i) in collChart.yTicks" :key="'cg'+i"
                :x1="PAD.l" :y1="t.y" :x2="CHART_W - PAD.r" :y2="t.y"
                class="fct-chart__grid"/>

              <!-- Y-axis labels -->
              <text v-for="(t,i) in collChart.yTicks" :key="'cl'+i"
                :x="PAD.l - 8" :y="t.y + 3.5"
                class="fct-chart__ylab">{{ fmtAxis(t.v) }}</text>

              <!-- X-axis labels with skip/rotate -->
              <text v-for="(l,i) in collChart.labels" :key="'cx'+i"
                v-show="i % collChart.labelSkip === 0"
                :x="l.x" :y="CHART_H - PAD.b + (collChart.rotateLabels ? 18 : 16)"
                class="fct-chart__xlab"
                :class="{ 'fct-chart__xlab--rotated': collChart.rotateLabels }"
                :transform="collChart.rotateLabels ? 'rotate(-45 ' + l.x + ' ' + (CHART_H - PAD.b + 18) + ')' : ''">{{ l.label }}</text>

              <!-- Grouped Bars -->
              <rect
                v-for="(bar,i) in collChart.bars"
                :key="'bar'+i"
                :x="bar.x"
                :y="bar.y"
                :width="bar.width"
                :height="Math.max(0, bar.height)"
                :fill="bar.color"
                :opacity="bar.type === 'expected' ? 0.8 : 1"
                rx="2"
                class="fct-chart__bar"
                @mouseenter="tipCollBar($event, bar)"
                @mouseleave="hideTip()"
                style="cursor:pointer"/>
            </svg>
            <div v-else class="fct-chart__empty">Tanlangan davr uchun yig'im ma'lumoti yo'q</div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════
           NEW CHARTS ROW: Net Profit & Contract Count (Bar Charts)
           ═══════════════════════════════════════════════════════════════ -->
      <div class="fct-charts-duo">

        <!-- ─── MONTHLY NET PROFIT: Bar Chart ─────────────────────────── -->
        <div class="fct-card fct-chart-card">
          <div class="fct-card__hd">
            <h2 class="fct-card__title">Oylik Sof Foyda</h2>
            <span class="fct-card__badge" style="color:#10b981; background:rgba(16,185,129,.12)">Foyda</span>
          </div>
          <div class="fct-chart__body">
            <svg v-if="netProfitChart.bars?.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H" preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
              <!-- Horizontal grid -->
              <line v-for="(t,i) in netProfitChart.yTicks" :key="'npg'+i"
                :x1="PAD.l" :y1="t.y" :x2="CHART_W - PAD.r" :y2="t.y"
                class="fct-chart__grid"/>

              <!-- Y-axis labels -->
              <text v-for="(t,i) in netProfitChart.yTicks" :key="'npl'+i"
                :x="PAD.l - 8" :y="t.y + 3.5"
                class="fct-chart__ylab">{{ fmtAxis(t.v) }}</text>

              <!-- X-axis labels with skip/rotate -->
              <text v-for="(bar,i) in netProfitChart.bars" :key="'npx'+i"
                v-show="i % netProfitChart.labelSkip === 0"
                :x="bar.x + bar.width/2" :y="CHART_H - PAD.b + (netProfitChart.rotateLabels ? 18 : 16)"
                class="fct-chart__xlab"
                :class="{ 'fct-chart__xlab--rotated': netProfitChart.rotateLabels }"
                :transform="netProfitChart.rotateLabels ? 'rotate(-45 ' + (bar.x + bar.width/2) + ' ' + (CHART_H - PAD.b + 18) + ')' : ''">{{ bar.label }}</text>

              <!-- Bars -->
              <rect
                v-for="(bar,i) in netProfitChart.bars"
                :key="'npbar'+i"
                :x="bar.x"
                :y="bar.y"
                :width="bar.width"
                :height="Math.max(0, bar.height)"
                :fill="bar.color"
                rx="3"
                class="fct-chart__bar"
                @mouseenter="tipNetProfit($event, bar)"
                @mouseleave="hideTip()"
                style="cursor:pointer"/>
            </svg>
            <div v-else class="fct-chart__empty">Tanlangan davr uchun foyda ma'lumoti yo'q</div>
          </div>
        </div>

        <!-- ─── MONTHLY CONTRACT COUNT: Bar Chart ─────────────────────── -->
        <div class="fct-card fct-chart-card">
          <div class="fct-card__hd">
            <h2 class="fct-card__title">Shartnomalar Soni</h2>
            <span class="fct-card__badge" style="color:#6366f1; background:rgba(99,102,241,.12)">Oylik</span>
          </div>
          <div class="fct-chart__body">
            <svg v-if="contractCountChart.bars?.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H" preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
              <!-- Horizontal grid -->
              <line v-for="(t,i) in contractCountChart.yTicks" :key="'ccg'+i"
                :x1="PAD.l" :y1="t.y" :x2="CHART_W - PAD.r" :y2="t.y"
                class="fct-chart__grid"/>

              <!-- Y-axis labels (count, no dollar sign) -->
              <text v-for="(t,i) in contractCountChart.yTicks" :key="'ccl'+i"
                :x="PAD.l - 8" :y="t.y + 3.5"
                class="fct-chart__ylab">{{ Math.round(t.v) }}</text>

              <!-- X-axis labels with skip/rotate -->
              <text v-for="(bar,i) in contractCountChart.bars" :key="'ccx'+i"
                v-show="i % contractCountChart.labelSkip === 0"
                :x="bar.x + bar.width/2" :y="CHART_H - PAD.b + (contractCountChart.rotateLabels ? 18 : 16)"
                class="fct-chart__xlab"
                :class="{ 'fct-chart__xlab--rotated': contractCountChart.rotateLabels }"
                :transform="contractCountChart.rotateLabels ? 'rotate(-45 ' + (bar.x + bar.width/2) + ' ' + (CHART_H - PAD.b + 18) + ')' : ''">{{ bar.label }}</text>

              <!-- Bars -->
              <rect
                v-for="(bar,i) in contractCountChart.bars"
                :key="'ccbar'+i"
                :x="bar.x"
                :y="bar.y"
                :width="bar.width"
                :height="Math.max(0, bar.height)"
                :fill="bar.color"
                rx="3"
                class="fct-chart__bar"
                @mouseenter="tipContractCount($event, bar)"
                @mouseleave="hideTip()"
                style="cursor:pointer"/>
            </svg>
            <div v-else class="fct-chart__empty">Tanlangan davr uchun shartnoma ma'lumoti yo'q</div>
          </div>
        </div>
      </div>
    </section>
  </main>

  <!-- TOOLTIP -->
  <teleport to="body">
    <div v-if="tip.show" class="fct-tip" :class="{ 'fct-tip--dark': isDark }" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">
      <div class="fct-tip__title">{{ tip.title }}</div>
      <div v-for="(r,i) in tip.rows" :key="i" class="fct-tip__row">
        <span :style="{ color: r.c }">{{ r.k }}</span>
        <strong>{{ r.v }}</strong>
      </div>
    </div>
  </teleport>
</div>
`;


// ═══════════════════════════════════════════════════════════════════════════════
// FCT_STYLES — Production Optimized CSS (v4)
// ═══════════════════════════════════════════════════════════════════════════════

const FCT_STYLES = `

/* ═══ RESET & ROOT ═══════════════════════════════════════════════════════════ */

.fct {
  --fct-bg-0: #f4f5f7;
  --fct-bg-1: #ffffff;
  --fct-bg-2: #f8f9fb;
  --fct-bg-glass: rgba(255,255,255,.72);
  --fct-bdr: #e3e5ea;
  --fct-bdr-subtle: #eef0f4;
  --fct-tx-0: #111318;
  --fct-tx-1: #3d4152;
  --fct-tx-2: #8590a5;
  --fct-tx-3: #b0b8c9;
  --fct-sh-card: 0 1px 3px rgba(17,19,24,.04), 0 0 0 1px rgba(17,19,24,.03);
  --fct-sh-hover: 0 8px 24px rgba(17,19,24,.07), 0 0 0 1px rgba(17,19,24,.04);
  --fct-sh-float: 0 12px 40px rgba(17,19,24,.12), 0 0 0 1px rgba(17,19,24,.05);
  --fct-radius: 14px;
  --fct-radius-sm: 10px;
  --fct-radius-xs: 7px;

  font-family: 'Instrument Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--fct-bg-0);
  color: var(--fct-tx-0);
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

.fct--dark {
  --fct-bg-0: #0b0d14;
  --fct-bg-1: #12151e;
  --fct-bg-2: #181b26;
  --fct-bg-glass: rgba(18,21,30,.78);
  --fct-bdr: #1f2330;
  --fct-bdr-subtle: #1a1d28;
  --fct-tx-0: #e8eaef;
  --fct-tx-1: #a0a7b8;
  --fct-tx-2: #5f677a;
  --fct-tx-3: #3a3f50;
  --fct-sh-card: 0 1px 3px rgba(0,0,0,.2), 0 0 0 1px rgba(255,255,255,.03);
  --fct-sh-hover: 0 8px 24px rgba(0,0,0,.3), 0 0 0 1px rgba(255,255,255,.04);
  --fct-sh-float: 0 12px 40px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.06);
}

.fct *, .fct *::before, .fct *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ═══ HEADER ═════════════════════════════════════════════════════════════════ */

.fct-hd {
  position: sticky; top: 0; z-index: 80;
  background: var(--fct-bg-glass);
  backdrop-filter: blur(20px) saturate(1.3);
  -webkit-backdrop-filter: blur(20px) saturate(1.3);
  border-bottom: 1px solid var(--fct-bdr);
}

.fct-hd__inner {
  max-width: 1600px; margin: 0 auto;
  padding: 10px 28px;
  display: flex; align-items: center; gap: 20px;
  flex-wrap: wrap;
}

.fct-hd__brand { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.fct-hd__logo svg { display: block; }
.fct-hd__title { font-size: 17px; font-weight: 700; letter-spacing: -.025em; color: var(--fct-tx-0); }
.fct-hd__meta { display: flex; align-items: center; gap: 8px; margin-top: 1px; }
.fct-hd__pill { font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 5px; color: var(--fct-tx-2); }
.fct-hd__dot { width: 6px; height: 6px; border-radius: 50%; }
.fct-hd__dot--live { background: #34d399; box-shadow: 0 0 6px #34d39966; }
.fct-hd__dot--load { background: #fbbf24; animation: fctPulse 1.2s ease-in-out infinite; }
.fct-hd__pill--load { color: #fbbf24; }
.fct-hd__ts { font-size: 11px; color: var(--fct-tx-3); }

.fct-hd__nav {
  display: flex; gap: 3px; margin-left: auto;
  background: var(--fct-bg-2); border: 1px solid var(--fct-bdr);
  border-radius: var(--fct-radius-sm); padding: 3px;
}
.fct-hd__tab {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 18px; border: none; border-radius: var(--fct-radius-xs);
  background: transparent; color: var(--fct-tx-2);
  font-size: 13px; font-weight: 600; font-family: inherit; cursor: pointer;
  transition: all .2s ease; white-space: nowrap;
}
.fct-hd__tab:hover { color: var(--fct-tx-1); background: var(--fct-bg-1); }
.fct-hd__tab--on {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
  color: #fff !important;
  box-shadow: 0 2px 10px rgba(99,102,241,.35);
}

.fct-hd__actions { display: flex; gap: 6px; }
.fct-hd__btn {
  width: 36px; height: 36px; border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs);
  background: var(--fct-bg-1); color: var(--fct-tx-2); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .2s;
}
.fct-hd__btn:hover { background: var(--fct-bg-2); color: var(--fct-tx-1); border-color: var(--fct-tx-3); }
.fct-hd__btn:disabled { opacity: .5; cursor: not-allowed; }

/* ═══ ERROR BAR ══════════════════════════════════════════════════════════════ */

.fct-err {
  max-width: 1600px; margin: 0 auto;
  padding: 10px 28px; display: flex; align-items: center; gap: 10px;
  background: #fef2f2; border-bottom: 1px solid #fecaca; color: #b91c1c; font-size: 13px;
}
.fct--dark .fct-err { background: #1a0808; border-color: #450a0a; color: #fca5a5; }
.fct-err__btn {
  margin-left: auto; padding: 3px 12px; border: 1px solid currentColor; border-radius: var(--fct-radius-xs);
  background: transparent; color: inherit; font-size: 12px; font-family: inherit; cursor: pointer;
}
.fct-err__x {
  padding: 2px 8px; border: none; background: transparent; color: inherit;
  font-size: 18px; cursor: pointer; line-height: 1;
}

/* ═══ BODY ═══════════════════════════════════════════════════════════════════ */

.fct-body {
  max-width: 1600px; margin: 0 auto; padding: 24px 28px;
  position: relative; min-height: 65vh;
}

.fct-v { animation: fctFadeUp .35s ease both; }

/* ═══ LOADER ═════════════════════════════════════════════════════════════════ */

.fct-loader {
  position: absolute; inset: 0; z-index: 60;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px;
  background: color-mix(in srgb, var(--fct-bg-0) 82%, transparent);
  backdrop-filter: blur(6px); border-radius: var(--fct-radius);
}
.fct-loader__ring {
  width: 36px; height: 36px; border: 3px solid var(--fct-bdr); border-top-color: #818cf8;
  border-radius: 50%; animation: fctSpin .7s linear infinite;
}
.fct-loader p { font-size: 13px; color: var(--fct-tx-2); }

.fct-pbar {
  height: 3px; background: var(--fct-bdr); border-radius: 2px; overflow: hidden; margin-bottom: 20px;
}
.fct-pbar__fill {
  height: 100%; width: 30%; background: linear-gradient(90deg, #818cf8, #a78bfa);
  border-radius: 2px; animation: fctProgress 1.5s ease-in-out infinite;
}

/* ═══ CARDS ══════════════════════════════════════════════════════════════════ */

.fct-card {
  background: var(--fct-bg-1); border: 1px solid var(--fct-bdr);
  border-radius: var(--fct-radius); box-shadow: var(--fct-sh-card);
  transition: box-shadow .25s ease;
}
.fct-card:hover { box-shadow: var(--fct-sh-hover); }
.fct-card__hd {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 22px 0;
}
.fct-card__title { font-size: 15px; font-weight: 700; letter-spacing: -.015em; color: var(--fct-tx-0); }
.fct-card__badge {
  font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px;
  letter-spacing: .02em;
}

/* ═══ KPI GRID ═══════════════════════════════════════════════════════════════ */

.fct-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(185px, 1fr));
  gap: 14px; margin-bottom: 18px;
}

.fct-kpi {
  background: var(--fct-bg-1); border: 1px solid var(--fct-bdr);
  border-radius: var(--fct-radius); padding: 16px 18px 12px;
  box-shadow: var(--fct-sh-card); position: relative; overflow: hidden;
  transition: all .25s ease; animation: fctSlideUp .4s ease both;
}
.fct-kpi::after {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--kpi-accent); opacity: .85;
}
.fct-kpi:hover { transform: translateY(-2px); box-shadow: var(--fct-sh-hover); }

.fct-kpi__head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.fct-kpi__label { font-size: 11.5px; font-weight: 600; color: var(--fct-tx-2); text-transform: uppercase; letter-spacing: .04em; }
.fct-kpi__icon { opacity: .45; }
.fct-kpi__val { font-size: 24px; font-weight: 800; letter-spacing: -.035em; font-variant-numeric: tabular-nums; color: var(--fct-tx-0); }
.fct-kpi__bar { height: 3px; background: var(--fct-bdr-subtle); border-radius: 2px; margin-top: 10px; overflow: hidden; }
.fct-kpi__barfill { height: 100%; width: 60%; background: var(--kpi-accent); border-radius: 2px; opacity: .3; }

/* ═══ DUO ROW (ROI + Summary) ═══════════════════════════════════════════════ */

.fct-duo { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px; }

.fct-roi__body { padding: 18px 22px 20px; display: flex; align-items: center; gap: 24px; flex-wrap: wrap; justify-content: center; }
.fct-roi__donut { position: relative; width: 155px; height: 155px; flex-shrink: 0; }
.fct-roi__svg { width: 100%; height: 100%; }
.fct-roi__arc { transition: stroke-dasharray .8s cubic-bezier(.4,0,.2,1); }
.fct-roi__center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.fct-roi__pct { font-size: 28px; font-weight: 800; color: var(--fct-tx-0); letter-spacing: -.04em; }
.fct-roi__lbl { font-size: 11px; color: var(--fct-tx-2); text-transform: uppercase; letter-spacing: .12em; }
.fct-roi__legend { display: flex; flex-direction: column; gap: 10px; }
.fct-roi__li { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--fct-tx-1); }
.fct-roi__li strong { margin-left: auto; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--fct-tx-0); min-width: 60px; text-align: right; }
.fct-roi__dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

.fct-summary__grid { padding: 14px 22px 18px; display: flex; flex-direction: column; gap: 5px; }
.fct-summary__row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 13px; }
.fct-summary__row span { color: var(--fct-tx-1); display: flex; align-items: center; gap: 6px; }
.fct-summary__row strong { font-weight: 700; font-variant-numeric: tabular-nums; font-size: 14px; }
.fct-summary__row--em { padding-top: 6px; }
.fct-summary__hr { height: 1px; background: var(--fct-bdr-subtle); margin: 3px 0; }
.fct-summary__dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.fct-health {
  font-size: 11px; font-weight: 700; padding: 3px 12px; border-radius: 20px;
  border: 1px solid; letter-spacing: .02em;
}

/* ═══ TIER GRID ══════════════════════════════════════════════════════════════ */

.fct-tier-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
}

.fct-tier-col {
  border-top: 3px solid var(--tier-accent);
  display: flex;
  flex-direction: column;
  min-height: 320px;
}

.fct-tier-col__hd {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 18px 12px;
}

.fct-tier-col__search {
  position: relative; display: flex; align-items: center;
  padding: 0 18px 12px;
}
.fct-tier__input--full { width: 100%; }

.fct-tier-col__list {
  flex: 1; overflow-y: auto; max-height: 420px;
  padding: 0 6px;
}

.fct-cust-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 12px; margin: 0 0 2px;
  border-radius: var(--fct-radius-xs);
  transition: background .15s ease;
  cursor: default;
}
.fct-cust-row:hover { background: var(--fct-bg-2); }

.fct-cust-row__info { display: flex; flex-direction: column; gap: 1px; min-width: 0; flex: 1; }
.fct-cust-row__name {
  font-size: 13px; font-weight: 600; color: var(--fct-tx-0);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fct-cust-row__id {
  font-size: 11px; color: var(--fct-tx-3);
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fct-cust-row__debt {
  font-size: 14px; font-weight: 800; font-variant-numeric: tabular-nums;
  font-family: 'JetBrains Mono', monospace;
  white-space: nowrap; padding-left: 12px;
  flex-shrink: 0;
}

.fct-tier-col__foot {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 18px; margin-top: auto;
  border-top: 1px solid var(--fct-bdr);
  font-size: 13px; font-weight: 700; color: var(--fct-tx-1);
}
.fct-tier-col__foot strong {
  font-size: 15px; font-weight: 800;
  font-family: 'JetBrains Mono', monospace;
  font-variant-numeric: tabular-nums;
}
.fct-tier__badge {
  width: 34px; height: 34px; border-radius: var(--fct-radius-xs);
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; flex-shrink: 0;
}
.fct-tier__info { flex: 1; min-width: 150px; }
.fct-tier__title { font-size: 14px; font-weight: 700; color: var(--fct-tx-0); }
.fct-tier__sub { font-size: 12px; color: var(--fct-tx-2); margin-top: 1px; }
.fct-tier__searchico { position: absolute; left: 10px; color: var(--fct-tx-3); pointer-events: none; }
.fct-tier__input {
  padding: 6px 10px 6px 30px; border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs);
  background: var(--fct-bg-2); color: var(--fct-tx-0); font-size: 12px; font-family: inherit;
  outline: none; width: 160px; transition: border-color .2s, box-shadow .2s;
}
.fct-tier__input:focus { border-color: #818cf8; box-shadow: 0 0 0 3px rgba(129,140,248,.12); }
.fct-tier__input::placeholder { color: var(--fct-tx-3); }
.fct-tier__tbl-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.fct-tier__empty { padding: 28px; text-align: center; font-size: 13px; color: var(--fct-tx-3); }

/* ═══ TABLES ═════════════════════════════════════════════════════════════════ */

.fct-tbl { width: 100%; border-collapse: collapse; }
.fct-tbl__th {
  padding: 9px 18px; text-align: left; font-size: 10.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .06em; color: var(--fct-tx-2);
  background: var(--fct-bg-2); border-bottom: 1px solid var(--fct-bdr); white-space: nowrap;
}
.fct-tbl__td { padding: 9px 18px; border-bottom: 1px solid var(--fct-bdr-subtle); color: var(--fct-tx-1); font-size: 13px; }
.fct-tbl__row { transition: background .15s; }
.fct-tbl__row:hover .fct-tbl__td { background: var(--fct-bg-2); }
.fct-tbl--r { text-align: right !important; }
.fct-tbl--mono { font-family: 'JetBrains Mono', monospace; font-size: 12px; }
.fct-tbl--bold { font-weight: 700; color: var(--fct-tx-0); }

.fct-pill {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 2px 9px; border-radius: 10px; font-size: 11px; font-weight: 700; color: #fff;
  min-width: 36px;
}
.fct-pill-g { background: #059669; }
.fct-pill-y { background: #d97706; }
.fct-pill-r { background: #dc2626; }

/* ═══ PERIODIC: DATES ════════════════════════════════════════════════════════ */

.fct-dates { margin-bottom: 18px; display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.fct-dates__fields { display: flex; align-items: flex-end; gap: 10px; }
.fct-dates__f { display: flex; flex-direction: column; gap: 4px; }
.fct-dates__f label { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--fct-tx-2); }
.fct-dates__input {
  padding: 8px 12px; border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs);
  background: var(--fct-bg-1); color: var(--fct-tx-0); font-size: 13px; font-family: inherit;
  outline: none; transition: border-color .2s, box-shadow .2s;
}
.fct-dates__input:focus { border-color: #818cf8; box-shadow: 0 0 0 3px rgba(129,140,248,.1); }
.fct-dates__go {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 18px; border: none; border-radius: var(--fct-radius-xs);
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff;
  font-size: 13px; font-weight: 700; font-family: inherit; cursor: pointer;
  transition: transform .15s, box-shadow .15s;
  box-shadow: 0 2px 10px rgba(99,102,241,.3);
}
.fct-dates__go:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(99,102,241,.4); }
.fct-dates__go:disabled { opacity: .5; cursor: not-allowed; transform: none; }
.fct-dates__presets { display: flex; gap: 4px; }
.fct-dates__pre {
  padding: 8px 13px; border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs);
  background: var(--fct-bg-1); color: var(--fct-tx-2); font-size: 12px; font-weight: 700;
  font-family: inherit; cursor: pointer; transition: all .15s;
}
.fct-dates__pre:hover { border-color: #818cf8; color: #818cf8; background: rgba(129,140,248,.06); }

/* ═══ CHARTS ═════════════════════════════════════════════════════════════════ */

/* v4: Two charts side-by-side on wide screens */
.fct-charts-duo {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-bottom: 18px;
}

.fct-chart-card { padding-bottom: 18px; }
.fct-chart__body { padding: 0 18px; overflow-x: auto; overflow-y: visible; -webkit-overflow-scrolling: touch; }
.fct-chart__svg { width: 100%; height: auto; min-width: 400px; overflow: visible; }
.fct-chart__grid { stroke: var(--fct-tx-2); stroke-width: .8; opacity: .5; stroke-dasharray: 4 4; }

/* ─── Area chart specific ────────────────────────────────────────────────── */
.fct-chart__area {
  transition: opacity .3s ease;
}
.fct-chart__line {
  transition: stroke-width .2s ease;
}

/* ─── Crosshair guide line ───────────────────────────────────────────────── */
.fct-chart__crosshair {
  stroke: var(--fct-tx-2);
  stroke-width: 1;
  stroke-dasharray: 4 3;
  opacity: .6;
  pointer-events: none;
  transition: opacity .15s ease;
}

/* ─── Data dots with hover expansion ─────────────────────────────────────── */
.fct-chart__dot {
  transition: r .2s cubic-bezier(.4,0,.2,1), filter .2s ease;
  cursor: crosshair;
}
.fct-chart__dot--active {
  /* r is set inline via Vue binding, glow via filter */
}

/* ─── Bar chart ──────────────────────────────────────────────────────────── */
.fct-chart__bar {
  transition: opacity .15s ease, filter .15s ease;
}
.fct-chart__bar:hover {
  opacity: 1 !important;
  filter: brightness(1.15) saturate(1.1);
}

/* ─── Axis labels: theme-aware via CSS variables ─────────────────────────── */
.fct-chart__ylab {
  font-size: 10px;
  fill: var(--fct-tx-2);
  font-family: 'JetBrains Mono', monospace;
  text-anchor: end;
}
.fct-chart__xlab {
  font-size: 10px;
  fill: var(--fct-tx-2);
  font-family: 'JetBrains Mono', monospace;
  text-anchor: middle;
}
.fct-chart__xlab--rotated {
  text-anchor: end;
  font-size: 9px;
}

.fct-chart__empty { display: flex; align-items: center; justify-content: center; min-height: 160px; color: var(--fct-tx-3); font-size: 13px; }

.fct-chart__legend { display: flex; gap: 14px; font-size: 12px; color: var(--fct-tx-1); }
.fct-chart__lsym { display: inline-block; vertical-align: middle; margin-right: 4px; }
.fct-chart__lsym--bar { width: 10px; height: 10px; border-radius: 2px; }

/* ═══ EFFICIENCY TABLE ═══════════════════════════════════════════════════════ */

.fct-eff { margin-bottom: 22px; }
.fct-eff__cell { display: flex; align-items: center; gap: 10px; justify-content: flex-end; }
.fct-eff__track { width: 70px; height: 6px; background: var(--fct-bdr); border-radius: 3px; overflow: hidden; flex-shrink: 0; }
.fct-eff__bar { height: 100%; border-radius: 3px; transition: width .5s cubic-bezier(.4,0,.2,1); }
.fct-eff__num { font-size: 12px; font-weight: 800; font-variant-numeric: tabular-nums; min-width: 44px; text-align: right; font-family: 'JetBrains Mono', monospace; }

/* ═══ TOOLTIP ════════════════════════════════════════════════════════════════ */

.fct-tip {
  position: fixed; z-index: 9999; pointer-events: none;
  background: var(--fct-bg-1, #fff); border: 1px solid var(--fct-bdr, #e3e5ea); border-radius: 10px;
  padding: 10px 14px; box-shadow: 0 10px 30px rgba(0,0,0,.12);
  font-size: 12px; min-width: 150px; max-width: 260px;
  backdrop-filter: blur(12px);
  animation: fctTipIn .15s ease;
}
.fct-tip--dark { background: #1a1d28; border-color: #2a2e3a; box-shadow: 0 10px 30px rgba(0,0,0,.4); color: #e8eaef; }
.fct-tip__title { font-weight: 700; margin-bottom: 6px; font-size: 13px; color: var(--fct-tx-0, #111); }
.fct-tip--dark .fct-tip__title { color: #e8eaef; }
.fct-tip__row { display: flex; justify-content: space-between; gap: 16px; padding: 2px 0; }
.fct-tip__row strong { font-weight: 700; color: var(--fct-tx-0, #111); }
.fct-tip--dark .fct-tip__row strong { color: #e8eaef; }

/* ═══ ANIMATIONS ═════════════════════════════════════════════════════════════ */

@keyframes fctFadeUp { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fctSlideUp { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fctSpin { to { transform: rotate(360deg); } }
@keyframes fctPulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
@keyframes fctProgress { 0% { transform: translateX(-100%); } 100% { transform: translateX(400%); } }
@keyframes fctTipIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

.fct-spin { animation: fctSpin .7s linear infinite; }
.fct-fade-enter-active { transition: opacity .3s ease; }
.fct-fade-leave-active { transition: opacity .2s ease; }
.fct-fade-enter-from, .fct-fade-leave-to { opacity: 0; }

/* ═══ RESPONSIVE ═════════════════════════════════════════════════════════════ */

@media (max-width: 1200px) {
  .fct-charts-duo { grid-template-columns: 1fr; }
}

@media (max-width: 1023px) {
  .fct-duo    { grid-template-columns: 1fr; gap: 14px; }
  .fct-charts-duo { grid-template-columns: 1fr; gap: 14px; }
  .fct-tier-grid { grid-template-columns: 1fr; gap: 14px; }
  .fct-tier-col { min-height: auto; }
  .fct-tier-col__list { max-height: 320px; }
}

@media (min-width: 641px) and (max-width: 1023px) {
  .fct-hd__inner  { padding: 10px 20px; gap: 14px; }
  .fct-body       { padding: 20px; }
  .fct-kpis       { grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .fct-kpi        { padding: 14px 14px 10px; }
  .fct-kpi__val   { font-size: 21px; }
  .fct-card__hd   { padding: 14px 18px 0; }
  .fct-roi__body  { gap: 18px; }
  .fct-tbl__th,
  .fct-tbl__td    { padding: 8px 14px; }
  .fct-dates      { gap: 10px; }
  .fct-chart__body { padding: 0 14px; }
}

@media (max-width: 640px) {
  .fct-hd__inner {
    padding: 8px 14px;
    gap: 8px;
    flex-wrap: wrap;
  }
  .fct-hd__brand  { flex: 1 1 auto; min-width: 0; }
  .fct-hd__logo svg { width: 24px; height: 24px; }
  .fct-hd__title  { font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
  .fct-hd__ts     { display: none; }
  .fct-hd__actions { flex-shrink: 0; }
  .fct-hd__nav    { order: 10; width: 100%; margin-left: 0; }
  .fct-hd__tab    { flex: 1; justify-content: center; padding: 7px 10px; font-size: 12px; }

  .fct-body { padding: 12px 14px; min-height: 50vh; }

  .fct-kpis     { grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
  .fct-kpi      { padding: 12px 12px 9px; }
  .fct-kpi__val { font-size: 20px; }
  .fct-kpi__label { font-size: 10px; }
  .fct-kpi__icon  { width: 15px; height: 15px; }

  .fct-duo { margin-bottom: 12px; }

  .fct-roi__body    { flex-direction: column; align-items: center; gap: 14px; padding: 14px 14px 16px; }
  .fct-roi__donut   { width: 140px; height: 140px; }
  .fct-roi__pct     { font-size: 24px; }
  .fct-roi__legend  { flex-direction: row; flex-wrap: wrap; gap: 12px; justify-content: center; }
  .fct-roi__li strong { min-width: auto; margin-left: 6px; }

  .fct-card__hd   { padding: 12px 14px 0; flex-wrap: wrap; gap: 6px; }
  .fct-card__title { font-size: 14px; }

  .fct-summary__grid { padding: 10px 14px 14px; }
  .fct-summary__row  { font-size: 12px; }
  .fct-summary__row strong { font-size: 13px; }

  .fct-tier-grid    { grid-template-columns: 1fr; gap: 10px; }
  .fct-tier-col__hd { padding: 12px 14px 8px; }
  .fct-tier-col__search { padding: 0 14px 10px; }
  .fct-tier-col__list { max-height: 280px; }
  .fct-cust-row     { padding: 8px 10px; }
  .fct-cust-row__name { font-size: 12px; }
  .fct-cust-row__debt { font-size: 13px; }
  .fct-tier-col__foot { padding: 10px 14px; font-size: 12px; }

  .fct-tbl__th  { padding: 8px 10px; font-size: 9.5px; }
  .fct-tbl__td  { padding: 8px 10px; font-size: 12px; }

  .fct-charts-duo  { margin-bottom: 12px; gap: 10px; }
  .fct-chart__body { padding: 0 10px; }
  .fct-chart__svg  { min-width: 340px; }

  .fct-dates        { flex-direction: column; align-items: stretch; gap: 10px; margin-bottom: 14px; }
  .fct-dates__fields { flex-wrap: wrap; gap: 8px; }
  .fct-dates__f     { flex: 1 1 130px; }
  .fct-dates__input { width: 100%; }
  .fct-dates__go    { align-self: flex-start; }
  .fct-dates__presets { flex-wrap: wrap; gap: 4px; }
  .fct-dates__pre   { flex: 1; text-align: center; }

  .fct-eff__track { width: 50px; }

  .fct-err { padding: 8px 14px; font-size: 12px; }
}

@media (max-width: 400px) {
  .fct-hd__inner  { padding: 8px 10px; }
  .fct-hd__title  { font-size: 13px; max-width: 140px; }
  .fct-hd__logo svg { width: 20px; height: 20px; }
  .fct-hd__btn    { width: 32px; height: 32px; }
  .fct-hd__pill   { display: none; }
  .fct-body       { padding: 10px; }
  .fct-kpis       { gap: 8px; }
  .fct-kpi        { padding: 10px 10px 8px; }
  .fct-kpi__val   { font-size: 18px; }
  .fct-dates__presets { gap: 3px; }
  .fct-dates__pre { padding: 7px 8px; font-size: 11px; }
}

@media (min-width: 1800px) {
  .fct-body { max-width: 1920px; padding: 28px 48px; }
  .fct-kpis { grid-template-columns: repeat(7, 1fr); }
  .fct-duo  { grid-template-columns: 420px 1fr; }
  .fct-charts-duo { grid-template-columns: 1fr 1fr; gap: 22px; }
  .fct-tier-col__list { max-height: 560px; }
}

@media print {
  .fct-hd { position: static; backdrop-filter: none; }
  .fct-hd__actions, .fct-hd__nav { display: none; }
  .fct-kpi:hover, .fct-card:hover { transform: none; box-shadow: var(--fct-sh-card); }
  .fct-body { padding: 0; }
}

/* ═══ FRAPPE OVERRIDES ═══════════════════════════════════════════════════════ */
.page-container[data-page-container] { background: transparent !important; max-width: 100% !important; width: 100% !important; }
#fct-mount .page-content { padding: 0 !important; }
#fct-mount { width: 100% !important; }
.main-section .container { max-width: 100% !important; width: 100% !important; padding: 0 !important; }
.main-section .layout-main { max-width: 100% !important; }
.layout-main-section-wrapper { max-width: 100% !important; }
.page-body .main-section { max-width: 100% !important; }
`;
