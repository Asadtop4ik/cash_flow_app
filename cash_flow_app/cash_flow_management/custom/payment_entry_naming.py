# Copyright (c) 2025, Your Company
# Custom naming for Payment Entry based on payment type

import frappe
from frappe.model.naming import make_autoname

def autoname(doc, method=None):
    """
    Custom naming for Payment Entry:
    - Receipt (Kirim) → CIN-.YYYY.-.#####
    - Pay (Chiqim) → COUT-.YYYY.-.#####
    """
    
    # Skip if already has a name (amend case)
    if doc.name and doc.name.startswith("new-payment-entry"):
        pass
    elif doc.name and not doc.name.startswith("new-"):
        return
    
    # Get naming series from Cash Settings
    try:
        settings = frappe.get_cached_doc("Cash Settings", "Cash Settings")
        cin_series = settings.cin_series or "CIN-.YYYY.-.#####"
        cout_series = settings.cout_series or "COUT-.YYYY.-.#####"
    except:
        # Fallback if Cash Settings not configured
        cin_series = "CIN-.YYYY.-.#####"
        cout_series = "COUT-.YYYY.-.#####"
    
    # Determine series based on payment_type
    if doc.payment_type == "Receive":
        series = cin_series
    elif doc.payment_type == "Pay":
        series = cout_series
    else:
        # Internal Transfer or other
        series = "PE-.YYYY.-.#####"
    
    # Generate name
    doc.name = make_autoname(series, doc.doctype, doc)
    
    frappe.logger().info(f"Payment Entry named: {doc.name} (Type: {doc.payment_type})")
