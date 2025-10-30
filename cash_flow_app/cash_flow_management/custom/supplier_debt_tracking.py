"""
Supplier Debt Tracking
Tracks debt to suppliers based on Installment Applications
"""

import frappe
from frappe import _
from frappe.utils import flt

def update_supplier_debt_on_submit(doc, method=None):
    """
    Called when Installment Application is submitted
    Adds debt to each supplier based on item costs
    
    Args:
        doc: Installment Application document
        method: Event method name (not used)
    """
    if not doc.items:
        return
    
    # Group items by supplier
    supplier_debts = {}
    
    for item in doc.items:
        if not item.custom_supplier:
            frappe.throw(_("Item {0}: Yetkazib beruvchi (Supplier) tanlanmagan!").format(item.item_name))
        
        supplier = item.custom_supplier
        item_total = flt(item.qty) * flt(item.rate)
        
        if supplier in supplier_debts:
            supplier_debts[supplier] += item_total
        else:
            supplier_debts[supplier] = item_total
    
    # Update each supplier's debt
    for supplier_name, debt_amount in supplier_debts.items():
        try:
            supplier = frappe.get_doc("Supplier", supplier_name)
            
            # Add to total debt
            current_total_debt = flt(supplier.get("custom_total_debt", 0))
            new_total_debt = current_total_debt + debt_amount
            
            # Calculate remaining debt
            paid_amount = flt(supplier.get("custom_paid_amount", 0))
            remaining_debt = new_total_debt - paid_amount
            
            # Determine status
            if remaining_debt <= 0:
                status = "To'landi"
            elif paid_amount > 0:
                status = "Qisman to'langan"
            else:
                status = "Qarzda"
            
            # Update supplier
            supplier.custom_total_debt = new_total_debt
            supplier.custom_remaining_debt = remaining_debt
            supplier.custom_payment_status = status
            
            supplier.save(ignore_permissions=True)
            
            frappe.msgprint(
                _("Supplier {0}: Qarz qo'shildi ${1:,.2f}").format(supplier_name, debt_amount),
                alert=True
            )
            
        except Exception as e:
            frappe.log_error(f"Error updating supplier debt for {supplier_name}: {str(e)}")
            frappe.throw(_("Supplier {0} debt update xatolik: {1}").format(supplier_name, str(e)))

def update_supplier_debt_on_payment(doc, method=None):
    """
    Called when Payment Entry (Pay type) is submitted
    Reduces debt from supplier
    
    Args:
        doc: Payment Entry document
        method: Event method name (not used)
    """
    if doc.payment_type != "Pay":
        return
    
    if doc.party_type != "Supplier":
        return
    
    supplier_name = doc.party
    paid_amount = flt(doc.paid_amount)
    
    try:
        supplier = frappe.get_doc("Supplier", supplier_name)
        
        # Update paid amount
        current_paid = flt(supplier.get("custom_paid_amount", 0))
        new_paid = current_paid + paid_amount
        
        # Calculate remaining debt
        total_debt = flt(supplier.get("custom_total_debt", 0))
        remaining_debt = total_debt - new_paid
        
        # Determine status
        if remaining_debt <= 0:
            status = "To'landi"
        elif new_paid > 0:
            status = "Qisman to'langan"
        else:
            status = "Qarzda"
        
        # Update supplier
        supplier.custom_paid_amount = new_paid
        supplier.custom_remaining_debt = remaining_debt
        supplier.custom_payment_status = status
        
        supplier.save(ignore_permissions=True)
        
        frappe.msgprint(
            _("Supplier {0}: To'lov kiritildi ${1:,.2f}. Qolgan qarz: ${2:,.2f}").format(
                supplier_name, paid_amount, remaining_debt
            ),
            alert=True
        )
        
    except Exception as e:
        frappe.log_error(f"Error updating supplier payment for {supplier_name}: {str(e)}")
        frappe.throw(_("Supplier {0} to'lov update xatolik: {1}").format(supplier_name, str(e)))

