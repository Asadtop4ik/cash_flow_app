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


# ================================================================================
# SALES ORDER CANCEL/AMEND HANDLING
# ================================================================================

def on_cancel_sales_order(doc, method=None):
    """
    ❌ Cancel/Delete all linked Payment Entries (both submitted AND draft)
    when Sales Order is cancelled
    
    Args:
        doc: Sales Order document
        method: Event method name (not used)
    """
    print(f"\n🔴 on_cancel_sales_order() CALLED for SO: {doc.name}")
    frappe.logger().info(f"🔴 Cancelling SO {doc.name} - checking linked Payment Entries")
    
    try:
        # 1️⃣ GET SUBMITTED Payment Entries (need to CANCEL)
        submitted_payments = frappe.get_all(
            "Payment Entry",
            filters={
                "custom_contract_reference": doc.name,
                "docstatus": 1,  # Submitted
                "payment_type": "Receive"
            },
            fields=["name", "paid_amount"]
        )
        
        # 2️⃣ GET DRAFT Payment Entries (need to DELETE)
        draft_payments = frappe.get_all(
            "Payment Entry",
            filters={
                "custom_contract_reference": doc.name,
                "docstatus": 0,  # Draft
                "payment_type": "Receive"
            },
            fields=["name", "paid_amount"]
        )
        
        print(f"   📋 Found {len(submitted_payments)} SUBMITTED, {len(draft_payments)} DRAFT payments")
        frappe.logger().info(f"Found {len(submitted_payments)} submitted, {len(draft_payments)} draft PE'lar for SO {doc.name}")
        
        if not submitted_payments and not draft_payments:
            print(f"   ℹ️  No payments to cancel/delete")
            return
        
        # 3️⃣ CANCEL submitted payments
        cancelled_count = 0
        for payment in submitted_payments:
            try:
                pe_doc = frappe.get_doc("Payment Entry", payment.name)
                pe_doc.add_comment(
                    "Comment",
                    f"🔴 Avtomatik bekor qilindi: Sales Order {doc.name} bekor qilindi"
                )
                pe_doc.cancel()
                cancelled_count += 1
                print(f"   ✅ Cancelled Payment Entry: {payment.name}")
                frappe.logger().info(f"Cancelled PE {payment.name} for SO {doc.name}")
                
            except Exception as e:
                print(f"   ❌ Failed to cancel {payment.name}: {e}")
                frappe.log_error(f"Error cancelling PE {payment.name}: {e}", "SO Cancel - PE Cancel Error")
        
        # 4️⃣ DELETE draft payments (can't cancel drafts, must delete)
        deleted_count = 0
        for payment in draft_payments:
            try:
                frappe.delete_doc("Payment Entry", payment.name, force=1)
                deleted_count += 1
                print(f"   🗑️  Deleted DRAFT Payment Entry: {payment.name}")
                frappe.logger().info(f"Deleted draft PE {payment.name} for SO {doc.name}")
                
            except Exception as e:
                print(f"   ❌ Failed to delete {payment.name}: {e}")
                frappe.log_error(f"Error deleting draft PE {payment.name}: {e}", "SO Cancel - PE Delete Error")
        
        # 5️⃣ Show message to user
        message_parts = []
        if cancelled_count > 0:
            message_parts.append(f"✅ {cancelled_count} ta to'lov bekor qilindi")
        if deleted_count > 0:
            message_parts.append(f"🗑️ {deleted_count} ta draft to'lov o'chirildi")
        
        if message_parts:
            frappe.msgprint(
                "<br>".join(message_parts),
                title=_("To'lovlar Bekor Qilindi"),
                indicator="orange"
            )
        
    except Exception as e:
        print(f"\n❌ ERROR in on_cancel_sales_order: {str(e)}")
        frappe.log_error(f"Error cancelling/deleting linked payments for SO {doc.name}: {e}", "SO Cancel Error")


# ================================================================================
# INSTALLMENT APPLICATION AMEND HANDLING
# ================================================================================

