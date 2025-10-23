# Copyright (c) 2025, Cash Flow App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	"""
	Supplier Debt Analysis Report
	Shows each payment transaction with running balance calculation
	"""
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data)
	
	chart = None
	
	# Disable automatic totals by NOT adding 'total_row' indicator
	# Our custom Total row already included in data
	return columns, data, None, chart, summary, None


def get_columns():
	"""Define report columns - har bir tranzaksiya alohida ko'rsatiladi"""
	return [
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 150
		},
		{
			"label": _("Transaction Type"),
			"fieldname": "transaction_type",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Document"),
			"fieldname": "document",
			"fieldtype": "Dynamic Link",
			"options": "document_type",
			"width": 150
		},
		{
			"label": _("Date"),
			"fieldname": "transaction_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Item"),
			"fieldname": "item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120
		},
		{
			"label": _("Amount"),
			"fieldname": "amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": _("Debt"),
			"fieldname": "debt",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": _("Outstanding"),
			"fieldname": "outstanding",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": _("Payment Method"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100
		}
	]


def get_data(filters):
	"""
	Get both Installment Applications (debt source) and Payment Entries (debt payment)
	Show all transactions in chronological order
	"""
	conditions = get_conditions(filters)
	
	# Build supplier filter for installments
	installment_conditions = ""
	if filters.get("supplier"):
		installment_conditions = "AND item.custom_supplier = %(supplier)s"
	
	# Get all Installment Applications (debt increases)
	installments_query = f"""
		SELECT
			'Installment Application' as transaction_type,
			ia.name as document,
			'Installment Application' as document_type,
			ia.name as installment_application,
			DATE(ia.transaction_date) as transaction_date,
			item.custom_supplier as supplier,
			item.item_code as item,
			0 as amount,
			(item.qty * item.rate) as debt_amount,
			ia.creation,
			'Debt Added' as status,
			'USD' as currency
		FROM `tabInstallment Application` ia
		INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
		WHERE ia.docstatus = 1
			AND item.custom_supplier IS NOT NULL
			{installment_conditions}
		ORDER BY ia.transaction_date, ia.creation
	"""
	
	# Get all Payment Entries (debt payments)
	payment_conditions = conditions.replace("pe.party", "party").replace("pe.posting_date", "posting_date") if conditions else ""
	payments_query = f"""
		SELECT
			'Payment Entry' as transaction_type,
			name as document,
			'Payment Entry' as document_type,
			DATE(posting_date) as transaction_date,
			party as supplier,
			custom_supplier_contract as installment_application,
			NULL as item,
			paid_amount as amount,
			0 as debt_amount,
			creation,
			mode_of_payment,
			CASE 
				WHEN docstatus = 0 THEN 'Draft'
				WHEN docstatus = 1 THEN 'Submitted'
				WHEN docstatus = 2 THEN 'Cancelled'
			END as status,
			'USD' as currency
		FROM `tabPayment Entry`
		WHERE docstatus = 1
		AND party_type = 'Supplier'
		AND payment_type = 'Pay'
		{payment_conditions}
		ORDER BY posting_date, creation
	"""
	
	# Combine both queries
	installments = frappe.db.sql(installments_query, filters, as_dict=1)
	payments = frappe.db.sql(payments_query, filters, as_dict=1)
	
	# Merge and sort by date and creation
	all_transactions = installments + payments
	all_transactions.sort(key=lambda x: (x.transaction_date, x.creation))
	
	if not all_transactions:
		return []
	
	# Calculate running balance
	result_data = []
	supplier_running = {}
	
	for txn in all_transactions:
		supplier = txn.supplier
		txn_type = txn.transaction_type
		amount = flt(txn.amount)
		debt_amount = flt(txn.debt_amount)
		
		# Initialize supplier if not exists
		if supplier not in supplier_running:
			supplier_running[supplier] = {
				'total_debt': 0,
				'total_paid': 0
			}
		
		# Update running totals
		if txn_type == 'Installment Application':
			# This is a debt increase - use debt_amount
			supplier_running[supplier]['total_debt'] += debt_amount
		elif txn_type == 'Payment Entry':
			# This is a payment (debt decrease) - use amount
			supplier_running[supplier]['total_paid'] += amount
		
		# Calculate current outstanding
		debt = supplier_running[supplier]['total_debt']
		outstanding = debt - supplier_running[supplier]['total_paid']
		
		# Add calculated fields - use correct amount field
		txn['amount'] = amount if txn_type == 'Payment Entry' else 0
		txn['debt'] = debt
		txn['outstanding'] = outstanding
		
		result_data.append(txn)
	
	# Add TOTAL row at the end with separator
	if result_data:
		# Calculate totals by transaction type
		total_paid = sum([flt(d.get('amount', 0)) for d in result_data if d.get('transaction_type') == 'Payment Entry'])
		
		# Calculate total outstanding from all unique suppliers
		# Get last outstanding for each unique supplier
		supplier_outstanding = {}
		for txn in result_data:
			supplier = txn.get('supplier')
			if supplier:
				supplier_outstanding[supplier] = flt(txn.get('outstanding', 0))
		
		total_outstanding = sum(supplier_outstanding.values())
		
		result_data.append({
			'supplier': 'Total',
			'transaction_type': '',
			'document': '',
			'document_type': '',
			'installment_application': '',
			'transaction_date': '',
			'item': '',
			'amount': total_paid,
			'debt': None,  # Bo'sh qoladi (None = $0.00 ko'rsatmaydi)
			'outstanding': total_outstanding,
			'mode_of_payment': '',
			'status': '',
			'currency': 'USD',
			'is_total_row': 1
		})
	
	return result_data


def get_conditions(filters):
	"""Build WHERE conditions"""
	conditions = []
	
	if filters.get("supplier"):
		conditions.append("AND pe.party = %(supplier)s")
	
	if filters.get("from_date"):
		conditions.append("AND pe.posting_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("AND pe.posting_date <= %(to_date)s")
	
	return " ".join(conditions)


def get_summary(data):
	"""Generate summary cards"""
	if not data:
		return []
	
	# Remove total row for calculation
	data_without_total = [d for d in data if not d.get('is_total_row')]
	
	if not data_without_total:
		return []
	
	# Separate by transaction type
	debt_transactions = [d for d in data_without_total if d.get('transaction_type') == 'Installment Application']
	payment_transactions = [d for d in data_without_total if d.get('transaction_type') == 'Payment Entry']
	
	total_suppliers = len(set([d.get("supplier") for d in data_without_total]))
	total_debts = len(debt_transactions)
	total_payments = len(payment_transactions)
	
	total_debt_amount = sum([flt(d.get("debt_amount", 0)) for d in debt_transactions])
	total_payment_amount = sum([flt(d.get("amount", 0)) for d in payment_transactions])
	
	summary = [
		{
			"value": total_suppliers,
			"indicator": "blue",
			"label": _("Total Suppliers"),
			"datatype": "Int"
		},
		{
			"value": total_debts,
			"indicator": "orange",
			"label": _("Total Debts"),
			"datatype": "Int"
		},
		{
			"value": total_payments,
			"indicator": "blue",
			"label": _("Total Payments"),
			"datatype": "Int"
		},
		{
			"value": total_debt_amount,
			"indicator": "red",
			"label": _("Total Debt Amount"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_payment_amount,
			"indicator": "green",
			"label": _("Total Paid"),
			"datatype": "Currency",
			"currency": "USD"
		}
	]
	
	return summary