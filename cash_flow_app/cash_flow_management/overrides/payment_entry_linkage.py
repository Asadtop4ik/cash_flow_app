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
    # 🔍 DEBUG LOG
    print(f"\n🔵 on_submit_payment_entry() CALLED for PE: {doc.name}")
    print(f"   Payment Type: {doc.payment_type}")
    print(f"   Contract Reference: {doc.custom_contract_reference}")
    print(f"   Paid Amount: {doc.paid_amount}")
    
    # Only process if contract reference is set
    if not doc.custom_contract_reference:
        print(f"   ❌ No contract reference - skipping")
        return
    
    # Only for Receive payments (Pay is expense, not contract payment)
    if doc.payment_type != "Receive":
        print(f"   ❌ Payment type is not Receive - skipping")
        return
    
    # IDEMPOTENCY CHECK: Prevent duplicate processing
    # If this payment was already processed, skip
    if hasattr(doc, '_payment_already_linked') and doc._payment_already_linked:
        print(f"   ⚠️  Already linked - skipping")
        frappe.logger().info(f"Payment {doc.name} already linked to SO, skipping")
        return
    
    print(f"   ➡️  Proceeding to link payment to SO...")
    
    try:
        # Get Sales Order (ignore permissions for system hooks)
        print(f"   📥 Getting Sales Order: {doc.custom_contract_reference}")
        so = frappe.get_doc("Sales Order", doc.custom_contract_reference, ignore_permissions=True)
        print(f"   ✅ SO loaded: {so.name}, Customer: {so.customer}")
        
        # Validate customer matches
        if so.customer != doc.party:
            print(f"   ❌ Customer mismatch!")
            frappe.throw(_("Shartnoma mijozi ({0}) to'lov mijozi ({1}) bilan mos kelmayapti!").format(
                so.customer, doc.party
            ))
        
        # CHECK: Is this payment already included in advance_paid?
        # Get current advance_paid
        current_advance = flt(so.advance_paid) or 0
        print(f"   💵 Current advance_paid: ${current_advance}")
        
        # Get sum of all submitted payments for this SO (excluding current one)
        print(f"   🔍 Checking for existing SUBMITTED payments...")
        existing_payments_sum = frappe.db.sql("""
            SELECT COALESCE(SUM(paid_amount), 0) as total
            FROM `tabPayment Entry`
            WHERE custom_contract_reference = %(so)s
                AND docstatus = 1
                AND name != %(pe)s
                AND payment_type = 'Receive'
        """, {'so': so.name, 'pe': doc.name}, as_dict=1)[0].total
        
        existing_payments_sum = flt(existing_payments_sum)
        print(f"   💵 Existing SUBMITTED payments sum: ${existing_payments_sum}")
        
        # Calculate what advance_paid SHOULD be if this payment is included
        expected_advance = existing_payments_sum + flt(doc.paid_amount)
        print(f"   💵 Expected advance (with this payment): ${expected_advance}")
        
        # ✅ IMPORTANT: Don't check against current_advance!
        # ERPNext may have updated advance_paid from draft PE references
        # We only care about actually submitted payments
        print(f"   ℹ️  Note: Current advance_paid may include draft PE references, ignoring for idempotency check")
        
        # Skip idempotency check based on advance_paid
        # Instead, check if THIS specific payment was already processed
        if hasattr(doc, '_payment_schedule_updated') and doc._payment_schedule_updated:
            print(f"   ⚠️  Payment schedule already updated for this PE! Skipping...")
            frappe.logger().warning(f"Payment {doc.name} schedule already updated")
            return
        
        # Update advance_paid
        new_advance = expected_advance
        print(f"   💾 Updating SO advance_paid: ${current_advance} → ${new_advance}")
        
        so.db_set("advance_paid", new_advance, update_modified=True)
        print(f"   ✅ SO advance_paid updated!")
        
        # Mark as processed to prevent duplicate runs
        doc._payment_already_linked = True
        
        # Update Payment Schedule
        print(f"   📅 Updating Payment Schedule...")
        updated_schedule = update_payment_schedule(so, doc.paid_amount, doc.posting_date, doc.name)
        print(f"   ✅ Payment Schedule updated! Row: {updated_schedule}")
        
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
        print(f"   🎉 ALL DONE!")
        
    except Exception as e:
        print(f"\n❌ ERROR in on_submit_payment_entry: {str(e)}")
        print(f"   Exception type: {type(e).__name__}")
        import traceback
        print(f"   Traceback:\n{traceback.format_exc()}")
        frappe.log_error(f"Error linking payment {doc.name} to SO: {e}", "Payment Entry Link Error")
        frappe.throw(_("Xatolik: Shartnomaga bog'lanmadi. {0}").format(str(e)))


