"""
Item DocType hook - auto-set item_name from custom_product_name
"""

import frappe
from frappe import _

def before_save_item(doc, method=None):
    """
    Auto-set item_name from custom_product_name if empty
    """
    # Priority 1: Use custom_product_name
    if doc.get("custom_product_name"):
        doc.item_name = doc.custom_product_name
    
    # Priority 2: If still empty, use item_code as fallback
    if not doc.item_name and doc.item_code:
        doc.item_name = doc.item_code
    
    # Set item_group if empty
    if not doc.item_group:
        doc.item_group = "Products"

def validate_item(doc, method=None):
    """
    Ensure required fields are set
    """
    # item_name should be auto-filled by before_save
    # But if somehow still empty, throw error
    if not doc.item_name:
        if not doc.get("custom_product_name"):
            frappe.throw(_("Mahsulot nomi (custom_product_name) kiriting!"))
        else:
            # This shouldn't happen, but just in case
            doc.item_name = doc.custom_product_name
    
    # Ensure item_group
    if not doc.item_group:
        doc.item_group = "Products"
