// Item Client Script - Auto-generate Item Code and hide it

frappe.ui.form.on('Item', {
    onload: function(frm) {
        // Hide item_code field (it's auto-generated)
        frm.set_df_property('item_code', 'hidden', 1);
        frm.set_df_property('item_code', 'reqd', 0);
        
        // Make item_name optional (auto-fills from custom_product_name)
        frm.set_df_property('item_name', 'reqd', 0);
    },
    
    refresh: function(frm) {
        // Hide item_code in both form and quick entry
        frm.set_df_property('item_code', 'hidden', 1);
        frm.set_df_property('item_code', 'reqd', 0);
        frm.set_df_property('item_name', 'reqd', 0);
    },
    
    custom_product_name: function(frm) {
        // Auto-fill item_name from custom_product_name
        if (frm.doc.custom_product_name && !frm.doc.item_name) {
            frm.set_value('item_name', frm.doc.custom_product_name);
        }
    },
    
    before_save: function(frm) {
        // Ensure item_name is set from custom_product_name
        if (frm.doc.custom_product_name && !frm.doc.item_name) {
            frm.doc.item_name = frm.doc.custom_product_name;
        }
    }
});

// Override Quick Entry Dialog for Item
frappe.provide('frappe.ui.form');

// Create custom Quick Entry class for Item
class ItemQuickEntry extends frappe.ui.form.QuickEntryForm {
    constructor(doctype, after_insert) {
        super(doctype, after_insert);
        this.skip_redirect_on_error = false;
    }

    render_dialog() {
        this.mandatory = this.get_variant_fields();
        super.render_dialog();
        
        // Hide item_code (auto-generated)
        this.dialog.set_df_property('item_code', 'hidden', 1);
        this.dialog.set_df_property('item_code', 'reqd', 0);
        
        // Hide item_name (auto-fills from custom_product_name)
        this.dialog.set_df_property('item_name', 'hidden', 1);
        this.dialog.set_df_property('item_name', 'reqd', 0);
        
        // Auto-fill item_name when custom_product_name changes
        this.dialog.fields_dict.custom_product_name.$input.on('change', () => {
            let product_name = this.dialog.get_value('custom_product_name');
            if (product_name) {
                this.dialog.set_value('item_name', product_name);
            }
        });
    }
    
    get_variant_fields() {
        // Only show essential fields in Quick Entry
        return [
            {
                fieldtype: 'Data',
                label: __('Mahsulot nomi'),
                fieldname: 'custom_product_name',
                reqd: 1
            },
            {
                fieldtype: 'Currency',
                label: __('Tan Narxi (USD)'),
                fieldname: 'custom_cost_price',
                options: 'USD',
                reqd: 1
            },
            {
                fieldtype: 'Data',
                label: __('IMEI / Serial'),
                fieldname: 'custom_imei',
                reqd: 0
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Link',
                label: __('Item Group'),
                fieldname: 'item_group',
                options: 'Item Group',
                default: 'Products',
                reqd: 1
            },
            {
                fieldtype: 'Link',
                label: __('Default Unit of Measure'),
                fieldname: 'stock_uom',
                options: 'UOM',
                default: 'Unit',
                reqd: 1
            },
            // Hidden fields - will auto-fill
            {
                fieldtype: 'Data',
                fieldname: 'item_code',
                hidden: 1,
                reqd: 0
            },
            {
                fieldtype: 'Data',
                fieldname: 'item_name',
                hidden: 1,
                reqd: 0
            }
        ];
    }
    
    insert() {
        // Auto-fill item_name before insert
        let product_name = this.dialog.get_value('custom_product_name');
        if (product_name && !this.dialog.get_value('item_name')) {
            this.dialog.set_value('item_name', product_name);
        }
        
        // Call parent insert
        return super.insert();
    }
}

// Register custom Quick Entry
frappe.ui.form.ItemQuickEntryForm = ItemQuickEntry;

// Make sure it's used for Item doctype
frappe.provide('frappe.ui.form.quick_entry_handlers');
frappe.ui.form.quick_entry_handlers['Item'] = ItemQuickEntry;