def update_payment_schedule(sales_order, paid_amount, payment_date, payment_entry_name=None):
    """
    Update Payment Schedule table with actual payment
    Marks earliest unpaid schedule as paid
    Returns the payment schedule row that was updated (for linking)
    """
    remaining_amount = flt(paid_amount)
    payment_date = getdate(payment_date)
    updated_schedule_name = None
    payment_description = None
    
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
        
        # Update paid_amount in the child table
        new_paid = paid_already + payment_for_schedule
        
        # 🔍 DEBUG LOG
        print(f"\n💰 Updating Payment Schedule:")
        print(f"   Schedule: {schedule.name}")
        print(f"   Paid Already: {paid_already}")
        print(f"   Payment for this schedule: {payment_for_schedule}")
        print(f"   New Paid Amount: {new_paid}")
        
        # ✅ UPDATE DATABASE DIRECTLY (not just memory!)
        frappe.db.set_value(
            "Payment Schedule",
            schedule.name,
            "paid_amount",
            new_paid,
            update_modified=False
        )
        
        print(f"   ✅ Database updated!")
        
        # Track which schedule was updated (for first payment)
        if not updated_schedule_name:
            updated_schedule_name = schedule.name
            payment_description = schedule.description or f"Month {schedule.idx}"
        
        remaining_amount -= payment_for_schedule
        
        frappe.logger().info(
            f"✅ Updated Payment Schedule: {schedule.name} - "
            f"Paid: {paid_already} → {new_paid} (Due: {schedule.payment_amount})"
        )
    
    # 🔍 DEBUG LOG
    print(f"\n📊 Committing database changes...")
    
    # ✅ COMMIT TO DATABASE
    frappe.db.commit()
    
    print(f"   ✅ Database committed!")
    
    # Update the Payment Entry with schedule row reference
    if payment_entry_name and updated_schedule_name:
        try:
            frappe.db.set_value(
                "Payment Entry", 
                payment_entry_name, 
                {
                    "custom_payment_schedule_row": updated_schedule_name,
                    "custom_payment_month": payment_description
                },
                update_modified=False
            )
            frappe.logger().info(f"Linked PE {payment_entry_name} to schedule {updated_schedule_name}")
        except Exception as e:
            frappe.log_error(f"Error linking PE to schedule: {e}")
    
    # Update next payment date and amount in Sales Order custom fields
    update_next_payment_info(sales_order)
    
    # Save parent to update modified timestamp
    sales_order.db_set("modified", frappe.utils.now(), update_modified=False)
    
    return updated_schedule_name


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
        so = frappe.get_doc("Sales Order", doc.custom_contract_reference, ignore_permissions=True)
        
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


def publish_customer_dashboard_refresh(doc, method=None):
    """
    ✅ Publish realtime event to refresh Customer Dashboard
    Called after Payment Entry is submitted
    """
    if doc.party_type == "Customer" and doc.party:
        # Publish realtime event via socket.io
        # ✅ SEND TO ALL USERS (not just current user!)
        frappe.publish_realtime(
            "payment_entry_submitted",
            {
                "customer": doc.party,
                "payment_entry": doc.name,
                "amount": flt(doc.paid_amount),
                "contract": doc.custom_contract_reference
            },
            # Remove user filter to send to ALL users
            after_commit=True  # Send after DB commit completes
        )
        
        frappe.logger().info(f"📡 Published dashboard refresh event for customer: {doc.party}")
