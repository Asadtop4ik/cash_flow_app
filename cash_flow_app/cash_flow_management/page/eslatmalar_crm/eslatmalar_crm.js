/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * ESLATMALAR CRM — Collections Worklist
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * "Eslatmalar" reportining CRM varianti. Report statik ro'yxat edi — operator
 * har kuni bir xil 337 qatorni ko'rib, kimga qo'ng'iroq qilishni o'zi hal
 * qilardi. Bu sahifa collections bo'limlarining jahon standartiga amal qiladi:
 *
 *   Chap panel  — prioritet ball bo'yicha navbat (kechikish + qarz + toifa +
 *                 buzilgan va'da − yaqinda aloqa qilinganlik jarimasi)
 *   O'ng panel  — tanlangan mijozning 360° ko'rinishi: telefonlar (bir klik),
 *                 FIFO to'lov jadvali, aloqa tarixi, va'dalar
 *   Tezkor oqim — natija qayd etilgandan keyin navbatdagi keyingi mijozga
 *                 avtomatik o'tiladi (power-dialer uslubi)
 *
 * Frappe v15 custom page, bundled Vue 3, tashqi kutubxona yo'q.
 * Patterni financial_control_to sahifasidan olingan.
 * ═══════════════════════════════════════════════════════════════════════════════
 */

const CRM_API = 'cash_flow_app.cash_flow_management.api.eslatmalar_crm_api';

