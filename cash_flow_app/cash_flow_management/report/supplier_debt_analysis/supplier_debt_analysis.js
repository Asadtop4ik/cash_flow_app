// Copyright (c) 2025, Cash Flow App and contributors
// For license information, please see license.txt

frappe.query_reports["Supplier Debt Analysis"] = {
	"filters": [
		{
			"fieldname": "supplier",
			"label": __("Supplier"),
			"fieldtype": "Link",
			"options": "Supplier",
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
			"fieldname": "debt_status",
			"label": __("Debt Status"),
			"fieldtype": "Select",
			"options": "\nFully Paid\nPartially Paid\nUnpaid",
			"width": 100
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Color code debt status
		if (column.fieldname == "debt_status") {
			if (value && value.includes("Fully Paid")) {
				value = `<span style="color: #16a34a; font-weight: 600;">✅ ${value}</span>`;
			} else if (value && value.includes("Unpaid")) {
				value = `<span style="color: #dc2626; font-weight: 600;">❌ ${value}</span>`;
			} else if (value && value.includes("Partially")) {
				value = `<span style="color: #ea580c; font-weight: 600;">🟡 ${value}</span>`;
			}
		}
		
		// Highlight outstanding amounts
		if (column.fieldname == "outstanding_debt" && data) {
			let amount = parseFloat(data.outstanding_debt) || 0;
			if (amount > 0) {
				value = `<span style="color: #dc2626; font-weight: 600;">${value}</span>`;
			} else {
				value = `<span style="color: #16a34a; font-weight: 600;">${value}</span>`;
			}
		}
		
		// Make supplier clickable
		if (column.fieldname == "supplier" && data && data.supplier) {
			value = `<a href="/app/supplier/${data.supplier}" target="_blank" style="font-weight: 600;">${data.supplier}</a>`;
		}
		
		// Make product clickable
		if (column.fieldname == "product" && data && data.product) {
			value = `<a href="/app/item/${data.product}" target="_blank" style="font-weight: 500;">${data.product}</a>`;
		}
		
		// Group separator row (when supplier changes)
		if (data && data.is_group_header) {
			return `<span style="background: #f3f4f6; font-weight: 700; padding: 5px;">${value}</span>`;
		}
		
		return value;
	},
	
	"onload": function(report) {
		// Add action buttons
		report.page.add_inner_button(__("View All Payments"), function() {
			frappe.set_route("List", "Payment Entry", {
				"party_type": "Supplier",
				"docstatus": 1
			});
		});
		
		report.page.add_inner_button(__("Export to Excel"), function() {
			report.export_report("xlsx");
		});
		
		report.page.add_inner_button(__("Supplier List"), function() {
			frappe.set_route("List", "Supplier");
		});
	},
	
	"tree": false,
	"name_field": "supplier",
	"parent_field": "",
	"initial_depth": 0
};
