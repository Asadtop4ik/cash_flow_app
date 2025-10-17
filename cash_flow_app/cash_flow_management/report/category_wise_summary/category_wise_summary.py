# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	"""Execute Category-wise Summary Report"""
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	summary = get_summary(data)
	
	return columns, data, None, chart, summary


def get_columns():
	"""Define report columns"""
	return [
		{
			"fieldname": "category",
			"label": _("Category"),
			"fieldtype": "Link",
			"options": "Counterparty Category",
			"width": 200
		},
		{
			"fieldname": "category_type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "transaction_count",
			"label": _("Transaction Count"),
			"fieldtype": "Int",
			"width": 130
		},
		{
			"fieldname": "total_amount",
			"label": _("Total Amount (USD)"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 150
		},
		{
			"fieldname": "percentage",
			"label": _("Percentage"),
			"fieldtype": "Percent",
			"width": 100
		},
		{
			"fieldname": "avg_transaction",
			"label": _("Avg per Transaction"),
			"fieldtype": "Currency",
			"options": "USD",
			"width": 150
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
	"""Get category-wise summary data"""
	conditions = get_conditions(filters)
	
	# Get category type filter if specified
	category_type_condition = ""
	if filters.get("category_type"):
		if filters.get("category_type") == "Income":
			category_type_condition = "AND pe.payment_type = 'Receive'"
		elif filters.get("category_type") == "Expense":
			category_type_condition = "AND pe.payment_type = 'Pay'"
	
	query = f"""
		SELECT
			pe.custom_counterparty_category as category,
			cc.category_type,
			COUNT(pe.name) as transaction_count,
			SUM(pe.paid_amount) as total_amount,
			pe.cost_center
		FROM
			`tabPayment Entry` pe
		LEFT JOIN
			`tabCounterparty Category` cc ON pe.custom_counterparty_category = cc.name
		WHERE
			pe.docstatus = 1
			{category_type_condition}
			{conditions}
		GROUP BY
			pe.custom_counterparty_category, pe.cost_center
		ORDER BY
			total_amount DESC
	"""
	
	data = frappe.db.sql(query, filters, as_dict=1)
	
	# Calculate total for percentage
	total_amount = sum(flt(row.total_amount) for row in data)
	
	# Add percentage and average
	for row in data:
		if total_amount > 0:
			row.percentage = (flt(row.total_amount) / total_amount) * 100
		else:
			row.percentage = 0
		
		if row.transaction_count > 0:
			row.avg_transaction = flt(row.total_amount) / row.transaction_count
		else:
			row.avg_transaction = 0
		
		# Set default category type if missing
		if not row.category_type and row.category:
			category_doc = frappe.get_cached_doc("Counterparty Category", row.category)
			row.category_type = category_doc.category_type if category_doc else "Unknown"
	
	return data


def get_conditions(filters):
	"""Build SQL conditions from filters"""
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("pe.posting_date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("pe.posting_date <= %(to_date)s")
	
	if filters.get("cost_center"):
		conditions.append("pe.cost_center = %(cost_center)s")
	
	if filters.get("branch"):
		conditions.append("pe.custom_branch = %(branch)s")
	
	if filters.get("category"):
		conditions.append("pe.custom_counterparty_category = %(category)s")
	
	return " AND " + " AND ".join(conditions) if conditions else ""


def get_summary(data):
	"""Calculate summary statistics"""
	if not data:
		return []
	
	# Calculate totals by type
	income_total = sum(flt(row.total_amount) for row in data if row.category_type == "Income")
	expense_total = sum(flt(row.total_amount) for row in data if row.category_type == "Expense")
	net_profit = income_total - expense_total
	
	total_transactions = sum(row.transaction_count for row in data)
	
	summary = [
		{
			"value": income_total,
			"indicator": "Green",
			"label": _("Total Income"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": expense_total,
			"indicator": "Red",
			"label": _("Total Expense"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": net_profit,
			"indicator": "Blue" if net_profit >= 0 else "Red",
			"label": _("Net Profit/Loss"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_transactions,
			"indicator": "Gray",
			"label": _("Total Transactions"),
			"datatype": "Int"
		}
	]
	
	return summary


def get_chart_data(data, filters):
	"""Generate chart data"""
	if not data:
		return None
	
	# Determine chart type based on filter
	category_type = filters.get("category_type")
	
	if category_type and category_type != "Both":
		# Show only one type - use pie chart
		categories = [row.category for row in data[:10]]  # Top 10
		amounts = [flt(row.total_amount) for row in data[:10]]
		
		return {
			"data": {
				"labels": categories,
				"datasets": [
					{
						"name": _("Amount"),
						"values": amounts
					}
				]
			},
			"type": "pie"
		}
	else:
		# Show both types - use bar chart grouped by type
		income_data = [row for row in data if row.category_type == "Income"]
		expense_data = [row for row in data if row.category_type == "Expense"]
		
		# Get top categories
		all_categories = list(set([row.category for row in data[:10]]))
		
		income_amounts = []
		expense_amounts = []
		
		for cat in all_categories:
			income_amt = sum(flt(row.total_amount) for row in income_data if row.category == cat)
			expense_amt = sum(flt(row.total_amount) for row in expense_data if row.category == cat)
			income_amounts.append(income_amt)
			expense_amounts.append(expense_amt)
		
		return {
			"data": {
				"labels": all_categories,
				"datasets": [
					{
						"name": _("Income"),
						"values": income_amounts
					},
					{
						"name": _("Expense"),
						"values": expense_amounts
					}
				]
			},
			"type": "bar",
			"colors": ["#28a745", "#dc3545"]
		}
