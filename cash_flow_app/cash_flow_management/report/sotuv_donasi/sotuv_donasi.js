// Copyright (c) 2026, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Sotuv Donasi"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("Dan (Sana)"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 0,
		},
		{
			fieldname: "to_date",
			label: __("Gacha (Sana)"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 0,
		},
		{
			fieldname: "customer",
			label: __("Mijoz"),
			fieldtype: "Link",
			options: "Customer",
			reqd: 0,
		},
		{
			fieldname: "item_code",
			label: __("Mahsulot"),
			fieldtype: "Link",
			options: "Item",
			reqd: 0,
		},
		{
			fieldname: "installment_application",
			label: __("Shartnoma ID"),
			fieldtype: "Link",
			options: "Installment Application",
			reqd: 0,
		},
	],
};