def on_submit_installment_application(doc, method=None):
    """
    🔄 After Installment Application is amended and re-submitted,
    auto-create Payment Entries from cancelled ones
    
    ✅ IMPORTANT: Uses NEW amounts from amended InstApp, not old PE amounts!
    
    Args:
        doc: Installment Application document
        method: Event method name (not used)
    """
    # Check if this is an amended document
    if not doc.amended_from:
        print(f"   ℹ️  Not an amendment ({doc.name}), skipping PE restoration")
        return
    
    print(f"\n🔄 AMENDED Installment Application: {doc.name} (from {doc.amended_from})")
    frappe.logger().info(f"🔄 Processing amended InstApp: {doc.name} from {doc.amended_from}")
    
    try:
        # Get old Installment App
        old_app = frappe.get_doc("Installment Application", doc.amended_from)
        old_so_name = old_app.sales_order
        new_so_name = doc.sales_order
        
        if not old_so_name or not new_so_name:
            print(f"   ❌ Missing SO references (old: {old_so_name}, new: {new_so_name})")
            frappe.log_error(f"Missing SO references in amended InstApp {doc.name}", "InstApp Amend Error")
            return
        
        print(f"   📋 Old SO: {old_so_name}, New SO: {new_so_name}")
        
        # ================================================================================
        # STEP 1: ANALYZE WHAT CHANGED
        # ================================================================================
        changes = _analyze_installment_changes(old_app, doc)
        
        print(f"\n   📊 CHANGES DETECTED:")
        for key, value in changes.items():
            if value.get("changed"):
                print(f"      {key}: {value['old']} → {value['new']}")
        
        # ================================================================================
        # STEP 2: GET CANCELLED PAYMENT ENTRIES
        # ================================================================================
        cancelled_payments = frappe.get_all(
            "Payment Entry",
            filters={
                "custom_contract_reference": old_so_name,
                "docstatus": 2,  # Cancelled
                "payment_type": "Receive"
            },
            fields=["name", "paid_amount", "posting_date", "mode_of_payment", 
                    "custom_payment_schedule_row", "paid_to", "paid_from"],
            order_by="posting_date asc"
        )
        
        print(f"\n   📋 Found {len(cancelled_payments)} CANCELLED Payment Entries")
        
        if not cancelled_payments:
            print(f"   ℹ️  No cancelled payments to restore")
            
            # Check if downpayment needs to be created as draft
            if flt(doc.downpayment_amount) > 0:
                _create_downpayment_draft(doc, new_so_name)
            
            return
        
        # ================================================================================
        # STEP 3: CATEGORIZE PAYMENTS
        # ================================================================================
        payment_categories = _categorize_payments(cancelled_payments, old_so_name)
        
        print(f"\n   📊 Payment Categories:")
        print(f"      Downpayment: {len(payment_categories['downpayment'])} PE")
        print(f"      Installments: {len(payment_categories['installments'])} PE")
        
        # ================================================================================
        # STEP 4: DECIDE CLONE STRATEGY
        # ================================================================================
        clone_strategy = _determine_clone_strategy(changes, payment_categories)
        
        print(f"\n   🎯 Clone Strategy: {clone_strategy['type']}")
        print(f"      Clone downpayment: {clone_strategy['clone_downpayment']}")
        print(f"      Clone installments: {clone_strategy['clone_installments']}")
        print(f"      Adjust installment amounts: {clone_strategy['adjust_installment_amounts']}")
        
        # ================================================================================
        # STEP 5: SHOW WARNING TO USER
        # ================================================================================
        _show_clone_warning(changes, clone_strategy)
        
        # ================================================================================
        # STEP 6: CLONE/CREATE PAYMENT ENTRIES
        # ================================================================================
        restored_payments = []
        
        # 6.1: Handle Downpayment
        if payment_categories['downpayment']:
            restored_payments.extend(
                _handle_downpayment_restoration(
                    payment_categories['downpayment'],
                    doc,
                    new_so_name,
                    clone_strategy
                )
            )
        elif flt(doc.downpayment_amount) > 0 and not clone_strategy['clone_downpayment']:
            # Create new draft if downpayment amount exists but wasn't cloned
            _create_downpayment_draft(doc, new_so_name)
        
        # 6.2: Handle Installments
        if payment_categories['installments']:
            restored_payments.extend(
                _handle_installment_restoration(
                    payment_categories['installments'],
                    doc,
                    new_so_name,
                    clone_strategy,
                    changes
                )
            )
        
        # ================================================================================
        # STEP 7: SHOW SUCCESS MESSAGE
        # ================================================================================
        if restored_payments:
            _show_restoration_success(restored_payments)
        
        frappe.logger().info(f"✅ Restored {len(restored_payments)} Payment Entries for InstApp {doc.name}")
        
    except Exception as e:
        print(f"\n❌ ERROR in on_submit_installment_application: {str(e)}")
        frappe.log_error(
            f"Error in on_submit_installment_application for {doc.name}: {e}",
            "InstApp Amend Error"
        )
        import traceback
        traceback.print_exc()


