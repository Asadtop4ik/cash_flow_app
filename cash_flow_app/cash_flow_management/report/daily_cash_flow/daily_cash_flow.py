# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	"""Execute Daily Cash Flow Report"""
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	summary = get_summary(data)
	
	return columns, data, None, chart, summary


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "posting_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "name",
			"label": _("Document"),
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 150
		},
		{
			"fieldname": "payment_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "mode_of_payment",
			"label": _("Mode of Payment"),
			"fieldtype": "Link",
			"options": "Mode of Payment",
			"width": 120
		},
		{
			"fieldname": "counterparty_category",
			"label": _("Category"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "party",
			"label": _("Party"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "debit",
			"label": _("Chiqim (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 120
		},
		{
			"fieldname": "credit",
			"label": _("Kirim (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 120
		},
		{
			"fieldname": "remarks",
			"label": _("Remarks"),
			"fieldtype": "Data",
			"width": 200
		}
	]


def get_data(filters):
	"""Get payment entry data"""
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT
			pe.posting_date,
			pe.name,
			pe.payment_type,
			pe.mode_of_payment,
			pe.custom_counterparty_category as counterparty_category,
			CASE 
				WHEN pe.party_type = 'Customer' THEN pe.party_name
				WHEN pe.party_type = 'Supplier' THEN pe.party_name
				WHEN pe.party_type = 'Employee' THEN pe.party_name
				ELSE pe.paid_to
			END as party,
			CASE 
				WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
				ELSE 0
			END as debit,
			CASE 
				WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
				ELSE 0
			END as credit,
			pe.remarks
		FROM
			`tabPayment Entry` pe
		WHERE
			pe.docstatus = 1
			{conditions}
		ORDER BY
			pe.posting_date, pe.creation
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	return data


def get_conditions(filters):
	"""Build SQL conditions from filters"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("pe.posting_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("pe.posting_date <= %(to_date)s")
	
	if filters.get("mode_of_payment"):
		conditions.append("pe.mode_of_payment = %(mode_of_payment)s")
	
	if filters.get("counterparty_category"):
		conditions.append("pe.custom_counterparty_category = %(counterparty_category)s")
	
	if filters.get("payment_type"):
		conditions.append("pe.payment_type = %(payment_type)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart_data(data, filters):
	"""Generate chart data"""
	if not data:
		return None
	
	# Group by date
	date_wise = {}
	for row in data:
		date = str(row.posting_date)
		if date not in date_wise:
			date_wise[date] = {"credit": 0, "debit": 0}
		
		date_wise[date]["credit"] += flt(row.credit)
		date_wise[date]["debit"] += flt(row.debit)
	
	# Sort dates
	sorted_dates = sorted(date_wise.keys())
	
	return {
		"data": {
			"labels": sorted_dates,
			"datasets": [
				{
					"name": _("Kirim (Income)"),
					"values": [date_wise[d]["credit"] for d in sorted_dates]
				},
				{
					"name": _("Chiqim (Expense)"),
					"values": [date_wise[d]["debit"] for d in sorted_dates]
				}
			]
		},
		"type": "bar",
		"colors": ["#28a745", "#dc3545"]
	}


def get_summary(data):
	"""Calculate summary statistics"""
	if not data:
		return []
	
	total_credit = sum(flt(row.credit) for row in data)
	total_debit = sum(flt(row.debit) for row in data)
	net_balance = total_credit - total_debit
	
	# Group by mode of payment
	mode_wise = {}
	for row in data:
		mode = row.mode_of_payment or "Not Specified"
		if mode not in mode_wise:
			mode_wise[mode] = {"credit": 0, "debit": 0}
		mode_wise[mode]["credit"] += flt(row.credit)
		mode_wise[mode]["debit"] += flt(row.debit)
	
	summary = [
		{
			"value": total_credit,
			"indicator": "Green",
			"label": _("Total Kirim"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_debit,
			"indicator": "Red",
			"label": _("Total Chiqim"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": net_balance,
			"indicator": "Blue" if net_balance >= 0 else "Red",
			"label": _("Net Balance"),
			"datatype": "Currency",
			"currency": "USD"
		}
	]
	
	return summary
