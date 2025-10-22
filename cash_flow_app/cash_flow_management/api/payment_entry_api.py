"""
Custom API methods for Payment Entry form
These methods use ignore_permissions=True for internal app functionality
"""

import frappe
from frappe import _


@frappe.whitelist()
def get_customer_contracts(customer):
	"""Get active Sales Orders for customer - used by Payment Entry form"""
	if not customer:
		return []
	
	try:
		# Get latest active Sales Order for this customer
		contracts = frappe.get_all(
			"Sales Order",
			filters={
				"customer": customer,
				"docstatus": 1,  # Submitted
				"status": ["not in", ["Completed", "Cancelled", "Closed"]]
			},
			fields=["name", "transaction_date", "custom_grand_total_with_interest", "advance_paid"],
			order_by="transaction_date desc",
			limit=1,
			ignore_permissions=True  # Internal app use
		)
		
		return contracts
		
	except Exception as e:
		frappe.log_error(f"Error fetching contracts for {customer}: {str(e)}")
		return []


@frappe.whitelist()
def get_payment_schedules(contract_reference):
	"""Get Payment Schedules for a Sales Order - used by Payment Entry form"""
	if not contract_reference:
		return []
	
	try:
		# Get unpaid payment schedules for this contract
		schedules = frappe.get_all(
			"Payment Schedule",
			filters={
				"parent": contract_reference,
				"parenttype": "Sales Order"
			},
			fields=["name", "idx", "due_date", "payment_amount", "paid_amount", "description"],
			order_by="idx asc",
			ignore_permissions=True  # Internal app use
		)
		
		return schedules
		
	except Exception as e:
		frappe.log_error(f"Error fetching payment schedules for {contract_reference}: {str(e)}")
		return []


@frappe.whitelist()
def get_installment_applications(customer):
	"""Get Installment Applications for customer - used by Payment Entry form"""
	if not customer:
		return []
	
	try:
		apps = frappe.get_all(
			"Installment Application",
			filters={
				"customer": customer,
				"docstatus": 1  # Submitted only
			},
			fields=["name", "transaction_date", "custom_grand_total_with_interest", "sales_order", "status"],
			order_by="creation desc",
			limit=5,
			ignore_permissions=True  # Internal app use
		)
		
		return apps
		
	except Exception as e:
		frappe.log_error(f"Error fetching installment applications for {customer}: {str(e)}")
		return []
