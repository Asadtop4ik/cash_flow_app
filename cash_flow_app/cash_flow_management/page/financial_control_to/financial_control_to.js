/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * FINANCIAL CONTROL TOWER - PRODUCTION OPTIMIZED v4.1
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Single-file Frappe v15 Custom Page — zero external dependencies.
 * Mounts a Vue 3 reactive dashboard using Frappe's bundled Vue.
 *
 * v4.1 CHANGES:
 *   - "Umumiy Ma'lumotlar" REPLACED with Contract Installation Tracker
 *   - Added search-based contract analysis with FIFO payment reconciliation
 *   - Search debounce: 300ms, minimum 3 characters
 *   - Real-time payment status: Paid / Partially Paid / Unpaid
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

	// ─── Ancestor traversal: walk every DOM node from the mount point up to
	// document.body and neutralise width constraints via inline important styles.
	// Inline !important beats any stylesheet !important — no selector guessing,
	// no specificity wars, Frappe-version-agnostic.
	function _releaseAncestors(startEl) {
		let node = startEl.parentElement;
		while (node && node !== document.body) {
			node.style.setProperty('max-width',     '100%',       'important');
			node.style.setProperty('width',         '100%',       'important');
			node.style.setProperty('padding-left',  '0',          'important');
			node.style.setProperty('padding-right', '0',          'important');
			node.style.setProperty('margin-left',   '0',          'important');
			node.style.setProperty('margin-right',  '0',          'important');
			node.style.setProperty('box-sizing',    'border-box', 'important');
			node = node.parentElement;
		}
	}

	_injectOnce('fct-font', 'link', {
		rel: 'stylesheet',
		href: 'https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap'
	});

	_injectOnce('fct-css', 'style', {}, FCT_STYLES);

	const mountEl = document.createElement('div');
	mountEl.id = 'fct-mount';
	page.main[0].innerHTML = '';
	page.main[0].appendChild(mountEl);
	_releaseAncestors(mountEl); // parentElement chain is established — safe to traverse

	function _initVueApp() {
		const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = Vue;

		const app = createApp({
			template: PAGE_TEMPLATE,
			setup() {
				// ═══════════════════════════════════════════════════════════
				// REACTIVE STATE
				// ═══════════════════════════════════════════════════════════
				const current_view = ref('general');
				const loading = ref(false);
				const loadingPeriodic = ref(false);
				const error = ref(null);
				const isDark = ref(false);
				const lastRefresh = ref(null);

				const kpis = ref({});
				const roi = ref({});
				const tiers = ref({ A: [], B: [], C: [] });

				const periodic = ref({ monthly_investment: [], collection_efficiency: [], net_profit: [], contract_count: [], monthly_sales: [], monthly_margin:[] });
				const dateFrom = ref(_monthsAgo(12));
				const dateTo = ref(_today());

				const tip = reactive({ show: false, x: 0, y: 0, title: '', rows: [] });
				const tierSearch = reactive({ A: '', B: '', C: '' });
				const crosshair = reactive({ show: false, x: 0, idx: -1 });

				// ═══════════════════════════════════════════════════════════
				// CONTRACT SEARCH STATE (v4.1)
				// ═══════════════════════════════════════════════════════════
				const contractSearch = reactive({
					query: '',
					loading: false,
					result: null,
					error: null,
					suggestions: [],
					showDropdown: false,
					searchLoading: false
				});
				let searchDebounceTimer = null;

				// ═══════════════════════════════════════════════════════════
				// CHART DIMENSIONS
				// ═══════════════════════════════════════════════════════════
				const CHART_W = 720;
				const CHART_H = 280;
				const PAD = { t: 20, r: 24, b: 65, l: 62 };

				const tierMeta = [
					{ key: 'A', title: 'A toifadagi mijozlar', sub: 'A toifadagi mijozlar', accent: '#34d399', accentBg: 'rgba(52,211,153,.12)', icon: '✓' },
					{ key: 'B', title: 'B toifadagi mijozlar', sub: 'B toifadagi mijozlar', accent: '#fbbf24', accentBg: 'rgba(251,191,36,.12)', icon: '⚡' },
					{ key: 'C', title: 'C toifadagi mijozlar', sub: 'C toifadagi mijozlar', accent: '#f87171', accentBg: 'rgba(248,113,113,.12)', icon: '⚠' }
				];

				const presets = [
					{ label: '3O', m: 3 }, { label: '6O', m: 6 },
					{ label: '1Y', m: 12 }, { label: '2Y', m: 24 },
					{ label: 'YB', ytd: true }
				];

				// ═══════════════════════════════════════════════════════════
				// COMPUTED: KPI Cards
				// ═══════════════════════════════════════════════════════════
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

				// ═══════════════════════════════════════════════════════════
				// COMPUTED: ROI Donut
				// ═══════════════════════════════════════════════════════════
				const donut = computed(() => {
					const cd = roi.value.chart_data || {};
					const total = cd.total || 1;
					const interest = cd.interest || 0;
					const C = 2 * Math.PI * 76;
					const iLen = (interest / total) * C;
					return {
						pct: Math.round(roi.value.roi_percentage || 0),
						interest: roi.value.net_profit || 0,
						principal: roi.value.invested_capital || 0,
						iDash: `${iLen} ${C - iLen}`,
						pDash: `${C - iLen} ${iLen}`,
						iOff: 0,
						pOff: -iLen
					};
				});

				// ═══════════════════════════════════════════════════════════
				// COMPUTED: Health
				// ═══════════════════════════════════════════════════════════
				const health = computed(() => {
					const d = kpis.value.total_debt || 0;
					if (d === 0) return { label: 'A\'lo', color: '#34d399' };
					const r = (kpis.value.debt_c || 0) / d;
					if (r > .3) return { label: 'Kritik', color: '#f87171' };
					if (r > .15) return { label: 'Xavfli', color: '#fb923c' };
					if (r > .05) return { label: 'O\'rtacha', color: '#fbbf24' };
					return { label: 'Yaxshi', color: '#34d399' };
				});

				// ═══════════════════════════════════════════════════════════
				// COMPUTED: Filtered Tier Rows
				// ═══════════════════════════════════════════════════════════
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

				// ═══════════════════════════════════════════════════════════
				// CHART MATH — AREA CHART
				// ═══════════════════════════════════════════════════════════

				function _calcLabelSkip(count) {
					if (count <= 6) return 1;
					if (count <= 12) return 2;
					if (count <= 18) return 3;
					return Math.ceil(count / 8);
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

					return { pts, yTicks, path, area, labelSkip: _calcLabelSkip(data.length), rotateLabels: _shouldRotateLabels(data.length) };
				}

				// ═══════════════════════════════════════════════════════════
				// CHART MATH — GROUPED BAR CHART
				// ═══════════════════════════════════════════════════════════

				function _dualScale(data) {
					if (!data?.length) return { bars: [], yTicks: [], labels: [], labelSkip: 1, rotateLabels: false };
					const pw = CHART_W - PAD.l - PAD.r;
					const ph = CHART_H - PAD.t - PAD.b;
					const mx = Math.max(...data.map(d => Math.max(d.expected || 0, d.actual || 0)), 1);
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
						const expH = Math.max(1, ((d.expected || 0) / mx) * ph);
						bars.push({ type: 'expected', x: groupX, y: PAD.t + ph - expH, width: barWidth, height: expH, value: d.expected || 0, label: d.label || '', color: '#60a5fa', index: i });
						const actH = Math.max(1, ((d.actual || 0) / mx) * ph);
						bars.push({ type: 'actual', x: groupX + barWidth + barGap, y: PAD.t + ph - actH, width: barWidth, height: actH, value: d.actual || 0, label: d.label || '', color: '#34d399', index: i });
						labels.push({ x: centerX, label: d.label || '', efficiency: d.efficiency_pct || 0 });
					});

					const yTicks = [];
					for (let i = 0; i <= 4; i++) { const v = (mx / 4) * i; yTicks.push({ v, y: PAD.t + ph - (v / mx) * ph }); }
					return { bars, yTicks, labels, labelSkip: _calcLabelSkip(data.length), rotateLabels: _shouldRotateLabels(data.length) };
				}

				const investChart = computed(() => _scale(periodic.value.monthly_investment, 'amount'));
				const collChart = computed(() => _dualScale(periodic.value.collection_efficiency));

				// ═══════════════════════════════════════════════════════════
				// CHART MATH — SINGLE BAR CHART
				// ═══════════════════════════════════════════════════════════

				function _singleBarScale(data, key, color) {
					if (!data?.length) return { bars: [], yTicks: [], labelSkip: 1, rotateLabels: false };
					const pw = CHART_W - PAD.l - PAD.r;
					const ph = CHART_H - PAD.t - PAD.b;
					const vals = data.map(d => d[key] || 0);
					const mx = Math.max(...vals, 1);
					const groupSlot = pw / data.length;
					const groupPadding = Math.max(6, Math.min(groupSlot * 0.3, 20));
					const barWidth = Math.max(8, Math.min(40, groupSlot - groupPadding));
					const bars = [];

					data.forEach((d, i) => {
						const centerX = PAD.l + (i + 0.5) * groupSlot;
						const barX = centerX - barWidth / 2;
						const barHeight = Math.max(1, ((d[key] || 0) / mx) * ph);
						bars.push({ x: barX, y: PAD.t + ph - barHeight, width: barWidth, height: barHeight, value: d[key] || 0, label: d.label || '', color: color, index: i });
					});

					const yTicks = [];
					for (let i = 0; i <= 4; i++) { const v = (mx / 4) * i; yTicks.push({ v, y: PAD.t + ph - (v / mx) * ph }); }
					return { bars, yTicks, labelSkip: _calcLabelSkip(data.length), rotateLabels: _shouldRotateLabels(data.length) };
				}

				const netProfitChart = computed(() => _singleBarScale(periodic.value.net_profit, 'amount', '#10b981'));
				const contractCountChart = computed(() => _singleBarScale(periodic.value.contract_count, 'count', '#6366f1'));
				const salesChart  = computed(() => _scale(periodic.value.monthly_sales, 'amount'));
				const marginChart = computed(() => _scale(periodic.value.monthly_margin, 'margin_pct'));

				// ═══════════════════════════════════════════════════════════
				// DATA FETCHING
				// ═══════════════════════════════════════════════════════════

				async function fetchGeneral(force = 0) {
					loading.value = true; error.value = null;
					try {
						const r = await frappe.call({ method: `${API_BASE}.get_intelligence_data`, args: { force_refresh: force }, freeze: false });
						const d = r.message;
						if (d?.success) {
							kpis.value = d.kpis || {};
							roi.value = d.roi || {};
							tiers.value = d.tiers || { A: [], B: [], C: [] };
							lastRefresh.value = new Date().toLocaleTimeString();
							if (d._from_cache) lastRefresh.value += ' (cache)';
						} else { error.value = d?.error || 'Ma\'lumot olishda xatolik'; }
					} catch (e) { error.value = e.message || 'Tarmoq xatosi'; }
					finally { loading.value = false; }
				}

				async function fetchPeriodic(force = 0) {
					loadingPeriodic.value = true; error.value = null;
					try {
						const r = await frappe.call({ method: `${API_BASE}.get_periodic_data`, args: { from_date: dateFrom.value, to_date: dateTo.value, force_refresh: force }, freeze: false });
						const d = r.message;
						if (d?.success) {
							periodic.value = {
								monthly_investment: d.monthly_investment || [],
								collection_efficiency: d.collection_efficiency || [],
								net_profit: d.net_profit || [],
								contract_count: d.contract_count || [],
								monthly_sales: d.monthly_sales || [],
								monthly_margin: d.monthly_margin || []
							};
						} else { error.value = d?.error || 'Davriy ma\'lumot olishda xatolik'; }
					} catch (e) { error.value = e.message || 'Tarmoq xatosi'; }
					finally { loadingPeriodic.value = false; }
				}

				// ═══════════════════════════════════════════════════════════
				// CONTRACT SEARCH (v4.1)
				// ═══════════════════════════════════════════════════════════
// ═══════════════════════════════════════════════════════════
			// CONTRACT SELECT (v4.2)
			// ═══════════════════════════════════════════════════════════

				async function fetchSuggestions() {
					if (!contractSearch.query || contractSearch.query.trim().length < 2) {
						contractSearch.suggestions = [];
						contractSearch.showDropdown = false;
						return;
					}
					contractSearch.searchLoading = true;
					try {
						const r = await frappe.call({
							method: `${API_BASE}.search_contracts`,
							args: { search_term: contractSearch.query.trim() },
							freeze: false
						});
						const d = r.message;
						if (d?.success && d.contracts?.length) {
							contractSearch.suggestions = d.contracts;
							contractSearch.showDropdown = true;
						} else {
							contractSearch.suggestions = [];
							contractSearch.showDropdown = true; // "topilmadi" ko'rsatish
						}
					} catch (e) {
						contractSearch.suggestions = [];
					} finally {
						contractSearch.searchLoading = false;
					}
				}

				function onSearchInput() {
					clearTimeout(searchDebounceTimer);
					contractSearch.result = null;
					contractSearch.error = null;
					searchDebounceTimer = setTimeout(() => { fetchSuggestions(); }, 300);
				}

				async function selectContract(contract) {
					contractSearch.showDropdown = false;
					contractSearch.query = contract.name + ' — ' + contract.customer_name;
					contractSearch.loading = true;
					contractSearch.error = null;
					try {
						const r = await frappe.call({
							method: `${API_BASE}.get_contract_installment_analysis`,
							args: { search_term: contract.name },
							freeze: false
						});
						const d = r.message;
						if (d?.success) { contractSearch.result = d; }
						else { contractSearch.error = d?.error || 'Ma\'lumot olishda xatolik'; contractSearch.result = null; }
					} catch (e) {
						contractSearch.error = e.message || 'Xatolik'; contractSearch.result = null;
					} finally { contractSearch.loading = false; }
				}

				function clearSearch() {
					contractSearch.query = '';
					contractSearch.result = null;
					contractSearch.error = null;
					contractSearch.suggestions = [];
					contractSearch.showDropdown = false;
				}

				function closeDropdown() {
					setTimeout(() => { contractSearch.showDropdown = false; }, 200);
				}

				function getStatusColor(status) {
					if (status === 'To\'langan' || status === 'Paid') return '#34d399';
					if (status === 'Qisman to\'langan' || status === 'Partially Paid') return '#fbbf24';
					return '#f87171';
				}

				// ═══════════════════════════════════════════════════════════
				// NAVIGATION & UTILS
				// ═══════════════════════════════════════════════════════════

				function refresh() {
					if (current_view.value === 'general') fetchGeneral(1);
					else fetchPeriodic(1);
				}

				function applyPreset(p) {
					dateFrom.value = p.ytd ? `${new Date().getFullYear()}-01-01` : _monthsAgo(p.m);
					dateTo.value = _today();
					fetchPeriodic();
				}

				function switchView(v) {
					current_view.value = v;
					if (v === 'periodic' && !periodic.value.monthly_investment?.length) fetchPeriodic();
				}

				// ═══════════════════════════════════════════════════════════
				// TOOLTIP & CROSSHAIR
				// ═══════════════════════════════════════════════════════════

				function showTip(ev, title, rows) {
					let tx = ev.clientX + 14, ty = ev.clientY - 20;
					if (tx + 200 > window.innerWidth) tx = ev.clientX - 200;
					if (ty < 10) ty = ev.clientY + 20;
					tip.show = true; tip.x = tx; tip.y = ty; tip.title = title; tip.rows = rows;
				}
				function hideTip() { tip.show = false; crosshair.show = false; }

				function tipInvest(ev, pt, idx) {
					crosshair.show = true; crosshair.x = pt.x; crosshair.idx = idx;
					showTip(ev, pt.label, [{ k: 'Sana', v: pt.label, c: 'var(--fct-tx-1)' }, { k: 'Summa', v: fmt(pt.val), c: '#818cf8' }]);
				}
				function hideInvestTip() { hideTip(); crosshair.show = false; crosshair.idx = -1; }

				function tipCollBar(ev, bar) {
					const d = periodic.value.collection_efficiency;
					const m = d?.[bar.index]; if (!m) return;
					showTip(ev, bar.label, [
						{ k: 'Kutilgan', v: fmt(m.expected), c: '#60a5fa' },
						{ k: 'Haqiqiy', v: fmt(m.actual), c: '#34d399' },
						{ k: 'Samaradorlik', v: m.efficiency_pct + '%', c: m.efficiency_pct >= 90 ? '#34d399' : m.efficiency_pct >= 70 ? '#fbbf24' : '#f87171' }
					]);
				}

				function tipColl(ev, idx) {
					const d = periodic.value.collection_efficiency; if (!d?.[idx]) return;
					const r = d[idx];
					showTip(ev, r.label, [
						{ k: 'Kutilgan', v: fmt(r.expected), c: '#60a5fa' },
						{ k: 'Haqiqiy', v: fmt(r.actual), c: '#34d399' },
						{ k: 'Samaradorlik', v: r.efficiency_pct + '%', c: r.efficiency_pct >= 90 ? '#34d399' : r.efficiency_pct >= 70 ? '#fbbf24' : '#f87171' }
					]);
				}

				function tipNetProfit(ev, bar) {
					showTip(ev, bar.label, [{ k: 'Sana', v: bar.label, c: 'var(--fct-tx-1)' }, { k: 'Sof Foyda', v: fmt(bar.value), c: '#10b981' }]);
				}

				function tipContractCount(ev, bar) {
					showTip(ev, bar.label, [{ k: 'Sana', v: bar.label, c: 'var(--fct-tx-1)' }, { k: 'Soni', v: bar.value + ' ta shartnoma', c: '#6366f1' }]);
				}

				// ═══════════════════════════════════════════════════════════
				// THEME
				// ═══════════════════════════════════════════════════════════
				function toggleDark() {
					isDark.value = !isDark.value;
					try { localStorage.setItem('fct_dark', isDark.value ? '1' : '0'); } catch(e) {}
				}

				// ═══════════════════════════════════════════════════════════
				// FORMATTERS
				// ═══════════════════════════════════════════════════════════
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
				function fmtCount(v) { return (parseInt(v) || 0).toLocaleString('en-US'); }
				function overdueCls(d) { if (d <= 30) return 'fct-pill-g'; if (d <= 90) return 'fct-pill-y'; return 'fct-pill-r'; }
				function effCls(p) { if (p >= 90) return '#34d399'; if (p >= 70) return '#fbbf24'; return '#f87171'; }

				// ═══════════════════════════════════════════════════════════
				// LIFECYCLE
				// ═══════════════════════════════════════════════════════════
				onMounted(() => {
					const frappeTheme = document.documentElement.getAttribute('data-theme');
					const stored = (() => { try { return localStorage.getItem('fct_dark'); } catch(e) { return null; } })();
					if (stored !== null) isDark.value = stored === '1';
					else isDark.value = frappeTheme === 'dark' || window.matchMedia('(prefers-color-scheme: dark)').matches;

					fetchGeneral();
					fetchPeriodic();

					// Real-time: only show notification, no auto-fetch (data is cached)
					frappe.realtime.on('fct_cache_cleared', (data) => {
						frappe.show_alert({ message: __(`${data.doctype} ${data.docname} yangilandi. "Yangilash" tugmasini bosing.`), indicator: 'blue' }, 5);
					});

					// On tab re-focus: only refresh if stale (>10 min since last load)
					let _lastFetchTime = Date.now();
					const STALE_MS = 10 * 60 * 1000; // 10 minutes
					const _onVisible = () => {
						if (!document.hidden && (Date.now() - _lastFetchTime) > STALE_MS) {
							_lastFetchTime = Date.now();
							if (current_view.value === 'general') fetchGeneral();
							else fetchPeriodic();
						}
					};
					document.addEventListener('visibilitychange', _onVisible);

					if (cur_page?.page?.wrapper) {
						$(cur_page.page.wrapper).on('remove', () => {
							frappe.realtime.off('fct_cache_cleared');
							document.removeEventListener('visibilitychange', _onVisible);
						});
					}
				});

				// ═══════════════════════════════════════════════════════════
				// EXPOSE
				// ═══════════════════════════════════════════════════════════
				return {
					current_view, loading, loadingPeriodic, error, isDark, lastRefresh,
					kpis, roi, tiers, periodic,
					dateFrom, dateTo, tip, tierSearch, crosshair,
					kpiCards, donut, health, filteredTiers,
					CHART_W, CHART_H, PAD,
					investChart, collChart, netProfitChart, contractCountChart,
					tierMeta, presets,
					refresh, fetchPeriodic, applyPreset, switchView, toggleDark,
					showTip, hideTip, tipInvest, hideInvestTip, tipColl, tipCollBar, tipNetProfit, tipContractCount,
					fmt, fmtAxis, fmtFull, fmtCount, overdueCls, effCls,
					contractSearch, fetchSuggestions, onSearchInput, selectContract, closeDropdown, clearSearch, getStatusColor, salesChart, marginChart
				};
			}
		});

		app.mount('#fct-mount');
		console.log('✅ FCT: Vue app mounted successfully');
	}

	// ═══════════════════════════════════════════════════════════════════════════
	// SAFE BOOT: Vue Detection with comprehensive logging
	// ═══════════════════════════════════════════════════════════════════════════
	console.log('🚀 FCT: Starting Vue detection...');
	console.log('  - window.Vue:', typeof window.Vue);
	console.log('  - frappe.Vue:', typeof frappe?.Vue);
	console.log('  - global Vue:', typeof Vue);

	// Try multiple Vue sources in order of preference
	let VueLib = null;

	// Method 1: Check frappe.boot.vue (Frappe v15+)
	if (typeof frappe !== 'undefined' && frappe.Vue) {
		VueLib = frappe.Vue;
		console.log('✅ FCT: Found Vue via frappe.Vue');
	}
	// Method 2: Check window.Vue
	else if (typeof window !== 'undefined' && window.Vue) {
		VueLib = window.Vue;
		console.log('✅ FCT: Found Vue via window.Vue');
	}
	// Method 3: Check global Vue
	else if (typeof Vue !== 'undefined') {
		VueLib = Vue;
		console.log('✅ FCT: Found Vue via global Vue');
	}

	if (VueLib && typeof VueLib.createApp === 'function') {
		console.log('✅ FCT: Vue 3 detected with createApp');
		window.Vue = VueLib;
		try {
			_initVueApp();
		} catch (e) {
			console.error('❌ FCT: Vue init error:', e);
			page.main[0].innerHTML = '<div style="padding:2rem;color:#f87171;font-family:sans-serif;"><h3>Vue xatosi</h3><p>' + e.message + '</p><pre style="font-size:11px;overflow:auto;max-height:200px;background:#1a1a1a;padding:10px;border-radius:8px;margin-top:10px;">' + e.stack + '</pre></div>';
		}
	} else {
		console.warn('⚠️ FCT: Vue not found locally, loading from CDN...');
		const vueScript = document.createElement('script');
		vueScript.src = 'https://unpkg.com/vue@3.4.21/dist/vue.global.prod.js';
		vueScript.crossOrigin = 'anonymous';
		vueScript.onload = function() {
			console.log('✅ FCT: Vue loaded from CDN');
			window.Vue = window.Vue || Vue;
			try {
				_initVueApp();
			} catch (e) {
				console.error('❌ FCT: Vue init error after CDN load:', e);
				page.main[0].innerHTML = '<div style="padding:2rem;color:#f87171;font-family:sans-serif;"><h3>Vue xatosi</h3><p>' + e.message + '</p></div>';
			}
		};
		vueScript.onerror = function(e) {
			console.error('❌ FCT: CDN load failed:', e);
			// Last resort: try to use any Vue that might be available
			if (typeof Vue !== 'undefined' && Vue.createApp) {
				console.log('🔄 FCT: Retrying with available Vue...');
				window.Vue = Vue;
				try { _initVueApp(); } catch(err) {
					page.main[0].innerHTML = '<div style="padding:2rem;color:#f87171;font-family:sans-serif;"><h3>Vue yuklanmadi</h3><p>Tarmoqni tekshiring yoki sahifani yangilang.</p><button onclick="location.reload()" style="margin-top:10px;padding:8px 16px;background:#6366f1;color:white;border:none;border-radius:6px;cursor:pointer;">Sahifani yangilash</button></div>';
				}
			} else {
				page.main[0].innerHTML = '<div style="padding:2rem;color:#f87171;font-family:sans-serif;"><h3>Vue yuklanmadi</h3><p>Tarmoqni tekshiring yoki sahifani yangilang.</p><button onclick="location.reload()" style="margin-top:10px;padding:8px 16px;background:#6366f1;color:white;border:none;border-radius:6px;cursor:pointer;">Sahifani yangilash</button></div>';
			}
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
	const el = document.createElement(tag); el.id = id;
	Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
	if (content) el.textContent = content;
	document.head.appendChild(el);
}


// ═══════════════════════════════════════════════════════════════════════════════
// PAGE_TEMPLATE — v4.1 (Contract Tracker replaces Umumiy Ma'lumotlar)
// ═══════════════════════════════════════════════════════════════════════════════

const PAGE_TEMPLATE = `
<div class="fct" :class="{ 'fct--dark': isDark }">

  <!-- HEADER -->
  <header class="fct-hd">
    <div class="fct-hd__inner">
      <div class="fct-hd__brand">
        <div class="fct-hd__logo">
          <svg viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="url(#fctGr)"/>
            <path d="M7 20V8" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
            <path d="M7 20h14" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
            <path d="M10 16l3.5-6 3 3.5L21 8" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="10" cy="16" r="1.5" fill="#fff"/><circle cx="13.5" cy="10" r="1.5" fill="#fff"/>
            <circle cx="16.5" cy="13.5" r="1.5" fill="#fff"/><circle cx="21" cy="8" r="1.5" fill="#fff"/>
            <defs><linearGradient id="fctGr" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs>
          </svg>
        </div>
        <div>
          <h1 class="fct-hd__title">MacOne Muddatli</h1>
          <div class="fct-hd__meta">
            <span class="fct-hd__pill" v-if="!loading && !loadingPeriodic"><span class="fct-hd__dot fct-hd__dot--live"></span> Jonli</span>
            <span class="fct-hd__pill fct-hd__pill--load" v-else><span class="fct-hd__dot fct-hd__dot--load"></span> Sinxronlanmoqda…</span>
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
          <svg v-if="isDark" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41" stroke-linecap="round"/></svg>
          <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" stroke-linecap="round" stroke-linejoin="round"/></svg>
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

  <!-- MAIN CONTENT -->
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
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" :stroke="c.color" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="fct-kpi__icon"><path :d="c.icon"/></svg>
          </div>
          <div class="fct-kpi__val">{{ c.isCount ? fmtCount(c.val) : fmt(c.val) }}</div>
          <div class="fct-kpi__bar"><div class="fct-kpi__barfill"></div></div>
        </div>
      </div>

      <!-- ROI + Contract Tracker -->
      <div class="fct-duo">

 <!-- ROI Donut — v4.2 -->
        <div class="fct-card fct-roi">
          <div class="fct-card__hd"><h2 class="fct-card__title">ROI Statistikasi</h2></div>
          <div class="fct-roi__body fct-roi__body--vertical">
            <div class="fct-roi__legend fct-roi__legend--horizontal">
              <div class="fct-roi__li"><span class="fct-roi__dot" style="background:#34d399"></span><span>Sof foyda</span><strong>{{ fmt(donut.interest) }}</strong></div>
              <div class="fct-roi__li"><span class="fct-roi__dot" style="background:#94a3b8"></span><span>Ustav Kapitali</span><strong>{{ fmt(donut.principal) }}</strong></div>
            </div>
            <div class="fct-roi__donut fct-roi__donut--large">
              <svg viewBox="0 0 200 200" class="fct-roi__svg">
                <circle cx="100" cy="100" r="76" fill="none" :stroke="isDark ? '#1e293b' : '#e2e8f0'" stroke-width="18"/>
                <circle cx="100" cy="100" r="76" fill="none" stroke="url(#fctRoiGr)" stroke-width="18" stroke-linecap="round" :stroke-dasharray="donut.iDash" :stroke-dashoffset="donut.iOff" transform="rotate(-90 100 100)" class="fct-roi__arc"/>
                <circle cx="100" cy="100" r="76" fill="none" :stroke="isDark ? '#334155' : '#94a3b8'" stroke-width="18" stroke-linecap="round" :stroke-dasharray="donut.pDash" :stroke-dashoffset="donut.pOff" transform="rotate(-90 100 100)" class="fct-roi__arc" style="opacity:.5"/>
                <defs><linearGradient id="fctRoiGr" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#34d399"/><stop offset="100%" stop-color="#059669"/></linearGradient></defs>
              </svg>
              <div class="fct-roi__center"><span class="fct-roi__pct">{{ donut.pct }}%</span><span class="fct-roi__lbl">ROI</span></div>
            </div>
          </div>
        </div>

        <!-- ★★★ CONTRACT INSTALLATION TRACKER (v4.1) ★★★ -->
        <div class="fct-card fct-contract-tracker">
          <div class="fct-card__hd">
            <h2 class="fct-card__title">Shartnoma Tahlili</h2>
            <button v-if="contractSearch.result" @click="clearSearch()" class="fct-contract__clear">
              <svg viewBox="0 0 20 20" width="14" height="14" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
              Tozalash
            </button>
          </div>

          <!-- Search + Dropdown Select -->
          <div class="fct-contract__search">
            <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor" class="fct-contract__search-icon"><path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/></svg>
            <input type="text" v-model="contractSearch.query"
              @input="onSearchInput()"
              @focus="contractSearch.suggestions.length && (contractSearch.showDropdown = true)"
              @blur="closeDropdown()"
              placeholder="Shartnoma ID yoki Mijoz nomi kiriting..."
              class="fct-contract__input" autocomplete="off"/>
            <div v-if="contractSearch.searchLoading || contractSearch.loading" class="fct-contract__spinner"></div>

            <!-- Dropdown -->
            <div v-if="contractSearch.showDropdown" class="fct-contract__dropdown">
              <div v-if="contractSearch.suggestions.length" class="fct-contract__dropdown-list">
                <div v-for="c in contractSearch.suggestions" :key="c.name"
                  class="fct-contract__dropdown-item"
                  @mousedown.prevent="selectContract(c)">
                  <div class="fct-contract__dropdown-main">
                    <span>{{ c.customer_name }}</span>
                    <strong>{{ c.name }}</strong>
                  </div>
                  <div class="fct-contract__dropdown-sub">
                    <span>{{ c.date }}</span>
                    <span>{{ fmtFull(c.total) }}</span>
                  </div>
                </div>
              </div>
              <div v-else class="fct-contract__dropdown-empty">Natija topilmadi</div>
            </div>
          </div>

          <!-- Error -->
          <div v-if="contractSearch.error" class="fct-contract__error">
            <svg viewBox="0 0 20 20" width="16" height="16" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 9.586 8.707 8.293z" clip-rule="evenodd"/></svg>
            <span>{{ contractSearch.error }}</span>
          </div>

          <!-- Contract Meta -->
          <div v-if="contractSearch.result?.contract" class="fct-contract__meta">
            <div class="fct-contract__meta-row"><span>Shartnoma №</span><strong>{{ contractSearch.result.contract.name }}</strong></div>
            <div class="fct-contract__meta-row"><span>Mijoz</span><strong>{{ contractSearch.result.contract.customer_name }}</strong></div>
            <div class="fct-contract__meta-row"><span>Jami summa</span><strong style="color:#60a5fa">{{ fmtFull(contractSearch.result.contract.grand_total_with_interest) }}</strong></div>
            <div class="fct-contract__meta-row"><span>To'langan</span><strong style="color:#34d399">{{ fmtFull(contractSearch.result.summary.total_paid) }}</strong></div>
            <div class="fct-contract__meta-row"><span>Qoldiq</span><strong style="color:#f87171">{{ fmtFull(contractSearch.result.summary.total_balance) }}</strong></div>
          </div>

          <!-- Payment Schedule Table -->
          <div v-if="contractSearch.result?.schedule?.length" class="fct-contract__table-wrap">
            <table class="fct-contract__table">
              <colgroup>
                <col style="width:18%">
                <col style="width:21%">
                <col style="width:21%">
                <col style="width:20%">
                <col style="width:20%">
              </colgroup>
              <thead><tr><th>Sana</th><th>Rejalashtirilgan</th><th>To'langan</th><th>Qoldiq</th><th>Holat</th></tr></thead>
              <tbody>
                <tr v-for="(row, idx) in contractSearch.result.schedule" :key="idx">
                  <td class="fct-contract__td--date">{{ row.due_date }}</td>
                  <td class="fct-contract__td--mono">{{ fmtFull(row.scheduled_amount) }}</td>
                  <td class="fct-contract__td--mono" :style="{ color: row.paid_amount > 0 ? '#34d399' : 'inherit' }">{{ fmtFull(row.paid_amount) }}</td>
                  <td class="fct-contract__td--mono" :style="{ color: row.balance > 0 ? '#f87171' : '#5f677a' }">{{ fmtFull(row.balance) }}</td>
                  <td class="fct-contract__td--status"><span class="fct-contract__status" :style="{ color: getStatusColor(row.status), background: getStatusColor(row.status) + '18' }">{{ row.status === 'Paid' ? 'To\\'landi' : row.status === 'Partially Paid' ? 'Qisman' : 'To\\'lanmagan' }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Empty State -->
          <div v-if="!contractSearch.result && !contractSearch.error && !contractSearch.loading" class="fct-contract__empty">
            <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <p>Shartnomani qidirish uchun ID yoki mijoz nomini kiriting</p>
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
            <svg viewBox="0 0 20 20" width="14" height="14" fill="currentColor" class="fct-tier__searchico"><path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/></svg>
            <input type="text" v-model="tierSearch[tm.key]" placeholder="Qidirish…" class="fct-tier__input fct-tier__input--full"/>
          </div>
          <div class="fct-tier-col__list" v-if="filteredTiers[tm.key]?.length">
            <div v-for="row in filteredTiers[tm.key]" :key="row.customer" class="fct-cust-row"
                 @mouseenter="showTip($event, row.customer_name, [
                   { k: 'Jami hisob', v: fmt(row.total_billed), c: '#60a5fa' },
                   { k: 'To\\'langan', v: fmt(row.total_paid), c: '#34d399' },
                   { k: 'Qoldiq qarz', v: fmt(row.total_debt), c: tm.accent },
                   { k: 'Shartnomalar', v: String(row.contract_count || 0), c: 'var(--fct-tx-1)' }
                 ])" @mouseleave="hideTip()">
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

      <div class="fct-dates">
        <div class="fct-dates__fields">
          <div class="fct-dates__f"><label>Boshlanish</label><input type="date" v-model="dateFrom" class="fct-dates__input"/></div>
          <div class="fct-dates__f"><label>Tugash</label><input type="date" v-model="dateTo" class="fct-dates__input"/></div>
          <button class="fct-dates__go" @click="fetchPeriodic()" :disabled="loadingPeriodic">
            <svg viewBox="0 0 20 20" width="14" height="14" fill="currentColor"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clip-rule="evenodd"/></svg>
            Qo'llash
          </button>
        </div>
        <div class="fct-dates__presets"><button v-for="p in presets" :key="p.label" class="fct-dates__pre" @click="applyPreset(p)">{{ p.label }}</button></div>
      </div>

      <div v-if="loadingPeriodic" class="fct-pbar"><div class="fct-pbar__fill"></div></div>

      <!-- Charts Row 1: Investment + Collections -->
      <div class="fct-charts-duo">
        <div class="fct-card fct-chart-card">
          <div class="fct-card__hd"><h2 class="fct-card__title">Savdoga Tikilgan Pul</h2><span class="fct-card__badge" style="color:#818cf8; background:rgba(129,140,248,.12)">Sarflangan kapital</span></div>
          <div class="fct-chart__body">
            <svg v-if="investChart.pts.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H" preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
              <defs>
              	<linearGradient id="fctInvGr" x1="0" y1="0" x2="0" y2="1">
				  <stop offset="0%" stop-color="#818cf8" stop-opacity="0.4"/>
				  <stop offset="40%" stop-color="#818cf8" stop-opacity="0.2"/>
				  <stop offset="100%" stop-color="#818cf8" stop-opacity="0.03"/>
				</linearGradient>
                <filter id="fctDotGlow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
              </defs>
              <line v-for="(t,i) in investChart.yTicks" :key="'ig'+i" :x1="PAD.l" :y1="t.y" :x2="CHART_W - PAD.r" :y2="t.y" class="fct-chart__grid"/>
              <text v-for="(t,i) in investChart.yTicks" :key="'il'+i" :x="PAD.l - 8" :y="t.y + 3.5" class="fct-chart__ylab">{{ fmtAxis(t.v) }}</text>
              <text v-for="(p,i) in investChart.pts" :key="'ix'+i" v-show="i % investChart.labelSkip === 0" :x="p.x" :y="CHART_H - PAD.b + (investChart.rotateLabels ? 18 : 16)" class="fct-chart__xlab" :class="{ 'fct-chart__xlab--rotated': investChart.rotateLabels }" :transform="investChart.rotateLabels ? 'rotate(-45 ' + p.x + ' ' + (CHART_H - PAD.b + 18) + ')' : ''">{{ p.label }}</text>
              <path :d="investChart.area" fill="url(#fctInvGr)" class="fct-chart__area"/>
              <path :d="investChart.path" fill="none" stroke="#818cf8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="fct-chart__line"/>
              <line v-if="crosshair.show" :x1="crosshair.x" :y1="PAD.t" :x2="crosshair.x" :y2="CHART_H - PAD.b" class="fct-chart__crosshair"/>
              <circle v-for="(p,i) in investChart.pts" :key="'ip'+i" :cx="p.x" :cy="p.y" :r="crosshair.idx === i ? 7 : 4" fill="#818cf8" :stroke="isDark ? '#12151e' : '#fff'" stroke-width="2.5" :filter="crosshair.idx === i ? 'url(#fctDotGlow)' : ''" class="fct-chart__dot"/>
              <rect v-for="(p,i) in investChart.pts" :key="'ih'+i" :x="i === 0 ? PAD.l : (investChart.pts[i-1].x + p.x) / 2" :y="PAD.t" :width="i === 0 ? (investChart.pts.length > 1 ? (investChart.pts[1].x - p.x) / 2 + (p.x - PAD.l) : CHART_W - PAD.l - PAD.r) : (i === investChart.pts.length - 1 ? (CHART_W - PAD.r) - (investChart.pts[i-1].x + p.x) / 2 : (investChart.pts[Math.min(i+1, investChart.pts.length-1)].x - investChart.pts[Math.max(i-1, 0)].x) / 2)" :height="CHART_H - PAD.t - PAD.b" fill="transparent" @mouseenter="tipInvest($event, p, i)" @mouseleave="hideInvestTip()" style="cursor:crosshair"/>
            </svg>
            <div v-else class="fct-chart__empty">Tanlangan davr uchun investitsiya ma'lumoti yo'q</div>
          </div>
        </div>

        <div class="fct-card fct-chart-card">
          <div class="fct-card__hd">
            <h2 class="fct-card__title">Haqiqiy va Kutilgan Yig'imlar</h2>
            <div class="fct-chart__legend"><span><span class="fct-chart__lsym fct-chart__lsym--bar" style="background:#60a5fa"></span>Kutilgan</span><span><span class="fct-chart__lsym fct-chart__lsym--bar" style="background:#34d399"></span>Haqiqiy</span></div>
          </div>
          <div class="fct-chart__body">
            <svg v-if="collChart.bars?.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H" preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
              <line v-for="(t,i) in collChart.yTicks" :key="'cg'+i" :x1="PAD.l" :y1="t.y" :x2="CHART_W - PAD.r" :y2="t.y" class="fct-chart__grid"/>
              <text v-for="(t,i) in collChart.yTicks" :key="'cl'+i" :x="PAD.l - 8" :y="t.y + 3.5" class="fct-chart__ylab">{{ fmtAxis(t.v) }}</text>
              <text v-for="(l,i) in collChart.labels" :key="'cx'+i" v-show="i % collChart.labelSkip === 0" :x="l.x" :y="CHART_H - PAD.b + (collChart.rotateLabels ? 18 : 16)" class="fct-chart__xlab" :class="{ 'fct-chart__xlab--rotated': collChart.rotateLabels }" :transform="collChart.rotateLabels ? 'rotate(-45 ' + l.x + ' ' + (CHART_H - PAD.b + 18) + ')' : ''">{{ l.label }}</text>
              <rect v-for="(bar,i) in collChart.bars" :key="'bar'+i" :x="bar.x" :y="bar.y" :width="bar.width" :height="Math.max(0, bar.height)" :fill="bar.color" :opacity="bar.type === 'expected' ? 0.8 : 1" rx="2" class="fct-chart__bar" @mouseenter="tipCollBar($event, bar)" @mouseleave="hideTip()" style="cursor:pointer"/>
            </svg>
            <div v-else class="fct-chart__empty">Tanlangan davr uchun yig'im ma'lumoti yo'q</div>
          </div>
        </div>
      </div>

      <!-- Charts Row 2: Net Profit + Contract Count -->
      <div class="fct-charts-duo">
        <div class="fct-card fct-chart-card">
          <div class="fct-card__hd"><h2 class="fct-card__title">Oylik Sof Foyda</h2><span class="fct-card__badge" style="color:#10b981; background:rgba(16,185,129,.12)">Foyda</span></div>
          <div class="fct-chart__body">
            <svg v-if="netProfitChart.bars?.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H" preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
              <line v-for="(t,i) in netProfitChart.yTicks" :key="'npg'+i" :x1="PAD.l" :y1="t.y" :x2="CHART_W - PAD.r" :y2="t.y" class="fct-chart__grid"/>
              <text v-for="(t,i) in netProfitChart.yTicks" :key="'npl'+i" :x="PAD.l - 8" :y="t.y + 3.5" class="fct-chart__ylab">{{ fmtAxis(t.v) }}</text>
              <text v-for="(bar,i) in netProfitChart.bars" :key="'npx'+i" v-show="i % netProfitChart.labelSkip === 0" :x="bar.x + bar.width/2" :y="CHART_H - PAD.b + (netProfitChart.rotateLabels ? 18 : 16)" class="fct-chart__xlab" :class="{ 'fct-chart__xlab--rotated': netProfitChart.rotateLabels }" :transform="netProfitChart.rotateLabels ? 'rotate(-45 ' + (bar.x + bar.width/2) + ' ' + (CHART_H - PAD.b + 18) + ')' : ''">{{ bar.label }}</text>
              <rect v-for="(bar,i) in netProfitChart.bars" :key="'npbar'+i" :x="bar.x" :y="bar.y" :width="bar.width" :height="Math.max(0, bar.height)" :fill="bar.color" rx="3" class="fct-chart__bar" @mouseenter="tipNetProfit($event, bar)" @mouseleave="hideTip()" style="cursor:pointer"/>
            </svg>
            <div v-else class="fct-chart__empty">Tanlangan davr uchun foyda ma'lumoti yo'q</div>
          </div>
        </div>

        <div class="fct-card fct-chart-card">
          <div class="fct-card__hd"><h2 class="fct-card__title">Shartnomalar Soni</h2><span class="fct-card__badge" style="color:#6366f1; background:rgba(99,102,241,.12)">Oylik</span></div>
          <div class="fct-chart__body">
            <svg v-if="contractCountChart.bars?.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H" preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
              <line v-for="(t,i) in contractCountChart.yTicks" :key="'ccg'+i" :x1="PAD.l" :y1="t.y" :x2="CHART_W - PAD.r" :y2="t.y" class="fct-chart__grid"/>
              <text v-for="(t,i) in contractCountChart.yTicks" :key="'ccl'+i" :x="PAD.l - 8" :y="t.y + 3.5" class="fct-chart__ylab">{{ Math.round(t.v) }}</text>
              <text v-for="(bar,i) in contractCountChart.bars" :key="'ccx'+i" v-show="i % contractCountChart.labelSkip === 0" :x="bar.x + bar.width/2" :y="CHART_H - PAD.b + (contractCountChart.rotateLabels ? 18 : 16)" class="fct-chart__xlab" :class="{ 'fct-chart__xlab--rotated': contractCountChart.rotateLabels }" :transform="contractCountChart.rotateLabels ? 'rotate(-45 ' + (bar.x + bar.width/2) + ' ' + (CHART_H - PAD.b + 18) + ')' : ''">{{ bar.label }}</text>
              <rect v-for="(bar,i) in contractCountChart.bars" :key="'ccbar'+i" :x="bar.x" :y="bar.y" :width="bar.width" :height="Math.max(0, bar.height)" :fill="bar.color" rx="3" class="fct-chart__bar" @mouseenter="tipContractCount($event, bar)" @mouseleave="hideTip()" style="cursor:pointer"/>
            </svg>
            <div v-else class="fct-chart__empty">Tanlangan davr uchun shartnoma ma'lumoti yo'q</div>
          </div>
        </div>
      </div>
      <!-- Charts Row 3: Savdo + Marja -->
<div class="fct-charts-duo">
  <div class="fct-card fct-chart-card">
    <div class="fct-card__hd">
      <h2 class="fct-card__title">Oylik Savdo</h2>
      <span class="fct-card__badge" style="color:#38bdf8; background:rgba(56,189,248,.12)">Savdo hajmi</span>
    </div>
    <div class="fct-chart__body">
      <svg v-if="salesChart.pts.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H"
           preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
        <defs>
          <linearGradient id="fctSalesGr" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stop-color="#38bdf8" stop-opacity="0.4"/>
            <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.03"/>
          </linearGradient>
        </defs>
        <line v-for="(t,i) in salesChart.yTicks" :key="'sg'+i"
              :x1="PAD.l" :y1="t.y" :x2="CHART_W-PAD.r" :y2="t.y" class="fct-chart__grid"/>
        <text v-for="(t,i) in salesChart.yTicks" :key="'sl'+i"
              :x="PAD.l-8" :y="t.y+3.5" class="fct-chart__ylab">{{ fmtAxis(t.v) }}</text>
        <text v-for="(p,i) in salesChart.pts" :key="'sx'+i"
              v-show="i % salesChart.labelSkip === 0"
              :x="p.x" :y="CHART_H - PAD.b + (salesChart.rotateLabels ? 18 : 16)"
              class="fct-chart__xlab"
              :class="{ 'fct-chart__xlab--rotated': salesChart.rotateLabels }"
              :transform="salesChart.rotateLabels ? 'rotate(-45 '+p.x+' '+(CHART_H-PAD.b+18)+')' : ''">
          {{ p.label }}
        </text>
        <path :d="salesChart.area" fill="url(#fctSalesGr)" class="fct-chart__area"/>
        <path :d="salesChart.path" fill="none" stroke="#38bdf8"
              stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        <circle v-for="(p,i) in salesChart.pts" :key="'sp'+i"
                :cx="p.x" :cy="p.y" r="4" fill="#38bdf8"
                :stroke="isDark ? '#12151e' : '#fff'" stroke-width="2.5"
                @mouseenter="showTip($event, p.label, [{k:'Savdo', v:fmt(p.val), c:'#38bdf8'}])"
                @mouseleave="hideTip()" style="cursor:pointer"/>
      </svg>
      <div v-else class="fct-chart__empty">Savdo ma'lumoti yo'q</div>
    </div>
  </div>

  <div class="fct-card fct-chart-card">
    <div class="fct-card__hd">
      <h2 class="fct-card__title">Oylik Marja</h2>
      <span class="fct-card__badge" style="color:#f59e0b; background:rgba(245,158,11,.12)">Foiz %</span>
    </div>
    <div class="fct-chart__body">
      <svg v-if="marginChart.pts.length" :viewBox="'0 0 ' + CHART_W + ' ' + CHART_H"
           preserveAspectRatio="xMidYMid meet" class="fct-chart__svg">
        <defs>
          <linearGradient id="fctMarginGr" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stop-color="#f59e0b" stop-opacity="0.4"/>
            <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.03"/>
          </linearGradient>
        </defs>
        <line v-for="(t,i) in marginChart.yTicks" :key="'mg'+i"
              :x1="PAD.l" :y1="t.y" :x2="CHART_W-PAD.r" :y2="t.y" class="fct-chart__grid"/>
        <text v-for="(t,i) in marginChart.yTicks" :key="'ml'+i"
              :x="PAD.l-8" :y="t.y+3.5" class="fct-chart__ylab">{{ t.v.toFixed(1) }}%</text>
        <text v-for="(p,i) in marginChart.pts" :key="'mx'+i"
              v-show="i % marginChart.labelSkip === 0"
              :x="p.x" :y="CHART_H - PAD.b + (marginChart.rotateLabels ? 18 : 16)"
              class="fct-chart__xlab"
              :class="{ 'fct-chart__xlab--rotated': marginChart.rotateLabels }"
              :transform="marginChart.rotateLabels ? 'rotate(-45 '+p.x+' '+(CHART_H-PAD.b+18)+')' : ''">
          {{ p.label }}
        </text>
        <path :d="marginChart.area" fill="url(#fctMarginGr)" class="fct-chart__area"/>
        <path :d="marginChart.path" fill="none" stroke="#f59e0b"
              stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        <circle v-for="(p,i) in marginChart.pts" :key="'mp'+i"
                :cx="p.x" :cy="p.y" r="4" fill="#f59e0b"
                :stroke="isDark ? '#12151e' : '#fff'" stroke-width="2.5"
                @mouseenter="showTip($event, p.label, [{k:'Marja', v:p.val.toFixed(2)+'%', c:'#f59e0b'}])"
                @mouseleave="hideTip()" style="cursor:pointer"/>
      </svg>
      <div v-else class="fct-chart__empty">Marja ma'lumoti yo'q</div>
    </div>
  </div>
</div>
    </section>
  </main>

  <!-- TOOLTIP -->
  <teleport to="body">
    <div v-if="tip.show" class="fct-tip" :class="{ 'fct-tip--dark': isDark }" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">
      <div class="fct-tip__title">{{ tip.title }}</div>
      <div v-for="(r,i) in tip.rows" :key="i" class="fct-tip__row"><span :style="{ color: r.c }">{{ r.k }}</span><strong>{{ r.v }}</strong></div>
    </div>
  </teleport>
</div>
`;


// ═══════════════════════════════════════════════════════════════════════════════
// FCT_STYLES — v4.1 Production CSS
// ═══════════════════════════════════════════════════════════════════════════════

const FCT_STYLES = `
.fct {
  --fct-bg-0: #f4f5f7; --fct-bg-1: #ffffff; --fct-bg-2: #f8f9fb;
  --fct-bg-glass: rgba(255,255,255,.72);
  --fct-bdr: #e3e5ea; --fct-bdr-subtle: #eef0f4;
  --fct-tx-0: #111318; --fct-tx-1: #3d4152; --fct-tx-2: #8590a5; --fct-tx-3: #b0b8c9;
  --fct-sh-card: 0 1px 3px rgba(17,19,24,.04), 0 0 0 1px rgba(17,19,24,.03);
  --fct-sh-hover: 0 8px 24px rgba(17,19,24,.07), 0 0 0 1px rgba(17,19,24,.04);
  --fct-sh-float: 0 12px 40px rgba(17,19,24,.12), 0 0 0 1px rgba(17,19,24,.05);
  --fct-radius: 14px; --fct-radius-sm: 10px; --fct-radius-xs: 7px;
  font-family: 'Instrument Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--fct-bg-0); color: var(--fct-tx-0); line-height: 1.5; -webkit-font-smoothing: antialiased;
}
.fct--dark {
  --fct-bg-0: #0b0d14; --fct-bg-1: #12151e; --fct-bg-2: #181b26;
  --fct-bg-glass: rgba(18,21,30,.78);
  --fct-bdr: #1f2330; --fct-bdr-subtle: #1a1d28;
--fct-tx-0: #e8eaef; --fct-tx-1: #a0a7b8; --fct-tx-2: #7a8294; --fct-tx-3: #4d5366;
  --fct-sh-card: 0 1px 3px rgba(0,0,0,.2), 0 0 0 1px rgba(255,255,255,.03);
  --fct-sh-hover: 0 8px 24px rgba(0,0,0,.3), 0 0 0 1px rgba(255,255,255,.04);
  --fct-sh-float: 0 12px 40px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.06);
}
.fct *, .fct *::before, .fct *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* HEADER */
.fct-hd { position: sticky; top: 0; z-index: 80; background: var(--fct-bg-glass); backdrop-filter: blur(20px) saturate(1.3); -webkit-backdrop-filter: blur(20px) saturate(1.3); border-bottom: 1px solid var(--fct-bdr); }
.fct-hd__inner { max-width: 100%; margin: 0; padding: 10px 28px; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.fct-hd__brand { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.fct-hd__logo svg { display: block; }
.fct-hd__title { font-size: clamp(13px, 2vw, 17px); font-weight: 700; letter-spacing: -.025em; color: var(--fct-tx-0); }
.fct-hd__meta { display: flex; align-items: center; gap: 8px; margin-top: 1px; }
.fct-hd__pill { font-size: 11px; font-weight: 600; display: inline-flex; align-items: center; gap: 5px; color: var(--fct-tx-2); }
.fct-hd__dot { width: 6px; height: 6px; border-radius: 50%; }
.fct-hd__dot--live { background: #34d399; box-shadow: 0 0 6px #34d39966; }
.fct-hd__dot--load { background: #fbbf24; animation: fctPulse 1.2s ease-in-out infinite; }
.fct-hd__pill--load { color: #fbbf24; }
.fct-hd__ts { font-size: 11px; color: var(--fct-tx-3); }
.fct-hd__nav { display: flex; gap: 3px; margin-left: auto; background: var(--fct-bg-2); border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-sm); padding: 3px; }
.fct-hd__tab { display: flex; align-items: center; gap: 6px; padding: 7px 18px; border: none; border-radius: var(--fct-radius-xs); background: transparent; color: var(--fct-tx-2); font-size: 13px; font-weight: 600; font-family: inherit; cursor: pointer; transition: all .2s ease; white-space: nowrap; }
.fct-hd__tab:hover { color: var(--fct-tx-1); background: var(--fct-bg-1); }
.fct-hd__tab--on { background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important; color: #fff !important; box-shadow: 0 2px 10px rgba(99,102,241,.35); }
.fct-hd__actions { display: flex; gap: 6px; }
.fct-hd__btn { width: 36px; height: 36px; border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs); background: var(--fct-bg-1); color: var(--fct-tx-2); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all .2s; }
.fct-hd__btn:hover { background: var(--fct-bg-2); color: var(--fct-tx-1); border-color: var(--fct-tx-3); }
.fct-hd__btn:disabled { opacity: .5; cursor: not-allowed; }

/* ERROR */
.fct-err { max-width: 100%; margin: 0; padding: 10px 28px; display: flex; align-items: center; gap: 10px; background: #fef2f2; border-bottom: 1px solid #fecaca; color: #b91c1c; font-size: 13px; }
.fct--dark .fct-err { background: #1a0808; border-color: #450a0a; color: #fca5a5; }
.fct-err__btn { margin-left: auto; padding: 3px 12px; border: 1px solid currentColor; border-radius: var(--fct-radius-xs); background: transparent; color: inherit; font-size: 12px; font-family: inherit; cursor: pointer; }
.fct-err__x { padding: 2px 8px; border: none; background: transparent; color: inherit; font-size: 18px; cursor: pointer; line-height: 1; }

/* BODY */
.fct-body { max-width: 100%; width: 100%; margin: 0; padding: 24px 28px; position: relative; min-height: 65vh; box-sizing: border-box; }
.fct-v { animation: fctFadeUp .35s ease both; }

/* LOADER */
.fct-loader { position: absolute; inset: 0; z-index: 60; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; background: color-mix(in srgb, var(--fct-bg-0) 82%, transparent); backdrop-filter: blur(6px); border-radius: var(--fct-radius); }
.fct-loader__ring { width: 36px; height: 36px; border: 3px solid var(--fct-bdr); border-top-color: #818cf8; border-radius: 50%; animation: fctSpin .7s linear infinite; }
.fct-loader p { font-size: 13px; color: var(--fct-tx-2); }
.fct-pbar { height: 3px; background: var(--fct-bdr); border-radius: 2px; overflow: hidden; margin-bottom: 20px; }
.fct-pbar__fill { height: 100%; width: 30%; background: linear-gradient(90deg, #818cf8, #a78bfa); border-radius: 2px; animation: fctProgress 1.5s ease-in-out infinite; }

/* CARDS */
.fct-card { background: var(--fct-bg-1); border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius); box-shadow: var(--fct-sh-card); transition: box-shadow .25s ease; }
.fct-card:hover { box-shadow: var(--fct-sh-hover); }
.fct-card__hd { display: flex; justify-content: space-between; align-items: center; padding: 16px 22px 0; }
.fct-card__title { font-size: clamp(13px, 1.8vw, 15px); font-weight: 700; letter-spacing: -.015em; color: var(--fct-tx-0); }
.fct-card__badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; letter-spacing: .02em; }

/* KPI GRID */
.fct-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin-bottom: 18px; }
.fct-kpi { background: var(--fct-bg-1); border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius); padding: 16px 18px 12px; box-shadow: var(--fct-sh-card); position: relative; overflow: hidden; transition: all .25s ease; animation: fctSlideUp .4s ease both; }
.fct-kpi::after { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--kpi-accent); opacity: .85; }
.fct-kpi:hover { transform: translateY(-2px); box-shadow: var(--fct-sh-hover); }
.fct-kpi__head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.fct-kpi__label { font-size: 11.5px; font-weight: 600; color: var(--fct-tx-2); text-transform: uppercase; letter-spacing: .04em; }
.fct-kpi__icon { opacity: .45; }
.fct-kpi__val { font-size: clamp(15px, 4.5vw, 24px); font-weight: 800; letter-spacing: -.035em; font-variant-numeric: tabular-nums; color: var(--fct-tx-0); }
.fct-kpi__bar { height: 3px; background: var(--fct-bdr-subtle); border-radius: 2px; margin-top: 10px; overflow: hidden; }
.fct-kpi__barfill { height: 100%; width: 60%; background: var(--kpi-accent); border-radius: 2px; opacity: .45; }

/* DUO ROW */
.fct-duo { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px; align-items: stretch; }

/* ROI — card stretches to match adjacent column */
.fct-roi { display: flex; flex-direction: column; height: 100%; }
.fct-roi__body { padding: 18px 22px 20px; display: flex; align-items: center; gap: 24px; flex-wrap: wrap; justify-content: center; flex: 1 1 auto; }
.fct-roi__donut { position: relative; flex-shrink: 0; aspect-ratio: 1; }
.fct-roi__svg { width: 100%; height: 100%; }
.fct-roi__arc { transition: stroke-dasharray .8s cubic-bezier(.4,0,.2,1); }
.fct-roi__center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.fct-roi__pct { font-size: clamp(24px, 2.2vw, 36px); font-weight: 800; color: var(--fct-tx-0); letter-spacing: -.04em; }
.fct-roi__lbl { font-size: 11px; color: var(--fct-tx-2); text-transform: uppercase; letter-spacing: .12em; }
.fct-roi__legend { display: flex; flex-direction: column; gap: 10px; }
.fct-roi__li { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--fct-tx-1); }
.fct-roi__li strong { margin-left: auto; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--fct-tx-0); min-width: 60px; text-align: right; }
/* ROI v4.2 — vertical layout with top label */
.fct-roi__body--vertical { flex-direction: column; align-items: center; justify-content: center; gap: 16px; }
.fct-roi__top-label { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.fct-roi__pct-top { font-size: 36px; font-weight: 800; color: var(--fct-tx-0); letter-spacing: -.04em; line-height: 1; }
.fct-roi__lbl-top { font-size: 12px; color: var(--fct-tx-2); text-transform: uppercase; letter-spacing: .12em; font-weight: 600; }
.fct-roi__legend--horizontal { display: flex; flex-direction: row; gap: 24px; flex-wrap: wrap; justify-content: center; }
.fct-roi__donut--large { width: clamp(160px, 22vw, 280px); height: auto; }
.fct-roi__dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* CONTRACT TRACKER (v4.1) */
.fct-contract-tracker { max-height: 600px; display: flex; flex-direction: column; min-width: 0; }
.fct-contract__clear { display: flex; align-items: center; gap: 5px; padding: 4px 12px; border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs); background: var(--fct-bg-2); color: var(--fct-tx-2); font-size: 11px; font-weight: 600; font-family: inherit; cursor: pointer; transition: all .2s; }
.fct-contract__clear:hover { border-color: #f87171; color: #f87171; background: rgba(248,113,113,.08); }
.fct-contract__search { position: relative; display: flex; align-items: center; padding: 0 22px 14px; }
.fct-contract__search-icon { position: absolute; left: 32px; color: var(--fct-tx-3); pointer-events: none; }
.fct-contract__input { width: 100%; padding: 10px 40px 10px 44px; border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs); background: var(--fct-bg-2); color: var(--fct-tx-0); font-size: 13px; font-family: inherit; outline: none; transition: border-color .2s, box-shadow .2s; }
.fct-contract__input:focus { border-color: #818cf8; box-shadow: 0 0 0 3px rgba(129,140,248,.12); }
.fct-contract__input::placeholder { color: var(--fct-tx-3); }
.fct-contract__spinner { position: absolute; right: 32px; width: 16px; height: 16px; border: 2px solid var(--fct-bdr); border-top-color: #818cf8; border-radius: 50%; animation: fctSpin .6s linear infinite; }
.fct-contract__error { display: flex; align-items: center; gap: 8px; padding: 10px 22px; margin: 0 22px 14px; background: rgba(248,113,113,.12); border: 1px solid rgba(248,113,113,.3); border-radius: var(--fct-radius-xs); color: #f87171; font-size: 12px; }
.fct-contract__meta { padding: 0 22px 14px; display: flex; flex-direction: column; gap: 6px; border-bottom: 1px solid var(--fct-bdr); }
.fct-contract__meta-row { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 3px 0; }
.fct-contract__meta-row span { color: var(--fct-tx-2); }
.fct-contract__meta-row strong { font-weight: 700; font-variant-numeric: tabular-nums; font-family: 'JetBrains Mono', monospace; }
.fct-contract__table-wrap { overflow-x: auto; overflow-y: auto; max-height: 320px; padding: 14px 22px; -webkit-overflow-scrolling: touch; min-width: 0; }
.fct-contract__table { width: 100%; min-width: 480px; border-collapse: collapse; font-size: 12px; table-layout: auto; }
.fct-contract__table thead th { position: sticky; top: 0; z-index: 1; padding: 8px 10px; text-align: left; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--fct-tx-2); background: var(--fct-bg-2); border-bottom: 1px solid var(--fct-bdr); }
.fct-contract__table thead th:nth-child(1) { min-width: 90px; }
.fct-contract__table thead th:nth-child(2),.fct-contract__table thead th:nth-child(3),.fct-contract__table thead th:nth-child(4) { text-align: right; min-width: 110px; }
.fct-contract__table thead th:nth-child(5) { text-align: center; min-width: 95px; }
.fct-contract__table tbody tr { border-bottom: 1px solid var(--fct-bdr-subtle); transition: background .15s; }
.fct-contract__table tbody tr:hover { background: var(--fct-bg-2); }
.fct-contract__table tbody td { padding: 9px 10px; color: var(--fct-tx-1); }
.fct-contract__td--mono { text-align: right; font-family: 'JetBrains Mono', monospace; }
.fct-contract__td--status { text-align: center; min-width: 95px; }
.fct-contract__td--date { font-size: 12px; color: var(--fct-tx-2); white-space: nowrap; min-width: 90px; }
.fct-contract__td--mono { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; text-align: right; min-width: 110px; }
.fct-contract__status { display: inline-block; padding: 3px 10px; border-radius: 10px; font-size: 10px; font-weight: 700; white-space: nowrap; }
/* CONTRACT DROPDOWN */
.fct-contract__search { position: relative; }
.fct-contract__dropdown { position: absolute; top: 100%; left: 22px; right: 22px; z-index: 50; background: var(--fct-bg-1); border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs); box-shadow: var(--fct-sh-float); max-height: 280px; overflow-y: auto; margin-top: -10px; }
.fct-contract__dropdown-list { padding: 4px; }
.fct-contract__dropdown-item { padding: 10px 12px; border-radius: 6px; cursor: pointer; transition: background .12s; }
.fct-contract__dropdown-item:hover { background: var(--fct-bg-2); }
.fct-contract__dropdown-main { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.fct-contract__dropdown-main strong { font-size: 13px; font-weight: 700; color: var(--fct-tx-0); font-family: 'JetBrains Mono', monospace; flex-shrink: 0; white-space: nowrap; }
.fct-contract__dropdown-main span { font-size: 12px; color: var(--fct-tx-1); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fct-contract__dropdown-sub { display: flex; justify-content: space-between; margin-top: 2px; font-size: 11px; color: var(--fct-tx-3); }
.fct-contract__dropdown-sub span:last-child { font-family: 'JetBrains Mono', monospace; color: var(--fct-tx-2); }
.fct-contract__dropdown-empty { padding: 16px; text-align: center; font-size: 12px; color: var(--fct-tx-3); }
.fct-contract__empty { padding: 40px 22px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 12px; color: var(--fct-tx-3); }
.fct-contract__empty svg { opacity: .5; }
.fct-contract__empty p { font-size: 13px; max-width: 280px; }

/* TIER GRID */
.fct-tier-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; }
.fct-tier-col { border-top: 3px solid var(--tier-accent); display: flex; flex-direction: column; min-height: 320px; }
.fct-tier-col__hd { display: flex; align-items: center; gap: 12px; padding: 16px 18px 12px; }
.fct-tier-col__search { position: relative; display: flex; align-items: center; padding: 0 18px 12px; width: 100%; }
.fct-tier__input--full { width: 100%; padding-left: 34px; }
.fct-tier-col__list { flex: 1; overflow-y: auto; max-height: 420px; padding: 0 6px; }
.fct-cust-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; margin: 0 0 2px; border-radius: var(--fct-radius-xs); transition: background .15s ease; cursor: default; }
.fct-cust-row:hover { background: var(--fct-bg-2); }
.fct-cust-row__info { display: flex; flex-direction: column; gap: 1px; min-width: 0; flex: 1; }
.fct-cust-row__name { font-size: 13px; font-weight: 600; color: var(--fct-tx-0); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fct-cust-row__id { font-size: 11px; color: var(--fct-tx-3); font-family: 'JetBrains Mono', monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fct-cust-row__debt { font-size: 14px; font-weight: 800; font-variant-numeric: tabular-nums; font-family: 'JetBrains Mono', monospace; white-space: nowrap; padding-left: 12px; flex-shrink: 0; }
.fct-tier-col__foot { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; margin-top: auto; border-top: 1px solid var(--fct-bdr); font-size: 14px; font-weight: 800; color: var(--fct-tx-0); text-transform: uppercase; letter-spacing: .03em; background: var(--fct-bg-2); }
.fct-tier-col__foot strong { font-size: clamp(13px, 2vw, 16px); font-weight: 800; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; letter-spacing: -.02em; }
.fct-tier__badge { width: 34px; height: 34px; border-radius: var(--fct-radius-xs); display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
.fct-tier__info { flex: 1; min-width: 150px; }
.fct-tier__title { font-size: 14px; font-weight: 700; color: var(--fct-tx-0); }
.fct-tier__sub { font-size: 12px; color: var(--fct-tx-2); margin-top: 1px; }
.fct-tier__searchico { position: absolute; left: 30px; top: 50%; transform: translateY(-80%); color: var(--fct-tx-2); pointer-events: none; z-index: 1; }
.fct-tier__input { padding: 8px 12px 8px 36px; border: 1.5px solid var(--fct-tx-3); border-radius: 10px; background: var(--fct-bg-2); color: var(--fct-tx-0); font-size: 12px; font-family: inherit; outline: none; width: 160px; transition: border-color .2s, box-shadow .2s; }
.fct-tier__input:focus { border-color: #818cf8; box-shadow: 0 0 0 3px rgba(129,140,248,.18); }
.fct-tier__input::placeholder { color: var(--fct-tx-3); }
.fct-tier__empty { padding: 28px; text-align: center; font-size: 13px; color: var(--fct-tx-3); }

/* DATES */
.fct-dates { margin-bottom: 18px; display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; }
.fct-dates__fields { display: flex; align-items: flex-end; gap: 10px; }
.fct-dates__f { display: flex; flex-direction: column; gap: 4px; }
.fct-dates__f label { font-size: 10.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: var(--fct-tx-2); }
.fct-dates__input { padding: 8px 12px; border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs); background: var(--fct-bg-1); color: var(--fct-tx-0); font-size: 13px; font-family: inherit; outline: none; transition: border-color .2s, box-shadow .2s; }
.fct-dates__input:focus { border-color: #818cf8; box-shadow: 0 0 0 3px rgba(129,140,248,.1); }
.fct-dates__go { display: flex; align-items: center; gap: 6px; padding: 8px 18px; border: none; border-radius: var(--fct-radius-xs); background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; font-size: 13px; font-weight: 700; font-family: inherit; cursor: pointer; transition: transform .15s, box-shadow .15s; box-shadow: 0 2px 10px rgba(99,102,241,.3); }
.fct-dates__go:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(99,102,241,.4); }
.fct-dates__go:disabled { opacity: .5; cursor: not-allowed; transform: none; }
.fct-dates__presets { display: flex; gap: 4px; }
.fct-dates__pre { padding: 8px 13px; border: 1px solid var(--fct-bdr); border-radius: var(--fct-radius-xs); background: var(--fct-bg-1); color: var(--fct-tx-2); font-size: 12px; font-weight: 700; font-family: inherit; cursor: pointer; transition: all .15s; }
.fct-dates__pre:hover { border-color: #818cf8; color: #818cf8; background: rgba(129,140,248,.06); }

/* CHARTS */
.fct-charts-duo { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px; }
.fct-chart-card { padding-bottom: 18px; }
.fct-chart__body { padding: 0 18px; overflow-x: auto; overflow-y: visible; -webkit-overflow-scrolling: touch; }
.fct-chart__svg { width: 100%; height: auto; min-width: 400px; overflow: visible; }
.fct-chart__grid { stroke: var(--fct-tx-2); stroke-width: 1.2; stroke-dasharray: none; opacity: 0.55; }
.fct-chart__area { transition: opacity .3s ease; }
.fct-chart__line { transition: stroke-width .2s ease; }
.fct-chart__crosshair { stroke: var(--fct-tx-1); stroke-width: 1; stroke-dasharray: 4 3; opacity: .7; pointer-events: none; }
.fct-chart__dot { transition: r .2s cubic-bezier(.4,0,.2,1), filter .2s ease; cursor: crosshair; }
.fct-chart__bar { transition: opacity .15s ease, filter .15s ease; }
.fct-chart__bar:hover { opacity: 1 !important; filter: brightness(1.15) saturate(1.1); }
.fct-chart__ylab { font-size: 10px; fill: var(--fct-tx-1); font-family: 'JetBrains Mono', monospace; text-anchor: end; }
.fct-chart__xlab { font-size: 10.5px; fill: var(--fct-tx-1); font-family: 'JetBrains Mono', monospace; text-anchor: middle; }
.fct-chart__xlab--rotated { text-anchor: end; font-size: 9px; }
.fct-chart__empty { display: flex; align-items: center; justify-content: center; min-height: 160px; color: var(--fct-tx-3); font-size: 13px; }
.fct-chart__legend { display: flex; gap: 14px; font-size: 12px; color: var(--fct-tx-1); }
.fct-chart__lsym { display: inline-block; vertical-align: middle; margin-right: 4px; }
.fct-chart__lsym--bar { width: 10px; height: 10px; border-radius: 2px; }

/* TOOLTIP */
.fct-tip { position: fixed; z-index: 9999; pointer-events: none; background: var(--fct-bg-1, #fff); border: 1px solid var(--fct-bdr, #e3e5ea); border-radius: 10px; padding: 10px 14px; box-shadow: 0 10px 30px rgba(0,0,0,.12); font-size: 12px; min-width: 150px; max-width: 260px; backdrop-filter: blur(12px); animation: fctTipIn .15s ease; }
.fct-tip--dark { background: #1a1d28; border-color: #2a2e3a; box-shadow: 0 10px 30px rgba(0,0,0,.4); color: #e8eaef; }
.fct-tip__title { font-weight: 700; margin-bottom: 6px; font-size: 13px; color: var(--fct-tx-0, #111); }
.fct-tip--dark .fct-tip__title { color: #e8eaef; }
.fct-tip__row { display: flex; justify-content: space-between; gap: 16px; padding: 2px 0; }
.fct-tip__row strong { font-weight: 700; color: var(--fct-tx-0, #111); }
.fct-tip--dark .fct-tip__row strong { color: #e8eaef; }

/* ANIMATIONS */
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

/* RESPONSIVE */
@media (max-width: 1200px) { .fct-charts-duo { grid-template-columns: 1fr; } }
@media (max-width: 1023px) { .fct-duo { grid-template-columns: 1fr; gap: 14px; } .fct-charts-duo { grid-template-columns: 1fr; gap: 14px; } .fct-tier-grid { grid-template-columns: 1fr; gap: 14px; } .fct-tier-col { min-height: auto; } .fct-tier-col__list { max-height: 320px; } }
@media (min-width: 641px) and (max-width: 1023px) { .fct-hd__inner { padding: 10px 20px; gap: 14px; } .fct-body { padding: 20px; } .fct-kpis { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; } .fct-kpi { padding: 14px 14px 10px; } .fct-card__hd { padding: 14px 18px 0; } .fct-roi__body { gap: 18px; } .fct-dates { gap: 10px; } .fct-chart__body { padding: 0 14px; } .fct-contract__table-wrap { padding: 10px 18px; } .fct-contract__meta { padding: 0 18px 12px; } }
@media (max-width: 768px) {
  .fct-contract__table-wrap { padding: 10px 0; }
  .fct-contract__table { font-size: 11.5px; }
  .fct-contract__table thead th { padding: 7px 8px; font-size: 9.5px; }
  .fct-contract__table tbody td { padding: 8px 7px; }
  .fct-contract__status { padding: 2px 8px; font-size: 9.5px; }
  .fct-kpis { grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; }
  .fct-duo { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
	/* inside @media (max-width: 640px) add/update: */
  .fct-roi__donut--large { width: 160px; height: auto; }
  .fct-roi__pct-top { font-size: 30px; }
  .fct-roi__legend--horizontal { gap: 16px; }
  .fct-contract__dropdown { left: 14px; right: 14px; max-height: 220px; }
  .fct-hd__inner { padding: 8px 10px; gap: 8px; flex-wrap: wrap; }
  .fct-hd__brand { flex: 1 1 auto; min-width: 0; } .fct-hd__logo svg { width: 24px; height: 24px; }
  .fct-hd__title { font-size: 14px; white-space: normal; overflow: visible; max-width: 100%; }
  .fct-hd__ts { display: none; } .fct-hd__actions { flex-shrink: 0; }
  .fct-hd__nav { order: 10; width: 100%; margin-left: 0; }
  .fct-hd__tab { flex: 1; justify-content: center; padding: 7px 10px; font-size: 12px; }
  .fct-body { padding: 10px 8px; min-height: 50vh; }
  .fct-kpis { grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
  .fct-kpi { padding: 12px 12px 9px; } .fct-kpi__val { font-size: clamp(13px, 3.8vw, 20px); } .fct-kpi__label { font-size: 10px; } .fct-kpi__icon { width: 15px; height: 15px; }
  .fct-duo { margin-bottom: 12px; }
  .fct-roi { height: auto; }
  .fct-roi__body { flex-direction: column; align-items: center; gap: 14px; padding: 14px 14px 16px; }
  .fct-roi__donut--large { width: 140px; height: auto; } .fct-roi__pct { font-size: 24px; }
  .fct-roi__legend { flex-direction: row; flex-wrap: wrap; gap: 12px; justify-content: center; } .fct-roi__li strong { min-width: auto; margin-left: 6px; }
  .fct-card__hd { padding: 12px 14px 0; flex-wrap: wrap; gap: 6px; } .fct-card__title { font-size: 14px; }
  .fct-contract-tracker { max-height: none; }
  .fct-contract__search { padding: 0 14px 10px; } .fct-contract__input { padding: 8px 36px 8px 40px; font-size: 12px; }
  .fct-contract__meta { padding: 0 14px 10px; }
  .fct-contract__table-wrap { padding: 8px 0; max-height: 260px; }
  .fct-contract__table { font-size: 11px; } .fct-contract__table thead th { padding: 6px 8px; font-size: 9px; } .fct-contract__table tbody td { padding: 7px 8px; }
  .fct-tier-grid { grid-template-columns: 1fr; gap: 10px; }
  .fct-tier-col__hd { padding: 12px 14px 8px; } .fct-tier-col__search { padding: 0 14px 10px; } .fct-tier-col__list { max-height: 280px; } .fct-tier__input { width: 100%; }
  .fct-cust-row { padding: 8px 10px; } .fct-cust-row__name { font-size: 12px; } .fct-cust-row__debt { font-size: 13px; }
.fct-tier-col__foot { padding: 12px 14px; font-size: 13px; }
  .fct-charts-duo { margin-bottom: 12px; gap: 10px; } .fct-chart__body { padding: 0 10px; } .fct-chart__svg { min-width: 340px; }
  .fct-dates { flex-direction: column; align-items: stretch; gap: 10px; margin-bottom: 14px; }
  .fct-dates__fields { flex-wrap: wrap; gap: 8px; } .fct-dates__f { flex: 1 1 130px; } .fct-dates__input { width: 100%; }
  .fct-dates__go { align-self: flex-start; } .fct-dates__presets { flex-wrap: wrap; gap: 4px; } .fct-dates__pre { flex: 1; text-align: center; }
  .fct-err { padding: 8px 14px; font-size: 12px; }
}
@media (max-width: 400px) {
.fct-hd__inner { padding: 8px 8px; }
.fct-hd__title { font-size: 13px; white-space: normal; max-width: 100%; }
.fct-hd__logo svg { width: 20px; height: 20px; }
.fct-hd__btn { width: 32px; height: 32px; }
.fct-hd__pill { display: none; }
.fct-roi__donut--large { width: 130px; height: auto; }
.fct-body { padding: 8px 6px; } .fct-kpis { gap: 8px; } .fct-kpi { padding: 10px 10px 8px; } .fct-kpi__val { font-size: clamp(12px, 3.5vw, 18px); } .fct-dates__presets { gap: 3px; } .fct-dates__pre { padding: 7px 8px; font-size: 11px; } }
@media (min-width: 1024px) { .fct-duo { grid-template-columns: minmax(320px, 1fr) minmax(0, 2fr); } }
@media (min-width: 1800px) { .fct-body { padding: 28px 48px; } .fct-kpis { grid-template-columns: repeat(7, 1fr); } .fct-duo { grid-template-columns: minmax(360px, 420px) 1fr; } .fct-charts-duo { grid-template-columns: 1fr 1fr; gap: 22px; } .fct-tier-col__list { max-height: 560px; } }
@media print { .fct-hd { position: static; backdrop-filter: none; } .fct-hd__actions, .fct-hd__nav { display: none; } .fct-kpi:hover, .fct-card:hover { transform: none; box-shadow: var(--fct-sh-card); } .fct-body { padding: 0; } }

/* FRAPPE OVERRIDES — width/margin/padding on all ancestors owned by _releaseAncestors() */
.page-container[data-page-container] { background: transparent !important; }
#fct-mount { width: 100% !important; margin: 0 !important; box-sizing: border-box !important; }
`;