def update_supplier_debt_on_cancel_payment(doc, method=None):
    """
    Called when Payment Entry (Pay type) is cancelled
    Reverses the payment from supplier debt
    
    Args:
        doc: Payment Entry document
        method: Event method name (not used)
    """
    if doc.payment_type != "Pay":
        return
    
    if doc.party_type != "Supplier":
        return
    
    supplier_name = doc.party
    paid_amount = flt(doc.paid_amount)
    
    try:
        supplier = frappe.get_doc("Supplier", supplier_name)
        
        # Reverse paid amount
        current_paid = flt(supplier.get("custom_paid_amount", 0))
        new_paid = max(0, current_paid - paid_amount)  # Don't go negative
        
        # Calculate remaining debt
        total_debt = flt(supplier.get("custom_total_debt", 0))
        remaining_debt = total_debt - new_paid
        
        # Determine status
        if remaining_debt <= 0:
            status = "To'landi"
        elif new_paid > 0:
            status = "Qisman to'langan"
        else:
            status = "Qarzda"
        
        # Update supplier
        supplier.custom_paid_amount = new_paid
        supplier.custom_remaining_debt = remaining_debt
        supplier.custom_payment_status = status
        
        supplier.save(ignore_permissions=True)
        
        frappe.msgprint(
            _("Supplier {0}: To'lov bekor qilindi ${1:,.2f}. Qolgan qarz: ${2:,.2f}").format(
                supplier_name, paid_amount, remaining_debt
            ),
            alert=True
        )
        
    except Exception as e:
        frappe.log_error(f"Error reversing supplier payment for {supplier_name}: {str(e)}")


def update_supplier_debt_on_cancel_installment(doc, method=None):
    """
    Called when Installment Application is cancelled
    Reverses debt from suppliers
    
    Args:
        doc: Installment Application document
        method: Event method name (not used)
    """
    if not doc.items:
        return
    
    print(f"\n🔴 on_cancel_installment_application() CALLED for InstApp: {doc.name}")
    frappe.logger().info(f"🔴 Cancelling InstApp {doc.name} - reversing supplier debts")
    
    # Group items by supplier
    supplier_debts = {}
    
    for item in doc.items:
        if not item.custom_supplier:
            continue  # Skip if no supplier
        
        supplier = item.custom_supplier
        item_total = flt(item.qty) * flt(item.rate)
        
        if supplier in supplier_debts:
            supplier_debts[supplier] += item_total
        else:
            supplier_debts[supplier] = item_total
    
    # Reverse each supplier's debt
    for supplier_name, debt_amount in supplier_debts.items():
        try:
            supplier = frappe.get_doc("Supplier", supplier_name)
            
            # Subtract from total debt
            current_total_debt = flt(supplier.get("custom_total_debt", 0))
            new_total_debt = max(0, current_total_debt - debt_amount)  # Don't go negative
            
            # Calculate remaining debt
            paid_amount = flt(supplier.get("custom_paid_amount", 0))
            remaining_debt = new_total_debt - paid_amount
            
            # Determine status
            if remaining_debt <= 0:
                status = "To'landi"
            elif paid_amount > 0:
                status = "Qisman to'langan"
            else:
                status = "Qarzda"
            
            # Update supplier
            supplier.custom_total_debt = new_total_debt
            supplier.custom_remaining_debt = remaining_debt
            supplier.custom_payment_status = status
            
            supplier.save(ignore_permissions=True)
            
            print(f"   ✅ Supplier {supplier_name}: Qarz kamaytrildi -${debt_amount} (qoldi: ${new_total_debt})")
            frappe.logger().info(f"Reversed supplier debt for {supplier_name}: -${debt_amount}")
            
            frappe.msgprint(
                _("Supplier {0}: Qarz kamaytrildi ${1:,.2f} (Qoldi: ${2:,.2f})").format(
                    supplier_name, debt_amount, new_total_debt
                ),
                alert=True,
                indicator="orange"
            )
            
        except Exception as e:
            frappe.log_error(f"Error reversing supplier debt for {supplier_name}: {str(e)}")
            print(f"   ❌ Failed to reverse debt for {supplier_name}: {e}")
