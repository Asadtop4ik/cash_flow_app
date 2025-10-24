// Copyright (c) 2025, Cash Flow App and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Expected Payments"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Data",
			"default": frappe.datetime.now_date().slice(0, 7),
			"description": __("Format: YYYY-MM (e.g., 2025-09 for September 2025)")
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "payment_status",
			"label": __("Payment Status"),
			"fieldtype": "Select",
			"options": "\nPaid\nPartially Paid\nUnpaid\nOverdue"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "payment_status") {
			if (value == "To'landi") {
				value = `<span style="color: green; font-weight: bold;">✅ ${value}</span>`;
			} else if (value == "Qisman to'langan") {
				value = `<span style="color: orange; font-weight: bold;">🟡 ${value}</span>`;
			} else if (value == "Muddati o'tgan") {
				value = `<span style="color: red; font-weight: bold;">❌ ${value}</span>`;
			} else {
				value = `<span style="color: blue;">⏳ ${value}</span>`;
			}
		}
		
		return value;
	}
};