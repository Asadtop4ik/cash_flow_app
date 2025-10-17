// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Outstanding Installments"] = {
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
			"default": frappe.datetime.year_start()
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.year_end()
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nActive\nOverdue\nCompleted",
			"default": ""
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "status") {
			if (data && data.status == "Overdue") {
				value = `<span class="badge badge-danger">Overdue</span>`;
			} else if (data && data.status == "Active") {
				value = `<span class="badge badge-info">Active</span>`;
			} else if (data && data.status == "Completed") {
				value = `<span class="badge badge-success">Completed</span>`;
			}
		}
		
		if (column.fieldname == "days_overdue" && data && data.days_overdue > 0) {
			value = `<span style="color: red; font-weight: bold;">${data.days_overdue}</span>`;
		}
		
		if (column.fieldname == "outstanding_amount" && data && data.outstanding_amount > 0) {
			if (data.days_overdue > 0) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			} else {
				value = `<span style="color: orange; font-weight: bold;">${value}</span>`;
			}
		}
		
		return value;
	}
};
