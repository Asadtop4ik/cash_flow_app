"""
Auto-select default cash account from Cash Settings
Called on Payment Entry load
"""

import frappe
from frappe import _

def onload_payment_entry(doc, method=None):
    """
    Set default cash account from Cash Settings
    Called when Payment Entry form loads
    """
    if doc.is_new():
        try:
            cash_settings = frappe.get_single("Cash Settings")
            default_cash_account = cash_settings.get("default_cash_account")
            
            if default_cash_account:
                if doc.payment_type == "Receive" and not doc.paid_to:
                    doc.paid_to = default_cash_account
                    doc.paid_to_account_currency = "USD"
                
                elif doc.payment_type == "Pay" and not doc.paid_from:
                    doc.paid_from = default_cash_account
                    doc.paid_from_account_currency = "USD"
        
        except Exception as e:
            frappe.logger().error(f"Error setting default cash account: {e}")
            # Don't throw error, just log it