frappe.pages['eslatmalar-crm'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, single_column: true });
	$(wrapper).find('.page-head').hide();

	// Frappe'ning konteyner kengligi cheklovlarini bo'shatish — sahifa to'liq
	// ekran bo'ylab cho'ziladi (ikki panelli layout uchun hayotiy muhim).
	function _releaseAncestors(startEl) {
		let node = startEl.parentElement;
		while (node && node !== document.body) {
			node.style.setProperty('max-width', '100%', 'important');
			node.style.setProperty('width', '100%', 'important');
			node.style.setProperty('padding-left', '0', 'important');
			node.style.setProperty('padding-right', '0', 'important');
			node.style.setProperty('box-sizing', 'border-box', 'important');
			node = node.parentElement;
		}
	}

	_injectCrmOnce('crm-css', 'style', {}, CRM_STYLES);

	const mountEl = document.createElement('div');
	mountEl.id = 'crm-mount';
	page.main[0].innerHTML = '';
	page.main[0].appendChild(mountEl);
	_releaseAncestors(mountEl);

	function _initVueApp() {
		const { createApp, ref, reactive, computed, onMounted, onUnmounted, nextTick } = Vue;

		const app = createApp({
			template: CRM_TEMPLATE,
			setup() {
				// ═══════════════════════════════════════════════════════════
				// STATE
				// ═══════════════════════════════════════════════════════════
				const view        = ref('today');
				const onlyMine    = ref(false);
				const searchInput = ref('');
				const search      = ref('');

				const rows    = ref([]);
				const total   = ref(0);
				const kpi     = ref({});
				const counts  = ref({});
				const loading = ref(false);
				const error   = ref(null);

				const selected      = ref(null);
				const detail        = ref(null);
				const detailLoading = ref(false);
				const activeTab     = ref('schedule');

				const operators = ref([]);

				// Ommaviy biriktirish uchun tanlangan shartnomalar
				const picked      = ref([]);
				const bulkOp      = ref('');
				const bulkSaving  = ref(false);

				const form = reactive({
					open: false,
					disposition: '',
					outcome_note: '',
					next_action_date: '',
					next_action_time: '',
					promised_date: '',
					promised_amount: '',
					grace_days: 3,
					phone_called: '',
					is_important: 0,
					saving: false,
				});

				const VIEWS = [
					{ key: 'today',      label: 'Bugun',         hint: 'Bugun qilinishi kerak bo‘lgan ishlar' },
					{ key: 'broken',     label: 'Buzilgan va‘da', hint: 'Va‘dasini bajarmaganlar' },
					{ key: 'promises',   label: 'Va‘dalar',      hint: 'Ochiq va‘dalar' },
					{ key: 'overdue',    label: 'Kechikkanlar',  hint: 'Barcha kechikkan to‘lovlar' },
					{ key: 'upcoming',   label: 'Yaqinlashayotgan', hint: '7 kun ichida to‘lovi bor' },
					{ key: 'unassigned', label: 'Biriktirilmagan', hint: 'Mas‘ul operatori yo‘q' },
					{ key: 'all',        label: 'Hammasi',       hint: 'Barcha to‘lanmagan shartnomalar' },
				];

				const FALLBACK_DISPOSITIONS = [
					{ value: "Va'da berdi", contacted: true },
					{ value: "To'ladi", contacted: true },
					{ value: 'Rad etdi', contacted: true },
					{ value: 'Nizo / Pretenziya', contacted: true },
					{ value: 'Javob bermadi', contacted: false },
					{ value: 'Band', contacted: false },
					{ value: "Telefon o'chiq", contacted: false },
					{ value: "Noto'g'ri raqam", contacted: false },
					{ value: 'Qarindoshi javob berdi', contacted: false },
					{ value: "Keyinroq qo'ng'iroq so'radi", contacted: true },
					{ value: 'Boshqa', contacted: false },
				];

				const STAGES = ['Yangi', 'Aloqada', "Va'da berdi", "Buzilgan va'da",
					'Eskalatsiya', 'Yuridik', 'Yopilgan'];

				// ═══════════════════════════════════════════════════════════
				// COMPUTED
				// ═══════════════════════════════════════════════════════════
				const dispositions = computed(() =>
					(detail.value && detail.value.dispositions) || FALLBACK_DISPOSITIONS);

				const selectedIndex = computed(() =>
					rows.value.findIndex(r => r.contract === selected.value));

				const needsPromise = computed(() => form.disposition === "Va'da berdi");

				const allPicked = computed(() =>
					rows.value.length > 0 && picked.value.length === rows.value.length);

				function isPicked(contract) {
					return picked.value.indexOf(contract) !== -1;
				}

				function togglePick(contract) {
					const i = picked.value.indexOf(contract);
					if (i === -1) picked.value.push(contract);
					else picked.value.splice(i, 1);
				}

				function togglePickAll() {
					picked.value = allPicked.value ? [] : rows.value.map(r => r.contract);
				}

				function clearPicked() { picked.value = []; }

				/**
				 * Tanlangan shartnomalarni bitta operatorga biriktirish.
				 *
				 * "Mening navbatim" ishlashi uchun shartnomalar kimgadir
				 * biriktirilgan bo'lishi kerak — bu rahbar uchun asosiy vosita.
				 */
				function bulkAssign() {
					if (!picked.value.length) return;
					if (!bulkOp.value) {
						frappe.show_alert({ message: 'Operatorni tanlang', indicator: 'orange' }, 3);
						return;
					}
					bulkSaving.value = true;
					frappe.call({
						method: `${CRM_API}.bulk_assign`,
						args: { contracts: picked.value, operator: bulkOp.value },
					}).then(r => {
						const m = r.message || {};
						frappe.show_alert({
							message: `✅ ${m.count || 0} shartnoma biriktirildi`,
							indicator: 'green',
						}, 3);
						clearPicked();
						loadOperators();
						loadQueue();
					}).catch(e => {
						frappe.show_alert({
							message: (e && e.message) || 'Biriktirishda xatolik',
							indicator: 'red',
						}, 5);
					}).finally(() => { bulkSaving.value = false; });
				}

				// ═══════════════════════════════════════════════════════════
				// DATA LOADING
				// ═══════════════════════════════════════════════════════════
				function loadQueue(keepSelection = true) {
					loading.value = true;
					error.value = null;
					const prev = selected.value;

					return frappe.call({
						method: `${CRM_API}.get_queue`,
						args: {
							view: view.value,
							only_mine: onlyMine.value ? 1 : 0,
							search: search.value,
						},
					}).then(r => {
						const m = r.message || {};
						rows.value  = m.rows || [];
						total.value = m.total || 0;
						kpi.value   = m.kpi || {};
						counts.value = m.counts || {};

						if (keepSelection && prev && rows.value.some(x => x.contract === prev)) {
							selected.value = prev;
						} else if (rows.value.length) {
							selectRow(rows.value[0]);
						} else {
							selected.value = null;
							detail.value = null;
						}
					}).catch(e => {
						error.value = (e && e.message) || 'Navbatni yuklashda xatolik';
					}).finally(() => { loading.value = false; });
				}

				function selectRow(row) {
					if (!row) return;
					selected.value = row.contract;
					form.open = false;
					activeTab.value = 'schedule';
					loadDetail(row.contract);
				}

				function loadDetail(contract) {
					detailLoading.value = true;
					return frappe.call({
						method: `${CRM_API}.get_contract_360`,
						args: { contract_reference: contract },
					}).then(r => {
						detail.value = r.message || null;
					}).catch(() => {
						detail.value = null;
					}).finally(() => { detailLoading.value = false; });
				}

				function loadOperators() {
					frappe.call({ method: `${CRM_API}.get_operators` })
						.then(r => { operators.value = r.message || []; });
				}

				// ═══════════════════════════════════════════════════════════
				// ACTIONS
				// ═══════════════════════════════════════════════════════════
				function setView(key) {
					view.value = key;
					clearPicked();
					loadQueue(false);
				}

				let searchTimer = null;
				function onSearch() {
					clearTimeout(searchTimer);
					searchTimer = setTimeout(() => {
						search.value = searchInput.value.trim();
						loadQueue(false);
					}, 350);
				}

				function callPhone(number) {
					form.phone_called = number;
					openForm();
					window.location.href = 'tel:' + String(number).replace(/[^0-9+]/g, '');
				}

				function copyPhone(number) {
					navigator.clipboard && navigator.clipboard.writeText(number);
					frappe.show_alert({ message: 'Raqam nusxalandi', indicator: 'green' }, 2);
				}

				function openForm(disposition) {
					form.open = true;
					form.disposition = disposition || '';
					form.outcome_note = '';
					form.next_action_date = '';
					form.next_action_time = '';
					form.promised_date = '';
					form.promised_amount = currentRow() ? currentRow().due_amount : '';
					form.grace_days = 3;
					form.is_important = 0;
					if (!form.phone_called && detail.value && detail.value.phones.length) {
						form.phone_called = detail.value.phones[0].number;
					}
					nextTick(() => {
						const el = document.getElementById('crm-note-input');
						if (el) el.focus();
					});
				}

				function closeForm() {
					form.open = false;
					form.phone_called = '';
				}

				function currentRow() {
					return rows.value.find(r => r.contract === selected.value) || null;
				}

				function saveActivity() {
					if (!selected.value) return;
					if (!form.disposition) {
						frappe.show_alert({ message: 'Natija kodini tanlang', indicator: 'orange' }, 3);
						return;
					}
					if (needsPromise.value && (!form.promised_date || !form.promised_amount)) {
						frappe.show_alert({ message: "Va'da sanasi va summasini kiriting", indicator: 'orange' }, 3);
						return;
					}

					const row = currentRow();
					form.saving = true;

					frappe.call({
						method: `${CRM_API}.log_activity`,
						args: {
							contract_reference: selected.value,
							disposition: form.disposition,
							outcome_note: form.outcome_note,
							channel: 'Telefon',
							next_action_date: form.next_action_date || null,
							next_action_time: form.next_action_time || null,
							phone_called: form.phone_called || null,
							promised_date: needsPromise.value ? form.promised_date : null,
							promised_amount: needsPromise.value ? form.promised_amount : null,
							grace_days: form.grace_days,
							is_important: form.is_important ? 1 : 0,
							overdue_days: row ? row.overdue_days : 0,
							outstanding: row ? row.due_amount : 0,
						},
					}).then(r => {
						const m = r.message || {};
						if (m.success) {
							frappe.show_alert({ message: '✅ Natija qayd etildi', indicator: 'green' }, 2);
							closeForm();
							advanceToNext();
						} else {
							frappe.show_alert({ message: m.message || 'Xatolik', indicator: 'red' }, 4);
						}
					}).catch(e => {
						frappe.show_alert({ message: (e && e.message) || 'Xatolik', indicator: 'red' }, 4);
					}).finally(() => { form.saving = false; });
				}

				/**
				 * Natija qayd etilgandan keyin navbatdagi keyingi mijozga o'tish.
				 * Qator navbatdan tushib ketishi mumkin (masalan bugun aloqa
				 * qilingani uchun), shuning uchun indeks bo'yicha o'tamiz.
				 */
				function advanceToNext() {
					const idx = selectedIndex.value;
					loadQueue(false).then(() => {
						if (!rows.value.length) return;
						const target = rows.value[Math.min(idx, rows.value.length - 1)];
						if (target) selectRow(target);
					});
				}

				function snooze(days) {
					if (!selected.value) return;
					form.disposition = form.disposition || 'Javob bermadi';
					form.next_action_date = frappe.datetime.add_days(frappe.datetime.get_today(), days);
					form.open = true;
					nextTick(() => {
						const el = document.getElementById('crm-note-input');
						if (el) el.focus();
					});
				}

				function assign(operator) {
					if (!selected.value) return;
					frappe.call({
						method: `${CRM_API}.assign_operator`,
						args: { contract_reference: selected.value, operator: operator || null },
					}).then(() => {
						frappe.show_alert({ message: 'Operator biriktirildi', indicator: 'green' }, 2);
						if (detail.value) detail.value.contract.collection_operator = operator;
						loadOperators();
						loadQueue();
					}).catch(e => {
						frappe.show_alert({
							message: (e && e.message) || 'Biriktirishda xatolik',
							indicator: 'red',
						}, 5);
					});
				}

				function changeStage(stage) {
					if (!selected.value) return;
					frappe.call({
						method: `${CRM_API}.set_stage`,
						args: { contract_reference: selected.value, stage: stage },
					}).then(() => {
						frappe.show_alert({ message: 'Bosqich o‘zgardi', indicator: 'green' }, 2);
						loadQueue();
					});
				}

				function cancelPromise(name) {
					frappe.prompt({ fieldname: 'reason', label: 'Bekor qilish sababi', fieldtype: 'Small Text' },
						(values) => {
							frappe.call({
								method: `${CRM_API}.cancel_promise`,
								args: { promise: name, reason: values.reason },
							}).then(() => {
								frappe.show_alert({ message: 'Va‘da bekor qilindi', indicator: 'green' }, 2);
								loadDetail(selected.value);
								loadQueue();
							});
						}, 'Va‘dani bekor qilish', 'Bekor qilish');
				}

				function openContract() {
					if (selected.value) {
						frappe.set_route('Form', 'Installment Application', selected.value);
					}
				}

				function openCustomer() {
					if (detail.value) {
						frappe.set_route('Form', 'Customer', detail.value.contract.customer);
					}
				}

				function newPayment() {
					if (!detail.value) return;
					frappe.new_doc('Payment Entry', {
						payment_type: 'Receive',
						party_type: 'Customer',
						party: detail.value.contract.customer,
						custom_contract_reference: detail.value.contract.sales_order,
						paid_amount: detail.value.active ? detail.value.active.due_amount : 0,
					});
				}

				// ═══════════════════════════════════════════════════════════
				// KEYBOARD — operator klaviaturadan chiqmasligi uchun
				//   j / k  — navbatda pastga / tepaga
				//   Enter  — natija formasini ochish
				//   Esc    — formani yopish
				// ═══════════════════════════════════════════════════════════
				function onKey(e) {
					if (/input|textarea|select/i.test((e.target.tagName || ''))) {
						if (e.key === 'Escape') e.target.blur();
						return;
					}
					const idx = selectedIndex.value;
					if (e.key === 'j' && idx < rows.value.length - 1) {
						selectRow(rows.value[idx + 1]);
					} else if (e.key === 'k' && idx > 0) {
						selectRow(rows.value[idx - 1]);
					} else if (e.key === 'Enter' && selected.value) {
						openForm();
					} else if (e.key === 'Escape') {
						closeForm();
					}
				}

				onMounted(() => {
					loadOperators();
					loadQueue(false);
					document.addEventListener('keydown', onKey);
				});
				onUnmounted(() => {
					document.removeEventListener('keydown', onKey);
				});

				// ═══════════════════════════════════════════════════════════
				// FORMATTERS
				// ═══════════════════════════════════════════════════════════
				function money(v) {
					const n = Number(v || 0);
					return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
				}
				function moneyShort(v) {
					const n = Number(v || 0);
					if (Math.abs(n) >= 1000000) return '$' + (n / 1000000).toFixed(1) + 'M';
					if (Math.abs(n) >= 1000) return '$' + (n / 1000).toFixed(1) + 'K';
					return '$' + n.toFixed(0);
				}
				function dateFmt(d) {
					return d ? frappe.datetime.str_to_user(String(d).slice(0, 10)) : '—';
				}
				function dateTimeFmt(d) {
					if (!d) return '—';
					return frappe.datetime.str_to_user(String(d).slice(0, 10)) + ' ' + String(d).slice(11, 16);
				}
				function ago(d) {
					if (!d) return 'hech qachon';
					const days = frappe.datetime.get_day_diff(frappe.datetime.get_today(), String(d).slice(0, 10));
					if (days <= 0) return 'bugun';
					if (days === 1) return 'kecha';
					return days + ' kun oldin';
				}
				function tierClass(t) { return 'tier tier-' + (t || 'A'); }
				function promiseClass(s) {
					const map = {
						'Open': 'pz-open', 'Kept': 'pz-kept', 'Partially Kept': 'pz-partial',
						'Broken': 'pz-broken', 'Cancelled': 'pz-cancelled',
					};
					return 'pz ' + (map[s] || 'pz-open');
				}

				return {
					view, onlyMine, searchInput, rows, total, kpi, counts, loading, error,
					selected, detail, detailLoading, activeTab, operators, form,
					picked, bulkOp, bulkSaving, allPicked,
					VIEWS, STAGES, dispositions, needsPromise,
					loadQueue, selectRow, setView, onSearch, callPhone, copyPhone,
					openForm, closeForm, saveActivity, snooze, assign, changeStage,
					isPicked, togglePick, togglePickAll, clearPicked, bulkAssign,
					cancelPromise, openContract, openCustomer, newPayment,
					money, moneyShort, dateFmt, dateTimeFmt, ago,
					tierClass, promiseClass,
				};
			},
		});

		app.mount('#crm-mount');
		console.log('✅ Eslatmalar CRM: Vue app mounted');
	}

	// ─── SAFE BOOT: Frappe bundled Vue, keyin CDN fallback ──────────────────
	let VueLib = null;
	if (typeof frappe !== 'undefined' && frappe.Vue) VueLib = frappe.Vue;
	else if (typeof window !== 'undefined' && window.Vue) VueLib = window.Vue;
	else if (typeof Vue !== 'undefined') VueLib = Vue;

	if (VueLib && typeof VueLib.createApp === 'function') {
		window.Vue = VueLib;
		try {
			_initVueApp();
		} catch (e) {
			console.error('❌ CRM: Vue init error:', e);
			page.main[0].innerHTML = '<div style="padding:2rem;color:#f87171;font-family:sans-serif;">'
				+ '<h3>Vue xatosi</h3><p>' + e.message + '</p><pre style="font-size:11px;overflow:auto;'
				+ 'max-height:240px;background:#18181b;color:#e4e4e7;padding:10px;border-radius:8px;">'
				+ e.stack + '</pre></div>';
		}
	} else {
		const s = document.createElement('script');
		s.src = 'https://unpkg.com/vue@3.4.21/dist/vue.global.prod.js';
		s.onload = () => { window.Vue = window.Vue || Vue; _initVueApp(); };
		s.onerror = () => {
			page.main[0].innerHTML = '<div style="padding:2rem;font-family:sans-serif;">'
				+ '<h3>Vue yuklanmadi</h3><p>Tarmoqni tekshirib sahifani yangilang.</p></div>';
		};
		document.head.appendChild(s);
	}
};


