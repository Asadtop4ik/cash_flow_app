// Copyright (c) 2025, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Operational Balance Sheet"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("Sana dan"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("Sana gacha"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(),
			"reqd": 1
		},
		{
			"fieldname": "periodicity",
			"label": __("Davr"),
			"fieldtype": "Select",
			"options": ["Daily", "Monthly", "Quarterly", "Yearly"],
			"default": "Monthly",
			"reqd": 1
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Main sections (AKTIVLAR, JAMI KREDITORKA, BALANS)
		if (data && data.indent === 0) {
			if (column.fieldname === "account") {
				value = `<span style="font-weight: bold; font-size: 15px; color: #2c3e50; text-transform: uppercase;">${value}</span>`;
			} else {
				value = `<span style="font-weight: bold; font-size: 14px;">${value}</span>`;
			}
		}

		// Level 1 bold (Pul, Debitorka, Kreditorka, Ustav, Sof Foyda)
		if (data && data.indent === 1 && data.is_group) {
			value = `<span style="font-weight: bold;">${value}</span>`;
		}

		// Level 2 bold (Mijozlar, Yetkazib beruvchilar)
		if (data && data.indent === 2 && data.is_group) {
			value = `<span style="font-weight: bold;">${value}</span>`;
		}

		// Level 3 bold (Customer Groups, Supplier Groups)
		if (data && data.indent === 3 && data.is_group) {
			value = `<span style="font-weight: bold; color: #555;">${value}</span>`;
		}

		// BALANS row highlighting
		if (data && data.account && data.account === "BALANS") {
			if (column.fieldname !== "account") {
				const numValue = parseFloat(data[column.fieldname]) || 0;
				const color = Math.abs(numValue) < 0.01 ? "#27ae60" : "#e74c3c";
				value = `<span style="font-weight: bold; color: ${color}; font-size: 14px;">${value}</span>`;
			}
		}

		// Format negative numbers with minus sign
		if (column.fieldname !== "account" && data) {
			const numValue = parseFloat(data[column.fieldname]);
			if (!isNaN(numValue) && numValue < 0) {
				value = value.replace(/[\d,.-]+/, function(match) {
					const absValue = Math.abs(parseFloat(match.replace(/,/g, '')));
					return `-${absValue.toLocaleString('en-US', {
						minimumFractionDigits: 2,
						maximumFractionDigits: 2
					})}`;
				});
				value = `<span style="color: #e74c3c;">${value}</span>`;
			}
		}

		return value;
	},

	"tree": true,
	"name_field": "account",
	"parent_field": "",
	"initial_depth": 2,

	onload: function(report) {
		// Refresh button
		report.page.add_inner_button(__("Yangilash"), function() {
			report.refresh();
		});

		// Export to Excel
		report.page.add_inner_button(__("Excel'ga eksport"), function() {
			frappe.utils.to_excel(report.data, report.report_name);
		});

		// Help button
		report.page.set_secondary_action(__("Yordam"), function() {
			frappe.msgprint({
				title: __("Operatsion Balans Hisoboti - Yordam"),
				message: `
					<h4 style="color: #2c3e50; margin-top: 15px;">📊 Hisobot Strukturasi</h4>
					<ul style="line-height: 1.8;">
						<li><b>AKTIVLAR:</b>
							<ul>
								<li>Pul - Kassa va bank hisoblaridagi mablag'lar</li>
								<li>Debitorka:
									<ul>
										<li>Mijozlar - Nasiya sotilgan mahsulotlar</li>
										<li>Yetkazib beruvchilar - Berilgan avanslar</li>
									</ul>
								</li>
							</ul>
						</li>
						<li style="margin-top: 10px;"><b>JAMI KREDITORKA:</b>
							<ul>
								<li>Kreditorka:
									<ul>
										<li>Mijozlar - Olingan avanslar</li>
										<li>Yetkazib beruvchilar - Yetkazib beruvchilarga qarzlar</li>
									</ul>
								</li>
								<li>Ustav Kapitali - Aksiyadorlardan olingan mablag'lar</li>
								<li>Sof Foyda - Foiz daromadlari minus xarajatlar</li>
							</ul>
						</li>
						<li style="margin-top: 10px;"><b>BALANS:</b>
							<span style="color: #27ae60;">Aktivlar - Jami Kreditorka = 0</span>
							(agar to'g'ri hisoblanmagan bo'lsa, qizil rangda ko'rinadi)
						</li>
					</ul>

					<h4 style="color: #2c3e50; margin-top: 20px;">📅 Davr Turlari</h4>
					<ul style="line-height: 1.8;">
						<li><b>Daily (Kunlik):</b> Har bir kun uchun alohida ustun</li>
						<li><b>Monthly (Oylik):</b> Har bir oy uchun alohida ustun</li>
						<li><b>Quarterly (Choraklik):</b> Har bir chorak uchun alohida ustun</li>
						<li><b>Yearly (Yillik):</b> Har bir yil uchun alohida ustun</li>
					</ul>

					<h4 style="color: #2c3e50; margin-top: 20px;">💾 Ma'lumotlar Manbalari</h4>
					<ul style="line-height: 1.8;">
						<li><b>Pul:</b> Payment Entry (Receive/Pay/Internal Transfer)</li>
						<li><b>Debitorka (Mijozlar):</b> Sales Order + Payment Entry (Pay)</li>
						<li><b>Debitorka (Yetkazib beruvchilar):</b> Payment Entry (Supplier, Pay)</li>
						<li><b>Kreditorka (Mijozlar):</b> Payment Entry (Customer, Receive)</li>
						<li><b>Kreditorka (Yetkazib beruvchilar):</b> Payment Entry (Supplier, Receive)</li>
						<li><b>Ustav Kapitali:</b> Payment Entry (Shareholder) - Receive minus Pay</li>
						<li><b>Sof Foyda:</b> Installment Application (Foiz daromadlari) - Counterparty Category (Xarajatlar)</li>
					</ul>

					<h4 style="color: #2c3e50; margin-top: 20px;">🎨 Ranglar</h4>
					<ul style="line-height: 1.8;">
						<li><span style="color: #27ae60;">● Yashil</span> - BALANS 0 ga teng (to'g'ri)</li>
						<li><span style="color: #e74c3c;">● Qizil</span> - BALANS 0 ga teng emas (xatolik bor)</li>
						<li><span style="color: #e74c3c;">● Qizil raqamlar</span> - Manfiy qiymatlar</li>
					</ul>

					<p style="margin-top: 20px; padding: 10px; background: #f8f9fa; border-left: 3px solid #3498db;">
						<b>💡 Maslahat:</b> Qatorlarni ochish/yopish uchun chap tomondagi + / - tugmalarini bosing.
					</p>
				`,
				wide: true
			});
		});

		// Add success message after load
		frappe.show_alert({
			message: __('Hisobot muvaffaqiyatli yuklandi'),
			indicator: 'green'
		}, 3);
	}
};
