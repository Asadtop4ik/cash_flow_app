# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
	"""
	Customer Hisoboti - Mijoz to'lovlari va shartnomalar hisoboti
	"""
	if not filters:
		filters = {}

	# Validate filters
	if not filters.get("customer"):
		frappe.throw(_("Iltimos, mijozni tanlang"))
	if not filters.get("from_date"):
		frappe.throw(_("Iltimos, boshlanish sanasini kiriting"))
	if not filters.get("to_date"):
		frappe.throw(_("Iltimos, tugash sanasini kiriting"))

	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data, filters)
	chart = None

	return columns, data, None, chart, summary, None


def get_columns():
	"""Report columns definition"""
	return [
		{
			"fieldname": "date",
			"label": _("Sana"),
			"fieldtype": "Date",
			"width": 110
		},
		{
			"fieldname": "contract_link",
			"label": _("Shartnoma"),
			"fieldtype": "Link",
			"options": "Installment Application",
			"width": 150
		},
		{
			"fieldname": "payment_link",
			"label": _("To'lov"),
			"fieldtype": "Link",
			"options": "Payment Entry",
			"width": 150
		},
		{
			"fieldname": "debit",
			"label": _("Debit (Bizdan qarz)"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "credit",
			"label": _("Kredit (Bizga to'lov)"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "balance",
			"label": _("Qoldiq"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "cash_account",
			"label": _("Kassa"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 150
		}
	]


def get_data(filters):
	"""Get report data with transactions"""
	customer = filters.get("customer")
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	contract_filter = filters.get("contract")

	data = []
	# 1. Calculate opening balance (before from_date)
	opening_balance = calculate_opening_balance(customer, from_date, contract_filter)

	# 1. Get all transactions (contracts and payments) in date range
	transactions = get_transactions(customer, from_date, to_date, contract_filter)

	# 2. Process transactions and calculate running balance
	# Start from opening balance inserted of 0
	running_balance = opening_balance
	for transaction in transactions:
		debit = flt(transaction.get("debit", 0))
		credit = flt(transaction.get("credit", 0))

		running_balance += debit - credit

		data.append({
			"date": transaction.get("date"),
			"contract_link": transaction.get("contract_link"),
			"payment_link": transaction.get("payment_link"),
			"debit": debit if debit > 0 else None,
			"credit": credit if credit > 0 else None,
			"balance": running_balance,
			"cash_account": transaction.get("cash_account")
		})

	return data


def calculate_opening_balance(customer, from_date, contract_filter=None):
	"""
	Calculate opening balance (boshlang'ich qoldiq):
	Sum of all contracts before from_date - Sum of all payments before from_date
	"""
	# Get all contracts before from_date
	contract_conditions = """
		WHERE customer = %s
		AND docstatus = 1
		AND DATE(transaction_date) < %s
	"""
	contract_params = [customer, from_date]

	if contract_filter:
		contract_conditions += " AND name = %s"
		contract_params.append(contract_filter)

	total_contracts = frappe.db.sql(f"""
		SELECT COALESCE(SUM(custom_grand_total_with_interest), 0) as total
		FROM `tabInstallment Application`
		{contract_conditions}
	""", tuple(contract_params))[0][0] or 0

	# Get all payments before from_date
	payment_conditions = """
		WHERE pe.docstatus = 1
		AND pe.party_type = 'Customer'
		AND pe.party = %s
		AND DATE(pe.posting_date) < %s
	"""
	payment_params = [customer, from_date]

	if contract_filter:
		payment_conditions += """
			AND pe.custom_contract_reference IN (
				SELECT sales_order
				FROM `tabInstallment Application`
				WHERE name = %s
			)
		"""
		payment_params.append(contract_filter)

	# Receive = Mijoz bizga to'ladi (kredit - ayiriladi)
	# Pay = Biz mijozga qaytardik (debit - qo'shiladi)
	payment_totals = frappe.db.sql(f"""
		SELECT
			COALESCE(SUM(CASE WHEN pe.payment_type = 'Receive' THEN pe.paid_amount ELSE 0 END), 0) as total_receive,
			COALESCE(SUM(CASE WHEN pe.payment_type = 'Pay' THEN pe.paid_amount ELSE 0 END), 0) as total_pay
		FROM `tabPayment Entry` pe
		{payment_conditions}
	""", tuple(payment_params))[0]

	total_receive = flt(payment_totals[0])
	total_pay = flt(payment_totals[1])

	# Debit (qarz) = contracts + pay (qaytargan pullar)
	# Credit (to'lov) = receive (olingan pullar)
	return flt(total_contracts) + total_pay - total_receive


def calculate_totals_for_range(customer, from_date, to_date, contract_filter=None):
	"""
	Calculate totals for date range (from_date to to_date)
	Returns: (total_debit, total_credit)
	"""
	# Get contracts in date range
	contract_conditions = """
		WHERE customer = %s
		AND docstatus = 1
		AND DATE(transaction_date) BETWEEN %s AND %s
	"""
	contract_params = [customer, from_date, to_date]

	if contract_filter:
		contract_conditions += " AND name = %s"
		contract_params.append(contract_filter)

	total_contracts = frappe.db.sql(f"""
		SELECT COALESCE(SUM(custom_grand_total_with_interest), 0) as total
		FROM `tabInstallment Application`
		{contract_conditions}
	""", tuple(contract_params))[0][0] or 0

	# Get payments in date range
	payment_conditions = """
		WHERE pe.docstatus = 1
		AND pe.party_type = 'Customer'
		AND pe.party = %s
		AND DATE(pe.posting_date) BETWEEN %s AND %s
	"""
	payment_params = [customer, from_date, to_date]

	if contract_filter:
		payment_conditions += """
			AND pe.custom_contract_reference IN (
				SELECT sales_order
				FROM `tabInstallment Application`
				WHERE name = %s
			)
		"""
		payment_params.append(contract_filter)

	# Receive = Mijoz bizga to'ladi (kredit)
	# Pay = Biz mijozga qaytardik (debit)
	payment_totals = frappe.db.sql(f"""
		SELECT
			COALESCE(SUM(CASE WHEN pe.payment_type = 'Receive' THEN pe.paid_amount ELSE 0 END), 0) as total_receive,
			COALESCE(SUM(CASE WHEN pe.payment_type = 'Pay' THEN pe.paid_amount ELSE 0 END), 0) as total_pay
		FROM `tabPayment Entry` pe
		{payment_conditions}
	""", tuple(payment_params))[0]

	total_receive = flt(payment_totals[0])
	total_pay = flt(payment_totals[1])

	# Total Debit = shartnomalar + biz qaytargan pullar (Pay)
	# Total Credit = mijoz to'lagan pullar (Receive)
	total_debit = flt(total_contracts) + total_pay
	total_credit = total_receive

	return total_debit, total_credit


def calculate_final_balance(customer, to_date, contract_filter=None):
	"""
	Calculate final balance (oxirgi qoldiq):
	Sum of all contracts up to to_date - Sum of all payments up to to_date
	"""
	# Get all contracts up to and including to_date
	contract_conditions = """
		WHERE customer = %s
		AND docstatus = 1
		AND DATE(transaction_date) <= %s
	"""
	contract_params = [customer, to_date]

	if contract_filter:
		contract_conditions += " AND name = %s"
		contract_params.append(contract_filter)

	total_contracts = frappe.db.sql(f"""
		SELECT COALESCE(SUM(custom_grand_total_with_interest), 0) as total
		FROM `tabInstallment Application`
		{contract_conditions}
	""", tuple(contract_params))[0][0] or 0

	# Get all payments up to and including to_date
	payment_conditions = """
		WHERE pe.docstatus = 1
		AND pe.party_type = 'Customer'
		AND pe.party = %s
		AND DATE(pe.posting_date) <= %s
	"""
	payment_params = [customer, to_date]

	if contract_filter:
		payment_conditions += """
			AND pe.custom_contract_reference IN (
				SELECT sales_order
				FROM `tabInstallment Application`
				WHERE name = %s
			)
		"""
		payment_params.append(contract_filter)

	# Receive = Mijoz bizga to'ladi (kredit - ayiriladi)
	# Pay = Biz mijozga qaytardik (debit - qo'shiladi)
	payment_totals = frappe.db.sql(f"""
		SELECT
			COALESCE(SUM(CASE WHEN pe.payment_type = 'Receive' THEN pe.paid_amount ELSE 0 END), 0) as total_receive,
			COALESCE(SUM(CASE WHEN pe.payment_type = 'Pay' THEN pe.paid_amount ELSE 0 END), 0) as total_pay
		FROM `tabPayment Entry` pe
		{payment_conditions}
	""", tuple(payment_params))[0]

	total_receive = flt(payment_totals[0])
	total_pay = flt(payment_totals[1])

	# Oxirgi qoldiq = shartnomalar + qaytarilgan pullar - to'langan pullar
	return flt(total_contracts) + total_pay - total_receive


def get_transactions(customer, from_date, to_date, contract_filter=None):
	"""
	Get all transactions (contracts and payments) in date range
	Returns sorted list by date
	"""
	transactions = []

	# Get contracts in date range
	contract_conditions = """
		WHERE customer = %s
		AND docstatus = 1
		AND DATE(transaction_date) BETWEEN %s AND %s
	"""
	contract_params = [customer, from_date, to_date]

	if contract_filter:
		contract_conditions += " AND name = %s"
		contract_params.append(contract_filter)

	contracts = frappe.db.sql(f"""
		SELECT
			name,
			DATE(transaction_date) as date,
			custom_grand_total_with_interest as amount
		FROM `tabInstallment Application`
		{contract_conditions}
		ORDER BY transaction_date
	""", tuple(contract_params), as_dict=1)

	for contract in contracts:
		transactions.append({
			"date": contract.date,
			"contract_link": contract.name,
			"payment_link": None,
			"debit": flt(contract.amount),
			"credit": 0,
			"cash_account": None,
			"sort_key": (contract.date, 0)  # 0 for contracts (comes first)
		})

	# Get payments in date range
	payment_conditions = """
		WHERE pe.docstatus = 1
		AND pe.party_type = 'Customer'
		AND pe.party = %s
		AND DATE(pe.posting_date) BETWEEN %s AND %s
	"""
	payment_params = [customer, from_date, to_date]

	if contract_filter:
		payment_conditions += """
			AND pe.custom_contract_reference IN (
				SELECT sales_order
				FROM `tabInstallment Application`
				WHERE name = %s
			)
		"""
		payment_params.append(contract_filter)

	payments = frappe.db.sql(f"""
		SELECT
			pe.name,
			DATE(pe.posting_date) as date,
			pe.paid_amount,
			pe.paid_to,
			pe.paid_from,
			pe.payment_type,
			ia.name as contract_name
		FROM `tabPayment Entry` pe
		LEFT JOIN `tabInstallment Application` ia
			ON ia.sales_order = pe.custom_contract_reference
		{payment_conditions}
		ORDER BY pe.posting_date
	""", tuple(payment_params), as_dict=1)

	for payment in payments:
		# Receive = Mijoz bizga to'ladi -> Credit
		# Pay = Biz mijozga qaytardik -> Debit
		if payment.payment_type == "Pay":
			debit_amount = flt(payment.paid_amount)
			credit_amount = 0
			cash_account = payment.paid_from
		else:  # Receive
			debit_amount = 0
			credit_amount = flt(payment.paid_amount)
			cash_account = payment.paid_to

		transactions.append({
			"date": payment.date,
			"contract_link": payment.contract_name,
			"payment_link": payment.name,
			"debit": debit_amount,
			"credit": credit_amount,
			"cash_account": cash_account,
			"sort_key": (payment.date, 1)  # 1 for payments (comes after contracts)
		})

	# Sort by date, then by type (contracts before payments on same date)
	transactions.sort(key=lambda x: x["sort_key"])

	return transactions


def get_summary(data, filters):
	"""
	Generate summary cards - katta kartochkalar tepada
	"""
	customer = filters.get("customer")
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	contract_filter = filters.get("contract")

	# 1. Boshlang'ich qoldiq (from_date gacha)
	opening_balance = calculate_opening_balance(customer, from_date, contract_filter)

	# 2. Jami Debit va Kredit (from_date to to_date orasida)
	total_debit, total_credit = calculate_totals_for_range(
		customer, from_date, to_date, contract_filter
	)

	# 3. Oxirgi qoldiq (to_date gacha)
	final_balance = calculate_final_balance(customer, to_date, contract_filter)

	summary = [
		{
			"value": opening_balance,
			"indicator": "blue",
			"label": "Boshlang'ich Qoldiq",
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_debit,
			"indicator": "red",
			"label": "Jami Debit (Bizdan qarz)",
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": total_credit,
			"indicator": "green",
			"label": "Jami Kredit (Bizga to'lov)",
			"datatype": "Currency",
			"currency": "USD"
		},
		{
			"value": final_balance,
			"indicator": "orange" if final_balance > 0 else "green",
			"label": "Oxirgi Qoldiq",
			"datatype": "Currency",
			"currency": "USD"
		}
	]

	return summary