function _injectCrmOnce(id, tag, attrs, content) {
	if (document.getElementById(id)) return;
	const el = document.createElement(tag);
	el.id = id;
	Object.entries(attrs || {}).forEach(([k, v]) => el.setAttribute(k, v));
	if (content) el.textContent = content;
	document.head.appendChild(el);
}


// ═════════════════════════════════════════════════════════════════════════════
//  TEMPLATE
// ═════════════════════════════════════════════════════════════════════════════

const CRM_TEMPLATE = `
<div class="crm-root">

  <!-- ─── TOP BAR ─────────────────────────────────────────────────────── -->
  <div class="crm-top">
    <div class="crm-title">
      <span class="crm-logo">☎</span>
      <div>
        <div class="crm-h1">Eslatmalar CRM</div>
        <div class="crm-sub">Qarz yig'ish navbati — eng kech qolganlar va va'dasini buzganlar tepada</div>
      </div>
    </div>
    <div class="crm-top-actions">
      <input class="crm-search" type="text" v-model="searchInput" @input="onSearch"
             placeholder="Mijoz, shartnoma yoki telefon…">
      <label class="crm-toggle">
        <input type="checkbox" v-model="onlyMine" @change="loadQueue(false)">
        <span>Mening navbatim</span>
      </label>
      <button class="crm-btn ghost" @click="loadQueue()" :disabled="loading">
        {{ loading ? '…' : '⟳' }}
      </button>
    </div>
  </div>

  <!-- ─── KPI ─────────────────────────────────────────────────────────── -->
  <div class="crm-kpis">
    <div class="kpi">
      <div class="kpi-l">Bugungi navbat</div>
      <div class="kpi-v">{{ kpi.queue_today || 0 }}</div>
      <div class="kpi-f">mening urinishim: {{ kpi.my_attempts_today || 0 }}</div>
    </div>
    <div class="kpi">
      <div class="kpi-l">Aloqa foizi (bugun)</div>
      <div class="kpi-v">{{ kpi.contact_rate != null ? kpi.contact_rate + '%' : '—' }}</div>
      <div class="kpi-f">{{ kpi.contacted_today || 0 }} / {{ kpi.attempts_today || 0 }} urinish</div>
    </div>
    <div class="kpi">
      <div class="kpi-l">Va'da bajarilishi</div>
      <div class="kpi-v">{{ kpi.ptp_kept_rate != null ? kpi.ptp_kept_rate + '%' : '—' }}</div>
      <div class="kpi-f">oxirgi 30 kun</div>
    </div>
    <div class="kpi">
      <div class="kpi-l">Ochiq va'dalar</div>
      <div class="kpi-v">{{ kpi.open_promises || 0 }}</div>
      <div class="kpi-f">{{ moneyShort(kpi.open_promise_amt) }}</div>
    </div>
    <div class="kpi danger">
      <div class="kpi-l">Buzilgan va'da</div>
      <div class="kpi-v">{{ kpi.broken_promises || 0 }}</div>
      <div class="kpi-f">30 kun ichida</div>
    </div>
    <div class="kpi">
      <div class="kpi-l">Kechikkan qarz</div>
      <div class="kpi-v">{{ moneyShort(kpi.overdue_amount) }}</div>
      <div class="kpi-f">{{ kpi.overdue_count || 0 }} shartnoma</div>
    </div>
    <div class="kpi ok">
      <div class="kpi-l">Bugun yig'ildi</div>
      <div class="kpi-v">{{ moneyShort(kpi.collected_today) }}</div>
      <div class="kpi-f">jami qarz {{ moneyShort(kpi.total_debt) }}</div>
    </div>
  </div>

  <!-- ─── BODY: ikki panel ────────────────────────────────────────────── -->
  <div class="crm-body">

    <!-- ══ CHAP: NAVBAT ══ -->
    <div class="crm-queue">
      <div class="crm-views">
        <button v-for="v in VIEWS" :key="v.key" :title="v.hint"
                :class="['vbtn', { on: view === v.key }]" @click="setView(v.key)">
          {{ v.label }}
          <span class="vcount">{{ counts[v.key] || 0 }}</span>
        </button>
      </div>

      <div class="crm-queue-head">
        <label class="qh-pick" v-if="rows.length">
          <input type="checkbox" :checked="allPicked" @change="togglePickAll">
          <span>{{ total }} ta qator</span>
        </label>
        <span v-else>{{ total }} ta qator</span>
        <span class="crm-hint">j / k — harakat · Enter — natija</span>
      </div>

      <!-- Ommaviy biriktirish — "Mening navbatim" ishlashi uchun shartnomalar
           operatorlarga taqsimlangan bo'lishi kerak -->
      <div v-if="picked.length" class="crm-bulk">
        <span class="cb-n">{{ picked.length }} tanlandi</span>
        <select class="d-select" v-model="bulkOp">
          <option value="">— operatorni tanlang —</option>
          <option v-for="o in operators" :key="o.name" :value="o.name">
            {{ o.full_name || o.name }} ({{ o.assigned }})
          </option>
        </select>
        <button class="crm-btn primary sm" @click="bulkAssign" :disabled="bulkSaving">
          {{ bulkSaving ? '…' : 'Biriktirish' }}
        </button>
        <button class="crm-btn ghost sm" @click="clearPicked">Tozalash</button>
      </div>

      <div class="crm-list">
        <div v-if="loading" class="crm-empty">Yuklanmoqda…</div>
        <div v-else-if="error" class="crm-empty err">{{ error }}</div>
        <div v-else-if="!rows.length && onlyMine" class="crm-empty">
          <div class="ce-big">👤</div>
          <div>Sizga biriktirilgan shartnoma yo'q</div>
          <div class="crm-hint">
            "Mening navbatim" faqat sizga biriktirilgan shartnomalarni ko'rsatadi.<br>
            Rahbar ularni taqsimlashi kerak: belgini olib tashlang, qatorlarni
            belgilab oling va <b>Biriktirish</b> tugmasidan foydalaning —
            yoki <b>Biriktirilmagan</b> ko'rinishiga o'ting.
          </div>
        </div>
        <div v-else-if="!rows.length" class="crm-empty">
          <div class="ce-big">✓</div>
          <div>Bu ko'rinishda qator yo'q</div>
          <div class="crm-hint">Bugungi navbat tugagan bo'lsa — barakalla.</div>
        </div>

        <div v-for="(r, i) in rows" :key="r.contract"
             :class="['qrow', { on: r.contract === selected }]"
             @click="selectRow(r)">
          <label class="qrow-pick" @click.stop>
            <input type="checkbox" :checked="isPicked(r.contract)"
                   @change="togglePick(r.contract)">
          </label>
          <div class="qrow-rank">{{ i + 1 }}</div>
          <div class="qrow-main">
            <div class="qrow-top">
              <span :class="tierClass(r.classification)">{{ r.classification }}</span>
              <span class="qname">{{ r.customer_name }}</span>
              <span class="qscore" title="Prioritet ball">{{ r.priority_score }}</span>
            </div>
            <div class="qrow-mid">
              <span class="qamt">{{ money(r.due_amount) }}</span>
              <span v-if="r.overdue_days > 0" class="qdays">{{ r.overdue_days }} kun kechikdi</span>
              <span v-else-if="r.days_diff === 0" class="qdays today">bugun to'lov</span>
              <span v-else class="qdays soft">{{ r.days_diff }} kundan keyin</span>
              <span class="qdebt">· qarz {{ moneyShort(r.remaining_debt) }}</span>
            </div>
            <div class="qrow-reasons">
              <span v-for="rs in r.reasons" :key="rs" class="chip">{{ rs }}</span>
              <span v-if="r.broken_promises" class="chip bad">{{ r.broken_promises }}× buzilgan</span>
            </div>
            <div class="qrow-foot">
              <span v-if="r.last_disposition">{{ r.last_disposition }} · {{ ago(r.last_contact) }}</span>
              <span v-else class="soft">hali aloqa qilinmagan</span>
              <span v-if="r.attempts" class="soft">· {{ r.attempts }} urinish</span>
              <span v-if="r.collection_operator" class="qop">{{ r.collection_operator }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ══ O'NG: MIJOZ 360° ══ -->
    <div class="crm-detail">
      <div v-if="!selected" class="crm-empty tall">
        <div class="ce-big">☎</div>
        <div>Navbatdan mijozni tanlang</div>
      </div>

      <template v-else-if="detail">
        <!-- Header -->
        <div class="d-head">
          <div class="d-head-l">
            <span :class="tierClass(detail.customer.classification)">{{ detail.customer.classification }}</span>
            <div>
              <div class="d-name" @click="openCustomer">{{ detail.contract.customer_name || detail.contract.customer }}</div>
              <div class="d-meta">
                <a @click.prevent="openContract" href="#">{{ detail.contract.name }}</a>
                · {{ dateFmt(detail.contract.transaction_date) }}
                · {{ detail.contract.installment_months }} oy
              </div>
            </div>
          </div>
          <div class="d-head-r">
            <select class="d-select" :value="detail.contract.collection_stage || 'Yangi'"
                    @change="changeStage($event.target.value)">
              <option v-for="s in STAGES" :key="s" :value="s">{{ s }}</option>
            </select>
            <select class="d-select" :value="detail.contract.collection_operator || ''"
                    @change="assign($event.target.value)">
              <option value="">— operator biriktirilmagan —</option>
              <option v-for="o in operators" :key="o.name" :value="o.name">
                {{ o.full_name || o.name }} ({{ o.assigned }})
              </option>
            </select>
          </div>
        </div>

        <!-- Telefonlar -->
        <div class="d-phones">
          <button v-for="p in detail.phones" :key="p.number" class="phone-btn"
                  @click="callPhone(p.number)">
            <span class="ph-ico">📞</span>
            <span class="ph-num">{{ p.number }}</span>
            <span class="ph-lbl">{{ p.label }}</span>
          </button>
          <span v-if="!detail.phones.length" class="d-nophone">⚠ Telefon raqami kiritilmagan</span>
          <button v-if="detail.phones.length" class="crm-btn ghost sm"
                  @click="copyPhone(detail.phones[0].number)">nusxa</button>
        </div>

        <!-- Metrikalar -->
        <div class="d-metrics">
          <div class="m">
            <div class="m-l">Hozir to'lashi kerak</div>
            <div class="m-v hot">{{ money(detail.active ? detail.active.due_amount : 0) }}</div>
          </div>
          <div class="m">
            <div class="m-l">Kechikish</div>
            <div class="m-v" :class="{ hot: detail.overdue_days > 0 }">
              {{ detail.overdue_days > 0 ? detail.overdue_days + ' kun' : 'yo‘q' }}
            </div>
          </div>
          <div class="m">
            <div class="m-l">Qolgan qarz</div>
            <div class="m-v">{{ money(detail.remaining_debt) }}</div>
          </div>
          <div class="m">
            <div class="m-l">To'langan</div>
            <div class="m-v">{{ detail.paid_percent }}%</div>
            <div class="m-bar"><div class="m-bar-in" :style="{ width: Math.min(detail.paid_percent, 100) + '%' }"></div></div>
          </div>
        </div>

        <!-- Ochiq va'da banneri -->
        <div v-for="p in detail.promises.filter(x => x.status === 'Open')" :key="p.name" class="d-promise">
          <span class="dp-ico">🤝</span>
          <span><b>{{ money(p.promised_amount) }}</b> — {{ dateFmt(p.promised_date) }} ga va'da berilgan</span>
          <span class="dp-paid" v-if="p.paid_amount">to'landi: {{ money(p.paid_amount) }}</span>
          <button class="crm-btn ghost sm" @click="cancelPromise(p.name)">bekor</button>
        </div>
        <div v-for="p in detail.promises.filter(x => x.status === 'Broken').slice(0, 1)" :key="p.name" class="d-promise bad">
          <span class="dp-ico">⚠</span>
          <span>Va'da buzilgan: <b>{{ money(p.promised_amount) }}</b>, {{ dateFmt(p.promised_date) }} ga aytilgan edi</span>
        </div>

        <!-- Harakat tugmalari -->
        <div class="d-actions">
          <button class="crm-btn primary" @click="openForm()">Natija qayd etish</button>
          <button class="crm-btn" @click="openForm('Va\\'da berdi')">Va'da olish</button>
          <button class="crm-btn" @click="snooze(1)">Ertaga qayta</button>
          <button class="crm-btn" @click="snooze(3)">3 kundan keyin</button>
          <button class="crm-btn ok" @click="newPayment">To'lov kiritish</button>
        </div>

        <!-- Natija formasi -->
        <div v-if="form.open" class="d-form">
          <div class="df-head">
            <span>Qo'ng'iroq natijasi</span>
            <button class="crm-btn ghost sm" @click="closeForm">✕</button>
          </div>

          <div class="df-disps">
            <button v-for="d in dispositions" :key="d.value"
                    :class="['dchip', { on: form.disposition === d.value, contacted: d.contacted }]"
                    @click="form.disposition = d.value">{{ d.value }}</button>
          </div>

          <textarea id="crm-note-input" class="df-note" v-model="form.outcome_note"
                    placeholder="Mijoz nima dedi? (ixtiyoriy, lekin keyingi operator uchun juda qimmat)"></textarea>

          <div v-if="needsPromise" class="df-promise">
            <div class="df-field">
              <label>Va'da sanasi *</label>
              <input type="date" v-model="form.promised_date">
            </div>
            <div class="df-field">
              <label>Va'da summasi (USD) *</label>
              <input type="number" step="0.01" v-model="form.promised_amount">
            </div>
            <div class="df-field">
              <label>Kutish muddati (kun)</label>
              <input type="number" v-model="form.grace_days">
            </div>
            <div class="df-note-hint">
              Va'da sanasidan {{ form.grace_days }} kun o'tib to'lov kelmasa — tizim
              va'dani <b>buzilgan</b> deb belgilaydi va bu mijoz navbat tepasiga chiqadi.
            </div>
          </div>

          <div class="df-row">
            <div class="df-field">
              <label>Keyingi harakat sanasi</label>
              <input type="date" v-model="form.next_action_date">
            </div>
            <div class="df-field">
              <label>Vaqti</label>
              <input type="time" v-model="form.next_action_time">
            </div>
            <div class="df-field">
              <label>Qo'ng'iroq qilingan raqam</label>
              <input type="text" v-model="form.phone_called">
            </div>
            <label class="df-check">
              <input type="checkbox" v-model="form.is_important"> Muhim
            </label>
          </div>

          <div class="df-foot">
            <button class="crm-btn primary" @click="saveActivity" :disabled="form.saving">
              {{ form.saving ? 'Saqlanmoqda…' : 'Saqlash va keyingisiga o‘tish' }}
            </button>
            <button class="crm-btn ghost" @click="closeForm">Bekor</button>
          </div>
        </div>

        <!-- Tablar -->
        <div class="d-tabs">
          <button :class="['tbtn', { on: activeTab === 'schedule' }]" @click="activeTab = 'schedule'">
            To'lov jadvali
          </button>
          <button :class="['tbtn', { on: activeTab === 'history' }]" @click="activeTab = 'history'">
            Aloqa tarixi <span class="vcount">{{ detail.activities.length }}</span>
          </button>
          <button :class="['tbtn', { on: activeTab === 'promises' }]" @click="activeTab = 'promises'">
            Va'dalar <span class="vcount">{{ detail.promises.length }}</span>
          </button>
          <button :class="['tbtn', { on: activeTab === 'payments' }]" @click="activeTab = 'payments'">
            To'lovlar <span class="vcount">{{ detail.payments.length }}</span>
          </button>
        </div>

        <div class="d-tabbody">
          <!-- Jadval -->
          <table v-if="activeTab === 'schedule'" class="d-table">
            <thead><tr><th>Sana</th><th class="r">Summa</th><th class="r">To'landi</th><th class="r">Qoldiq</th><th>Holat</th></tr></thead>
            <tbody>
              <tr v-for="(s, i) in detail.schedule" :key="i" :class="{ ovr: s.is_overdue }">
                <td>{{ dateFmt(s.due_date) }}</td>
                <td class="r">{{ money(s.amount) }}</td>
                <td class="r">{{ money(s.paid) }}</td>
                <td class="r">{{ money(s.outstanding) }}</td>
                <td>
                  <span v-if="s.status === 'paid'" class="pz pz-kept">to'landi</span>
                  <span v-else-if="s.status === 'partial'" class="pz pz-partial">qisman</span>
                  <span v-else-if="s.is_overdue" class="pz pz-broken">{{ s.overdue_days }} kun kechikdi</span>
                  <span v-else class="pz pz-open">kutilmoqda</span>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Aloqa tarixi -->
          <div v-else-if="activeTab === 'history'" class="d-timeline">
            <div v-if="!detail.activities.length && !detail.legacy_notes.length" class="crm-empty sm">
              Hali aloqa qayd etilmagan
            </div>
            <div v-for="a in detail.activities" :key="a.name" class="tl">
              <div class="tl-dot"></div>
              <div class="tl-body">
                <div class="tl-top">
                  <b>{{ a.disposition }}</b>
                  <span class="soft">{{ a.channel }} · {{ dateTimeFmt(a.activity_datetime) }}</span>
                  <span v-if="a.is_important" class="chip bad">muhim</span>
                </div>
                <div v-if="a.outcome_note" class="tl-note">{{ a.outcome_note }}</div>
                <div class="tl-foot">
                  <span>{{ a.operator }}</span>
                  <span v-if="a.phone_called">· {{ a.phone_called }}</span>
                  <span v-if="a.next_action_date">· keyingi: {{ dateFmt(a.next_action_date) }}
                    {{ a.next_action_time || '' }}</span>
                  <span v-if="a.promise">· va'da yaratildi</span>
                </div>
              </div>
            </div>
            <!-- CRM'dan oldingi izohlar yo'qolmasligi uchun -->
            <div v-for="n in detail.legacy_notes" :key="n.name" class="tl legacy">
              <div class="tl-dot"></div>
              <div class="tl-body">
                <div class="tl-top">
                  <b>{{ n.note_category || 'Izoh' }}</b>
                  <span class="soft">{{ dateFmt(n.note_date) }} · eski izoh</span>
                </div>
                <div class="tl-note">{{ n.note_text }}</div>
                <div class="tl-foot"><span>{{ n.created_by_user || '' }}</span></div>
              </div>
            </div>
          </div>

          <!-- Va'dalar -->
          <table v-else-if="activeTab === 'promises'" class="d-table">
            <thead><tr><th>Va'da sanasi</th><th class="r">Summa</th><th class="r">To'landi</th><th>Holat</th><th>Operator</th></tr></thead>
            <tbody>
              <tr v-if="!detail.promises.length"><td colspan="5" class="soft">Va'da yo'q</td></tr>
              <tr v-for="p in detail.promises" :key="p.name">
                <td>{{ dateFmt(p.promised_date) }}</td>
                <td class="r">{{ money(p.promised_amount) }}</td>
                <td class="r">{{ money(p.paid_amount) }}</td>
                <td><span :class="promiseClass(p.status)">{{ p.status }}</span></td>
                <td class="soft">{{ p.operator }}</td>
              </tr>
            </tbody>
          </table>

          <!-- To'lovlar -->
          <table v-else class="d-table">
            <thead><tr><th>Sana</th><th class="r">Summa</th><th>Usul</th><th>Hujjat</th></tr></thead>
            <tbody>
              <tr v-if="!detail.payments.length"><td colspan="4" class="soft">To'lov yo'q</td></tr>
              <tr v-for="p in detail.payments" :key="p.name">
                <td>{{ dateFmt(p.posting_date) }}</td>
                <td class="r">{{ money(p.paid_amount) }}</td>
                <td class="soft">{{ p.mode_of_payment || '—' }}</td>
                <td class="soft">{{ p.name }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <div v-else-if="detailLoading" class="crm-empty tall">Yuklanmoqda…</div>
      <div v-else class="crm-empty tall err">Ma'lumotni yuklab bo'lmadi</div>
    </div>
  </div>
</div>
`;


