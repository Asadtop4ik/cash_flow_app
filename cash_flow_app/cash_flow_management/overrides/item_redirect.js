/**
 * Item Redirect Script
 * When Item is saved from Installment Application link, redirect back to parent
 */

frappe.ui.form.on('Item', {
    after_save: function(frm) {
        // Check if we came from Installment Application
        // Frappe stores referrer in route_options
        const route = frappe.get_route();
        const from_link_field = frappe.route_options && frappe.route_options.from_link_field;
        
        // Check if opened from a link field (like item_code in Installment Application Item)
        if (from_link_field) {
            // Find draft Installment Applications using this Item
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Installment Application',
                    filters: {
                        'docstatus': 0,  // Draft only
                        'items.item_code': frm.doc.name
                    },
                    fields: ['name'],
                    limit: 1
                },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        const parent_name = r.message[0].name;
                        
                        // Show success message
                        frappe.show_alert({
                            message: __('✅ Item saqlandi. Shartnomaga qaytilmoqda...'),
                            indicator: 'green'
                        });
                        
                        // Redirect to parent Installment Application after 1 second
                        setTimeout(() => {
                            frappe.set_route('Form', 'Installment Application', parent_name);
                        }, 1000);
                    }
                }
            });
        }
    }
});
