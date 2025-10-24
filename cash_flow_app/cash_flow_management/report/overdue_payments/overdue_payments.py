# Copyright (c) 2025, Cash Flow App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, today


def execute(filters=None):
	"""
	Overdue Payments Report
	Shows Installment Application link but uses Sales Order backend
	"""
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data)
	
	return columns, data, None, None, summary


def get_columns():
	"""Define report columns"""
	return [
		{
			"label": _("Customer"),
			"fieldname": "customer",
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"label": _("Contract"),
			"fieldname": "installment_application",
			"fieldtype": "Link",
			"options": "Installment Application",
			"width": 180
		},
		{
			"label": _("Sales Order"),
			"fieldname": "sales_order",
			"fieldtype": "Link",
			"options": "Sales Order",
			"width": 150
		},
		{
			"label": _("Due Date"),
			"fieldname": "due_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": _("Days Overdue"),
			"fieldname": "days_overdue",
			"fieldtype": "Int",
			"width": 100
		},
		{
			"label": _("Payment Amount"),
			"fieldname": "payment_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130
		},
		{
			"label": _("Outstanding"),
			"fieldname": "outstanding",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 130
		},
		{
			"label": _("Phone"),
			"fieldname": "phone",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 120
		}
	]


def get_data(filters):
	"""Get overdue payments - reads from Sales Order, links to Installment Application"""
	conditions = get_conditions(filters)
	
	# Query Sales Order Payment Schedule
	query = f"""
		SELECT
			so.customer,
			so.name as sales_order,
			ps.name as schedule_id,
			ps.due_date,
			ps.payment_amount,
			COALESCE(ps.paid_amount, 0) as paid_amount,
			(ps.payment_amount - COALESCE(ps.paid_amount, 0)) as outstanding,
			c.custom_phone_1 as phone,
			'USD' as currency,
			DATEDIFF(CURDATE(), ps.due_date) as days_overdue
		FROM `tabPayment Schedule` ps
		INNER JOIN `tabSales Order` so ON so.name = ps.parent
		LEFT JOIN `tabCustomer` c ON c.name = so.customer
		WHERE ps.parenttype = 'Sales Order'
			AND so.docstatus = 1
			AND ps.due_date < CURDATE()
			AND COALESCE(ps.paid_amount, 0) < ps.payment_amount
			{conditions}
		ORDER BY ps.due_date ASC, so.customer
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Add Installment Application link for each row
	for row in data:
		# Find Installment Application linked to this Sales Order
		inst_app = frappe.db.get_value("Installment Application",
			{"custom_sales_order": row.sales_order, "docstatus": 1},
			"name")
		
		row['installment_application'] = inst_app or row.sales_order
		
		# Add status
		paid = flt(row.paid_amount)
		payment_amount = flt(row.payment_amount)
		
		if paid > 0:
			row['status'] = 'Qisman to\'langan'
		else:
			row['status'] = 'To\'lanmagan'
	
	return data


def get_conditions(filters):
	"""Build WHERE conditions"""
	conditions = []
	
	if filters.get("customer"):
		conditions.append("AND so.customer = %(customer)s")
	
	if filters.get("from_date"):
		conditions.append("AND ps.due_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("AND ps.due_date <= %(to_date)s")
	
	if filters.get("min_days_overdue"):
		conditions.append("AND DATEDIFF(CURDATE(), ps.due_date) >= %(min_days_overdue)s")
	
	return " ".join(conditions)


def get_summary(data):
	"""Generate summary cards"""
	if not data:
		return []
	
	total_customers = len(set([d.get("customer") for d in data]))
	total_overdue_payments = len(data)
	total_outstanding = sum([flt(d.get("outstanding", 0)) for d in data])
	
	summary = [
		{
			"value": total_customers,
			"indicator": "red",
			"label": _("Customers with Overdue"),
			"datatype": "Int"
		},
		{
			"value": total_overdue_payments,
			"indicator": "red",
			"label": _("Total Overdue Payments"),
			"datatype": "Int"
		},
		{
			"value": total_outstanding,
			"indicator": "red",
			"label": _("Total Outstanding"),
			"datatype": "Currency",
			"currency": "USD"
		}
	]
	
	return summary