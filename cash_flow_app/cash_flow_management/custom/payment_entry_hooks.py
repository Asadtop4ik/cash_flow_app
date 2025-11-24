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
    # TEMPORARILY DISABLED
    # if not doc.custom_counterparty_category:
    #     frappe.throw(_("Counterparty Category is mandatory"))
    
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
    """Validate contract reference for Bosh to'lov category"""
    if doc.custom_counterparty_category == "Bosh to'lov":
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
    
    # ✅ UPDATE Payment Schedule paid_amount (CRITICAL!)
    if doc.custom_payment_schedule_row:
        try:
            print(f"\n🔵 UPDATING Payment Schedule: {doc.custom_payment_schedule_row}")
            print(f"   Payment Entry: {doc.name}")
            print(f"   Amount: {doc.paid_amount}")
            print(f"   Payment Type: {doc.payment_type}")

            # Calculate TOTAL paid amount for this schedule row from ALL Payment Entries
            # ✅ Receive qo'shiladi, Pay ayiriladi (customerga pul qaytarilsa)
            total_paid = frappe.db.sql("""
                SELECT COALESCE(
                    SUM(CASE WHEN payment_type = 'Receive' THEN paid_amount ELSE -paid_amount END),
                    0
                ) as total
                FROM `tabPayment Entry`
                WHERE custom_payment_schedule_row = %(schedule_row)s
                    AND docstatus = 1
                    AND payment_type IN ('Receive', 'Pay')
            """, {'schedule_row': doc.custom_payment_schedule_row}, as_dict=1)[0].total

            print(f"   Total Paid (all payments): {total_paid}")
            
            # Update Payment Schedule with calculated total
            frappe.db.sql("""
                UPDATE `tabPayment Schedule`
                SET paid_amount = %(total_paid)s
                WHERE name = %(schedule_row)s
            """, {
                'total_paid': total_paid,
                'schedule_row': doc.custom_payment_schedule_row
            })
            
            frappe.db.commit()
            
            print(f"✅ UPDATED Payment Schedule: {doc.custom_payment_schedule_row}")
            print(f"   Total Paid Amount: {total_paid}\n")
            
        except Exception as e:
            print(f"\n❌ ERROR updating Payment Schedule: {str(e)}\n")
            frappe.log_error(
                title="Payment Schedule Update Failed",
                message=f"Failed to update Payment Schedule {doc.custom_payment_schedule_row}: {str(e)}"
            )
    
    # Trigger real-time refresh for Customer dashboard
    if doc.party_type == "Customer" and doc.party:
        event_data = {
            'customer': doc.party,
            'payment_entry': doc.name,
            'amount': doc.paid_amount,
            'contract': doc.custom_contract_reference
        }
        
        print(f"\n🔵 PUBLISHING REALTIME EVENT:")
        print(f"   Event: payment_entry_submitted")
        print(f"   Customer: {doc.party}")
        print(f"   Payment: {doc.name}")
        
        frappe.publish_realtime(
            event='payment_entry_submitted',
            message=event_data,
            user=frappe.session.user
        )
        
        print(f"✅ Event published successfully!\n")

def on_cancel(doc, method=None):
    """After cancel actions - REVERSE payment schedule update"""
    frappe.logger().info(f"Payment Entry cancelled: {doc.name}")
    
    # ✅ REVERSE Payment Schedule paid_amount when cancelled
    if doc.custom_payment_schedule_row:
        try:
            print(f"\n🔴 REVERSING Payment Schedule: {doc.custom_payment_schedule_row}")
            print(f"   Cancelled Payment: {doc.name}")
            print(f"   Amount: {doc.paid_amount}")
            print(f"   Payment Type: {doc.payment_type}")

            # Calculate TOTAL paid amount EXCLUDING this cancelled payment
            # ✅ Receive qo'shiladi, Pay ayiriladi (customerga pul qaytarilsa)
            total_paid = frappe.db.sql("""
                SELECT COALESCE(
                    SUM(CASE WHEN payment_type = 'Receive' THEN paid_amount ELSE -paid_amount END),
                    0
                ) as total
                FROM `tabPayment Entry`
                WHERE custom_payment_schedule_row = %(schedule_row)s
                    AND docstatus = 1
                    AND payment_type IN ('Receive', 'Pay')
                    AND name != %(payment_entry)s
            """, {
                'schedule_row': doc.custom_payment_schedule_row,
                'payment_entry': doc.name
            }, as_dict=1)[0].total

            print(f"   New Total Paid: {total_paid}")
            
            # Update Payment Schedule
            frappe.db.sql("""
                UPDATE `tabPayment Schedule`
                SET paid_amount = %(total_paid)s
                WHERE name = %(schedule_row)s
            """, {
                'total_paid': total_paid,
                'schedule_row': doc.custom_payment_schedule_row
            })
            
            frappe.db.commit()
            
            print(f"✅ REVERSED Payment Schedule: {doc.custom_payment_schedule_row}")
            print(f"   New Total Paid: {total_paid}\n")
            
        except Exception as e:
            print(f"\n❌ ERROR reversing Payment Schedule: {str(e)}\n")
            frappe.log_error(
                title="Payment Schedule Reversal Failed",
                message=f"Failed to reverse Payment Schedule {doc.custom_payment_schedule_row}: {str(e)}"
            )

