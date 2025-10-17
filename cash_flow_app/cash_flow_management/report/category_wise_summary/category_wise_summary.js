// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Category-wise Summary"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.month_end(),
			"reqd": 1
		},
		{
			"fieldname": "category_type",
			"label": __("Category Type"),
			"fieldtype": "Select",
			"options": "Both\nIncome\nExpense",
			"default": "Both"
		},
		{
			"fieldname": "category",
			"label": __("Specific Category"),
			"fieldtype": "Link",
			"options": "Counterparty Category"
		},
		{
			"fieldname": "cost_center",
			"label": __("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center"
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Data"
		}
	],
	
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		
		if (column.fieldname == "category_type") {
			if (data && data.category_type == "Income") {
				value = `<span class="badge badge-success">Income</span>`;
			} else if (data && data.category_type == "Expense") {
				value = `<span class="badge badge-danger">Expense</span>`;
			}
		}
		
		if (column.fieldname == "total_amount") {
			if (data && data.category_type == "Income") {
				value = `<span style="color: green; font-weight: bold;">${value}</span>`;
			} else if (data && data.category_type == "Expense") {
				value = `<span style="color: red; font-weight: bold;">${value}</span>`;
			}
		}
		
		if (column.fieldname == "percentage" && data && data.percentage) {
			value = `${data.percentage.toFixed(2)}%`;
		}
		
		return value;
	},
	
	"onload": function(report) {
		// Add custom button to export detailed breakdown
		report.page.add_inner_button(__("Export Details"), function() {
			frappe.msgprint(__("Exporting detailed breakdown..."));
			// Future: Implement detailed export functionality
		}, __("Actions"));
	}
};
