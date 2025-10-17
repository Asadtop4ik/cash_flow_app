"""
Script to fix the auto_debit Property Setter
Run with: bench --site asadstack.com execute cash_flow_app.scripts.fix_auto_debit.run
"""

import frappe

def run():
    """Delete incorrect Property Setter and create correct one"""
    
    # Delete incorrect one if exists
    if frappe.db.exists("Property Setter", "Customer-auto_repeat-hidden"):
        frappe.delete_doc("Property Setter", "Customer-auto_repeat-hidden", force=1, ignore_permissions=True)
        print("✓ Deleted incorrect Property Setter: Customer-auto_repeat-hidden")
    
    # Create correct one
    property_setter_name = "Customer-custom_auto_debit-hidden"
    
    if frappe.db.exists("Property Setter", property_setter_name):
        print(f"✓ Property Setter already exists: {property_setter_name}")
    else:
        ps = frappe.get_doc({
            "doctype": "Property Setter",
            "name": property_setter_name,
            "doctype_or_field": "DocField",
            "doc_type": "Customer",
            "field_name": "custom_auto_debit",
            "property": "hidden",
            "value": "1",
            "property_type": "Check"
        })
        ps.insert(ignore_permissions=True)
        print(f"✓ Created Property Setter: {property_setter_name}")
    
    frappe.db.commit()
    print("\n✅ Property Setter fixed successfully!")
