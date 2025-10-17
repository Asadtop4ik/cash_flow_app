// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.ui.form.on("Installment Application", {
	refresh(frm) {
		// Hide timezone display (Asia/Samarkand text)
		setTimeout(() => {
			$('.frappe-control[data-fieldname="transaction_date"] .help-box').hide();
			$('.frappe-control[data-fieldname="custom_start_date"] .help-box').hide();
		}, 100);
		
		// Auto-calculate on refresh if values exist
		if (frm.doc.total_amount && frm.doc.downpayment_amount && frm.doc.monthly_payment) {
			frm.trigger('calculate_totals');
		}
	},
	
	// Calculate button click
	calculate_schedule_button(frm) {
		if (!frm.doc.total_amount || frm.doc.total_amount <= 0) {
			frappe.msgprint(__('Iltimos avval mahsulot qo\'shing!'));
			return;
		}
		
		if (!frm.doc.downpayment_amount || frm.doc.downpayment_amount <= 0) {
			frappe.msgprint(__('Iltimos boshlang\'ich to\'lovni kiriting!'));
			return;
		}
		
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
		
		// Add downpayment row
		let downpayment_row = frm.add_child('payment_schedule');
		downpayment_row.due_date = frm.doc.custom_start_date;
		downpayment_row.payment_amount = flt(frm.doc.downpayment_amount);
		downpayment_row.invoice_portion = (flt(frm.doc.downpayment_amount) / flt(frm.doc.total_amount)) * 100;
		downpayment_row.description = 'Boshlang\'ich to\'lov';
		
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
		let msg = `<div style="font-size: 14px; line-height: 1.8;">
			<p><strong>📊 HISOB-KITOB:</strong></p>
			<p>Umumiy narx: <strong>$${flt(frm.doc.total_amount).toFixed(2)}</strong></p>
			<p>Boshlang'ich to'lov: <strong>$${flt(frm.doc.downpayment_amount).toFixed(2)}</strong></p>
			<p>Qolgan: <strong>$${flt(frm.doc.finance_amount).toFixed(2)}</strong></p>
			<p>Oylik to'lov: <strong>$${flt(frm.doc.monthly_payment).toFixed(2)} × ${frm.doc.installment_months} oy</strong></p>
			<p>To'lov kuni: <strong>Har oyning ${payment_day}-sanasi</strong></p>
			<p>Jami foiz: <strong style="color: orange;">$${flt(frm.doc.custom_total_interest).toFixed(2)}</strong></p>
			<p>Jami to'lanadi: <strong style="color: green;">$${flt(frm.doc.custom_grand_total_with_interest).toFixed(2)}</strong></p>
			<hr>
			<p><strong>📅 TO'LOV JADVALI:</strong></p>
			<p>Jami qatorlar: <strong>${months + 1} ta</strong> (1 boshlang'ich + ${months} oylik)</p>
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
	
	qty(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
	},
	
	rate(frm, cdt, cdn) {
		calculate_item_amount(frm, cdt, cdn);
	}
});

function calculate_item_amount(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	row.amount = flt(row.qty) * flt(row.rate);
	frm.refresh_field('items');
	frm.trigger('calculate_item_totals');
}

frappe.ui.form.on("Installment Application", {
	calculate_item_totals(frm) {
		let total = 0;
		(frm.doc.items || []).forEach(item => {
			total += flt(item.amount);
		});
		frm.set_value('total_amount', total);
		frm.trigger('calculate_totals');
	}
});
