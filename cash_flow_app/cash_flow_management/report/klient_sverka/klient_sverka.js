// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Klient Sverka"] = {
	"filters": [
		{
			"fieldname": "customer",
			"label": __("Mijoz"),
			"fieldtype": "Link",
			"options": "Customer",
			"reqd": 1,
			"width": 150
		},
		{
			"fieldname": "from_date",
			"label": __("Boshlanish Sanasi"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("Tugash Sanasi"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "contract",
			"label": __("Shartnoma"),
			"fieldtype": "Link",
			"options": "Installment Application",
			"get_query": function() {
				var customer = frappe.query_report.get_filter_value('customer');
				return {
					"filters": {
						"customer": customer,
						"docstatus": 1
					}
				};
			}
		}
	]
};
