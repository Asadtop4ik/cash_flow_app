// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["IMEI Qidiruv"] = {
	"filters": [
		{
			"fieldname": "imei",
			"label": __("IMEI / Serial No"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "supplier_name",
			"label": __("Supplier Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "customer_name",
			"label": __("Customer Name"),
			"fieldtype": "Data",
			"width": 150
		}
	]
};
