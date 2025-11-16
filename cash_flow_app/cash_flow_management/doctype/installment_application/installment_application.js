// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.ui.form.on("Installment Application", {
	setup(frm) {
		// Disable autocomplete for item_code in Items table
		// BUT allow updated item to be selected after edit
		frm.set_query('item_code', 'items', function() {
			const updated_item = localStorage.getItem('updated_item_code');

			if (updated_item) {
				// Allow ONLY the updated item to be selected
				return {
					filters: {
						'name': updated_item
					}
				};
			}

			// For new items, disable autocomplete
			return {
				filters: {
					'name': ['=', '__FORCE_MANUAL_ENTRY__']
				}
			};
		});
	},

	onload(frm) {
		// Store current form name in localStorage for Item redirect
		if (frm.doc.name) {
			localStorage.setItem('current_installment_application', frm.doc.name);
		}
	},

	refresh(frm) {
		// Hide timezone display (Asia/Samarkand text)
		setTimeout(() => {
			$('.frappe-control[data-fieldname="transaction_date"] .help-box').hide();
			$('.frappe-control[data-fieldname="custom_start_date"] .help-box').hide();
		}, 100);

		// Store current form name for Item redirect
		if (frm.doc.name) {
			localStorage.setItem('current_installment_application', frm.doc.name);
		}

		// Clear cancelled Sales Order link for amended documents
		if (frm.doc.sales_order && frm.doc.amended_from) {
			frappe.db.get_value('Sales Order', frm.doc.sales_order, 'docstatus', (r) => {
				if (r && r.docstatus == 2) {  // Cancelled
					console.log('Clearing cancelled SO link:', frm.doc.sales_order);
					frm.set_value('sales_order', null);
				}
			});
		}

		// Auto-calculate on refresh if values exist
		if (frm.doc.total_amount && frm.doc.downpayment_amount && frm.doc.monthly_payment) {
			frm.trigger('calculate_totals');
		}

		// ============================================
		// YANGI: Create Payment Entry button
		// ============================================
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__('Create Payment Entry'), function() {
				create_payment_entry(frm);
			}, __('Create'));
		}

		// ============================================
		// YANGI: To'lovlarni ko'rish button
		// Submitted va Cancelled ikkalasi uchun ham ishlaydi
		// ============================================
		if (frm.doc.sales_order && (frm.doc.docstatus === 1 || frm.doc.docstatus === 2)) {
			frm.add_custom_button(__('To\'lovlarni ko\'rish'), function() {
				view_filtered_payments(frm);
			});
		}
	},

	// Calculate button click
	calculate_schedule_button(frm) {
		if (!frm.doc.total_amount || frm.doc.total_amount <= 0) {
			frappe.msgprint(__('Iltimos avval mahsulot qo\'shing!'));
			return;
		}

		// Boshlang'ich to'lov ixtiyoriy (0 bo'lishi mumkin)
		// if (!frm.doc.downpayment_amount || frm.doc.downpayment_amount <= 0) {
		// 	frappe.msgprint(__('Iltimos boshlang\'ich to\'lovni kiriting!'));
		// 	return;
		// }

		if (!frm.doc.monthly_payment || frm.doc.monthly_payment <= 0) {
			frappe.msgprint(__('Iltimos oylik to\'lovni kiriting!'));
			return;
		}

		if (!frm.doc.custom_start_date) {
			frappe.msgprint(__('Iltimos birinchi to\'lov sanasini kiriting!'));
			return;
		}

		if (!frm.doc.custom_monthly_payment_day || frm.doc.custom_monthly_payment_day < 1 || frm.doc.custom_monthly_payment_day > 31) {
			frappe.msgprint(__('Iltimos har oy qaysi sana to\'lanishini kiriting (1-31)!'));
			return;
		}

		// Calculate totals first
		frm.trigger('calculate_totals');

		// Clear existing payment schedule
		frm.clear_table('payment_schedule');

		// Add downpayment row only if downpayment > 0
		if (flt(frm.doc.downpayment_amount) > 0) {
			let downpayment_row = frm.add_child('payment_schedule');
			downpayment_row.due_date = frm.doc.custom_start_date;
			downpayment_row.payment_amount = flt(frm.doc.downpayment_amount);
			downpayment_row.invoice_portion = (flt(frm.doc.downpayment_amount) / flt(frm.doc.total_amount)) * 100;
			downpayment_row.description = 'Boshlang\'ich to\'lov';
		}

		// Add monthly payment rows with specific day
		let months = flt(frm.doc.installment_months) || 6;
		let monthly_payment = flt(frm.doc.monthly_payment);
		let monthly_portion = (monthly_payment / flt(frm.doc.total_amount)) * 100;
		let payment_day = flt(frm.doc.custom_monthly_payment_day);

		// Get start date to determine first payment month
		let start_date = frappe.datetime.str_to_obj(frm.doc.custom_start_date);
		let current_year = start_date.getFullYear();
		let current_month = start_date.getMonth(); // 0-indexed

		for (let i = 1; i <= months; i++) {
			let row = frm.add_child('payment_schedule');

			// Calculate next month
			let target_month = current_month + i;
			let target_year = current_year;

			// Handle year overflow
			while (target_month > 11) {
				target_month -= 12;
				target_year += 1;
			}

			// Create date with specific day
			let due_date = new Date(target_year, target_month, payment_day);

			// Handle invalid dates (e.g., Feb 30 -> Feb 28/29)
			if (due_date.getDate() !== payment_day) {
				// Date rolled over, use last day of month
				due_date = new Date(target_year, target_month + 1, 0);
			}

			row.due_date = frappe.datetime.obj_to_str(due_date);
			row.payment_amount = monthly_payment;
			row.invoice_portion = monthly_portion;
			row.description = `${i}-oy to\'lovi`;
		}

		// Refresh the table
		frm.refresh_field('payment_schedule');

		frappe.show_alert({
			message: __('To\'lov jadvali yaratildi! ✓'),
			indicator: 'green'
		}, 5);

		// Show calculation summary
		let downpayment_display = flt(frm.doc.downpayment_amount) > 0
			? `<p>Boshlang'ich to'lov: <strong>$${flt(frm.doc.downpayment_amount).toFixed(2)}</strong></p>`
			: `<p>Boshlang'ich to'lov: <strong style="color: gray;">Yo'q (0)</strong></p>`;

		let total_rows = flt(frm.doc.downpayment_amount) > 0 ? months + 1 : months;
		let row_description = flt(frm.doc.downpayment_amount) > 0
			? `(1 boshlang'ich + ${months} oylik)`
			: `(${months} oylik)`;

		let msg = `<div style="font-size: 14px; line-height: 1.8;">
			<p><strong>📊 HISOB-KITOB:</strong></p>
			<p>Umumiy narx: <strong>$${flt(frm.doc.total_amount).toFixed(2)}</strong></p>
			${downpayment_display}
			<p>Qolgan: <strong>$${flt(frm.doc.finance_amount).toFixed(2)}</strong></p>
			<p>Oylik to'lov: <strong>$${flt(frm.doc.monthly_payment).toFixed(2)} × ${frm.doc.installment_months} oy</strong></p>
			<p>To'lov kuni: <strong>Har oyning ${payment_day}-sanasi</strong></p>
			<p>Jami foiz: <strong style="color: orange;">$${flt(frm.doc.custom_total_interest).toFixed(2)}</strong></p>
			<p>Jami to'lanadi: <strong style="color: green;">$${flt(frm.doc.custom_grand_total_with_interest).toFixed(2)}</strong></p>
			<hr>
			<p><strong>📅 TO'LOV JADVALI:</strong></p>
			<p>Jami qatorlar: <strong>${total_rows} ta</strong> ${row_description}</p>
		</div>`;

		frappe.msgprint({
			title: __('To\'lov Ma\'lumotlari'),
			message: msg,
			indicator: 'blue'
		});
	},

	// Auto-calculate when fields change
	downpayment_amount(frm) {
		frm.trigger('calculate_totals');
	},

	monthly_payment(frm) {
		frm.trigger('calculate_totals');
	},

	installment_months(frm) {
		frm.trigger('calculate_totals');
	},

	// Calculate totals
	calculate_totals(frm) {
		if (!frm.doc.total_amount || frm.doc.total_amount <= 0) {
			return;
		}

		// Calculate finance amount (qolgan summa)
		let downpayment = flt(frm.doc.downpayment_amount) || 0;
		let finance_amount = flt(frm.doc.total_amount) - downpayment;
		frm.set_value('finance_amount', finance_amount);

		// Calculate interest
		let monthly_payment = flt(frm.doc.monthly_payment) || 0;
		let months = flt(frm.doc.installment_months) || 6;

		// Total to be paid in installments
		let total_installments = monthly_payment * months;

		// Interest (Foyda) = (Monthly × Months) - Finance Amount
		let total_interest = total_installments - finance_amount;
		frm.set_value('custom_total_interest', total_interest);

		// Grand total = Downpayment + Total Installments
		let grand_total = downpayment + total_installments;
		frm.set_value('custom_grand_total_with_interest', grand_total);

		// Marja Foiz (%) = (Total Interest / Total Installments) × 100%
		// Bu ko'rsatadi: oylik to'lovlarning qancha qismi foyda
		let profit_percentage = 0;
		if (total_installments > 0) {
			profit_percentage = (total_interest / total_installments) * 100;
			profit_percentage = parseFloat(profit_percentage.toFixed(2)); // 2 raqam verguldan keyin
		}
		frm.set_value('custom_profit_percentage', profit_percentage);

		// Ustama Foiz (%) = (Total Interest / Finance Amount) × 100%
		// Bu ko'rsatadi: qolgan summadan qancha foiz foyda
		let finance_profit_percentage = 0;
		if (finance_amount > 0) {
			finance_profit_percentage = (total_interest / finance_amount) * 100;
			finance_profit_percentage = parseFloat(finance_profit_percentage.toFixed(2)); // 2 raqam verguldan keyin
		}
		frm.set_value('custom_finance_profit_percentage', finance_profit_percentage);
	},

	calculate_item_totals(frm) {
		let total = 0;
		(frm.doc.items || []).forEach(item => {
			total += flt(item.amount);
		});
		frm.set_value('total_amount', total);
		frm.trigger('calculate_totals');
	}
});

