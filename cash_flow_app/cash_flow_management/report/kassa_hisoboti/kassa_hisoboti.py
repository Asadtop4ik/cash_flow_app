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

	return columns, data, None, summary

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
		# ✅ YANGI USTUN - KASSA NOMI
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

			-- ✅ YANGI FIELD - Qaysi kassaga kirim yoki qaysi kassadan chiqim
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
			END AS cash_account

		FROM `tabPayment Entry` pe
		WHERE pe.docstatus = 1
		{conditions}
		ORDER BY pe.posting_date, pe.creation
	"""

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

	if filters.get("cash_account"):
		conditions.append("(pe.paid_from = %(cash_account)s OR pe.paid_to = %(cash_account)s)")

	if filters.get("counterparty_category"):
		conditions.append("pe.custom_counterparty_category = %(counterparty_category)s")

	if filters.get("payment_type"):
		conditions.append("pe.payment_type = %(payment_type)s")

	return " AND " + " AND ".join(conditions) if conditions else ""

# ============================================================
# ✅ SUMMARY (HECH NIMA O'ZGARMAYDI)
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
