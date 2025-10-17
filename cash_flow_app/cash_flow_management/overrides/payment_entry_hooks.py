"""
Auto-naming hook for Payment Entry
Sets naming series based on payment type:
- Receive → CIN-.YYYY.-.#####
- Pay → COUT-.YYYY.-.#####
"""

import frappe
from frappe import _

def autoname_payment_entry(doc, method=None):
    """
    Set naming series based on payment type
    Called on before_naming event
    """
    if doc.payment_type == "Receive":
        doc.naming_series = "CIN-.YYYY.-.#####"
    elif doc.payment_type == "Pay":
        doc.naming_series = "COUT-.YYYY.-.#####"
    else:
        # Default ERPNext naming
        doc.naming_series = "ACC-PAY-.YYYY.-.#####"

def validate_payment_entry(doc, method=None):
    """
    Additional validations for Payment Entry
    """
    # Ensure counterparty category is set
    if not doc.custom_counterparty_category:
        frappe.throw(_("Counterparty Category tanlanishi shart!"))
    
    # If contract reference is set, validate it matches party
    if doc.custom_contract_reference:
        so = frappe.get_doc("Sales Order", doc.custom_contract_reference)
        if so.customer != doc.party:
            frappe.throw(_("Shartnoma mijozi to'lov mijozi bilan mos kelmayapti!"))