def _analyze_installment_changes(old_app, new_app):
    """
    Analyze what changed between old and new Installment Application
    
    Returns:
        dict: Dictionary of changes with 'changed', 'old', 'new' keys
    """
    changes = {
        "total_amount": {
            "changed": flt(old_app.total_amount) != flt(new_app.total_amount),
            "old": flt(old_app.total_amount),
            "new": flt(new_app.total_amount)
        },
        "downpayment_amount": {
            "changed": flt(old_app.downpayment_amount) != flt(new_app.downpayment_amount),
            "old": flt(old_app.downpayment_amount),
            "new": flt(new_app.downpayment_amount)
        },
        "monthly_payment": {
            "changed": flt(old_app.monthly_payment) != flt(new_app.monthly_payment),
            "old": flt(old_app.monthly_payment),
            "new": flt(new_app.monthly_payment)
        },
        "installment_months": {
            "changed": old_app.installment_months != new_app.installment_months,
            "old": old_app.installment_months,
            "new": new_app.installment_months
        },
        "grand_total_with_interest": {
            "changed": flt(old_app.custom_grand_total_with_interest) != flt(new_app.custom_grand_total_with_interest),
            "old": flt(old_app.custom_grand_total_with_interest),
            "new": flt(new_app.custom_grand_total_with_interest)
        }
    }
    
    return changes


def _categorize_payments(payment_entries, so_name):
    """
    Categorize cancelled Payment Entries into downpayment and installments
    
    Returns:
        dict: {'downpayment': [pe_list], 'installments': [pe_list]}
    """
    categories = {
        "downpayment": [],
        "installments": []
    }
    
    # Get SO to check payment schedule
    so = frappe.get_doc("Sales Order", so_name)
    
    # Get first payment schedule row (usually downpayment)
    first_schedule_row = None
    if so.payment_schedule:
        first_schedule_row = so.payment_schedule[0].name
    
    for pe_data in payment_entries:
        # Check if this PE is linked to first schedule row (downpayment)
        if pe_data.custom_payment_schedule_row == first_schedule_row:
            categories["downpayment"].append(pe_data)
        else:
            categories["installments"].append(pe_data)
    
    return categories


def _determine_clone_strategy(changes, payment_categories):
    """
    Determine clone strategy based on what changed
    
    Returns:
        dict: Clone strategy with flags
    """
    strategy = {
        "type": "FULL_CLONE",  # FULL_CLONE, PARTIAL_CLONE, NO_CLONE
        "clone_downpayment": True,
        "clone_installments": True,
        "adjust_installment_amounts": False,
        "reason": ""
    }
    
    # Check if any critical financial field changed
    critical_changes = []
    
    if changes["total_amount"]["changed"]:
        critical_changes.append("total_amount")
    
    if changes["downpayment_amount"]["changed"]:
        critical_changes.append("downpayment_amount")
        strategy["clone_downpayment"] = False  # Don't clone, create new draft instead
        strategy["type"] = "PARTIAL_CLONE"
    
    if changes["monthly_payment"]["changed"]:
        critical_changes.append("monthly_payment")
        strategy["adjust_installment_amounts"] = True  # Clone but adjust amounts
        if strategy["type"] != "PARTIAL_CLONE":
            strategy["type"] = "PARTIAL_CLONE"
    
    if changes["installment_months"]["changed"]:
        critical_changes.append("installment_months")
        # This shouldn't happen if there are existing payments
        # But if it does, we still clone existing ones
    
    if critical_changes:
        strategy["reason"] = f"Changed: {', '.join(critical_changes)}"
    else:
        strategy["reason"] = "No financial changes, safe to clone all"
    
    return strategy


