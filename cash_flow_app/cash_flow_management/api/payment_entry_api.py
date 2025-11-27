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


@frappe.whitelist()
def get_supplier_contracts(supplier):
	"""Get Installment Applications for supplier - used by Payment Entry form (Pay type)"""
	if not supplier:
		return []

	try:
		# Get Installment Applications where this supplier has items
		# We need to query from Installment Application Item table
		contracts = frappe.db.sql("""
			SELECT DISTINCT
				ia.name,
				ia.transaction_date,
				ia.status,
				SUM(item.qty * item.rate) as total_amount
			FROM `tabInstallment Application` ia
			INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
			WHERE item.custom_supplier = %(supplier)s
				AND ia.docstatus = 1
			GROUP BY ia.name
			ORDER BY ia.transaction_date DESC
			LIMIT 10
		""", {'supplier': supplier}, as_dict=1)

		return contracts

	except Exception as e:
		frappe.log_error(f"Error fetching supplier contracts: {str(e)}")
		return []


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_supplier_contracts_query(doctype, txt, searchfield, start, page_len, filters):
	"""Query method for custom_supplier_contract Link field - filters by supplier"""
	supplier = filters.get('supplier')

	if not supplier:
		return []

	return frappe.db.sql("""
		SELECT DISTINCT ia.name, ia.transaction_date, ia.status
		FROM `tabInstallment Application` ia
		INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
		WHERE item.custom_supplier = %(supplier)s
			AND ia.docstatus = 1
			AND (ia.name LIKE %(txt)s OR ia.status LIKE %(txt)s)
		ORDER BY ia.transaction_date DESC
		LIMIT %(start)s, %(page_len)s
	""", {
		'supplier': supplier,
		'txt': '%%' + txt + '%%',
		'start': start,
		'page_len': page_len
	})