// ═════════════════════════════════════════════════════════════════════════════
//  STYLES — Frappe'ning light/dark mavzusiga moslashadi
// ═════════════════════════════════════════════════════════════════════════════

const CRM_STYLES = `
#crm-mount {
  --bg:        #f6f7f9;
  --surface:   #ffffff;
  --surface-2: #f1f2f5;
  --border:    #e2e4e9;
  --text:      #16181d;
  --text-2:    #5c6370;
  --text-3:    #8b919e;
  --accent:    #4f46e5;
  --accent-bg: rgba(79,70,229,.09);
  --hot:       #dc2626;
  --hot-bg:    rgba(220,38,38,.09);
  --warn:      #d97706;
  --warn-bg:   rgba(217,119,6,.10);
  --ok:        #059669;
  --ok-bg:     rgba(5,150,105,.10);
  --radius:    10px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif;
  color: var(--text);
  background: var(--bg);
}
[data-theme="dark"] #crm-mount {
  --bg:        #141518;
  --surface:   #1c1e22;
  --surface-2: #24262b;
  --border:    #2e3137;
  --text:      #e8e9ec;
  --text-2:    #a0a5b0;
  --text-3:    #6f7580;
  --accent:    #818cf8;
  --accent-bg: rgba(129,140,248,.14);
  --hot:       #f87171;
  --hot-bg:    rgba(248,113,113,.14);
  --warn:      #fbbf24;
  --warn-bg:   rgba(251,191,36,.14);
  --ok:        #34d399;
  --ok-bg:     rgba(52,211,153,.14);
}

#crm-mount * { box-sizing: border-box; }
#crm-mount .crm-root { display: flex; flex-direction: column; height: calc(100vh - 8px); overflow: hidden; }

/* ── TOP BAR ───────────────────────────────────────────────────────────── */
#crm-mount .crm-top {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 12px 18px; background: var(--surface); border-bottom: 1px solid var(--border);
}
#crm-mount .crm-title { display: flex; align-items: center; gap: 12px; }
#crm-mount .crm-logo {
  width: 36px; height: 36px; display: grid; place-items: center; font-size: 18px;
  background: var(--accent-bg); color: var(--accent); border-radius: var(--radius);
}
#crm-mount .crm-h1 { font-size: 15px; font-weight: 700; letter-spacing: -.01em; }
#crm-mount .crm-sub { font-size: 11.5px; color: var(--text-3); margin-top: 1px; }
#crm-mount .crm-top-actions { display: flex; align-items: center; gap: 10px; }
#crm-mount .crm-search {
  width: 280px; padding: 7px 11px; font-size: 12.5px; color: var(--text);
  background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; outline: none;
}
#crm-mount .crm-search:focus { border-color: var(--accent); }
#crm-mount .crm-toggle {
  display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-2);
  cursor: pointer; user-select: none; margin: 0;
}

/* ── BUTTONS ───────────────────────────────────────────────────────────── */
#crm-mount .crm-btn {
  padding: 7px 13px; font-size: 12.5px; font-weight: 500; font-family: inherit;
  color: var(--text); background: var(--surface-2);
  border: 1px solid var(--border); border-radius: 8px; cursor: pointer;
  transition: all .12s;
}
#crm-mount .crm-btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }
#crm-mount .crm-btn:disabled { opacity: .5; cursor: default; }
#crm-mount .crm-btn.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
#crm-mount .crm-btn.primary:hover:not(:disabled) { opacity: .9; color: #fff; }
#crm-mount .crm-btn.ok { background: var(--ok-bg); border-color: transparent; color: var(--ok); }
#crm-mount .crm-btn.ghost { background: transparent; }
#crm-mount .crm-btn.sm { padding: 3px 8px; font-size: 11px; }

/* ── KPI ───────────────────────────────────────────────────────────────── */
#crm-mount .crm-kpis {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px;
  background: var(--border); border-bottom: 1px solid var(--border);
}
#crm-mount .kpi { padding: 10px 14px; background: var(--surface); }
#crm-mount .kpi-l { font-size: 10.5px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-3); }
#crm-mount .kpi-v { font-size: 20px; font-weight: 700; letter-spacing: -.02em; margin-top: 3px; }
#crm-mount .kpi-f { font-size: 10.5px; color: var(--text-3); margin-top: 1px; }
#crm-mount .kpi.danger .kpi-v { color: var(--hot); }
#crm-mount .kpi.ok .kpi-v { color: var(--ok); }

/* ── BODY ──────────────────────────────────────────────────────────────── */
#crm-mount .crm-body { flex: 1; display: grid; grid-template-columns: 430px 1fr; min-height: 0; }
#crm-mount .crm-queue {
  display: flex; flex-direction: column; min-height: 0;
  background: var(--surface); border-right: 1px solid var(--border);
}
#crm-mount .crm-detail { overflow-y: auto; padding: 16px 20px 40px; min-height: 0; }

/* ── VIEW TABS ─────────────────────────────────────────────────────────── */
#crm-mount .crm-views {
  display: flex; flex-wrap: wrap; gap: 5px; padding: 10px 12px;
  border-bottom: 1px solid var(--border);
}
#crm-mount .vbtn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 9px; font-size: 11.5px; font-family: inherit; color: var(--text-2);
  background: transparent; border: 1px solid var(--border); border-radius: 20px; cursor: pointer;
}
#crm-mount .vbtn:hover { color: var(--text); }
#crm-mount .vbtn.on { background: var(--accent); border-color: var(--accent); color: #fff; }
#crm-mount .vcount {
  font-size: 10px; font-weight: 600; padding: 0 5px; border-radius: 10px;
  background: var(--surface-2); color: var(--text-2);
}
#crm-mount .vbtn.on .vcount { background: rgba(255,255,255,.22); color: #fff; }

#crm-mount .crm-queue-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 14px; font-size: 11px; color: var(--text-3);
  background: var(--surface-2); border-bottom: 1px solid var(--border);
}
#crm-mount .crm-hint { font-size: 10.5px; color: var(--text-3); line-height: 1.6; }
#crm-mount .qh-pick { display: flex; align-items: center; gap: 7px; margin: 0; cursor: pointer; }
#crm-mount .crm-bulk {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px;
  background: var(--accent-bg); border-bottom: 1px solid var(--border);
}
#crm-mount .cb-n { font-size: 11.5px; font-weight: 600; color: var(--accent); }
#crm-mount .crm-bulk .d-select { flex: 1; min-width: 0; }
#crm-mount .qrow-pick { display: flex; align-items: flex-start; padding-top: 3px; margin: 0; cursor: pointer; }

/* ── QUEUE ROWS ────────────────────────────────────────────────────────── */
#crm-mount .crm-list { flex: 1; overflow-y: auto; }
#crm-mount .qrow {
  display: flex; gap: 10px; padding: 10px 14px;
  border-bottom: 1px solid var(--border); cursor: pointer; transition: background .1s;
}
#crm-mount .qrow:hover { background: var(--surface-2); }
#crm-mount .qrow.on { background: var(--accent-bg); box-shadow: inset 3px 0 0 var(--accent); }
#crm-mount .qrow-rank {
  flex: 0 0 22px; font-size: 11px; font-weight: 600; color: var(--text-3);
  text-align: right; padding-top: 2px;
}
#crm-mount .qrow-main { flex: 1; min-width: 0; }
#crm-mount .qrow-top { display: flex; align-items: center; gap: 7px; }
#crm-mount .qname {
  flex: 1; font-size: 13px; font-weight: 600; letter-spacing: -.01em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
#crm-mount .qscore {
  font-size: 10.5px; font-weight: 700; padding: 1px 6px; border-radius: 6px;
  background: var(--surface-2); color: var(--text-2);
}
#crm-mount .qrow-mid { display: flex; align-items: baseline; gap: 6px; margin-top: 3px; font-size: 11.5px; }
#crm-mount .qamt { font-weight: 600; }
#crm-mount .qdays { color: var(--hot); font-weight: 500; }
#crm-mount .qdays.today { color: var(--warn); }
#crm-mount .qdays.soft { color: var(--text-3); font-weight: 400; }
#crm-mount .qdebt { color: var(--text-3); }
#crm-mount .qrow-reasons { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 5px; }
#crm-mount .qrow-foot {
  display: flex; gap: 5px; align-items: center; margin-top: 5px;
  font-size: 10.5px; color: var(--text-2);
}
#crm-mount .qop {
  margin-left: auto; font-size: 10px; padding: 1px 6px; border-radius: 6px;
  background: var(--surface-2); color: var(--text-3);
  max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
#crm-mount .soft { color: var(--text-3); }

/* ── CHIPS / BADGES ────────────────────────────────────────────────────── */
#crm-mount .chip {
  font-size: 10px; padding: 1px 7px; border-radius: 20px;
  background: var(--warn-bg); color: var(--warn); white-space: nowrap;
}
#crm-mount .chip.bad { background: var(--hot-bg); color: var(--hot); }
#crm-mount .tier {
  flex: 0 0 auto; width: 19px; height: 19px; display: grid; place-items: center;
  font-size: 10.5px; font-weight: 700; border-radius: 6px;
}
#crm-mount .tier-A { background: var(--ok-bg); color: var(--ok); }
#crm-mount .tier-B { background: var(--warn-bg); color: var(--warn); }
#crm-mount .tier-C { background: var(--hot-bg); color: var(--hot); }
#crm-mount .pz { font-size: 10.5px; padding: 1px 7px; border-radius: 6px; white-space: nowrap; }
#crm-mount .pz-open { background: var(--accent-bg); color: var(--accent); }
#crm-mount .pz-kept { background: var(--ok-bg); color: var(--ok); }
#crm-mount .pz-partial { background: var(--warn-bg); color: var(--warn); }
#crm-mount .pz-broken { background: var(--hot-bg); color: var(--hot); }
#crm-mount .pz-cancelled { background: var(--surface-2); color: var(--text-3); }

/* ── DETAIL HEADER ─────────────────────────────────────────────────────── */
#crm-mount .d-head { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
#crm-mount .d-head-l { display: flex; gap: 10px; align-items: flex-start; }
#crm-mount .d-name { font-size: 18px; font-weight: 700; letter-spacing: -.02em; cursor: pointer; }
#crm-mount .d-name:hover { color: var(--accent); }
#crm-mount .d-meta { font-size: 11.5px; color: var(--text-3); margin-top: 2px; }
#crm-mount .d-meta a { color: var(--accent); text-decoration: none; }
#crm-mount .d-head-r { display: flex; gap: 8px; }
#crm-mount .d-select {
  padding: 5px 9px; font-size: 11.5px; font-family: inherit; color: var(--text);
  background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; outline: none;
}

/* ── PHONES ────────────────────────────────────────────────────────────── */
#crm-mount .d-phones { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 14px; }
#crm-mount .phone-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 8px 14px; font-size: 13.5px; font-weight: 600; font-family: inherit;
  color: var(--ok); background: var(--ok-bg);
  border: 1px solid transparent; border-radius: var(--radius); cursor: pointer;
}
#crm-mount .phone-btn:hover { border-color: var(--ok); }
#crm-mount .ph-lbl { font-size: 10px; font-weight: 400; opacity: .7; }
#crm-mount .d-nophone { font-size: 12px; color: var(--hot); }

/* ── METRICS ───────────────────────────────────────────────────────────── */
#crm-mount .d-metrics {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 14px;
}
#crm-mount .m { padding: 10px 13px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); }
#crm-mount .m-l { font-size: 10.5px; text-transform: uppercase; letter-spacing: .04em; color: var(--text-3); }
#crm-mount .m-v { font-size: 17px; font-weight: 700; letter-spacing: -.02em; margin-top: 2px; }
#crm-mount .m-v.hot { color: var(--hot); }
#crm-mount .m-bar { height: 4px; border-radius: 4px; background: var(--surface-2); margin-top: 6px; overflow: hidden; }
#crm-mount .m-bar-in { height: 100%; background: var(--ok); border-radius: 4px; }

/* ── PROMISE BANNER ────────────────────────────────────────────────────── */
#crm-mount .d-promise {
  display: flex; align-items: center; gap: 9px; margin-top: 12px;
  padding: 9px 13px; font-size: 12.5px; border-radius: var(--radius);
  background: var(--accent-bg); color: var(--accent);
}
#crm-mount .d-promise.bad { background: var(--hot-bg); color: var(--hot); }
#crm-mount .dp-paid { margin-left: auto; font-size: 11.5px; opacity: .8; }

/* ── ACTIONS ───────────────────────────────────────────────────────────── */
#crm-mount .d-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }

/* ── DISPOSITION FORM ──────────────────────────────────────────────────── */
#crm-mount .d-form {
  margin-top: 14px; padding: 14px; background: var(--surface);
  border: 1px solid var(--accent); border-radius: var(--radius);
}
#crm-mount .df-head {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 12px; font-weight: 600; color: var(--text-2); margin-bottom: 10px;
}
#crm-mount .df-disps { display: flex; flex-wrap: wrap; gap: 6px; }
#crm-mount .dchip {
  padding: 5px 11px; font-size: 11.5px; font-family: inherit; color: var(--text-2);
  background: var(--surface-2); border: 1px solid var(--border);
  border-radius: 20px; cursor: pointer;
}
#crm-mount .dchip.contacted { color: var(--ok); }
#crm-mount .dchip:hover { border-color: var(--accent); }
#crm-mount .dchip.on { background: var(--accent); border-color: var(--accent); color: #fff; }
#crm-mount .df-note {
  width: 100%; min-height: 64px; margin-top: 10px; padding: 9px 11px;
  font-size: 12.5px; font-family: inherit; color: var(--text); resize: vertical;
  background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; outline: none;
}
#crm-mount .df-note:focus { border-color: var(--accent); }
#crm-mount .df-promise {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px;
  padding: 11px; background: var(--accent-bg); border-radius: 8px;
}
#crm-mount .df-note-hint {
  grid-column: 1 / -1; font-size: 11px; color: var(--text-2); line-height: 1.45;
}
#crm-mount .df-row { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; margin-top: 10px; }
#crm-mount .df-field { display: flex; flex-direction: column; gap: 3px; }
#crm-mount .df-field label { font-size: 10.5px; color: var(--text-3); }
#crm-mount .df-field input {
  padding: 6px 9px; font-size: 12px; font-family: inherit; color: var(--text);
  background: var(--surface-2); border: 1px solid var(--border); border-radius: 7px; outline: none;
}
#crm-mount .df-field input:focus { border-color: var(--accent); }
#crm-mount .df-check { display: flex; align-items: center; gap: 5px; font-size: 11.5px; color: var(--text-2); margin: 0 0 5px; }
#crm-mount .df-foot { display: flex; gap: 8px; margin-top: 12px; }

/* ── TABS + TABLES ─────────────────────────────────────────────────────── */
#crm-mount .d-tabs { display: flex; gap: 4px; margin-top: 18px; border-bottom: 1px solid var(--border); }
#crm-mount .tbtn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 7px 12px; font-size: 12px; font-family: inherit; color: var(--text-2);
  background: transparent; border: none; border-bottom: 2px solid transparent; cursor: pointer;
}
#crm-mount .tbtn:hover { color: var(--text); }
#crm-mount .tbtn.on { color: var(--accent); border-bottom-color: var(--accent); }
#crm-mount .d-tabbody { margin-top: 12px; }
#crm-mount .d-table { width: 100%; border-collapse: collapse; font-size: 12px; }
#crm-mount .d-table th {
  padding: 7px 10px; font-size: 10.5px; font-weight: 600; text-align: left;
  text-transform: uppercase; letter-spacing: .04em; color: var(--text-3);
  background: var(--surface-2); border-bottom: 1px solid var(--border);
}
#crm-mount .d-table td { padding: 7px 10px; border-bottom: 1px solid var(--border); }
#crm-mount .d-table .r { text-align: right; font-variant-numeric: tabular-nums; }
#crm-mount .d-table tr.ovr td { background: var(--hot-bg); }

/* ── TIMELINE ──────────────────────────────────────────────────────────── */
#crm-mount .d-timeline { position: relative; padding-left: 16px; }
#crm-mount .d-timeline::before {
  content: ''; position: absolute; left: 4px; top: 6px; bottom: 6px;
  width: 1px; background: var(--border);
}
#crm-mount .tl { position: relative; padding: 0 0 14px; }
#crm-mount .tl-dot {
  position: absolute; left: -16px; top: 5px; width: 9px; height: 9px;
  border-radius: 50%; background: var(--accent); border: 2px solid var(--surface);
}
#crm-mount .tl.legacy .tl-dot { background: var(--text-3); }
#crm-mount .tl-top { display: flex; flex-wrap: wrap; align-items: center; gap: 7px; font-size: 12.5px; }
#crm-mount .tl-note {
  margin-top: 4px; padding: 7px 10px; font-size: 12px; line-height: 1.5;
  background: var(--surface-2); border-radius: 8px; white-space: pre-wrap;
}
#crm-mount .tl-foot { margin-top: 4px; font-size: 10.5px; color: var(--text-3); display: flex; gap: 5px; flex-wrap: wrap; }

/* ── EMPTY ─────────────────────────────────────────────────────────────── */
#crm-mount .crm-empty {
  padding: 40px 20px; text-align: center; font-size: 12.5px; color: var(--text-3);
}
#crm-mount .crm-empty.tall { padding-top: 140px; }
#crm-mount .crm-empty.sm { padding: 20px; }
#crm-mount .crm-empty.err { color: var(--hot); }
#crm-mount .ce-big { font-size: 34px; opacity: .3; margin-bottom: 10px; }

/* ── RESPONSIVE ────────────────────────────────────────────────────────── */
@media (max-width: 1500px) {
  #crm-mount .crm-kpis { grid-template-columns: repeat(4, 1fr); }
}
@media (max-width: 1150px) {
  #crm-mount .crm-body { grid-template-columns: 1fr; }
  #crm-mount .crm-queue { max-height: 45vh; border-right: none; border-bottom: 1px solid var(--border); }
  #crm-mount .d-metrics { grid-template-columns: repeat(2, 1fr); }
  #crm-mount .crm-kpis { grid-template-columns: repeat(2, 1fr); }
}
`;
