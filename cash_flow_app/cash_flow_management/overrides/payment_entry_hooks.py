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
    Auto-fill contract reference if missing
    """
    # Ensure counterparty category is set
    if not doc.custom_counterparty_category:
        frappe.throw(_("Counterparty Category tanlanishi shart!"))
    
    # Auto-fill contract reference for customer payments
    if doc.payment_type == "Receive" and doc.party_type == "Customer" and not doc.custom_contract_reference:
        # Find latest active Sales Order for this customer
        latest_so = frappe.db.get_value(
            "Sales Order",
            filters={
                "customer": doc.party,
                "docstatus": 1,
                "status": ["!=", "Completed"]
            },
            fieldname="name",
            order_by="transaction_date DESC"
        )
        
        if latest_so:
            doc.custom_contract_reference = latest_so
            frappe.msgprint(
                _("ℹ️ Avtomatik: Shartnoma {0} bog'landi").format(latest_so),
                alert=True,
                indicator="blue"
            )
    
    # If contract reference is set, validate it matches party
    if doc.custom_contract_reference:
        # Use db.get_value to avoid permission issues
        so_customer = frappe.db.get_value("Sales Order", doc.custom_contract_reference, "customer")
        if so_customer and so_customer != doc.party:
            frappe.throw(_("Shartnoma mijozi to'lov mijozi bilan mos kelmayapti!"))
