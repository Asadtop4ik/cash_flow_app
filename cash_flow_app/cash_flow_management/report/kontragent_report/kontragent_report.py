import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 150
		},
		{
			"label": _("Type"),
			"fieldname": "party_type",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Op. Debit"),
			"fieldname": "opening_debit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Op. Credit"),
			"fieldname": "opening_credit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Tr. Debit"),
			"fieldname": "transaction_debit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Tr. Credit"),
			"fieldname": "transaction_credit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Cl. Debit"),
			"fieldname": "closing_debit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Cl. Credit"),
			"fieldname": "closing_credit",
			"fieldtype": "Currency",
			"width": 100
		}
	]


def get_data(filters):
	from_date = filters.get('from_date') or '2025-01-01'
	to_date = filters.get('to_date') or '2025-12-31'
	party_type_filter = filters.get('party_type') or ''
	party_filter = filters.get('party') or ''

	data = []

	# CUSTOMERS - Sales Order asosida
	if not party_type_filter or party_type_filter == 'Customer':
		customers = frappe.db.sql("""
			SELECT DISTINCT customer FROM `tabSales Order`
			WHERE docstatus = 1
			AND customer IS NOT NULL
			AND customer != ''
			{party_condition}
			ORDER BY customer
		""".format(
			party_condition=f"AND customer = '{party_filter}'" if party_filter else ""
		), as_dict=True)

		cust_total = {
			'party': "Jami",
			'party_type': 'CUSTOMER TOTAL',
			'opening_debit': 0,
			'opening_credit': 0,
			'transaction_debit': 0,
			'transaction_credit': 0,
			'closing_debit': 0,
			'closing_credit': 0
		}

		for c in customers:
			# Sales Order summalarini olish
			sales_data = frappe.db.sql("""
				SELECT
					SUM(CASE WHEN transaction_date < %s THEN rounded_total ELSE 0 END) as opening_sales,
					SUM(CASE WHEN transaction_date >= %s AND transaction_date <= %s THEN rounded_total ELSE 0 END) as period_sales,
					SUM(CASE WHEN transaction_date <= %s THEN rounded_total ELSE 0 END) as total_sales
				FROM `tabSales Order`
				WHERE customer = %s
				AND docstatus = 1
			""", (from_date, from_date, to_date, to_date, c['customer']), as_dict=True)[0]

			# To'lovlarni olish (Payment Entry dan)
			payment_data = frappe.db.sql("""
				SELECT
					SUM(CASE WHEN posting_date < %s THEN paid_amount ELSE 0 END) as opening_payments,
					SUM(CASE WHEN posting_date >= %s AND posting_date <= %s THEN paid_amount ELSE 0 END) as period_payments,
					SUM(CASE WHEN posting_date <= %s THEN paid_amount ELSE 0 END) as total_payments
				FROM `tabPayment Entry`
				WHERE party = %s
				AND party_type = 'Customer'
				AND payment_type = 'Receive'
				AND docstatus = 1
			""", (from_date, from_date, to_date, to_date, c['customer']), as_dict=True)[0]

			# Opening balance: Sales - Payments (Debit - Credit mantiq)
			opening_sales = flt(sales_data.get('opening_sales'))
			opening_payments = flt(payment_data.get('opening_payments'))
			opening_balance = opening_sales - opening_payments

			# Transaction: faqat davr ichidagi
			period_sales = flt(sales_data.get('period_sales'))
			period_payments = flt(payment_data.get('period_payments'))

			# Closing balance: Total Sales - Total Payments
			total_sales = flt(sales_data.get('total_sales'))
			total_payments = flt(payment_data.get('total_payments'))
			closing_balance = total_sales - total_payments

			row = {
				'party': c['customer'],
				'party_type': 'Customer',
				'opening_debit': opening_balance if opening_balance > 0 else 0,
				'opening_credit': abs(opening_balance) if opening_balance < 0 else 0,
				'transaction_debit': period_sales,
				'transaction_credit': period_payments,
				'closing_debit': closing_balance if closing_balance > 0 else 0,
				'closing_credit': abs(closing_balance) if closing_balance < 0 else 0
			}
			data.append(row)

			for k in ['opening_debit', 'opening_credit', 'transaction_debit',
					  'transaction_credit', 'closing_debit', 'closing_credit']:
				cust_total[k] += row[k]

		if customers:
			data.append(cust_total)
			data.append({
				'party': '', 'party_type': '',
				'opening_debit': 0, 'opening_credit': 0,
				'transaction_debit': 0, 'transaction_credit': 0,
				'closing_debit': 0, 'closing_credit': 0
			})

	# SUPPLIERS - GL Entry asosida (eskicha)
	if not party_type_filter or party_type_filter == 'Supplier':
		suppliers = frappe.db.sql("""
			SELECT DISTINCT party FROM `tabGL Entry`
			WHERE party_type = 'Supplier'
			AND party IS NOT NULL
			AND party != ''
			AND is_cancelled = 0
			{party_condition}
			ORDER BY party
		""".format(
			party_condition=f"AND party = '{party_filter}'" if party_filter else ""
		), as_dict=True)

		supp_total = {
			'party': "Jami",
			'party_type': 'SUPPLIER TOTAL',
			'opening_debit': 0,
			'opening_credit': 0,
			'transaction_debit': 0,
			'transaction_credit': 0,
			'closing_debit': 0,
			'closing_credit': 0
		}

		for s in suppliers:
			gl = frappe.db.sql("""
				SELECT
					SUM(CASE WHEN posting_date < %s THEN debit ELSE 0 END) as od,
					SUM(CASE WHEN posting_date < %s THEN credit ELSE 0 END) as oc,
					SUM(CASE WHEN posting_date >= %s AND posting_date <= %s THEN debit ELSE 0 END) as td,
					SUM(CASE WHEN posting_date >= %s AND posting_date <= %s THEN credit ELSE 0 END) as tc,
					SUM(CASE WHEN posting_date <= %s THEN debit ELSE 0 END) as cd,
					SUM(CASE WHEN posting_date <= %s THEN credit ELSE 0 END) as cc
				FROM `tabGL Entry`
				WHERE party = %s
				AND party_type = 'Supplier'
				AND is_cancelled = 0
			""", (
				from_date, from_date, from_date, to_date,
				from_date, to_date, to_date, to_date, s['party']
			), as_dict=True)[0]

			# Opening balance hisobi: Supplier uchun Credit - Debit
			opening_debit_total = flt(gl['od'])
			opening_credit_total = flt(gl['oc'])
			opening_balance = opening_credit_total - opening_debit_total

			# Closing balance hisobi: Supplier uchun Credit - Debit
			closing_debit_total = flt(gl['cd'])
			closing_credit_total = flt(gl['cc'])
			closing_balance = closing_credit_total - closing_debit_total

			row = {
				'party': s['party'],
				'party_type': 'Supplier',
				'opening_debit': abs(opening_balance) if opening_balance < 0 else 0,
				'opening_credit': opening_balance if opening_balance > 0 else 0,
				'transaction_debit': flt(gl['td']),
				'transaction_credit': flt(gl['tc']),
				'closing_debit': abs(closing_balance) if closing_balance < 0 else 0,
				'closing_credit': closing_balance if closing_balance > 0 else 0
			}
			data.append(row)

			for k in ['opening_debit', 'opening_credit', 'transaction_debit',
					  'transaction_credit', 'closing_debit', 'closing_credit']:
				supp_total[k] += row[k]

		if suppliers:
			data.append(supp_total)

	return data
