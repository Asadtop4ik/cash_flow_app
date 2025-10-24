# Copyright (c) 2025, Cash Flow App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_first_day, get_last_day
from datetime import datetime


def execute(filters=None):
	"""
	Monthly Expected Payments Report
	Shows Installment Application link but uses Sales Order backend
	"""
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data)
	chart = get_chart_data(data)
	
	return columns, data, None, chart, summary


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
			"label": _("Payment Status"),
			"fieldname": "payment_status",
			"fieldtype": "Data",
			"width": 130
		},
		{
			"label": _("Contract Status"),
			"fieldname": "contract_status",
			"fieldtype": "Data",
			"width": 100
		}
	]


def get_data(filters):
	"""Get scheduled payments for selected month"""
	
	# Get month range
	if filters.get("month"):
		year_month = filters.get("month")
		date_obj = datetime.strptime(year_month + "-01", "%Y-%m-%d")
		from_date = get_first_day(date_obj)
		to_date = get_last_day(date_obj)
	else:
		from_date = get_first_day(getdate())
		to_date = get_last_day(getdate())
	
	conditions = get_conditions(filters)
	
	# Query Sales Order Payment Schedule
	query = f"""
		SELECT
			so.customer,
			so.name as sales_order,
			so.status as contract_status,
			ps.due_date,
			ps.payment_amount,
			COALESCE(ps.paid_amount, 0) as paid_amount,
			(ps.payment_amount - COALESCE(ps.paid_amount, 0)) as outstanding,
			c.custom_phone_1 as phone,
			'USD' as currency
		FROM `tabPayment Schedule` ps
		INNER JOIN `tabSales Order` so ON so.name = ps.parent
		LEFT JOIN `tabCustomer` c ON c.name = so.customer
		WHERE ps.parenttype = 'Sales Order'
			AND so.docstatus = 1
			AND ps.due_date >= %(from_date)s
			AND ps.due_date <= %(to_date)s
			{conditions}
		ORDER BY ps.due_date ASC, so.customer
	"""
	
	data = frappe.db.sql(query, {
		'from_date': from_date,
		'to_date': to_date,
		**filters
	}, as_dict=1)
	
	# Add Installment Application link and payment status
	today_date = getdate()
	for row in data:
		# Find Installment Application
		inst_app = frappe.db.get_value("Installment Application",
			{"custom_sales_order": row.sales_order, "docstatus": 1},
			"name")
		
		row['installment_application'] = inst_app or row.sales_order
		
		# Calculate payment status
		paid = flt(row.paid_amount)
		payment_amount = flt(row.payment_amount)
		due_date = getdate(row.due_date)
		
		if paid >= payment_amount:
			row['payment_status'] = 'To\'landi'
		elif paid > 0:
			row['payment_status'] = 'Qisman to\'langan'
		elif due_date < today_date:
			row['payment_status'] = 'Muddati o\'tgan'
		else:
			row['payment_status'] = 'Kutilmoqda'
	
	return data


def get_conditions(filters):
	"""Build WHERE conditions"""
	conditions = []
	
	if filters.get("customer"):
		conditions.append("AND so.customer = %(customer)s")
	
	if filters.get("payment_status"):
		status = filters.get("payment_status")
		if status == "Paid":
			conditions.append("AND COALESCE(ps.paid_amount, 0) >= ps.payment_amount")
		elif status == "Partially Paid":
			conditions.append("AND COALESCE(ps.paid_amount, 0) > 0 AND COALESCE(ps.paid_amount, 0) < ps.payment_amount")
		elif status == "Unpaid":
			conditions.append("AND COALESCE(ps.paid_amount, 0) = 0")
		elif status == "Overdue":
			conditions.append("AND ps.due_date < CURDATE() AND COALESCE(ps.paid_amount, 0) < ps.payment_amount")
	
	return " ".join(conditions)


def get_summary(data):
	"""Generate summary cards"""
	if not data:
		return []
	
	total_customers = len(set([d.get("customer") for d in data]))
	total_expected = sum([flt(d.get("payment_amount", 0)) for d in data])
	total_received = sum([flt(d.get("paid_amount", 0)) for d in data])
	total_outstanding = sum([flt(d.get("outstanding", 0)) for d in data])
	
	collection_rate = (total_received / total_expected * 100) if total_expected > 0 else 0
	
	summary = [
		{
			"value": total_customers,
			"indicator": "blue",
			"label": _("Total Customers"),
			"datatype": "Int"
		},
		{
			"value": total_expected,
			"indicator": "blue",
			"label": _("Expected Amount"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_received,
			"indicator": "green",
			"label": _("Received Amount"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_outstanding,
			"indicator": "orange",
			"label": _("Outstanding"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": collection_rate,
			"indicator": "green" if collection_rate >= 80 else "orange",
			"label": _("Collection Rate (%)"),
			"datatype": "Percent"
		}
	]
	
	return summary


def get_chart_data(data):
	"""Generate chart showing payment status breakdown"""
	if not data:
		return None
	
	status_totals = {}
	for row in data:
		status = row.get("payment_status")
		amount = flt(row.get("payment_amount", 0))
		
		if status in status_totals:
			status_totals[status] += amount
		else:
			status_totals[status] = amount
	
	sorted_statuses = sorted(status_totals.items(), key=lambda x: x[1], reverse=True)
	
	chart = {
		"data": {
			"labels": [s[0] for s in sorted_statuses],
			"datasets": [
				{
					"name": "Amount",
					"values": [s[1] for s in sorted_statuses]
				}
			]
		},
		"type": "donut",
		"colors": ["#22c55e", "#f59e0b", "#ef4444", "#3b82f6"],
		"height": 280
	}
	
	return chart