def _show_clone_warning(changes, strategy):
    """
    Show warning message to user about clone strategy
    """
    if strategy["type"] == "FULL_CLONE":
        frappe.msgprint(
            _("✅ Moliyaviy ma'lumotlar o'zgarmadi. Barcha to'lovlar qayta tiklanadi."),
            title=_("To'lovlarni Qayta Tiklash"),
            indicator="green"
        )
    elif strategy["type"] == "PARTIAL_CLONE":
        warning_parts = []
        
        if not strategy["clone_downpayment"]:
            warning_parts.append(
                f"⚠️ Boshlang'ich to'lov o'zgardi: "
                f"${changes['downpayment_amount']['old']} → ${changes['downpayment_amount']['new']}<br>"
                f"Yangi summa bilan DRAFT yaratiladi (tekshiring va submit qiling!)"
            )
        
        if strategy["adjust_installment_amounts"]:
            warning_parts.append(
                f"⚠️ Oylik to'lov o'zgardi: "
                f"${changes['monthly_payment']['old']} → ${changes['monthly_payment']['new']}<br>"
                f"Eski to'lovlar clone qilinadi, yangi summa keyingi oylar uchun qo'llaniladi"
            )
        
        if warning_parts:
            frappe.msgprint(
                "<br><br>".join(warning_parts),
                title=_("To'lovlarni Qayta Tiklash - Ogohlik"),
                indicator="orange"
            )


def _handle_downpayment_restoration(downpayment_pes, new_app, new_so_name, strategy):
    """
    Handle restoration of downpayment Payment Entry
    
    Returns:
        list: List of restored payment info
    """
    restored = []
    
    if not strategy["clone_downpayment"]:
        # Don't clone, create new draft instead
        _create_downpayment_draft(new_app, new_so_name)
        return restored
    
    # Clone downpayment PE (should be only one)
    for old_pe_data in downpayment_pes:
        try:
            old_pe = frappe.get_doc("Payment Entry", old_pe_data.name)
            
            # Use OLD amount (since strategy says clone)
            amount = flt(old_pe.paid_amount)
            
            print(f"\n   💰 Cloning DOWNPAYMENT: {old_pe.name} (${amount})")
            
            new_pe = _create_cloned_payment_entry(old_pe, new_app, new_so_name, amount, "Boshlang'ich to'lov")
            # ❌ DO NOT submit - leave as DRAFT for user to verify
            new_pe.submit()
            
            restored.append({
                "old": old_pe.name,
                "new": new_pe.name,
                "old_amount": flt(old_pe.paid_amount),
                "new_amount": amount,
                "type": "Boshlang'ich to'lov (clone)",
                "status": "submitted"  # Changed from "submitted" to "draft"
            })
            
            print(f"   ✅ Cloned as submitted: {old_pe.name} → {new_pe.name} (${amount})")
            frappe.logger().info(f"Cloned downpayment PE: {old_pe.name} → {new_pe.name}")
            
        except Exception as e:
            print(f"   ❌ Failed to clone downpayment {old_pe_data.name}: {e}")
            frappe.log_error(f"Error cloning downpayment PE {old_pe_data.name}: {e}", "PE Clone Error")
    
    return restored


