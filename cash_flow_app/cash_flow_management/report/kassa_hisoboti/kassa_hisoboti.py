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

	if cash_account:
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
				END AS cash_account

			FROM `tabPayment Entry` pe
			WHERE pe.docstatus = 1
			{conditions}
			ORDER BY pe.posting_date, pe.creation
		"""
	else:
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
						CONCAT('From: ', pe.paid_from, ' To: ', pe.paid_to)
					ELSE pe.paid_to
				END AS party,

				CASE
					WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' THEN pe.paid_amount
					ELSE 0
				END AS debit,

				CASE
					WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' THEN pe.received_amount
					ELSE 0
				END AS credit,

				CASE
					WHEN pe.payment_type = 'Receive' THEN pe.paid_to
					WHEN pe.payment_type = 'Pay' THEN pe.paid_from
					WHEN pe.payment_type = 'Internal Transfer' THEN pe.paid_from
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
# ✅ SUMMARY
# ============================================================

def get_summary(data, filters=None):
	"""Summary boxes - har bir cash uchun alohida: Opening Balance, Total Kirim, Total Chiqim, Net Balance"""
	
	if not filters or not data:
		return []

	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	cash_account = filters.get("cash_account")

	# Agar specific kassa tanlangan bo'lsa, faqat uni ko'rsat
	if cash_account:
		opening_balance = get_opening_balance(from_date, cash_account)
		total_kirim = sum(flt(x.get('credit', 0)) for x in data) if data else 0.0
		total_chiqim = sum(flt(x.get('debit', 0)) for x in data) if data else 0.0
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

	# Agar kassa tanlangan bo'lmasa, barcha kassalarni ko'rsat
	# Get unique cash accounts from data
	cash_accounts = list(set(x.get('cash_account') for x in data if x.get('cash_account')))
	
	if not cash_accounts:
		return []

	summary = []
	for cash in sorted(cash_accounts):
		opening_balance = get_opening_balance(from_date, cash)
		total_kirim = sum(flt(x.get('credit', 0)) for x in data if x.get('cash_account') == cash)
		total_chiqim = sum(flt(x.get('debit', 0)) for x in data if x.get('cash_account') == cash)
		net_balance = get_net_balance(to_date, cash)

		summary.append({
			"value": f"{cash}: Opening Balance",
			"indicator": "Blue",
			"label": _("Opening Balance"),
			"datatype": "Data"
		})
		summary.append({
			"value": opening_balance,
			"indicator": "Blue",
			"label": "",
			"datatype": "Currency",
			"currency": "USD"
		})

		summary.append({
			"value": f"{cash}: Total Kirim",
			"indicator": "Green",
			"label": _("Total Kirim"),
			"datatype": "Data"
		})
		summary.append({
			"value": total_kirim,
			"indicator": "Green",
			"label": "",
			"datatype": "Currency",
			"currency": "USD"
		})

		summary.append({
			"value": f"{cash}: Total Chiqim",
			"indicator": "Red",
			"label": _("Total Chiqim"),
			"datatype": "Data"
		})
		summary.append({
			"value": total_chiqim,
			"indicator": "Red",
			"label": "",
			"datatype": "Currency",
			"currency": "USD"
		})

		summary.append({
			"value": f"{cash}: Net Balance = Opening + Kirim - Chiqim",
			"indicator": "Blue" if net_balance >= 0 else "Red",
			"label": _("Net Balance"),
			"datatype": "Data"
		})
		summary.append({
			"value": net_balance,
			"indicator": "Blue" if net_balance >= 0 else "Red",
			"label": "",
			"datatype": "Currency",
			"currency": "USD"
		})

	return summary


# ============================================================
# ✅ OPENING BALANCE - from_date dan oldingi
# ============================================================

def get_opening_balance(from_date, cash_account=None):
	"""from_date dan oldingi barcha kirim - chiqim (Internal Transfer o'z ichiga oladi)"""
	
	if not from_date:
		return 0.0
	
	conditions = ["pe.docstatus = 1"]
	params = {"from_date": from_date}
	
	conditions.append("pe.posting_date < %(from_date)s")
	
	if cash_account:
		conditions.append("(pe.paid_from = %(cash_account)s OR pe.paid_to = %(cash_account)s)")
		params["cash_account"] = cash_account
		
		where_clause = " AND ".join(conditions)
		
		query = f"""
			SELECT
				COALESCE(SUM(CASE 
					WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_to = %(cash_account)s THEN pe.received_amount
					ELSE 0 
				END), 0) as total_receive,
				COALESCE(SUM(CASE 
					WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_from = %(cash_account)s THEN pe.paid_amount
					ELSE 0 
				END), 0) as total_pay
			FROM `tabPayment Entry` pe
			WHERE {where_clause}
		"""
	else:
		where_clause = " AND ".join(conditions)
		
		query = f"""
			SELECT
				COALESCE(SUM(CASE 
					WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' THEN pe.received_amount
					ELSE 0 
				END), 0) as total_receive,
				COALESCE(SUM(CASE 
					WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' THEN pe.paid_amount
					ELSE 0 
				END), 0) as total_pay
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
	"""to_date gacha barcha kirim - chiqim (Internal Transfer o'z ichiga oladi)"""
	
	if not to_date:
		return 0.0
	
	conditions = ["pe.docstatus = 1"]
	params = {"to_date": to_date}
	
	conditions.append("pe.posting_date <= %(to_date)s")
	
	if cash_account:
		conditions.append("(pe.paid_from = %(cash_account)s OR pe.paid_to = %(cash_account)s)")
		params["cash_account"] = cash_account
		
		where_clause = " AND ".join(conditions)
		
		query = f"""
			SELECT
				COALESCE(SUM(CASE 
					WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_to = %(cash_account)s THEN pe.received_amount
					ELSE 0 
				END), 0) as total_receive,
				COALESCE(SUM(CASE 
					WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_from = %(cash_account)s THEN pe.paid_amount
					ELSE 0 
				END), 0) as total_pay
			FROM `tabPayment Entry` pe
			WHERE {where_clause}
		"""
	else:
		where_clause = " AND ".join(conditions)
		
		query = f"""
			SELECT
				COALESCE(SUM(CASE 
					WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' THEN pe.received_amount
					ELSE 0 
				END), 0) as total_receive,
				COALESCE(SUM(CASE 
					WHEN pe.payment_type = 'Pay' THEN pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' THEN pe.paid_amount
					ELSE 0 
				END), 0) as total_pay
			FROM `tabPayment Entry` pe
			WHERE {where_clause}
		"""

	result = frappe.db.sql(query, params, as_dict=1)
	
	if result and result[0]:
		total_receive = flt(result[0].get('total_receive', 0))
		total_pay = flt(result[0].get('total_pay', 0))
		return total_receive - total_pay
	
	return 0.0
