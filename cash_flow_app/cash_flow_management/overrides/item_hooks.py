"""
Item DocType hook - auto-set item_name from custom_product_name and auto-generate item_code
"""

import frappe
from frappe import _

def before_naming_item(doc, method=None):
    """
    Auto-generate Item Code in format ITEM-0001, ITEM-0002, etc.
    """
    # If item_code is temp or not set, let auto-naming handle it
    if not doc.item_code or doc.item_code.startswith('temp-') or doc.item_code.startswith('new-'):
        # Don't set anything - let DocType autoname handle it
        pass

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
    
    # Set stock_uom if empty
    if not doc.stock_uom:
        doc.stock_uom = "Unit"

def validate_item(doc, method=None):
    """
    Ensure required fields are set
    """
    # item_name should be auto-filled by before_save
    # But if somehow still empty, auto-fill it
    if not doc.item_name:
        if doc.get("custom_product_name"):
            doc.item_name = doc.custom_product_name
        elif doc.item_code and not doc.item_code.startswith('temp-'):
            # Use item_code as fallback
            doc.item_name = doc.item_code
        else:
            # Last resort - throw error
            frappe.throw(_("Mahsulot nomi (custom_product_name) kiriting!"))
    
    # Ensure item_group
    if not doc.item_group:
        doc.item_group = "Products"
    
    # Ensure stock_uom
    if not doc.stock_uom:
        doc.stock_uom = "Unit"
