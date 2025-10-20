# Copyright (c) 2025, Cash Flow App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	"""
	Customer Payment History Report
	Shows all payments for customers with detailed breakdown
	"""
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data)
	
	# No chart needed - table is sufficient
	chart = None
	
	return columns, data, None, chart, summary


def get_columns():
	"""Define report columns - Each payment entry as a separate row"""
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
			"options": "Installment Application",
			"width": 150
		},
		{
			"label": _("Contract Total"),
			"fieldname": "contract_total",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Total Paid (Contract)"),
			"fieldname": "total_paid",
			"fieldtype": "Data",
			"width": 140
		},
		{
			"label": _("Outstanding"),
			"fieldname": "outstanding",
			"fieldtype": "Data",
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
	"""Get report data - Each payment entry as a separate row"""
	conditions = get_conditions(filters)
	
	# Query to get all payment entries with Installment Application details
	query = """
		SELECT
			pe.name as payment_entry,
			pe.party as customer,
			pe.posting_date as payment_date,
			pe.paid_amount as payment_amount,
			pe.mode_of_payment,
			CASE 
				WHEN pe.docstatus = 0 THEN 'Draft'
				WHEN pe.docstatus = 1 THEN 'Submitted'
				WHEN pe.docstatus = 2 THEN 'Cancelled'
			END as status,
			ia.name as contract,
			CONCAT('$ ', FORMAT(ia.custom_grand_total_with_interest, 2)) as contract_total,
			CONCAT('$ ', FORMAT(so.advance_paid, 2)) as total_paid,
			CONCAT('$ ', FORMAT(ia.custom_grand_total_with_interest - COALESCE(so.advance_paid, 0), 2)) as outstanding,
			'USD' as currency
		FROM `tabPayment Entry` pe
		LEFT JOIN `tabSales Order` so ON so.name = pe.custom_contract_reference
		LEFT JOIN `tabInstallment Application` ia ON ia.sales_order = so.name
		WHERE pe.docstatus = 1
		AND pe.party_type = 'Customer'
		AND pe.payment_type = 'Receive'
		{conditions}
		ORDER BY pe.posting_date DESC, pe.party, pe.name
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""Build WHERE conditions based on filters"""
	conditions = []
	
	if filters.get("customer"):
		conditions.append("AND pe.party = %(customer)s")
	
	if filters.get("from_date"):
		conditions.append("AND pe.posting_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("AND pe.posting_date <= %(to_date)s")
	
	if filters.get("contract_status"):
		conditions.append("AND so.status = %(contract_status)s")
	
	if filters.get("payment_status"):
		payment_status = filters.get("payment_status")
		if payment_status == "Fully Paid":
			conditions.append("AND COALESCE(so.advance_paid, 0) >= so.grand_total")
		elif payment_status == "Partially Paid":
			conditions.append("AND COALESCE(so.advance_paid, 0) > 0 AND COALESCE(so.advance_paid, 0) < so.grand_total")
		elif payment_status == "Pending":
			conditions.append("AND COALESCE(so.advance_paid, 0) = 0")
		elif payment_status == "Overdue":
			conditions.append("""
				AND EXISTS (
					SELECT 1 FROM `tabPayment Schedule` ps 
					WHERE ps.parent = so.name 
					AND ps.due_date < CURDATE() 
					AND COALESCE(ps.paid_amount, 0) < ps.payment_amount
				)
			""")
	
	return " ".join(conditions)


def get_summary(data):
	"""Generate summary cards for the top of the report"""
	if not data:
		return []
	
	total_customers = len(set([d.get("customer") for d in data]))
	total_payments = len(data)
	total_payment_amount = sum([flt(d.get("payment_amount", 0)) for d in data])
	
	# Get unique contracts
	contracts = set([d.get("contract") for d in data if d.get("contract")])
	total_contracts = len(contracts)
	
	# Calculate average payment
	avg_payment = total_payment_amount / total_payments if total_payments > 0 else 0
	
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
		},
		{
			"value": avg_payment,
			"indicator": "orange",
			"label": _("Average Payment"),
			"datatype": "Currency",
			"currency": "USD"
		}
	]
	
	return summary


def get_chart_data(data):
	"""Generate chart for payments by customer"""
	if not data:
		return None
	
	# Group payments by customer
	customer_payments = {}
	for row in data:
		customer = row.get("customer")
		amount = flt(row.get("payment_amount", 0))
		if customer:
			customer_payments[customer] = customer_payments.get(customer, 0) + amount
	
	# Get top 10 customers by payment amount
	sorted_customers = sorted(customer_payments.items(), key=lambda x: x[1], reverse=True)[:10]
	
	if not sorted_customers:
		return None
	
	chart = {
		"data": {
			"labels": [c[0] for c in sorted_customers],
			"datasets": [
				{
					"name": "Total Payments",
					"values": [c[1] for c in sorted_customers]
				}
			]
		},
		"type": "bar",
		"colors": ["#2563eb"],
		"height": 280
	}
	
	return chart
