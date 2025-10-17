# Copyright (c) 2025, Your Company
# API for Payment Entry

import frappe

@frappe.whitelist()
def get_mode_account(mode_of_payment, company):
    """Get default account for mode of payment"""
    if not mode_of_payment or not company:
        return None
    
    accounts = frappe.get_all(
        "Mode of Payment Account",
        filters={
            "parent": mode_of_payment,
            "company": company
        },
        fields=["default_account"]
    )
    
    if accounts:
        return accounts[0].default_account
    
    return None

@frappe.whitelist()
def get_customer_contracts(customer):
    """Get active contracts for customer"""
    if not customer:
        return []
    
    contracts = frappe.get_all(
        "Sales Order",
        filters={
            "customer": customer,
            "docstatus": 1,
            "status": ["not in", ["Completed", "Cancelled"]]
        },
        fields=["name", "transaction_date", "grand_total", "customer_name"],
        order_by="transaction_date desc"
    )
    
    return contracts

