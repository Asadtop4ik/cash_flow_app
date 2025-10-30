// Copyright (c) 2025, Cash Flow App and contributors
// For license information, please see license.txt

frappe.query_reports["Supplier Debt Analysis"] = {
	"filters": [
		{
			"fieldname": "supplier",
			"label": __("Yetkazib beruvchi"),
			"fieldtype": "Link",
			"options": "Supplier",
			"reqd": 1,
			"width": 180
		},
		{
			"fieldname": "from_date",
			"label": __("Boshlanish sanasi"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -6),
			"width": 130
		},
		{
			"fieldname": "to_date",
			"label": __("Tugash sanasi"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"width": 130
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// JAMI qatori
		if (data && data.is_total_row) {
			if (column.fieldname == "item_name") {
				return `<span style="font-weight: 700; font-size: 15px; color: #1e3a8a;">JAMI</span>`;
			}
			if (['kredit', 'debit', 'outstanding'].includes(column.fieldname)) {
				return `<span style="font-weight: 700; color: #1e3a8a; font-size: 15px;">${value}</span>`;
			}
			return '';
		}

		// Boshlang'ich qoldiq qatori
		if (data && data.is_initial_row) {
			if (column.fieldname == "item_name") {
				return `<span style="font-weight: 600; font-size: 13px; color: #2563eb; font-style: italic;">${value}</span>`;
			}
			if (['kredit', 'debit', 'outstanding'].includes(column.fieldname)) {
				return `<span style="font-weight: 600; color: #2563eb; font-size: 13px;">${value}</span>`;
			}
			return '';
		}

		// Kredit - qizil
		if (column.fieldname == "kredit" && flt(data.kredit) > 0) {
			value = `<span style="color: #dc2626; font-weight: 600; font-size: 13px;">${value}</span>`;
		}

		// Debit - yashil
		if (column.fieldname == "debit" && flt(data.debit) > 0) {
			value = `<span style="color: #16a34a; font-weight: 600; font-size: 13px;">${value}</span>`;
		}

		// Qoldiq
		if (column.fieldname == "outstanding") {
			let amount = flt(data.outstanding);
			if (amount > 0) {
				value = `<span style="color: #dc2626; font-weight: 700; font-size: 13px;">${value}</span>`;
			} else if (amount < 0) {
				value = `<span style="color: #16a34a; font-weight: 700; font-size: 13px;">${value}</span>`;
			} else {
				value = `<span style="color: #6b7280; font-weight: 600; font-size: 13px;">${value}</span>`;
			}
		}

		// Hujjat linki
		if (column.fieldname == "document" && data.document && data.document_type) {
			// Initial Balance uchun link qilmaslik
			if (data.document === 'Initial Balance') {
				value = `<span style="color: #2563eb; font-weight: 600; font-size: 13px; font-style: italic;">${data.document}</span>`;
			} else {
				let route = data.document_type.toLowerCase().replace(/ /g, '-');
				value = `<a href="/app/${route}/${data.document}" target="_blank" style="color: #2563eb; font-weight: 600; font-size: 13px;">${data.document}</a>`;
			}
		}

		// Izoh
		if (column.fieldname == "notes" && value) {
			let text = value.replace(/<[^>]*>/g, '').trim();
			if (text && text.length < 80) {
				value = `<span style="font-size: 12px; color: #6b7280;">${text}</span>`;
			} else {
				value = '';
			}
		}

		// Kassa (custom_cashier)
		if (column.fieldname == "custom_cashier" && value && value.trim()) {
			value = `<span style="background:#2563eb; color:white; padding:2px 6px; border-radius:3px; font-size:11px; font-weight:600;">${value}</span>`;
		}

		return value;
	},

	"onload": function(report) {
		// Tugmalar
		report.page.add_inner_button(__("Barcha to'lovlar"), () => {
			frappe.set_route("List", "Payment Entry", { "party_type": "Supplier", "docstatus": 1 });
		});
		report.page.add_inner_button(__("Excel ga eksport"), () => report.export_report("xlsx"));
		report.page.add_inner_button(__("Yangi to'lov"), () => {
			frappe.new_doc("Payment Entry", { "party_type": "Supplier", "payment_type": "Pay" });
		});

		// Ogohlantirish
		if (!frappe.query_report.get_filter_value('supplier')) {
			frappe.show_alert({ message: __('Iltimos, yetkazib beruvchini tanlang'), indicator: 'orange' }, 5);
		}

		// CSS - Jadval va Dashboard optimallashtirish
		let css = `
			/* Jadval - to'liq ko'rinishi uchun */
			.report-wrapper .dt-scroll-body {
				max-height: 60vh !important;
				overflow-y: auto !important;
			}
			.dt-responsive table.dataTable {
				width: 100% !important;
				min-width: auto !important;
				table-layout: auto !important;
			}
			.dataTable th, .dataTable td {
				min-width: 110px !important;
				max-width: 250px !important;
				padding: 8px 10px !important;
				font-size: 13px !important;
				white-space: nowrap !important;
				overflow: hidden !important;
				text-overflow: ellipsis !important;
			}
			.dataTable th {
				background: #f8fafc !important;
				font-weight: 600 !important;
				position: sticky !important;
				top: 0 !important;
				z-index: 10 !important;
			}

			/* Dashboard kartalari - bir qatorda, pastga tushmaydi */
			.dashboard-summary {
				display: flex !important;
				flex-wrap: nowrap !important;
				overflow-x: auto !important;
				gap: 12px !important;
				padding: 8px 0 !important;
				margin-bottom: 8px !important;
				scrollbar-width: thin;
			}
			.dashboard-summary::-webkit-scrollbar {
				height: 6px;
			}
			.dashboard-summary::-webkit-scrollbar-thumb {
				background: #cbd5e1;
				border-radius: 3px;
			}
			.dashboard-summary .summary-card {
				flex: 0 0 auto !important;
				min-width: 135px !important;
				max-width: 160px !important;
				padding: 10px 8px !important;
				border-radius: 6px !important;
				box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
				background: white !important;
				text-align: center !important;
				font-size: 13px !important;
				margin: 0 !important;
			}
			.dashboard-summary .summary-card .label {
				font-size: 11.5px !important;
				color: #4b5563 !important;
				margin-bottom: 4px !important;
				white-space: nowrap !important;
				overflow: hidden !important;
				text-overflow: ellipsis !important;
			}
			.dashboard-summary .summary-card .value {
				font-size: 16px !important;
				font-weight: 700 !important;
				color: #1f2937 !important;
			}

			/* Umumiy oq fonni optimallashtirish */
			.report-wrapper {
				padding: 8px !important;
			}
			.page-container {
				background: #f1f5f9 !important;
			}
		`;

		// CSS ni qo'shish
		if (!$('style#supplier-debt-custom-css').length) {
			$('head').append(`<style id="supplier-debt-custom-css">${css}</style>`);
		}
	}
};

