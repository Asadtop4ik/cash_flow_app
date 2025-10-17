# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, date_diff, add_months, get_first_day, get_last_day


def execute(filters=None):
	"""Execute Monthly Payment Schedule Report"""
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data)
	chart = get_chart_data(data)
	
	return columns, data, None, chart, summary


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "due_date",
			"label": _("Due Date"),
			"fieldtype": "Date",
			"width": 100
		},
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
			"fieldname": "payment_amount",
			"label": _("Payment Amount (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 150
		},
		{
			"fieldname": "paid_amount",
			"label": _("Paid Amount (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 140
		},
		{
			"fieldname": "outstanding",
			"label": _("Outstanding (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 140
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "days_to_due",
			"label": _("Days to Due"),
			"fieldtype": "Int",
			"width": 100
		},
		{
			"fieldname": "contact_mobile",
			"label": _("Phone"),
			"fieldtype": "Data",
			"width": 120
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
	"""Get payment schedule data"""
	# Set default month if not provided
	if not filters.get("month"):
		filters["month"] = today()
	
	# Get first and last day of selected month
	first_day = get_first_day(filters.get("month"))
	last_day = get_last_day(filters.get("month"))
	
	# Also include next month if show_next_month is checked
	if filters.get("show_next_month"):
		next_month = add_months(filters.get("month"), 1)
		last_day = get_last_day(next_month)
	
	conditions = get_conditions(filters)
	
	query = f"""
		SELECT
			ps.due_date,
			so.customer,
			so.customer_name,
			so.name as sales_order,
			ps.payment_amount,
			IFNULL(ps.paid_amount, 0) as paid_amount,
			(ps.payment_amount - IFNULL(ps.paid_amount, 0)) as outstanding,
			so.cost_center
		FROM
			`tabPayment Schedule` ps
		INNER JOIN
			`tabSales Order` so ON ps.parent = so.name
		WHERE
			ps.parenttype = 'Sales Order'
			AND so.docstatus = 1
			AND ps.due_date BETWEEN %(first_day)s AND %(last_day)s
			AND (ps.payment_amount - IFNULL(ps.paid_amount, 0)) > 0
			{conditions}
		ORDER BY
			ps.due_date, so.customer
	"""
	
	data = frappe.db.sql(query, {
		"first_day": first_day,
		"last_day": last_day,
		**filters
	}, as_dict=1)
	
	# Add status and days to due
	for row in data:
		# Calculate days to due
		days_diff = date_diff(row.due_date, today())
		row.days_to_due = days_diff
		
		# Determine status
		if flt(row.outstanding) == 0:
			row.status = "Paid"
		elif days_diff < 0:
			row.status = "Overdue"
		elif days_diff == 0:
			row.status = "Due Today"
		elif days_diff <= 7:
			row.status = "Due This Week"
		else:
			row.status = "Pending"
		
		# Get customer phone
		row.contact_mobile = get_customer_phone(row.customer)
	
	return data


def get_customer_phone(customer):
	"""Get customer mobile number"""
	phone = frappe.db.get_value("Customer", customer, "mobile_no")
	if not phone:
		# Try to get from primary contact
		contact = frappe.db.get_value(
			"Dynamic Link",
			{
				"link_doctype": "Customer",
				"link_name": customer,
				"parenttype": "Contact"
			},
			"parent"
		)
		if contact:
			phone = frappe.db.get_value("Contact", contact, "mobile_no")
	
	return phone or ""


def get_conditions(filters):
	"""Build SQL conditions from filters"""
	conditions = []
	
	if filters.get("customer"):
		conditions.append("so.customer = %(customer)s")
	
	if filters.get("cost_center"):
		conditions.append("so.cost_center = %(cost_center)s")
	
	if filters.get("status"):
		# Will be filtered in Python after calculating status
		pass
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_summary(data):
	"""Calculate summary statistics"""
	if not data:
		return []
	
	total_expected = sum(flt(row.payment_amount) for row in data)
	total_paid = sum(flt(row.paid_amount) for row in data)
	total_pending = sum(flt(row.outstanding) for row in data)
	overdue_amount = sum(flt(row.outstanding) for row in data if row.days_to_due < 0)
	
	summary = [
		{
			"value": total_expected,
			"indicator": "Blue",
			"label": _("Expected This Period"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_paid,
			"indicator": "Green",
			"label": _("Collected"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_pending,
			"indicator": "Orange",
			"label": _("Pending"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": overdue_amount,
			"indicator": "Red",
			"label": _("Overdue"),
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
	status_wise = {
		"Paid": 0,
		"Pending": 0,
		"Overdue": 0,
		"Due Today": 0,
		"Due This Week": 0
	}
	
	for row in data:
		if row.status in status_wise:
			status_wise[row.status] += flt(row.outstanding)
	
	# Remove zero values
	status_wise = {k: v for k, v in status_wise.items() if v > 0}
	
	return {
		"data": {
			"labels": list(status_wise.keys()),
			"datasets": [
				{
					"name": _("Amount"),
					"values": list(status_wise.values())
				}
			]
		},
		"type": "pie",
		"colors": ["#28a745", "#ffc107", "#dc3545", "#ff5722", "#ff9800"]
	}