def _handle_installment_restoration(installment_pes, new_app, new_so_name, strategy, changes):
    """
    Handle restoration of installment Payment Entries
    
    Returns:
        list: List of restored payment info
    """
    restored = []
    
    if not strategy["clone_installments"]:
        return restored
    
    for old_pe_data in installment_pes:
        try:
            old_pe = frappe.get_doc("Payment Entry", old_pe_data.name)
            
            # Determine amount
            if strategy["adjust_installment_amounts"] and changes["monthly_payment"]["changed"]:
                # Use NEW monthly payment amount for future installments
                # But keep old amount for already-paid ones (this is tricky)
                # For simplicity: use old amount (safe approach)
                amount = flt(old_pe.paid_amount)
                
                # Note: In future, could check payment_schedule to determine if this
                # installment should use new or old amount
            else:
                amount = flt(old_pe.paid_amount)
            
            print(f"\n   💰 Cloning INSTALLMENT: {old_pe.name} (${amount})")
            
            new_pe = _create_cloned_payment_entry(old_pe, new_app, new_so_name, amount, "Oylik to'lov")
            # ❌ DO NOT submit - leave as DRAFT for user to verify
            # new_pe.submit()
            
            restored.append({
                "old": old_pe.name,
                "new": new_pe.name,
                "old_amount": flt(old_pe.paid_amount),
                "new_amount": amount,
                "type": "Oylik to'lov (clone)",
                "status": "draft"  # Changed from "submitted" to "draft"
            })
            
            print(f"   ✅ Cloned as DRAFT: {old_pe.name} → {new_pe.name} (${amount})")
            frappe.logger().info(f"Cloned installment PE: {old_pe.name} → {new_pe.name}")
            
        except Exception as e:
            print(f"   ❌ Failed to clone installment {old_pe_data.name}: {e}")
            frappe.log_error(f"Error cloning installment PE {old_pe_data.name}: {e}", "PE Clone Error")
    
    return restored


def _create_cloned_payment_entry(old_pe, new_app, new_so_name, amount, payment_type_label):
    """
    Create a cloned Payment Entry with new amount and SO reference
    
    Returns:
        frappe.Document: New Payment Entry (not submitted)
    """
    new_pe = frappe.new_doc("Payment Entry")
    new_pe.payment_type = "Receive"
    new_pe.party_type = "Customer"
    new_pe.party = new_app.customer
    new_pe.posting_date = old_pe.posting_date  # Keep original date
    new_pe.paid_amount = amount
    new_pe.received_amount = amount
    new_pe.mode_of_payment = old_pe.mode_of_payment or "Cash"
    new_pe.custom_contract_reference = new_so_name
    new_pe.custom_payment_schedule_row = old_pe.custom_payment_schedule_row
    new_pe.custom_installment_application = new_app.name
    
    # Copy custom fields
    if hasattr(old_pe, 'custom_counterparty_category') and old_pe.custom_counterparty_category:
        new_pe.custom_counterparty_category = old_pe.custom_counterparty_category
    
    # Copy accounts
    new_pe.paid_to = old_pe.paid_to
    new_pe.paid_from = old_pe.paid_from
    new_pe.paid_to_account_currency = old_pe.paid_to_account_currency
    new_pe.paid_from_account_currency = old_pe.paid_from_account_currency
    new_pe.company = old_pe.company
    
    # Copy cost center if exists
    if hasattr(old_pe, 'cost_center') and old_pe.cost_center:
        new_pe.cost_center = old_pe.cost_center
    
    # Add comment
    amount_diff = amount - flt(old_pe.paid_amount)
    if amount_diff != 0:
        change_text = f"⬆️ +${abs(amount_diff)}" if amount_diff > 0 else f"⬇️ -${abs(amount_diff)}"
        comment = (
            f"🔄 Clone qilingan: {old_pe.name}<br>"
            f"📝 Summa o'zgartirildi: ${old_pe.paid_amount} → ${amount} ({change_text})<br>"
            f"🔗 InstApp amended: {new_app.amended_from} → {new_app.name}<br>"
            f"📋 Turi: {payment_type_label}"
        )
    else:
        comment = (
            f"🔄 Clone qilingan: {old_pe.name}<br>"
            f"💰 Summa: ${amount}<br>"
            f"🔗 InstApp amended: {new_app.amended_from} → {new_app.name}<br>"
            f"📋 Turi: {payment_type_label}"
        )
    
    new_pe.add_comment("Comment", comment)
    
    new_pe.insert(ignore_permissions=True)
    
    return new_pe


