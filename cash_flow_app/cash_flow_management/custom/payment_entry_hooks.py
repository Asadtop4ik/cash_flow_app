# Copyright (c) 2025, Your Company
# Payment Entry server-side hooks

import frappe
from frappe import _
from frappe.utils import flt

def validate(doc, method=None):
    """Validate Payment Entry before save"""
    validate_counterparty_category(doc)
    set_default_values(doc)
    validate_contract_reference(doc)

def validate_counterparty_category(doc):
    """Ensure counterparty category matches payment type"""
    if not doc.custom_counterparty_category:
        frappe.throw(_("Counterparty Category is mandatory"))
    
    # Use ignore_permissions to avoid "Not permitted" error when validating
    try:
        category = frappe.get_cached_doc("Counterparty Category", doc.custom_counterparty_category)
    except frappe.PermissionError:
        category = frappe.get_doc("Counterparty Category", doc.custom_counterparty_category, ignore_permissions=True)
    
    # Income category faqat Receive uchun
    if doc.payment_type == "Receive" and category.category_type != "Income":
        frappe.throw(
            _("For Receipt (Kirim), Counterparty Category must be Income type.<br>"
              f"Selected category '{category.category_name}' is {category.category_type} type."),
            title=_("Invalid Category")
        )
    
    # Expense category faqat Pay uchun
    if doc.payment_type == "Pay" and category.category_type != "Expense":
        frappe.throw(
            _("For Payment (Chiqim), Counterparty Category must be Expense type.<br>"
              f"Selected category '{category.category_name}' is {category.category_type} type."),
            title=_("Invalid Category")
        )
        
def set_default_values(doc):
    """Set default values from Cash Settings"""
    if doc.is_new():
        try:
            settings = frappe.get_cached_doc("Cash Settings", "Cash Settings")
            
            # Set default cost center if not set (faqat non-group)
            if not doc.cost_center and settings.default_cost_center:
                cc = frappe.get_cached_doc("Cost Center", settings.default_cost_center)
                if not cc.is_group:  # Check group emas
                    doc.cost_center = settings.default_cost_center
                else:
                    # Get first non-group child
                    non_group = frappe.db.get_value(
                        "Cost Center",
                        {
                            "parent_cost_center": settings.default_cost_center,
                            "is_group": 0,
                            "company": doc.company
                        },
                        "name"
                    )
                    if non_group:
                        doc.cost_center = non_group
            
            # Set default accounts...
            # (qolgan kod o'zgarmaydi)
        except Exception as e:
            frappe.logger().error(f"Error setting defaults: {str(e)}")

def validate_contract_reference(doc):
    """Validate contract reference for Klient category"""
    if doc.custom_counterparty_category == "Klient":
        if not doc.custom_contract_reference:
            # Warning faqat, majburiy emas
            frappe.msgprint(
                _("Consider adding Contract Reference for customer payments"),
                indicator="orange",
                alert=True
            )

def on_submit(doc, method=None):
    """After submit actions"""
    # Log kassa transaction
    frappe.logger().info(
        f"Payment Entry submitted: {doc.name} | "
        f"Type: {doc.payment_type} | "
        f"Amount: {doc.paid_amount} | "
        f"Category: {doc.custom_counterparty_category}"
    )

def on_cancel(doc, method=None):
    """After cancel actions"""
    frappe.logger().info(f"Payment Entry cancelled: {doc.name}")

