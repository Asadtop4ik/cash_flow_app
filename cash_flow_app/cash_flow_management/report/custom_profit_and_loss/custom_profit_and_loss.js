// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Custom Profit and Loss"] = {
    "formatter": function(value, row, column, data, default_formatter) {
        if (value === undefined || value === null || value === "") return "";

        // Birinchi ustun (account) emas bo'lsa - raqamli formatlaymiz
        if (column.fieldname !== "account" && data) {
            // Identify if the row should be treated as a percentage
            const isPercentage = data.account?.includes("Rentabillik");

            // Qiymatni raqamga aylantirish
            let numValue = parseFloat(String(value).replace(/[^0-9.-]/g, ''));
            
            if (isNaN(numValue)) {
                return default_formatter(value, row, column, data);
            }

            if (isPercentage) {
                // Format as 19.0%
                return `<span style="font-style: italic;">${numValue.toFixed(1)}%</span>`;
            }

            // 1. Round to integer
            let roundedValue = Math.round(numValue);
            
            // 2. Format with spaces using ru-RU and FORCE replace non-breaking spaces with standard spaces
            let formattedNumber = new Intl.NumberFormat('ru-RU').format(Math.abs(roundedValue)).replace(/\u00a0/g, ' ');

            // 3. Construct the final string
            let displayValue = (roundedValue < 0) ? `- $ ${formattedNumber}` : `$ ${formattedNumber}`;

            // 4. Styling logic
            let styles = [];
            if (roundedValue < 0) styles.push("color: #e74c3c"); // Red for negative
            // Bold for key rows
            if (["Savdo", "Tannarx", "Yalpi foyda", "Jami harajatlar", "Sof foyda"].includes(data.account)) {
                styles.push("font-weight: 700");
            }

            if (styles.length > 0) {
                return `<span style="${styles.join('; ')}">${displayValue}</span>`;
            }
            return displayValue;
        }

        // For non-numeric columns (like "account"), use default formatter then apply styling
        value = default_formatter(value, row, column, data);

        if (!data) return value;

        // Savdo - bold va link
        if (data.account === "Savdo" && column.fieldname === "account") {
            const from_date = frappe.query_report.get_filter_value('from_date');
            const to_date = frappe.query_report.get_filter_value('to_date');

            value = `<a href="#" onclick="
                frappe.set_route('query-report', 'Savdo va Foyda', {
                    'from_date': '${from_date}',
                    'to_date': '${to_date}'
                });
                return false;
            " style="font-weight: 700; color: #2490ef; text-decoration: underline; cursor: pointer;">
                ${data.account}
            </a>`;
        } else if (data.account === "Savdo") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Tannarx - bold
        if (data.account === "Tannarx" && column.fieldname === "account") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Yalpi foyda - bold
        if (data.account === "Yalpi foyda" && column.fieldname === "account") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Jami harajatlar - bold
        if (data.account === "Jami harajatlar" && column.fieldname === "account") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Sof foyda - bold
        if (data.account === "Sof foyda" && column.fieldname === "account") {
            value = `<span style="font-weight: 700;">${value}</span>`;
        }

        // Rentabillik - qiyshaygan
        if (data.account === "Rentabillik" && column.fieldname === "account") {
            value = `<span style="font-style: italic;">${value}</span>`;
        }

        // Sof Rentabillik - qiyshaygan
        if (data.account === "Sof Rentabillik" && column.fieldname === "account") {
            value = `<span style="font-style: italic;">${value}</span>`;
        }

        // Xarajat kategoriyalari uchun link qo'shish
        if (column.fieldname === "account" && data.category_id && data.indent === 1) {
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