// Child table events
frappe.ui.form.on('Installment Application Item', {
	items_add(frm, cdt, cdn) {
		frm.trigger('calculate_item_totals');
	},

	items_remove(frm, cdt, cdn) {
		frm.trigger('calculate_item_totals');
	},

	item_code(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		// Clear updated_item_code from localStorage after selection
		localStorage.removeItem('updated_item_code');

		// Fetch IMEI from Item
		if (row.item_code) {
			frappe.db.get_value('Item', row.item_code, 'custom_imei', (r) => {
				if (r && r.custom_imei) {
					frappe.model.set_value(cdt, cdn, 'imei', r.custom_imei);
					frappe.show_alert({
						message: __('IMEI avto to\'ldirildi: {0}', [r.custom_imei]),
						indicator: 'green'
					}, 3);
				}
			});
		}
	},

	qty(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
	},

	rate(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
	},

	custom_notes(frm, cdt, cdn) {
		// Just refresh to show the note was saved
		frm.refresh_field('items');
	}
});

function calculate_item_amount(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	row.amount = flt(row.qty) * flt(row.rate);
	frm.refresh_field('items');
	frm.trigger('calculate_item_totals');
}

// ============================================
// YANGI FUNKSIYA: Payment Entry yaratish
// ============================================
// installment_application.js - TO'LIQ ISHLOVCHI YECHIM
// installment_application.js - TO'LIQ ISHLOVCHI YECHIM
// installment_application.js - TO'LIQ ISHLOVCHI YECHIM

