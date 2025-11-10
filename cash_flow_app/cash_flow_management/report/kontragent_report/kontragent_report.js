// Kontragent Report - JavaScript
frappe.query_reports["Kontragent Report"] = {
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
            "fieldname": "party_type",
            "label": __("Party Type"),
            "fieldtype": "Select",
            "options": ["", "Customer", "Supplier"],
            "default": ""
        },
        {
            "fieldname": "party",
            "label": __("Party"),
            "fieldtype": "Dynamic Link",
            "options": "party_type"
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        // Agar party_type da "TOTAL" yoki party da "Jami" bo'lsa
        if (data && (
            (data.party_type && data.party_type.includes('TOTAL')) ||
            (data.party && data.party === 'Jami')
        )) {
            // Butun qatorni bold qilish va background color
            value = `<span style="font-weight: bold;">${value}</span>`;
        }

        return value;
    }
};
