// Copyright (c) 2024, Ruxshona and contributors
// For license information, please see license.txt

frappe.query_reports["Savdo va Foyda"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("Boshlanish Sanasi"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 0
		},
		{
			"fieldname": "to_date",
			"label": __("Tugash Sanasi"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 0
		},
		{
			"fieldname": "installment_application",
			"label": __("Shartnoma ID"),
			"fieldtype": "Link",
			"options": "Installment Application",
			"reqd": 0,
			"get_query": function() {
				return {
					"filters": {
						"docstatus": 1
					}
				};
			}
		},
		{
			"fieldname": "customer",
			"label": __("Mijoz"),
			"fieldtype": "Link",
			"options": "Customer",
			"reqd": 0
		}
	],

	onload: function(report) {
		// Qo'shimcha tugmalar (agar kerak bo'lsa)
		report.page.add_inner_button(__("Yangilash"), function() {
			report.refresh();
		});
	}
};
