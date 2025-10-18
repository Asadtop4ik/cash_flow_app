"""
Auto-naming for Item
Generates ITEM-0001, ITEM-0002, etc.
"""

import frappe

def autoname_item(doc, method=None):
    """Auto-generate item code"""
    if not doc.item_code:
        # Get last item number
        last_item = frappe.db.sql("""
            SELECT name 
            FROM `tabItem` 
            WHERE name LIKE 'ITEM-%' 
            ORDER BY creation DESC 
            LIMIT 1
        """, as_dict=1)
        
        if last_item:
            last_num = int(last_item[0].name.split('-')[1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        doc.item_code = f"ITEM-{new_num:04d}"
        doc.item_name = doc.item_code
