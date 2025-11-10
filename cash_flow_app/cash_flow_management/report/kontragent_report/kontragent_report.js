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

    onload: function(report) {
        frappe.after_ajax(() => {
            this.add_total_row_styling();
        });
    },

    refresh: function(report) {
        this.add_total_row_styling();
    },

    add_total_row_styling: function() {
        setTimeout(() => {
            // Barcha qatorlarni topish
            const rows = document.querySelectorAll('.dt-row');

            rows.forEach(row => {
                const cells = row.querySelectorAll('.dt-cell__content');
                
                // Party Type (2-ustun) ni tekshirish
                if (cells.length > 1) {
                    const partyTypeText = cells[1].textContent.trim();
                    
                    // Agar "TOTAL" so'zi bo'lsa
                    if (partyTypeText.includes('TOTAL')) {
                        cells.forEach(cell => {
                            cell.style.fontWeight = 'bold';
                            cell.style.backgroundColor = '#f0f0f0';
                        });
                    }
                }
            });
        }, 100);
    }
};
