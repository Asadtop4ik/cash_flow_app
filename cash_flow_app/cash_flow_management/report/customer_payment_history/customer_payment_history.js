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
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		// Style TOTAL row
		if (data && data.is_total_row) {
			if (column.fieldname == "customer") {
				return `<div style="background: #1e3a8a; color: white; font-weight: 600; font-size: 13px; padding: 6px; text-align: center; border-radius: 4px;">TOTAL</div>`;
			}
			return `<span style="font-weight: 600; color: #1e3a8a; font-size: 13px;">${value}</span>`;
		}
		
		// Color code status
		if (column.fieldname == "status") {
			if (value && value.includes("Submitted")) {
				value = `<span style="color: #16a34a; font-weight: 600;">✅ ${value}</span>`;
			} else if (value && value.includes("Draft")) {
				value = `<span style="color: #ea580c; font-weight: 600;">📝 ${value}</span>`;
			}
		}
		
		// Highlight outstanding amounts
		if (column.fieldname == "outstanding" && data && !data.is_total_row) {
			let amount = parseFloat(data.outstanding) || 0;
			if (amount > 0) {
				value = `<span style="color: #dc2626; font-weight: 600;">${value}</span>`;
			} else {
				value = `<span style="color: #16a34a; font-weight: 600;">${value}</span>`;
			}
		}
		
		// Make contract clickable
		if (column.fieldname == "contract" && data && data.contract && !data.is_total_row) {
			value = `<a href="/app/sales-order/${data.contract}" target="_blank" style="font-weight: 600;">${data.contract}</a>`;
		}
		
		// Make customer clickable (but NOT for Total row)
		if (column.fieldname == "customer" && data && data.customer && !data.is_total_row) {
			value = `<a href="/app/customer/${data.customer}" target="_blank" style="font-weight: 600;">${data.customer}</a>`;
		}
		
		// Make payment entry clickable
		if (column.fieldname == "payment_entry" && data && data.payment_entry && !data.is_total_row) {
			value = `<a href="/app/payment-entry/${data.payment_entry}" target="_blank" style="font-weight: 500;">${data.payment_entry}</a>`;
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
	},
	
	// Disable Frappe's automatic total row calculation
	"disable_auto_totals": true
};
