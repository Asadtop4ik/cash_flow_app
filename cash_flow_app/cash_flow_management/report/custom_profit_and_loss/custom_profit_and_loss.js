// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Profit and Loss"] = {
	"formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // Savdo - yashil bold
        if (data && data.account === "Savdo") {
            if (column.fieldname !== "account") {
                value = `<span style="font-weight: 700; color: #16a34a; font-size: 14px;">${value}</span>`;
            } else {
                value = `<span style="font-weight: 700; color: #16a34a; font-size: 14px; background: #dcfce7; padding: 4px 8px; border-radius: 4px;">${value}</span>`;
            }
        }

        // Tannarx - to'q sariq bold
        if (data && data.account === "Tannarx") {
            if (column.fieldname !== "account") {
                value = `<span style="font-weight: 700; color: #ea580c; font-size: 14px;">${value}</span>`;
            } else {
                value = `<span style="font-weight: 700; color: #ea580c; font-size: 14px; background: #fed7aa; padding: 4px 8px; border-radius: 4px;">${value}</span>`;
            }
        }

        // Yalpi foyda - ko'k bold
        if (data && data.account === "Yalpi foyda") {
            if (column.fieldname !== "account") {
                value = `<span style="font-weight: 700; color: #2563eb; font-size: 14px;">${value}</span>`;
            } else {
                value = `<span style="font-weight: 700; color: #2563eb; font-size: 14px; background: #dbeafe; padding: 4px 8px; border-radius: 4px;">${value}</span>`;
            }
        }

        // Jami harajatlar - qizil bold
        if (data && data.account === "Jami harajatlar") {
            if (column.fieldname !== "account") {
                value = `<span style="font-weight: 700; color: #dc2626; font-size: 14px;">${value}</span>`;
            } else {
                value = `<span style="font-weight: 700; color: #dc2626; font-size: 14px; background: #fee2e2; padding: 4px 8px; border-radius: 4px;">${value}</span>`;
            }
        }

        // Sof foyda - binafsha bold
        if (data && data.account === "Sof foyda") {
            if (column.fieldname !== "account") {
                value = `<span style="font-weight: 700; color: #9333ea; font-size: 14px;">${value}</span>`;
            } else {
                value = `<span style="font-weight: 700; color: #9333ea; font-size: 14px; background: #f3e8ff; padding: 4px 8px; border-radius: 4px;">${value}</span>`;
            }
        }

        // Rentabillik va Sof Rentabillik - qiyshaygan
        if (data && (data.account === "Rentabillik" || data.account === "Sof Rentabillik")) {
            value = `<span style="font-style: italic; color: #64748b; font-size: 13px;">${value}</span>`;
        }

        return value;
    },
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
