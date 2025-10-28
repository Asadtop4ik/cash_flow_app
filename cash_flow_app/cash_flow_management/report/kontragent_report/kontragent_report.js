frappe.query_reports["Kontragent Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
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
            "options": "\nCustomer\nSupplier\nEmployee\nShareholder",
            "default": ""
        },
        {
            "fieldname": "party",
            "label": __("Party"),
            "fieldtype": "Dynamic Link",
            "get_options": function() {
                var party_type = frappe.query_report.get_filter_value('party_type');
                var party = frappe.query_report.get_filter_value('party');
                if(party && !party_type) {
                    frappe.throw(__("Please select Party Type first"));
                }
                return party_type;
            }
        }
    ],
    
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        
        // Bold and highlight total row
        if (data && data.party === __("Total")) {
            value = `<span style="font-weight: bold; background-color: #e3f2fd; padding: 2px 5px; display: block;">${value}</span>`;
            return value;
        }
        
        // Highlight rows with significant closing balance
        if (column.fieldname == "party" && data) {
            var closing_credit = data.closing_credit || 0;
            var closing_debit = data.closing_debit || 0;
            var total_closing = closing_credit + closing_debit;
            
            // Highlight if closing balance > 1,000,000
            if (total_closing > 1000000) {
                value = `<span style="background-color: #ffeb3b; padding: 2px 5px; display: block;">${value}</span>`;
            }
            
            // Agar party_type Customer bo'lsa, link qo'shish
            if (data.party_type === "Customer") {
                value = `<a href="#" class="party-link" data-party="${data.party}" data-party_type="${data.party_type}">${value}</a>`;
            }
        }
        
        return value;
    },
    
    onload: function(report) {
        // Click eventni ulash
        report.page.wrapper.on('click', '.party-link', function(e) {
            e.preventDefault();
            var party = $(this).data('party');
            var party_type = $(this).data('party_type');
            
            if (party_type === 'Customer') {
                // Installment Application ro'yxatini shu customer bo'yicha ochish
                frappe.set_route('List', 'Installment Application', {'customer': party});
            }
        });
    }
};
