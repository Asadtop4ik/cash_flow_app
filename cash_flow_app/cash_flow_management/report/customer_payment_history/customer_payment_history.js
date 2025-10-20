// Copyright (c) 2025, Cash Flow App and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Payment History"] = {
	"filters": [
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 100
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -6),
			"width": 80
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"width": 80
		},
		{
			"fieldname": "contract_status",
			"label": __("Contract Status"),
			"fieldtype": "Select",
			"options": "\nDraft\nTo Deliver and Bill\nTo Bill\nTo Deliver\nCompleted\nCancelled\nClosed",
			"width": 100
		},
		{
			"fieldname": "payment_status",
			"label": __("Payment Status"),
			"fieldtype": "Select",
			"options": "\nFully Paid\nPartially Paid\nPending\nOverdue",
			"width": 100
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code payment status
		if (column.fieldname == "payment_status") {
			if (value && value.includes("Fully Paid")) {
				value = `<span style="color: #16a34a; font-weight: 600;">${value}</span>`;
			} else if (value && value.includes("Overdue")) {
				value = `<span style="color: #dc2626; font-weight: 600;">${value}</span>`;
			} else if (value && value.includes("Partially")) {
				value = `<span style="color: #ea580c; font-weight: 600;">${value}</span>`;
			} else if (value && value.includes("Pending")) {
				value = `<span style="color: #2563eb; font-weight: 600;">${value}</span>`;
			}
		}
		
		// Color code contract status
		if (column.fieldname == "contract_status") {
			if (value && value.includes("Active")) {
				value = `<span style="color: #2563eb; font-weight: 600;">🔵 ${value}</span>`;
			} else if (value && value.includes("Completed")) {
				value = `<span style="color: #16a34a; font-weight: 600;">✅ ${value}</span>`;
			} else if (value && value.includes("Pending")) {
				value = `<span style="color: #ea580c; font-weight: 600;">⏳ ${value}</span>`;
			}
		}
		
		// Highlight outstanding amounts
		if (column.fieldname == "outstanding_amount" && data) {
			let amount = parseFloat(data.outstanding_amount) || 0;
			if (amount > 0) {
				value = `<span style="color: #dc2626; font-weight: 600;">${value}</span>`;
			} else {
				value = `<span style="color: #16a34a; font-weight: 600;">${value}</span>`;
			}
		}
		
		// Make contract clickable
		if (column.fieldname == "contract" && data && data.contract) {
			value = `<a href="/app/installment-application/${data.contract}" target="_blank" style="font-weight: 600;">${data.contract}</a>`;
		}
		
		// Make customer clickable
		if (column.fieldname == "customer" && data && data.customer) {
			value = `<a href="/app/customer/${data.customer}" target="_blank" style="font-weight: 600;">${data.customer}</a>`;
		}
		
		return value;
	},
	
	"onload": function(report) {
		// Add summary cards at the top
		report.page.add_inner_button(__("View All Payments"), function() {
			frappe.set_route("List", "Payment Entry", {
				"party_type": "Customer",
				"docstatus": 1
			});
		});
		
		report.page.add_inner_button(__("Export to Excel"), function() {
			report.export_report("xlsx");
		});
	}
};
