// Kontragent Report - Party Filter Controller
// File: cash_flow_app/cash_flow_management/report/kontragent_report/kontragent_report.js

frappe.query_reports["Kontragent Report"] = {
    "onload": function(report) {
        console.log('📊 Kontragent Report loaded');

        // Party Type o'zgarganda Party filterini yangilash
        report.page.add_inner_button(__('Refresh'), function() {
            report.refresh();
        });
    },

    "filters": [
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
            "options": "\nCustomer\nSupplier\nEmployee",
            "default": "Customer",
            "on_change": function(query_report) {
                // Party Type o'zgarganda Party filterini tozalash va yangilash
                let party_type = query_report.get_filter_value('party_type');
                let party_filter = query_report.get_filter('party');

                if (party_filter && party_type) {
                    // Party filter options'ni yangilash
                    party_filter.df.options = party_type;
                    party_filter.refresh();

                    // Party qiymatini tozalash
                    query_report.set_filter_value('party', '');

                    console.log(`✅ Party filter options yangilandi: ${party_type}`);
                }
            }
        },
        {
            "fieldname": "party",
            "label": __("Party"),
            "fieldtype": "Link",
            "options": "Customer",  // Default - Party Type bilan o'zgaradi
            "get_query": function() {
                let party_type = frappe.query_report.get_filter_value('party_type');

                if (!party_type) {
                    frappe.msgprint(__('Avval Party Type tanlang'));
                    return { filters: { 'name': '' } };  // Bo'sh natija
                }

                // Party Type'ga mos filterlar
                return {
                    filters: {
                        'disabled': 0
                    }
                };
            }
        }
    ]
};
