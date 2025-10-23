# Copyright (c) 2025, Cash Flow App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	"""
	Customer Payment History Report
	Shows each payment transaction with contract details
	"""
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data)
	
	chart = None
	
	# Disable automatic totals by NOT adding 'total_row' indicator
	# Our custom Total row already included in data
	return columns, data, None, chart, summary, None


def get_columns():
	"""Define report columns - har bir tranzaksiya alohida"""
	return [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"label": _("Payment Entry"),
			"fieldname": "payment_entry",
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 140
		},
		{
			"label": _("Payment Date"),
			"fieldname": "payment_date",
			"fieldtype": "Date",
			"width": 110
		},
		{
			"label": _("Payment Amount"),
			"fieldname": "payment_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130
		},
		{
			"label": _("Contract (Shartnoma)"),
			"fieldname": "contract",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 150
		},
		{
			"label": _("Contract Total"),
			"fieldname": "contract_total",
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
			"width": 130
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
	Get payment data with contract information
	Har bir to'lov uchun o'sha paytdagi contract holatini hisoblash
	"""
	conditions = get_conditions(filters)
	
	# Get all payment entries
	query = """
		SELECT
			pe.name as payment_entry,
			pe.party as customer,
			pe.posting_date as payment_date,
			pe.paid_amount as payment_amount,
			pe.mode_of_payment,
			pe.creation,
			pe.custom_contract_reference as contract,
			CASE 
				WHEN pe.docstatus = 0 THEN 'Draft'
				WHEN pe.docstatus = 1 THEN 'Submitted'
				WHEN pe.docstatus = 2 THEN 'Cancelled'
			END as status,
			'USD' as currency
		FROM `tabPayment Entry` pe
		WHERE pe.docstatus = 1
		AND pe.party_type = 'Customer'
		AND pe.payment_type = 'Receive'
		{conditions}
		ORDER BY pe.party, pe.posting_date, pe.creation
	""".format(conditions=conditions)
	
	payments = frappe.db.sql(query, filters, as_dict=1)
	
	if not payments:
		return []
	
	# Get contract totals (from Sales Order)
	contract_data = {}
	unique_contracts = set([p.contract for p in payments if p.contract])
	
	for contract in unique_contracts:
		so = frappe.db.get_value('Sales Order', contract,
			['custom_grand_total_with_interest', 'grand_total'], as_dict=1)
		if so:
			contract_data[contract] = {
				'total': flt(so.custom_grand_total_with_interest or so.grand_total)
			}
	
	# Calculate running outstanding for each payment
	result_data = []
	contract_paid_running = {}
	
	for payment in payments:
		contract = payment.contract
		payment_amount = flt(payment.payment_amount)
		
		if contract:
			# Initialize if not exists
			if contract not in contract_paid_running:
				contract_paid_running[contract] = 0
			
			# Add this payment to running total
			contract_paid_running[contract] += payment_amount
			
			# Get contract total
			contract_total = contract_data.get(contract, {}).get('total', 0)
			
			# Calculate outstanding AFTER this payment
			outstanding = contract_total - contract_paid_running[contract]
			
			payment['contract_total'] = contract_total
			payment['outstanding'] = outstanding
		else:
			payment['contract_total'] = 0
			payment['outstanding'] = 0
		
		result_data.append(payment)
	
	# Add TOTAL row
	if result_data:
		total_payment = sum([flt(d.get('payment_amount', 0)) for d in result_data])
		
		# Calculate total outstanding from all unique contracts
		# Get last outstanding for each unique contract
		contract_outstanding = {}
		for payment in result_data:
			contract = payment.get('contract')
			if contract:
				contract_outstanding[contract] = flt(payment.get('outstanding', 0))
		
		total_outstanding = sum(contract_outstanding.values())
		
		result_data.append({
			'customer': 'Total',
			'payment_entry': '',
			'payment_date': '',
			'payment_amount': total_payment,
			'contract': '',
			'contract_total': None,  # Bo'sh qoladi (None = $0.00 ko'rsatmaydi)
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
	
	if filters.get("customer"):
		conditions.append("AND pe.party = %(customer)s")
	
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
	data_without_total = [d for d in data if d.get('customer') != 'Total']
	
	if not data_without_total:
		return []
	
	total_customers = len(set([d.get("customer") for d in data_without_total]))
	total_payments = len(data_without_total)
	total_payment_amount = sum([flt(d.get("payment_amount", 0)) for d in data_without_total])
	
	# Get unique contracts
	contracts = set([d.get("contract") for d in data_without_total if d.get("contract")])
	total_contracts = len(contracts)
	
	
	summary = [
		{
			"value": total_customers,
			"indicator": "blue",
			"label": _("Total Customers"),
			"datatype": "Int"
		},
		{
			"value": total_payments,
			"indicator": "blue",
			"label": _("Total Payments"),
			"datatype": "Int"
		},
		{
			"value": total_contracts,
			"indicator": "grey",
			"label": _("Total Contracts"),
			"datatype": "Int"
		},
		{
			"value": total_payment_amount,
			"indicator": "green",
			"label": _("Total Received"),
			"datatype": "Currency",
			"currency": "USD"
		}
	]
	
	return summary