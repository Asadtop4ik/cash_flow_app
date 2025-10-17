"""
Create default Item Group and set it as default for new items
"""

import frappe

def setup_default_item_group():
    """
    1. Create "Products" item group if not exists
    2. Set it as default for Item DocType
    """
    
    # 1. Check if "Products" item group exists
    if not frappe.db.exists("Item Group", "Products"):
        # Create it
        item_group = frappe.get_doc({
            "doctype": "Item Group",
            "item_group_name": "Products",
            "parent_item_group": "All Item Groups",
            "is_group": 0
        })
        item_group.insert(ignore_permissions=True)
        print("✅ Created Item Group: Products")
    else:
        print("✅ Item Group 'Products' already exists")
    
    # 2. Set default item_group value
    prop_setter = None
    existing = frappe.db.exists("Property Setter", {
        "doc_type": "Item",
        "field_name": "item_group",
        "property": "default"
    })
    
    if existing:
        frappe.db.set_value("Property Setter", existing, "value", "Products")
        print("✅ Updated default item_group to 'Products'")
    else:
        prop_setter = frappe.get_doc({
            "doctype": "Property Setter",
            "doctype_or_field": "DocField",
            "doc_type": "Item",
            "field_name": "item_group",
            "property": "default",
            "property_type": "Data",
            "value": "Products"
        })
        prop_setter.insert(ignore_permissions=True)
        print("✅ Set default item_group to 'Products'")
    
    frappe.db.commit()
    print("✅ Item Group setup complete!")

if __name__ == "__main__":
    setup_default_item_group()
