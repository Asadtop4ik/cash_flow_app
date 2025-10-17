# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, date_diff


def execute(filters=None):
	"""Execute Outstanding Installments Report"""
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data)
	chart = get_chart_data(data)
	
	return columns, data, None, chart, summary


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "customer",
			"label": _("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "customer_name",
			"label": _("Customer Name"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "sales_order",
			"label": _("Contract (SO)"),
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 150
		},
		{
			"fieldname": "transaction_date",
			"label": _("Contract Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "grand_total",
			"label": _("Total Amount (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 130
		},
		{
			"fieldname": "paid_amount",
			"label": _("Paid Amount (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 130
		},
		{
			"fieldname": "outstanding_amount",
			"label": _("Outstanding (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 130
		},
		{
			"fieldname": "next_payment_date",
			"label": _("Next Payment Date"),
			"fieldtype": "Date",
			"width": 120
		},
		{
			"fieldname": "next_payment_amount",
			"label": _("Next Payment (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 130
		},
		{
			"fieldname": "days_overdue",
			"label": _("Days Overdue"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "cost_center",
			"label": _("Cost Center"),
			"fieldtype": "Link",
			"options": "Cost Center",
			"width": 150
		}
	]


def get_data(filters):
	"""Get outstanding installments data"""
	conditions = get_conditions(filters)
	
	# Get sales orders with payment schedules
	query = f"""
		SELECT
			so.customer,
			so.customer_name,
			so.name as sales_order,
			so.transaction_date,
			IFNULL(so.custom_grand_total_with_interest, so.grand_total) as grand_total,
			IFNULL(so.advance_paid, 0) as paid_amount,
			(IFNULL(so.custom_grand_total_with_interest, so.grand_total) - IFNULL(so.advance_paid, 0)) as outstanding_amount,
			so.custom_next_payment_date as next_payment_date,
			IFNULL(so.custom_next_payment_amount, 0) as next_payment_amount,
			so.cost_center,
			so.status
		FROM
			`tabSales Order` so
		WHERE
			so.docstatus = 1
			AND so.status NOT IN ('Completed', 'Cancelled', 'Closed')
			AND (IFNULL(so.custom_grand_total_with_interest, so.grand_total) - IFNULL(so.advance_paid, 0)) > 0
			{conditions}
		ORDER BY
			so.transaction_date DESC
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Calculate days overdue and status
	for row in data:
		# Calculate days overdue
		if row.next_payment_date:
			days_diff = date_diff(today(), row.next_payment_date)
			row.days_overdue = days_diff if days_diff > 0 else 0
		else:
			row.days_overdue = 0
		
		# Determine status
		if row.days_overdue > 0:
			row.status = "Overdue"
		elif row.outstanding_amount > 0:
			row.status = "Active"
		else:
			row.status = "Completed"
	
	return data


def get_conditions(filters):
	"""Build SQL conditions from filters"""
	conditions = []
	
	if filters.get("customer"):
		conditions.append("so.customer = %(customer)s")
	
	if filters.get("from_date"):
		conditions.append("so.transaction_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("so.transaction_date <= %(to_date)s")
	
	if filters.get("cost_center"):
		conditions.append("so.cost_center = %(cost_center)s")
	
	if filters.get("status"):
		if filters.get("status") == "Overdue":
			# Will be filtered in Python after calculating days_overdue
			pass
		elif filters.get("status") == "Active":
			conditions.append("so.status NOT IN ('Completed', 'Cancelled', 'Closed')")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_summary(data):
	"""Calculate summary statistics"""
	if not data:
		return []
	
	total_outstanding = sum(flt(row.outstanding_amount) for row in data)
	total_overdue = sum(flt(row.outstanding_amount) for row in data if row.days_overdue > 0)
	active_contracts = len(data)
	overdue_contracts = len([row for row in data if row.days_overdue > 0])
	
	summary = [
		{
			"value": active_contracts,
			"indicator": "Blue",
			"label": _("Active Contracts"),
			"datatype": "Int"
		},
		{
			"value": total_outstanding,
			"indicator": "Orange",
			"label": _("Total Outstanding"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": overdue_contracts,
			"indicator": "Red",
			"label": _("Overdue Contracts"),
			"datatype": "Int"
		},
		{
			"value": total_overdue,
			"indicator": "Red",
			"label": _("Overdue Amount"),
			"datatype": "Currency",
			"currency": "USD"
		}
	]
	
	return summary


def get_chart_data(data):
	"""Generate chart data"""
	if not data:
		return None
	
	# Group by status
	status_wise = {"Active": 0, "Overdue": 0}
	
	for row in data:
		if row.status in status_wise:
			status_wise[row.status] += flt(row.outstanding_amount)
	
	return {
		"data": {
			"labels": list(status_wise.keys()),
			"datasets": [
				{
					"name": _("Outstanding Amount"),
					"values": list(status_wise.values())
				}
			]
		},
		"type": "pie",
		"colors": ["#17a2b8", "#dc3545"]
	}
