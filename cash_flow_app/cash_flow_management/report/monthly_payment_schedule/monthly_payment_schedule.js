// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Payment Schedule"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"reqd": 1
		},
		{
			"fieldname": "show_next_month",
			"label": __("Include Next Month"),
			"fieldtype": "Check",
			"default": 0
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer"
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": "\nPending\nOverdue\nDue Today\nDue This Week\nPaid"
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
			} else if (data && data.status == "Due Today") {
				value = `<span class="badge badge-warning">Due Today</span>`;
			} else if (data && data.status == "Due This Week") {
				value = `<span class="badge badge-warning">Due This Week</span>`;
			} else if (data && data.status == "Pending") {
				value = `<span class="badge badge-info">Pending</span>`;
			} else if (data && data.status == "Paid") {
				value = `<span class="badge badge-success">Paid</span>`;
			}
		}
		
		if (column.fieldname == "days_to_due") {
			if (data && data.days_to_due < 0) {
				value = `<span style="color: red; font-weight: bold;">${data.days_to_due} (Overdue)</span>`;
			} else if (data && data.days_to_due == 0) {
				value = `<span style="color: orange; font-weight: bold;">Today</span>`;
			} else if (data && data.days_to_due <= 7) {
				value = `<span style="color: orange;">${data.days_to_due}</span>`;
			}
		}
		
		if (column.fieldname == "outstanding" && data && data.outstanding > 0) {
			if (data.days_to_due < 0) {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		return value;
	},
	
	"onload": function(report) {
		// Add custom button to send SMS reminders (placeholder for future)
		report.page.add_inner_button(__("Send Reminders"), function() {
			frappe.msgprint(__("SMS reminder feature will be implemented in future phase."));
		}, __("Actions"));
	}
};
