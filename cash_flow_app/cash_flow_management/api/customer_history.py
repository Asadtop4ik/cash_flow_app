# Customer History API
# Provides contract and payment history for customers

import frappe
from frappe import _
from frappe.utils import flt, getdate, date_diff, today

@frappe.whitelist()
def get_customer_contracts(customer):
    """Get ALL customer's contracts with summary"""
    if not customer:
        return []
    
    contracts = frappe.db.sql("""
        SELECT 
            so.name,
            so.customer_name,
            so.transaction_date,
            so.grand_total as total_amount,
            so.custom_grand_total_with_interest as grand_total_with_interest,
            so.custom_downpayment_amount as downpayment,
            so.advance_paid as paid_amount,
            (so.custom_grand_total_with_interest - so.advance_paid) as outstanding_amount,
            so.custom_next_payment_date as next_payment_date,
            so.custom_next_payment_amount as next_payment_amount,
            ia.installment_months,
            ia.monthly_payment,
            so.status
        FROM `tabSales Order` so
        LEFT JOIN `tabInstallment Application` ia ON ia.sales_order = so.name
        WHERE so.customer = %(customer)s
            AND so.docstatus = 1
        ORDER BY so.transaction_date DESC
    """, {'customer': customer}, as_dict=1)
    
    if not contracts:
        return []
    
    # Determine status and color based on payment progress
    for contract in contracts:
        outstanding = flt(contract.outstanding_amount)
        total_with_interest = flt(contract.grand_total_with_interest)
        paid = flt(contract.paid_amount)
        
        # Calculate payment progress
        if total_with_interest > 0:
            payment_percentage = (paid / total_with_interest) * 100
        else:
            payment_percentage = 0
        
        # Determine custom status
        if outstanding <= 0:
            contract['custom_status'] = 'Completed'
            contract['status_color'] = 'green'
            contract['status_icon'] = '✅'
        elif payment_percentage > 0 and payment_percentage < 100:
            contract['custom_status'] = 'On Process'
            contract['status_color'] = 'blue'
            contract['status_icon'] = '🔄'
        elif contract.status == 'Overdue':
            contract['custom_status'] = 'Overdue'
            contract['status_color'] = 'red'
            contract['status_icon'] = '⚠️'
        else:
            contract['custom_status'] = 'Pending'
            contract['status_color'] = 'orange'
            contract['status_icon'] = '⏳'
        
        # Add payment progress
        contract['payment_percentage'] = round(payment_percentage, 2)
    
    return contracts


@frappe.whitelist()
def get_payment_schedule_with_history(customer):
    """
    ✅ FIXED VERSION - Get payment schedule with REAL-TIME paid_amount from DB
    """
    if not customer:
        return []
    
    # Get ALL contracts for this customer
    contracts = frappe.db.sql("""
        SELECT name, transaction_date 
        FROM `tabSales Order` 
        WHERE customer = %(customer)s 
            AND docstatus = 1 
        ORDER BY transaction_date DESC
    """, {'customer': customer}, as_dict=1)
    
    if not contracts:
        return []
    
    # Loop through ALL contracts and aggregate schedules
    all_schedules = []
    
    for contract in contracts:
        sales_order = contract.name
        
        # ✅ GET PAYMENT SCHEDULE - use GREATEST to get max of both fields
        schedule = frappe.db.sql("""
            SELECT 
                ps.name,
                ps.idx as payment_number,
                ps.due_date,
                ps.payment_amount,
                ps.paid_amount,
                ps.description
            FROM `tabPayment Schedule` ps
            WHERE ps.parent = %(sales_order)s
                AND ps.parenttype = 'Sales Order'
            ORDER BY ps.idx
        """, {'sales_order': sales_order}, as_dict=1)
        
        # ✅ GET PAYMENT ENTRIES FOR THIS CONTRACT (for payment_date display)
        payments = frappe.db.sql("""
            SELECT 
                pe.name as payment_name,
                pe.posting_date,
                pe.paid_amount,
                pe.custom_payment_schedule_row
            FROM `tabPayment Entry` pe
            WHERE pe.party = %(customer)s
                AND pe.docstatus = 1
                AND pe.payment_type = 'Receive'
                AND pe.custom_contract_reference = %(sales_order)s
            ORDER BY pe.posting_date
        """, {'customer': customer, 'sales_order': sales_order}, as_dict=1)
        
        # Create payment map by schedule row
        payment_map = {}
        for payment in payments:
            schedule_row = payment.custom_payment_schedule_row
            if schedule_row:
                if schedule_row not in payment_map:
                    payment_map[schedule_row] = []
                payment_map[schedule_row].append(payment)
        
        # Enhance schedule with status and payment info
        today_date = getdate(today())
        
        for row in schedule:
            due_date = getdate(row.due_date)
            payment_amount = flt(row.payment_amount)
            
            # ✅ USE PAID_AMOUNT DIRECTLY FROM DB (already updated by on_submit hook)
            paid = flt(row.get('paid_amount', 0))
            row['paid_amount'] = paid
            
            # Find linked payments for this schedule row (for display only)
            row['payments'] = payment_map.get(row.name, [])
            row['payment_count'] = len(row['payments'])
            
            # Get latest payment date (for display)
            if row['payments']:
                latest_payment = max(row['payments'], key=lambda x: x.posting_date)
                row['payment_date'] = str(latest_payment.posting_date)
                row['payment_name'] = latest_payment.payment_name
            else:
                row['payment_date'] = None
                row['payment_name'] = None
            
            # Calculate outstanding
            row['outstanding'] = max(0, payment_amount - paid)
            
            # Add contract reference
            row['contract'] = sales_order
            
            # ✅ DETERMINE STATUS based on REAL-TIME paid_amount from DB
            if paid >= payment_amount:
                # FULLY PAID
                if row['payment_date']:
                    payment_date = getdate(row['payment_date'])
                    days_diff = date_diff(payment_date, due_date)
                    
                    if days_diff <= 0:
                        row['status'] = '✅ To\'landi (Vaqtida)'
                        row['status_color'] = 'green'
                        row['days_late'] = 0
                    else:
                        row['status'] = f'✅ To\'landi ({days_diff} kun kech)'
                        row['status_color'] = 'orange'
                        row['days_late'] = days_diff
                else:
                    row['status'] = '✅ To\'landi'
                    row['status_color'] = 'green'
                    row['days_late'] = 0
            elif paid > 0:
                # PARTIALLY PAID
                row['status'] = f'🟡 Qisman to\'landi (${paid:.2f}/${payment_amount:.2f})'
                row['status_color'] = 'orange'
                if today_date > due_date:
                    row['days_late'] = date_diff(today_date, due_date)
                else:
                    row['days_late'] = 0
            else:
                # NOT PAID YET
                if today_date > due_date:
                    days_overdue = date_diff(today_date, due_date)
                    row['status'] = f'❌ Muddati o\'tgan ({days_overdue} kun)'
                    row['status_color'] = 'red'
                    row['days_late'] = days_overdue
                else:
                    days_remaining = date_diff(due_date, today_date)
                    row['status'] = f'⏳ Kutilmoqda ({days_remaining} kun qoldi)'
                    row['status_color'] = 'blue'
                    row['days_remaining'] = days_remaining
                    row['days_late'] = 0
        
        # Append this contract's schedule to all_schedules
        all_schedules.extend(schedule)
    
    # Return schedules for ALL contracts combined
    return all_schedules