function create_payment_entry(frm) {
	if (!frm.doc.customer) {
		frappe.msgprint(__('Customer tanlanmagan!'));
		return;
	}

	if (!frm.doc.sales_order) {
		frappe.msgprint(__('Sales Order hali yaratilmagan!'));
		return;
	}

	frappe.call({
		method: 'cash_flow_app.cash_flow_management.doctype.installment_application.installment_application.create_payment_entry_from_installment',
		args: {
			source_name: frm.doc.name
		},
		freeze: true,
		freeze_message: __('Payment Entry tayyorlanmoqda...'),
		callback: function(r) {
			if (r.message) {
				// Yangi Payment Entry yaratish
				frappe.model.with_doctype('Payment Entry', function() {
					let payment_entry = frappe.model.get_new_doc('Payment Entry');

					// Ma'lumotlarni to'ldirish
					payment_entry.payment_type = r.message.payment_type;
					payment_entry.posting_date = r.message.posting_date;
					payment_entry.mode_of_payment = r.message.mode_of_payment;
					payment_entry.party_type = r.message.party_type;
					payment_entry.party = r.message.party;
					payment_entry.company = r.message.company;
					payment_entry.remarks = r.message.remarks;

					// Custom contract reference
					if (r.message.custom_contract_reference) {
						payment_entry.custom_contract_reference = r.message.custom_contract_reference;
					}

					// Sales Order linkini saqlash (yashirin o'zgaruvchi)
					payment_entry.__sales_order_link = r.message.custom_contract_reference;

					// Formani ochish
					frappe.set_route('Form', 'Payment Entry', payment_entry.name);

					// Payment Entry formasida event qo'shish
					setTimeout(function() {
						if (cur_frm && cur_frm.doctype === 'Payment Entry') {
							// Party fieldini trigger qilish
							cur_frm.set_value('party', r.message.party);

							// Payment Type o'zgarganda custom_contract_reference ni saqlash
							setup_payment_type_handler(cur_frm);
						}
					}, 500);
				});
			}
		},
		error: function(r) {
			frappe.msgprint({
				title: __('Xatolik'),
				indicator: 'red',
				message: __('Payment Entry yaratib bo\'lmadi.')
			});
		}
	});
}

