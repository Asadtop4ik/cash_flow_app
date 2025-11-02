// Kontragent Report - JavaScript
// Click on Party Name → Open personal dashboard/form

frappe.provide('frappe.views');

frappe.views.QueryReport = frappe.views.QueryReport.extend({
    setup_click_handlers: function() {
        const self = this;

        // Listen for party name clicks
        this.$result.on('click', 'a[data-fieldname="party"]', function(e) {
            e.preventDefault();
            e.stopPropagation();

            const party_name = $(this).text().trim();
            const $row = $(this).closest('tr');
            const party_type = $row.find('[data-fieldname="party_type"]').text().trim();

            console.log('Party clicked:', {party_name, party_type});

            // Don't navigate if TOTAL row
            if (party_name === 'TOTAL') {
                return;
            }

            // Open Party's personal form/dashboard
            if (party_type === 'Customer') {
                // Open Customer form (personal dashboard)
                frappe.set_route('Form', 'Customer', party_name);
            }
            else if (party_type === 'Supplier') {
                // Open Supplier form (personal dashboard)
                frappe.set_route('Form', 'Supplier', party_name);
            }
        });
    }
});

// Alternative: Using DataTable row click
cur_list && cur_list.settings && (cur_list.settings.row_action = function(row_name, data) {
    if (data.party && data.party !== 'TOTAL') {
        if (data.party_type === 'Customer') {
            frappe.set_route('Form', 'Customer', data.party);
        }
        else if (data.party_type === 'Supplier') {
            frappe.set_route('Form', 'Supplier', data.party);
        }
    }
});
