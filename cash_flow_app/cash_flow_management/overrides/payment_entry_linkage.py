"""
Payment Entry to Sales Order linkage
Updates advance_paid and payment_schedule when payment is made
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

def on_submit_payment_entry(doc, method=None):
    """
    Link payment to Sales Order and update advance_paid
    Called when Payment Entry is submitted
    """
    # Only process if contract reference is set
    if not doc.custom_contract_reference:
        return
    
    # Only for Receive payments (Pay is expense, not contract payment)
    if doc.payment_type != "Receive":
        return
    
    try:
        # Get Sales Order
        so = frappe.get_doc("Sales Order", doc.custom_contract_reference)
        
        # Validate customer matches
        if so.customer != doc.party:
            frappe.throw(_("Shartnoma mijozi ({0}) to'lov mijozi ({1}) bilan mos kelmayapti!").format(
                so.customer, doc.party
            ))
        
        # Update advance_paid
        current_advance = flt(so.advance_paid) or 0
        new_advance = current_advance + flt(doc.paid_amount)
        
        so.db_set("advance_paid", new_advance, update_modified=True)
        
        # Update Payment Schedule
        update_payment_schedule(so, doc.paid_amount, doc.posting_date)
        
        # Check if fully paid - use custom_grand_total_with_interest if available
        grand_total = flt(so.custom_grand_total_with_interest) or flt(so.grand_total)
        outstanding = grand_total - flt(new_advance)
        
        if outstanding <= 0.01:  # Allow small rounding differences
            so.db_set("status", "Completed", update_modified=True)
            frappe.msgprint(_("✅ Shartnoma to'liq to'landi! Status: Completed"), alert=True)
        else:
            frappe.msgprint(
                _("✅ To'lov qabul qilindi! Qolgan summa: {0} USD").format(outstanding),
                alert=True
            )
        
        # Log the linkage
        frappe.logger().info(f"Payment {doc.name} linked to SO {so.name}. Advance: {current_advance} → {new_advance}. Outstanding: {outstanding}")
        
    except Exception as e:
        frappe.log_error(f"Error linking payment {doc.name} to SO: {e}")
        frappe.throw(_("Xatolik: Shartnomaga bog'lanmadi. {0}").format(str(e)))


def update_payment_schedule(sales_order, paid_amount, payment_date):
    """
    Update Payment Schedule table with actual payment
    Marks earliest unpaid schedule as paid
    """
    remaining_amount = flt(paid_amount)
    payment_date = getdate(payment_date)
    
    # Get unpaid schedules, sorted by due date
    schedules = sales_order.get("payment_schedule", [])
    
    for schedule in sorted(schedules, key=lambda x: x.due_date):
        if remaining_amount <= 0:
            break
        
        # Check if already paid
        paid_already = flt(schedule.get("paid_amount")) or 0
        due_amount = flt(schedule.payment_amount) - paid_already
        
        if due_amount <= 0:
            continue  # Already paid
        
        # Calculate payment for this schedule
        payment_for_schedule = min(remaining_amount, due_amount)
        
        # Update paid_amount
        new_paid = paid_already + payment_for_schedule
        schedule.db_set("paid_amount", new_paid, update_modified=False)
        
        remaining_amount -= payment_for_schedule
        
        frappe.logger().info(
            f"Updated Payment Schedule: {schedule.name} - "
            f"Paid: {paid_already} → {new_paid} (Due: {schedule.payment_amount})"
        )
    
    # Update next payment date and amount in Sales Order custom fields
    update_next_payment_info(sales_order)
    
    # Save parent to update modified timestamp
    sales_order.db_set("modified", frappe.utils.now(), update_modified=False)


def update_next_payment_info(sales_order):
    """
    Update custom_next_payment_date and custom_next_payment_amount
    based on the next unpaid payment schedule
    """
    # Get next unpaid schedule
    next_schedule = None
    
    for schedule in sorted(sales_order.get("payment_schedule", []), key=lambda x: x.due_date):
        paid_already = flt(schedule.get("paid_amount")) or 0
        due_amount = flt(schedule.payment_amount) - paid_already
        
        if due_amount > 0:
            next_schedule = schedule
            break
    
    if next_schedule:
        # Calculate outstanding amount for this schedule
        outstanding = flt(next_schedule.payment_amount) - flt(next_schedule.get("paid_amount") or 0)
        
        # Update custom fields
        sales_order.db_set("custom_next_payment_date", next_schedule.due_date, update_modified=False)
        sales_order.db_set("custom_next_payment_amount", outstanding, update_modified=False)
        
        frappe.logger().info(
            f"Next payment for SO {sales_order.name}: {next_schedule.due_date} - ${outstanding}"
        )
    else:
        # All paid - clear next payment info
        sales_order.db_set("custom_next_payment_date", None, update_modified=False)
        sales_order.db_set("custom_next_payment_amount", 0, update_modified=False)
        
        frappe.logger().info(f"SO {sales_order.name}: All payments completed")


def on_cancel_payment_entry(doc, method=None):
    """
    Reverse the payment linkage when Payment Entry is cancelled
    """
    if not doc.custom_contract_reference:
        return
    
    if doc.payment_type != "Receive":
        return
    
    try:
        so = frappe.get_doc("Sales Order", doc.custom_contract_reference)
        
        # Reduce advance_paid
        current_advance = flt(so.advance_paid) or 0
        new_advance = current_advance - flt(doc.paid_amount)
        
        # Ensure it doesn't go negative
        new_advance = max(0, new_advance)
        
        so.db_set("advance_paid", new_advance, update_modified=True)
        
        # Reverse payment schedule update
        reverse_payment_schedule(so, doc.paid_amount)
        
        # Update status back to previous
        outstanding = flt(so.grand_total) - flt(new_advance)
        if outstanding > 0:
            so.db_set("status", "To Deliver and Bill", update_modified=True)
        
        frappe.msgprint(_("❌ To'lov bekor qilindi. Advance: {0} USD").format(new_advance), alert=True)
        
    except Exception as e:
        frappe.log_error(f"Error reversing payment {doc.name}: {e}")


def reverse_payment_schedule(sales_order, cancelled_amount):
    """
    Reverse payment schedule update when payment is cancelled
    """
    remaining_amount = flt(cancelled_amount)
    
    # Get schedules in reverse order (newest paid first)
    schedules = sales_order.get("payment_schedule", [])
    
    for schedule in sorted(schedules, key=lambda x: x.due_date, reverse=True):
        if remaining_amount <= 0:
            break
        
        paid_already = flt(schedule.get("paid_amount")) or 0
        
        if paid_already <= 0:
            continue  # Nothing to reverse
        
        # Calculate reversal for this schedule
        reversal_amount = min(remaining_amount, paid_already)
        
        # Update paid_amount
        new_paid = paid_already - reversal_amount
        schedule.db_set("paid_amount", new_paid, update_modified=False)
        
        remaining_amount -= reversal_amount
    
    sales_order.db_set("modified", frappe.utils.now(), update_modified=False)
