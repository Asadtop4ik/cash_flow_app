// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Profit and Loss"] = {
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        // Savdo - bold
        if (data.account === "Savdo") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Tannarx - bold
        if (data.account === "Tannarx") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Yalpi foyda - bold
        if (data.account === "Yalpi foyda") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Jami harajatlar - bold
        if (data.account === "Jami harajatlar") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Sof foyda - bold
        if (data.account === "Sof foyda") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Rentabillik - qiyshaygan
        if (data.account === "Rentabillik") {
            value = `<span style="font-style: italic;">${value}</span>`;
        }

        // Sof Rentabillik - qiyshaygan
        if (data.account === "Sof Rentabillik") {
            value = `<span style="font-style: italic;">${value}</span>`;
        }

        // Xarajat kategoriyalari uchun link qo'shish
        if (column.fieldname === "account" && data.category_id && data.indent === 1) {
            const category_name = value.trim();
            value = `<a href="#" onclick="
                frappe.set_route('List', 'Payment Entry', {
                    'custom_counterparty_category': '${data.category_id}'
                });
                return false;
            " style="color: #2490ef; text-decoration: underline; cursor: pointer;">
                ${value}
            </a>`;
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
       console.log("Custom Profit and Loss report yuklandi");
    },

    get_datatable_options: function(options) {
       return Object.assign(options, {
          checkboxColumn: false,
          layout: 'fluid'
       });
    }
};
