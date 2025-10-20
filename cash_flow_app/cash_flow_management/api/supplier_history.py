"""
Supplier History API
Provides data for supplier debt tracking and history display
"""

import frappe
from frappe import _
from frappe.utils import flt

@frappe.whitelist()
def get_supplier_contracts(supplier):
    """
    Get all Installment Applications that have items from this supplier
    """
    if not supplier:
        return []
    
    # Get all submitted Installment Applications with items from this supplier
    contracts = frappe.db.sql("""
        SELECT DISTINCT
            ia.name,
            ia.customer,
            ia.customer_name,
            ia.transaction_date,
            ia.total_amount,
            ia.status
        FROM `tabInstallment Application` ia
        INNER JOIN `tabInstallment Application Item` iai 
            ON iai.parent = ia.name
        WHERE iai.custom_supplier = %(supplier)s
        AND ia.docstatus = 1
        ORDER BY ia.transaction_date DESC
    """, {"supplier": supplier}, as_dict=1)
    
    # Calculate supplier-specific amounts for each contract
    for contract in contracts:
        # Get items for this supplier in this contract
        items = frappe.db.sql("""
            SELECT 
                item_name,
                qty,
                rate,
                amount
            FROM `tabInstallment Application Item`
            WHERE parent = %(contract)s
            AND custom_supplier = %(supplier)s
        """, {"contract": contract.name, "supplier": supplier}, as_dict=1)
        
        supplier_amount = sum(flt(item.amount) for item in items)
        contract['supplier_amount'] = supplier_amount
        contract['items_count'] = len(items)
        contract['items'] = items
    
    return contracts

@frappe.whitelist()
def get_supplier_payment_history(supplier):
    """
    Get payment history for a supplier
    """
    if not supplier:
        return []
    
    # Get all submitted Payment Entries (Pay type) for this supplier
    payments = frappe.db.sql("""
        SELECT 
            name,
            posting_date,
            paid_amount,
            mode_of_payment,
            reference_no,
            remarks,
            creation,
            owner
        FROM `tabPayment Entry`
        WHERE party_type = 'Supplier'
        AND party = %(supplier)s
        AND payment_type = 'Pay'
        AND docstatus = 1
        ORDER BY posting_date DESC, creation DESC
    """, {"supplier": supplier}, as_dict=1)
    
    return payments

@frappe.whitelist()
def get_supplier_debt_summary(supplier):
    """
    Get comprehensive debt summary for a supplier
    """
    if not supplier:
        return {}
    
    supplier_doc = frappe.get_doc("Supplier", supplier)
    
    total_debt = flt(supplier_doc.get("custom_total_debt", 0))
    paid_amount = flt(supplier_doc.get("custom_paid_amount", 0))
    remaining_debt = flt(supplier_doc.get("custom_remaining_debt", 0))
    status = supplier_doc.get("custom_payment_status", "Qarzda")
    
    # Get contracts count
    contracts_count = frappe.db.count("Installment Application Item", {
        "custom_supplier": supplier,
        "docstatus": 1
    })
    
    # Get payments count
    payments_count = frappe.db.count("Payment Entry", {
        "party_type": "Supplier",
        "party": supplier,
        "payment_type": "Pay",
        "docstatus": 1
    })
    
    return {
        "supplier_name": supplier_doc.supplier_name,
        "total_debt": total_debt,
        "paid_amount": paid_amount,
        "remaining_debt": remaining_debt,
        "payment_status": status,
        "payment_percentage": (paid_amount / total_debt * 100) if total_debt > 0 else 0,
        "contracts_count": contracts_count,
        "payments_count": payments_count
    }
