"""
Make item_group not required since it's hidden
"""

import frappe

def fix_item_group_required():
    """Make item_group field optional"""
    
    # Check if Property Setter exists
    existing = frappe.db.exists("Property Setter", {
        "doc_type": "Item",
        "field_name": "item_group",
        "property": "reqd"
    })
    
    if existing:
        frappe.db.set_value("Property Setter", existing, "value", "0")
    else:
        doc = frappe.get_doc({
            "doctype": "Property Setter",
            "doctype_or_field": "DocField",
            "doc_type": "Item",
            "field_name": "item_group",
            "property": "reqd",
            "property_type": "Check",
            "value": "0"
        })
        doc.insert(ignore_permissions=True)
    
    frappe.db.commit()
    print("✅ Item Group is now optional!")

if __name__ == "__main__":
    fix_item_group_required()
