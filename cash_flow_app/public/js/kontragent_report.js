// Kontragent Report - JavaScript
// Click on Party Name → Open personal dashboard/form

frappe.query_reports["Kontragent Report"] = {
    // ✅ Filters (agar kerak bo'lsa)
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

    // ✅ Report yuklanganida styling qo'llash
    onload: function(report) {
        frappe.after_ajax(() => {
            this.add_total_row_styling();
            this.setup_click_handlers(report);
        });
    },

    // ✅ Har refresh bo'lganda styling qayta qo'llash
    refresh: function(report) {
        this.add_total_row_styling();
        this.setup_click_handlers(report);
    },

    // ✅ TOTAL qatorlarini bold qilish funksiyasi
    add_total_row_styling: function() {
        setTimeout(() => {
            const rows = document.querySelectorAll('.dt-row');

            rows.forEach(row => {
                // "TOTAL" yoki "CUSTOMER TOTAL" yoki "SUPPLIER TOTAL" so'zi bor qatorlarni topish
                const cells = row.querySelectorAll('.dt-cell__content');

                cells.forEach(cell => {
                    const text = cell.textContent.trim();

                    // Agar cell "TOTAL" so'zini o'z ichiga olsa
                    if (text.includes('TOTAL') || text === 'CUSTOMER TOTAL' || text === 'SUPPLIER TOTAL') {
                        // Butun qatorni bold qilish
                        const allCells = row.querySelectorAll('.dt-cell__content');
                        allCells.forEach(c => {
                            c.style.fontWeight = 'bold';
                            c.style.backgroundColor = '#f0f0f0';
                            c.style.fontSize = '14px';
                        });

                        // Butun rowga background
                        row.style.backgroundColor = '#f5f5f5';
                    }
                });
            });
        }, 150);
    },

    // ✅ Party name click handlerlari
    setup_click_handlers: function(report) {
        const self = this;

        // Biroz kutib, DOM elementlari yuklanishini kutamiz
        setTimeout(() => {
            // Party name ustiga click qilish
            const partyLinks = document.querySelectorAll('[data-fieldname="party"] a');

            partyLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();

                    const party_name = this.textContent.trim();
                    const row = this.closest('.dt-row');

                    if (!row) return;

                    // Party type topish
                    const partyTypeCell = row.querySelector('[data-fieldname="party_type"] .dt-cell__content');
                    const party_type = partyTypeCell ? partyTypeCell.textContent.trim() : '';

                    console.log('Party clicked:', {party_name, party_type});

                    // TOTAL qatorlarni ignore qilish
                    if (party_type.includes('TOTAL') || party_name.includes('TOTAL')) {
                        return;
                    }

                    // Party formiga o'tish
                    if (party_type === 'Customer') {
                        frappe.set_route('Form', 'Customer', party_name);
                    }
                    else if (party_type === 'Supplier') {
                        frappe.set_route('Form', 'Supplier', party_name);
                    }
                });
            });
        }, 200);
    }
};
