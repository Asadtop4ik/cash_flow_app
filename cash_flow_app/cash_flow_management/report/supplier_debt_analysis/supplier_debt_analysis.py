# Copyright (c) 2025, Cash Flow App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	"""
	Supplier Debt Analysis Report
	Shows all payments to suppliers with detailed breakdown
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
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 180
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
			"label": _("Total Debt"),
			"fieldname": "total_debt",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Total Paid"),
			"fieldname": "total_paid",
			"fieldtype": "Data",
			"width": 120
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
	"""Get supplier payment data - Each payment entry as a separate row"""
	conditions = get_conditions(filters)
	
	# Query to get all payment entries to suppliers
	query = """
		SELECT
			pe.name as payment_entry,
			pe.party as supplier,
			pe.posting_date as payment_date,
			pe.paid_amount as payment_amount,
			pe.mode_of_payment,
			CASE 
				WHEN pe.docstatus = 0 THEN 'Draft'
				WHEN pe.docstatus = 1 THEN 'Submitted'
				WHEN pe.docstatus = 2 THEN 'Cancelled'
			END as status,
			CONCAT('$ ', FORMAT(s.custom_total_debt, 2)) as total_debt,
			CONCAT('$ ', FORMAT(s.custom_paid_amount, 2)) as total_paid,
			CONCAT('$ ', FORMAT(s.custom_remaining_debt, 2)) as outstanding,
			'USD' as currency
		FROM `tabPayment Entry` pe
		LEFT JOIN `tabSupplier` s ON s.name = pe.party
		WHERE pe.docstatus = 1
		AND pe.party_type = 'Supplier'
		AND pe.payment_type = 'Pay'
		{conditions}
		ORDER BY pe.posting_date DESC, pe.party, pe.name
	""".format(conditions=conditions)
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""Build WHERE conditions"""
	conditions = []
	
	if filters.get("supplier"):
		conditions.append("AND pe.party = %(supplier)s")
	
	if filters.get("from_date"):
		conditions.append("AND pe.posting_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("AND pe.posting_date <= %(to_date)s")
	
	# Debt status filter removed - showing all payments
	
	return " ".join(conditions)


def get_summary(data):
	"""Generate summary cards"""
	if not data:
		return []
	
	total_suppliers = len(set([d.get("supplier") for d in data]))
	total_payments = len(data)
	total_payment_amount = sum([flt(d.get("payment_amount", 0)) for d in data])
	
	# Calculate average payment
	avg_payment = total_payment_amount / total_payments if total_payments > 0 else 0
	
	summary = [
		{
			"value": total_suppliers,
			"indicator": "blue",
			"label": _("Total Suppliers"),
			"datatype": "Int"
		},
		{
			"value": total_payments,
			"indicator": "blue",
			"label": _("Total Payments"),
			"datatype": "Int"
		},
		{
			"value": total_payment_amount,
			"indicator": "green",
			"label": _("Total Paid"),
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
	"""Generate chart for payments by supplier"""
	if not data:
		return None
	
	# Group payments by supplier
	supplier_payments = {}
	for row in data:
		supplier = row.get("supplier")
		amount = flt(row.get("payment_amount", 0))
		if supplier:
			supplier_payments[supplier] = supplier_payments.get(supplier, 0) + amount
	
	# Get top 10 suppliers by payment amount
	sorted_suppliers = sorted(supplier_payments.items(), key=lambda x: x[1], reverse=True)[:10]
	
	if not sorted_suppliers:
		return None
	
	chart = {
		"data": {
			"labels": [s[0] for s in sorted_suppliers],
			"datasets": [
				{
					"name": "Total Payments",
					"values": [s[1] for s in sorted_suppliers]
				}
			]
		},
		"type": "bar",
		"colors": ["#dc2626"],
		"height": 280
	}
	
	return chart
