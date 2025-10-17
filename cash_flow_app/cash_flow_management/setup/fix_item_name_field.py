"""
Fix Item name field - copy custom_product_name to item_name
"""

import frappe

def fix_item_name_field():
    """
    Make item_name fetch from custom_product_name
    """
    
    # Set item_name to fetch from custom_product_name
    prop_setter = frappe.get_doc({
        "doctype": "Property Setter",
        "doctype_or_field": "DocField",
        "doc_type": "Item",
        "field_name": "item_name",
        "property": "fetch_from",
        "property_type": "Small Text",
        "value": "custom_product_name"
    })
    
    try:
        existing = frappe.db.exists("Property Setter", {
            "doc_type": "Item",
            "field_name": "item_name",
            "property": "fetch_from"
        })
        
        if existing:
            frappe.db.set_value("Property Setter", existing, "value", "custom_product_name")
        else:
            prop_setter.insert(ignore_permissions=True)
    except Exception as e:
        print(f"Note: {e}")
    
    # Make item_name visible and required
    fields_to_update = [
        {"property": "hidden", "value": "0"},
        {"property": "reqd", "value": "1"},
        {"property": "read_only", "value": "0"}
    ]
    
    for field_prop in fields_to_update:
        existing = frappe.db.exists("Property Setter", {
            "doc_type": "Item",
            "field_name": "item_name",
            "property": field_prop["property"]
        })
        
        if existing:
            frappe.db.set_value("Property Setter", existing, "value", field_prop["value"])
        else:
            prop = frappe.get_doc({
                "doctype": "Property Setter",
                "doctype_or_field": "DocField",
                "doc_type": "Item",
                "field_name": "item_name",
                "property": field_prop["property"],
                "property_type": "Check",
                "value": field_prop["value"]
            })
            prop.insert(ignore_permissions=True)
    
    frappe.db.commit()
    print("✅ Item name field configured!")
    print("   item_name is now visible and required")

if __name__ == "__main__":
    fix_item_name_field()
