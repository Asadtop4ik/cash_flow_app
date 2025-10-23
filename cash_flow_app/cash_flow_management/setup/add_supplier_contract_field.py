#!/usr/bin/env python3
"""
Setup script to add custom_supplier_contract field to Payment Entry
This field is used to link Payment Entry (Pay type) to Installment Application
"""

import frappe

def setup_supplier_contract_field():
    """Add custom_supplier_contract field to Payment Entry"""
    
    # Check if field already exists
    if frappe.db.exists("Custom Field", "Payment Entry-custom_supplier_contract"):
        print("✅ Field 'custom_supplier_contract' already exists in Payment Entry")
        return
    
    # Create custom field
    custom_field = frappe.get_doc({
        "doctype": "Custom Field",
        "dt": "Payment Entry",
        "fieldname": "custom_supplier_contract",
        "label": "Shartnoma (Installment Application)",
        "fieldtype": "Link",
        "options": "Installment Application",
        "insert_after": "party_name",
        "depends_on": "eval:doc.payment_type=='Pay' && doc.party_type=='Supplier'",
        "in_list_view": 0,
        "reqd": 0,
        "bold": 0,
        "hidden": 0
    })
    
    custom_field.insert(ignore_permissions=True)
    frappe.db.commit()
    
    print("✅ Successfully created 'custom_supplier_contract' field in Payment Entry")
    print("   Field will show when Payment Type = Pay and Party Type = Supplier")

if __name__ == "__main__":
    frappe.init(site="your_site_name")  # Replace with your site name
    frappe.connect()
    setup_supplier_contract_field()
    print("\n✅ Setup complete!")