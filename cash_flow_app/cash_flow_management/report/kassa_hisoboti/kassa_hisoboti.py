# Kassa Hisoboti Report

import frappe
from frappe import _
from frappe.utils import flt


# ============================================================
# ✅ MAIN EXECUTE
# ============================================================

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data, filters)

	return columns, data, None, None, summary


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
		},
		{
			"fieldname": "cash_account",
			"label": _("Cash"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 150
		}
	]


# ============================================================
# ✅ DATA LOADING
# ============================================================

def get_data(filters):
	conditions = get_conditions(filters)
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
			END AS credit,

			CASE
				WHEN pe.payment_type = 'Receive' THEN pe.paid_to
				WHEN pe.payment_type = 'Pay' THEN pe.paid_from
				WHEN pe.payment_type = 'Internal Transfer' THEN
					CASE
						WHEN pe.paid_to = %(cash_account)s THEN pe.paid_to
						WHEN pe.paid_from = %(cash_account)s THEN pe.paid_from
						ELSE pe.paid_to
					END
				ELSE pe.paid_to
			END AS cash_account,

			pe.paid_from,
			pe.paid_to,
			pe.paid_amount,
			pe.received_amount

		FROM `tabPayment Entry` pe
		WHERE pe.docstatus = 1
		{conditions}
		ORDER BY pe.posting_date, pe.creation
	"""

	query_filters = dict(filters)
	if not query_filters.get('cash_account'):
		query_filters['cash_account'] = ''

	data = frappe.db.sql(query, query_filters, as_dict=1)

	# Agar cash_account filtri bo'sh bo'lsa, Internal Transfer lar uchun
	# ikkita alohida qator yaratish kerak
	if not cash_account:
		expanded_data = []
		for row in data:
			if row.get('payment_type') == 'Internal Transfer':
				# 1. Paid From uchun qator (chiqim)
				from_row = row.copy()
				from_row['party'] = f"To: {row.get('paid_to')}"
				from_row['debit'] = row.get('paid_amount', 0)
				from_row['credit'] = 0
				from_row['cash_account'] = row.get('paid_from')
				expanded_data.append(from_row)

				# 2. Paid To uchun qator (kirim)
				to_row = row.copy()
				to_row['party'] = f"From: {row.get('paid_from')}"
				to_row['debit'] = 0
				to_row['credit'] = row.get('received_amount', 0)
				to_row['cash_account'] = row.get('paid_to')
				expanded_data.append(to_row)
			else:
				expanded_data.append(row)

		return expanded_data

	return data


# ============================================================
# ✅ CONDITIONS
# ============================================================

def get_conditions(filters):
	conditions = []

	if filters.get("from_date"):
		conditions.append("pe.posting_date >= %(from_date)s")

	if filters.get("to_date"):
		conditions.append("pe.posting_date <= %(to_date)s")

	if filters.get("cash_account"):
		conditions.append("(pe.paid_from = %(cash_account)s OR pe.paid_to = %(cash_account)s)")

	if filters.get("counterparty_category"):
		conditions.append("pe.custom_counterparty_category = %(counterparty_category)s")

	if filters.get("payment_type"):
		conditions.append("pe.payment_type = %(payment_type)s")

	return " AND " + " AND ".join(conditions) if conditions else ""


# ============================================================
# ✅ SUMMARY
# ============================================================

def get_summary(data, filters=None):
	"""Summary boxes - Opening Balance, Total Kirim, Total Chiqim, Net Balance"""

	if not filters:
		return []

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	cash_account = filters.get("cash_account")

	# ✅ 1. Opening Balance (from_date dan oldingi)
	opening_balance = get_opening_balance(from_date, cash_account)

	# ✅ 2. Total Kirim va Chiqim (hozirgi data dan)
	total_kirim = sum(flt(x.get('credit', 0)) for x in data) if data else 0.0
	total_chiqim = sum(flt(x.get('debit', 0)) for x in data) if data else 0.0

	# ✅ 3. Net Balance (to_date gacha barcha)
	net_balance = get_net_balance(to_date, cash_account)

	summary = [
		{
			"value": opening_balance,
			"indicator": "Blue",
			"label": _("Opening Balance"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_kirim,
			"indicator": "Green",
			"label": _("Total Kirim"),
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_chiqim,
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


# ============================================================
# ✅ OPENING BALANCE - from_date dan oldingi
# ============================================================

def get_opening_balance(from_date, cash_account=None):
	"""from_date dan oldingi barcha kirim - chiqim"""

	if not from_date:
		return 0.0

	conditions = ["pe.docstatus = 1"]
	params = {"from_date": from_date, "cash_account": cash_account}

	conditions.append("pe.posting_date < %(from_date)s")

	if cash_account:
		conditions.append("(pe.paid_from = %(cash_account)s OR pe.paid_to = %(cash_account)s)")

	where_clause = " AND ".join(conditions)

	# Internal Transfer logic faqat cash_account berilgan bo'lsa ishlaydi
	if cash_account:
		internal_transfer_receive = "WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_to = %(cash_account)s THEN pe.received_amount"
		internal_transfer_pay = "WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_from = %(cash_account)s THEN pe.paid_amount"
	else:
		internal_transfer_receive = ""
		internal_transfer_pay = ""

	query = f"""
		SELECT
			COALESCE(SUM(
				CASE
					WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
					{internal_transfer_receive}
					ELSE 0
				END
			), 0) as total_receive,
			COALESCE(SUM(
				CASE
					WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
					{internal_transfer_pay}
					ELSE 0
				END
			), 0) as total_pay
		FROM `tabPayment Entry` pe
		WHERE {where_clause}
	"""

	result = frappe.db.sql(query, params, as_dict=1)

	if result and result[0]:
		total_receive = flt(result[0].get('total_receive', 0))
		total_pay = flt(result[0].get('total_pay', 0))
		return total_receive - total_pay

	return 0.0


# ============================================================
# ✅ NET BALANCE - to_date gacha barcha
# ============================================================

def get_net_balance(to_date, cash_account=None):
	"""to_date gacha barcha kirim - chiqim"""

	if not to_date:
		return 0.0

	conditions = ["pe.docstatus = 1"]
	params = {"to_date": to_date, "cash_account": cash_account}

	conditions.append("pe.posting_date <= %(to_date)s")

	if cash_account:
		conditions.append("(pe.paid_from = %(cash_account)s OR pe.paid_to = %(cash_account)s)")

	where_clause = " AND ".join(conditions)

	# Internal Transfer logic faqat cash_account berilgan bo'lsa ishlaydi
	if cash_account:
		internal_transfer_receive = "WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_to = %(cash_account)s THEN pe.received_amount"
		internal_transfer_pay = "WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_from = %(cash_account)s THEN pe.paid_amount"
	else:
		internal_transfer_receive = ""
		internal_transfer_pay = ""

	query = f"""
		SELECT
			COALESCE(SUM(
				CASE
					WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
					{internal_transfer_receive}
					ELSE 0
				END
			), 0) as total_receive,
			COALESCE(SUM(
				CASE
					WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
					{internal_transfer_pay}
					ELSE 0
				END
			), 0) as total_pay
		FROM `tabPayment Entry` pe
		WHERE {where_clause}
	"""

	result = frappe.db.sql(query, params, as_dict=1)

	if result and result[0]:
		total_receive = flt(result[0].get('total_receive', 0))
		total_pay = flt(result[0].get('total_pay', 0))
		return total_receive - total_pay

	return 0.0
