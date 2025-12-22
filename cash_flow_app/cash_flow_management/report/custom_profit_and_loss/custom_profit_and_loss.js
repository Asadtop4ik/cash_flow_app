// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Profit and Loss"] = {
	"filters": [
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.year_start(),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "periodicity",
			"label": __("Davr turi"),
			"fieldtype": "Select",
			"options": "Monthly\nYearly",
			"default": "Monthly",
			"reqd": 1
		}
	],

	onload: function(report) {
		// Report yuklanganda bajariladigan kod
		console.log("Custom Profit and Loss report yuklandi");
	},

	get_datatable_options: function(options) {
		// Jadval parametrlarini sozlash
		return Object.assign(options, {
			checkboxColumn: false,
			layout: 'fluid'
		});
	}
};