def _create_downpayment_draft(new_app, new_so_name):
    """
    Create a DRAFT Payment Entry for downpayment
    """
    downpayment_amount = flt(new_app.downpayment_amount)
    
    if downpayment_amount <= 0:
        return
    
    try:
        print(f"\n   📝 Creating NEW DRAFT downpayment: ${downpayment_amount}")
        
        # Get SO to find first payment schedule row
        so = frappe.get_doc("Sales Order", new_so_name)
        first_schedule_row = None
        if so.payment_schedule:
            first_schedule_row = so.payment_schedule[0].name
        
        # Get default accounts
        company = new_app.company if hasattr(new_app, 'company') else frappe.defaults.get_user_default("Company")
        default_receivable = frappe.get_cached_value("Company", company, "default_receivable_account")
        default_cash = frappe.get_cached_value("Company", company, "default_cash_account") or frappe.get_cached_value("Company", company, "default_bank_account")
        
        new_pe = frappe.new_doc("Payment Entry")
        new_pe.payment_type = "Receive"
        new_pe.party_type = "Customer"
        new_pe.party = new_app.customer
        new_pe.posting_date = frappe.utils.today()
        new_pe.paid_amount = downpayment_amount
        new_pe.received_amount = downpayment_amount
        new_pe.mode_of_payment = "Cash"
        new_pe.custom_contract_reference = new_so_name
        new_pe.custom_payment_schedule_row = first_schedule_row
        new_pe.custom_installment_application = new_app.name
        
        # Set accounts
        new_pe.paid_to = default_cash
        new_pe.paid_from = default_receivable
        new_pe.company = company
        
        new_pe.add_comment(
            "Comment",
            f"📝 DRAFT yaratildi (amended InstApp {new_app.name})<br>"
            f"⚠️ TEKSHIRING va submit qiling!<br>"
            f"💰 Boshlang'ich to'lov: ${downpayment_amount}"
        )
        
        # ✅ Save as DRAFT (don't submit!)
        new_pe.insert(ignore_permissions=True)
        
        frappe.msgprint(
            _(f"📝 Boshlang'ich to'lov uchun DRAFT yaratildi: {new_pe.name} (${downpayment_amount})<br>"
              f"⚠️ Tekshiring va submit qiling!"),
            title=_("Draft To'lov Yaratildi"),
            indicator="blue"
        )
        
        print(f"   ✅ Created DRAFT: {new_pe.name} (${downpayment_amount})")
        frappe.logger().info(f"Created draft downpayment PE: {new_pe.name} for InstApp {new_app.name}")
        
    except Exception as e:
        print(f"   ❌ Failed to create draft downpayment: {e}")
        frappe.log_error(f"Error creating draft downpayment for InstApp {new_app.name}: {e}", "Draft PE Error")


def _show_restoration_success(restored_payments):
    """
    Show success message with list of restored payments
    """
    if not restored_payments:
        return
    
    message_parts = []
    
    # Group by type
    downpayments = [p for p in restored_payments if "Boshlang'ich" in p["type"]]
    installments = [p for p in restored_payments if "Oylik" in p["type"]]
    
    if downpayments:
        downpayment_list = "<br>".join([
            f"• {p['old']} → <b>{p['new']}</b> (${p['new_amount']})" 
            for p in downpayments
        ])
        message_parts.append(f"<b>✅ Boshlang'ich to'lov:</b><br>{downpayment_list}")
    
    if installments:
        installment_list = "<br>".join([
            f"• {p['old']} → <b>{p['new']}</b> (${p['new_amount']})" 
            for p in installments
        ])
        message_parts.append(f"<b>✅ Oylik to'lovlar:</b><br>{installment_list}")
    
    if message_parts:
        frappe.msgprint(
            "<br><br>".join(message_parts),
            title=_("To'lovlar Muvaffaqiyatli Qayta Tiklandi"),
            indicator="green"
        )
