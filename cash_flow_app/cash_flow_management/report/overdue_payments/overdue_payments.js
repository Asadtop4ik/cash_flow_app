// Copyright (c) 2025, Cash Flow App and contributors
// For license information, please see license.txt

frappe.query_reports["Overdue Payments"] = {
	"filters": [
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},
		{
			"fieldname": "min_days_overdue",
			"label": __("Min Days Overdue"),
			"fieldtype": "Int",
			"default": 1
		}
	],
	onload: function(report) {
		report.page.add_inner_button(__('Export to Excel'), function() {
			report.export_report('xlsx');
		});
	}
};