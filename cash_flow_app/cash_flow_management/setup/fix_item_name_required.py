"""
Make item_name optional and auto-fill from custom_product_name
"""

import frappe

def fix_item_name_required():
    """Make item_name field optional"""
    
    # Make item_name not required
    existing = frappe.db.exists("Property Setter", {
        "doc_type": "Item",
        "field_name": "item_name",
        "property": "reqd"
    })
    
    if existing:
        frappe.db.set_value("Property Setter", existing, "value", "0")
    else:
        doc = frappe.get_doc({
            "doctype": "Property Setter",
            "doctype_or_field": "DocField",
            "doc_type": "Item",
            "field_name": "item_name",
            "property": "reqd",
            "property_type": "Check",
            "value": "0"
        })
        doc.insert(ignore_permissions=True)
    
    frappe.db.commit()
    print("✅ Item Name is now optional!")

if __name__ == "__main__":
    fix_item_name_required()
