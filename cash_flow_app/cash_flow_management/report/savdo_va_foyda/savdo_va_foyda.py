# Copyright (c) 2024, Ruxshona and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	"""Report ustunlarini belgilash"""
	columns = [
		{
			"fieldname": "name",
			"label": _("Shartnoma ID"),
			"fieldtype": "Link",
			"options": "Installment Application",
			"width": 150
		},
		{
			"fieldname": "customer",
			"label": _("Mijoz"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 200
		},
		{
			"fieldname": "contract_amount",
			"label": _("Shartnoma Summasi"),
			"fieldtype": "Currency",
			"width": 160
		},
		{
			"fieldname": "cost_price",
			"label": _("Tavar Tannarxi"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "initial_payment",
			"label": _("Boshlang'ich To'lov"),
			"fieldtype": "Currency",
			"width": 160
		},
		{
			"fieldname": "net_profit",
			"label": _("Sof Foyda"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "remaining_amount",
			"label": _("Tannarx"),
			"fieldtype": "Currency",
			"width": 150
		}
	]

	return columns


def get_data(filters):
	"""Ma'lumotlarni olish"""

	# Conditions va values tayyorlash
	conditions = []
	values = {}

	# Date range filter
	if filters.get("from_date"):
		conditions.append("ia.transaction_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")

	if filters.get("to_date"):
		conditions.append("ia.transaction_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	# Shartnoma ID filter
	if filters.get("installment_application"):
		conditions.append("ia.name = %(installment_application)s")
		values["installment_application"] = filters.get("installment_application")

	# Customer filter
	if filters.get("customer"):
		conditions.append("ia.customer = %(customer)s")
		values["customer"] = filters.get("customer")

	# WHERE clause yaratish
	where_clause = ""
	if conditions:
		where_clause = "WHERE " + " AND ".join(conditions)

	# SQL query
	query = """
		SELECT
			ia.name,
			ia.customer,
			COALESCE(ia.custom_grand_total_with_interest, 0) as contract_amount,
			COALESCE(ia.total_amount, 0) as cost_price,
			COALESCE(ia.downpayment_amount, 0) as initial_payment,
			(COALESCE(ia.custom_grand_total_with_interest, 0) - COALESCE(ia.downpayment_amount, 0)) as net_profit,
			(COALESCE(ia.total_amount, 0) - COALESCE(ia.downpayment_amount, 0)) as remaining_amount
		FROM
			`tabInstallment Application` ia
		{where_clause}
		ORDER BY
			ia.transaction_date DESC, ia.name DESC
	""".format(where_clause=where_clause)

	data = frappe.db.sql(query, values=values, as_dict=1)

	return data