// Payment Type o'zgarganda shartnoma linkini saqlash
function setup_payment_type_handler(frm) {
	// Sales Order linkini saqlab qolish
	let saved_sales_order = frm.doc.custom_contract_reference || frm.doc.__sales_order_link;

	// Payment Type fieldiga custom handler qo'shish
	frm.fields_dict.payment_type.$input.off('change.keep_contract').on('change.keep_contract', function() {
		setTimeout(function() {
			// Agar custom_contract_reference yo'qolgan bo'lsa, qaytarish
			if (!frm.doc.custom_contract_reference && saved_sales_order) {
				frm.set_value('custom_contract_reference', saved_sales_order);
			}

			// Party Type ni to'g'rilash
			if (frm.doc.payment_type === 'Receive') {
				frm.set_value('party_type', 'Customer');
			} else if (frm.doc.payment_type === 'Pay') {
				frm.set_value('party_type', 'Supplier');
				// Party ni tozalash (qo'lda tanlansin)
				frm.set_value('party', '');
			}
		}, 100);
	});
}

// ============================================
// YANGI FUNKSIYA: Payment Entry listga o'tish va filter qo'yish
// ============================================
function view_filtered_payments(frm) {
	if (!frm.doc.sales_order) {
		frappe.msgprint(__('Sales Order topilmadi!'));
		return;
	}

	// Payment Entry list sahifasiga o'tish va filter qo'yish
	frappe.set_route('List', 'Payment Entry', {
		'custom_contract_reference': frm.doc.sales_order
	});
}
