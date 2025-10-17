# Customer History API
# Provides contract and payment history for customers

import frappe
from frappe import _
from frappe.utils import flt, getdate, date_diff, today

@frappe.whitelist()
def get_customer_contracts(customer):
    """Get customer's contracts with summary"""
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
        LIMIT 1
    """, {'customer': customer}, as_dict=1)
    
    if not contracts:
        return []
    
    # Determine status color
    for contract in contracts:
        if contract.outstanding_amount <= 0:
            contract['status_color'] = 'green'
        elif contract.status == 'Overdue':
            contract['status_color'] = 'red'
        else:
            contract['status_color'] = 'orange'
    
    return contracts


@frappe.whitelist()
def get_payment_schedule_with_history(customer):
    """Get payment schedule with actual payment history"""
    if not customer:
        return []
    
    # Get latest contract
    contract = frappe.db.sql("""
        SELECT name 
        FROM `tabSales Order` 
        WHERE customer = %(customer)s 
            AND docstatus = 1 
        ORDER BY transaction_date DESC 
        LIMIT 1
    """, {'customer': customer}, as_dict=1)
    
    if not contract:
        return []
    
    sales_order = contract[0].name
    
    # Get payment schedule with payments
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
    
    # Get actual payments
    payments = frappe.db.sql("""
        SELECT 
            pe.posting_date,
            pe.paid_amount,
            per.allocated_amount,
            per.reference_name
        FROM `tabPayment Entry` pe
        INNER JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
        WHERE pe.party = %(customer)s
            AND pe.docstatus = 1
            AND pe.payment_type = 'Receive'
            AND per.reference_name = %(sales_order)s
        ORDER BY pe.posting_date
    """, {'customer': customer, 'sales_order': sales_order}, as_dict=1)
    
    # Map payments to schedule
    payment_map = {}
    for payment in payments:
        date = str(payment.posting_date)
        if date not in payment_map:
            payment_map[date] = []
        payment_map[date].append(payment)
    
    # Enhance schedule with status
    today_date = getdate(today())
    
    for row in schedule:
        due_date = getdate(row.due_date)
        paid = flt(row.paid_amount)
        
        # Find matching payment
        row['payment_date'] = None
        for payment_date, payment_list in payment_map.items():
            for p in payment_list:
                if flt(p.allocated_amount) == flt(row.payment_amount):
                    row['payment_date'] = payment_date
                    break
        
        # Determine status
        if paid >= flt(row.payment_amount):
            # Paid
            if row['payment_date']:
                payment_date = getdate(row['payment_date'])
                days_diff = date_diff(payment_date, due_date)
                
                if days_diff <= 0:
                    row['status'] = 'On Time'
                    row['days_late'] = 0
                else:
                    row['status'] = 'Late'
                    row['days_late'] = days_diff
            else:
                row['status'] = 'On Time'
                row['days_late'] = 0
        else:
            # Not paid yet
            if today_date > due_date:
                row['status'] = 'Overdue'
                row['days_late'] = date_diff(today_date, due_date)
            else:
                row['status'] = 'Upcoming'
                row['days_remaining'] = date_diff(due_date, today_date)
    
    return schedule
