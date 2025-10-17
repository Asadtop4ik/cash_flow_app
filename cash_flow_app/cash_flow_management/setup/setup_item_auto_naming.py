"""
Setup Item auto-naming and hide item_code field
"""

import frappe

def setup_item_auto_naming():
    """
    1. Set Item naming to auto-generate (ITEM-.YYYY.-.#####)
    2. Hide item_code field from form
    3. Make it optional
    """
    
    property_setters = []
    
    # 1. Set autoname format
    property_setters.append({
        "doctype": "Property Setter",
        "doctype_or_field": "DocType",
        "doc_type": "Item",
        "property": "autoname",
        "property_type": "Data",
        "value": "ITEM-.YYYY.-.#####"
    })
    
    # 2. Hide item_code field (already hidden, but ensure it)
    property_setters.append({
        "doctype": "Property Setter",
        "doctype_or_field": "DocField",
        "doc_type": "Item",
        "field_name": "item_code",
        "property": "hidden",
        "property_type": "Check",
        "value": "1"
    })
    
    # 3. Make item_code not required
    property_setters.append({
        "doctype": "Property Setter",
        "doctype_or_field": "DocField",
        "doc_type": "Item",
        "field_name": "item_code",
        "property": "reqd",
        "property_type": "Check",
        "value": "0"
    })
    
    # Create Property Setters
    for prop in property_setters:
        try:
            existing = frappe.db.exists("Property Setter", {
                "doc_type": prop["doc_type"],
                "field_name": prop.get("field_name"),
                "property": prop["property"]
            })
            
            if existing:
                frappe.db.set_value("Property Setter", existing, "value", prop["value"])
            else:
                doc = frappe.get_doc(prop)
                doc.insert(ignore_permissions=True)
        except Exception as e:
            print(f"⚠️ {prop.get('field_name', 'DocType')}: {e}")
    
    frappe.db.commit()
    print(f"✅ Item auto-naming setup complete!")
    print("   Format: ITEM-.YYYY.-.#####")
    print("   item_code field hidden and optional")

if __name__ == "__main__":
    setup_item_auto_naming()
