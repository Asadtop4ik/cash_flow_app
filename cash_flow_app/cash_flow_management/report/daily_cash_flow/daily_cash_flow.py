# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


# ============================================================
# ✅ MAIN EXECUTE
# ============================================================

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart_data(data)
	summary = get_summary(data, filters)

	return columns, data, None, chart, summary

import frappe
from frappe import _
from frappe.utils import flt


# ============================================================
# ✅ COLUMNS
# ============================================================

def get_columns():
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
		}
	]


# ============================================================
# ✅ DATA LOADING
# ============================================================

def get_data(filters):
	conditions = get_conditions(filters)

	# ✅ cash_account parametrini qo'shish
	cash_account = filters.get("cash_account")

	query = f"""
		SELECT
			pe.posting_date,
			pe.name,
			pe.payment_type,
			pe.mode_of_payment,
			pe.custom_counterparty_category AS counterparty_category,
			CASE
				WHEN pe.party_type IN ('Customer', 'Supplier', 'Employee') THEN pe.party_name
				WHEN pe.payment_type = 'Internal Transfer' THEN
					CASE
						WHEN pe.paid_to = %(cash_account)s THEN CONCAT('From: ', pe.paid_from)
						WHEN pe.paid_from = %(cash_account)s THEN CONCAT('To: ', pe.paid_to)
						ELSE pe.paid_to
					END
				ELSE pe.paid_to
			END AS party,

			CASE
				WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
				WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_from = %(cash_account)s THEN pe.paid_amount
				ELSE 0
			END AS debit,

			CASE
				WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
				WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_to = %(cash_account)s THEN pe.received_amount
				ELSE 0
			END AS credit

		FROM `tabPayment Entry` pe
		WHERE pe.docstatus = 1
		{conditions}
		ORDER BY pe.posting_date, pe.creation
	"""

	# ✅ cash_account parametrini filters'ga qo'shish
	query_filters = dict(filters)
	if not query_filters.get('cash_account'):
		query_filters['cash_account'] = ''

	return frappe.db.sql(query, query_filters, as_dict=1)

# ============================================================
# ✅ CONDITIONS
# ============================================================

def get_conditions(filters):
	conditions = []

	if filters.get("from_date"):
		conditions.append("pe.posting_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("pe.posting_date <= %(to_date)s")

	# ✅ Yangi filter ( CASH REGISTER)
	if filters.get("cash_account"):
		conditions.append("(pe.paid_from = %(cash_account)s OR pe.paid_to = %(cash_account)s)")

	if filters.get("counterparty_category"):
		conditions.append("pe.custom_counterparty_category = %(counterparty_category)s")

	if filters.get("payment_type"):
		conditions.append("pe.payment_type = %(payment_type)s")

	return " AND " + " AND ".join(conditions) if conditions else ""


# ============================================================
# ✅ CHART DATA
# ============================================================

def get_chart_data(data):
	if not data:
		return None

	date_map = {}

	for row in data:
		date = str(row.posting_date)

		if date not in date_map:
			date_map[date] = {"credit": 0, "debit": 0}

		date_map[date]["credit"] += flt(row.credit)
		date_map[date]["debit"] += flt(row.debit)

	dates = sorted(date_map.keys())

	return {
		"type": "bar",
		"data": {
			"labels": dates,
			"datasets": [
				{"name": _("Kirim (Income)"), "values": [date_map[d]["credit"] for d in dates]},
				{"name": _("Chiqim (Expense)"), "values": [date_map[d]["debit"] for d in dates]},
			]
		},
		"colors": ["#28a745", "#dc3545"]
	}


# ============================================================
# ✅ SUMMARY (HECH NIMA O‘ZGARMAYDI)
# ============================================================

def get_summary(data, filters=None):
	if not data:
		return []

	total_credit = sum(flt(x.credit) for x in data)
	total_debit = sum(flt(x.debit) for x in data)
	net_balance = total_credit - total_debit

	summary = [
		{
			"value": 0,
			"indicator": "Blue",
			"label": _("Opening Balance"),
			"datatype": "Currency",
			"currency": "USD"
		},
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
