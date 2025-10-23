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
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Style TOTAL row
		if (data && data.is_total_row) {
			if (column.fieldname == "supplier") {
				return `<div style="background: #1e3a8a; color: white; font-weight: 600; font-size: 13px; padding: 6px; text-align: center; border-radius: 4px;">TOTAL</div>`;
			}
			return `<span style="font-weight: 600; color: #1e3a8a; font-size: 13px;">${value}</span>`;
		}
		
		// Color code status
		if (column.fieldname == "status") {
			if (value && value.includes("Debt Added")) {
				value = `<span style="color: #dc2626; font-weight: 600;">📊 ${value}</span>`;
			} else if (value && value.includes("Submitted")) {
				value = `<span style="color: #16a34a; font-weight: 600;">✅ ${value}</span>`;
			}
		}
		
		// Highlight outstanding amounts
		if (column.fieldname == "outstanding" && data) {
			let amount = parseFloat(data.outstanding) || 0;
			if (amount > 0) {
				value = `<span style="color: #dc2626; font-weight: 600;">${value}</span>`;
			} else {
				value = `<span style="color: #16a34a; font-weight: 600;">${value}</span>`;
			}
		}
		
		// Make supplier clickable (but NOT for Total row)
		if (column.fieldname == "supplier" && data && data.supplier && !data.is_total_row) {
			value = `<a href="/app/supplier/${data.supplier}" target="_blank" style="font-weight: 600;">${data.supplier}</a>`;
		}
		
		// Make document clickable
		if (column.fieldname == "document" && data && data.document && data.document_type) {
			let route = data.document_type.toLowerCase().replace(/ /g, '-');
			value = `<a href="/app/${route}/${data.document}" target="_blank" style="font-weight: 500;">${data.document}</a>`;
		}
		
		// Make item clickable
		if (column.fieldname == "item" && data && data.item) {
			value = `<a href="/app/item/${data.item}" target="_blank" style="font-weight: 500;">${data.item}</a>`;
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
	
	// Disable Frappe's automatic total row calculation
	"disable_auto_totals": true,
	
	"tree": false,
	"name_field": "supplier",
	"parent_field": "",
	"initial_depth": 0
};
