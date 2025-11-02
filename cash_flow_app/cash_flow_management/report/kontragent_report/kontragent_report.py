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
			"options": "party_type",  # Dynamic link party_type ga bog'langan
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
	party_filter = filters.get('party') or ''  # Party filtri qo'shildi

	data = []

	# CUSTOMERS
	if not party_type_filter or party_type_filter == 'Customer':
		customers = frappe.db.sql("""
			SELECT DISTINCT party FROM `tabGL Entry`
			WHERE party_type = 'Customer'
			AND party IS NOT NULL
			AND party != ''
			AND is_cancelled = 0
			{party_condition}
			ORDER BY party
		""".format(
			party_condition=f"AND party = '{party_filter}'" if party_filter else ""
		), as_dict=True)

		cust_total = {
			'party': '',
			'party_type': 'CUSTOMER TOTAL',
			'opening_debit': 0,
			'opening_credit': 0,
			'transaction_debit': 0,
			'transaction_credit': 0,
			'closing_debit': 0,
			'closing_credit': 0
		}

		for c in customers:
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
				AND party_type = 'Customer'
			""", (
				from_date, from_date, from_date, to_date,
				from_date, to_date, to_date, to_date, c['party']
			), as_dict=True)[0]

			row = {
				'party': c['party'],
				'party_type': 'Customer',
				'opening_debit': flt(gl['od']),
				'opening_credit': flt(gl['oc']),
				'transaction_debit': flt(gl['td']),
				'transaction_credit': flt(gl['tc']),
				'closing_debit': flt(gl['cd']),
				'closing_credit': flt(gl['cc'])
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

	# SUPPLIERS
	if not party_type_filter or party_type_filter == 'Supplier':
		suppliers = frappe.db.sql("""
			SELECT DISTINCT party FROM `tabGL Entry`
			WHERE party_type = 'Supplier'
			AND party IS NOT NULL
			AND party != ''
			{party_condition}
			ORDER BY party
		""".format(
			party_condition=f"AND party = '{party_filter}'" if party_filter else ""
		), as_dict=True)

		supp_total = {
			'party': '',
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
			""", (
				from_date, from_date, from_date, to_date,
				from_date, to_date, to_date, to_date, s['party']
			), as_dict=True)[0]

			row = {
				'party': s['party'],
				'party_type': 'Supplier',
				'opening_debit': flt(gl['od']),
				'opening_credit': flt(gl['oc']),
				'transaction_debit': flt(gl['td']),
				'transaction_credit': flt(gl['tc']),
				'closing_debit': flt(gl['cd']),
				'closing_credit': flt(gl['cc'])
			}
			data.append(row)

			for k in ['opening_debit', 'opening_credit', 'transaction_debit',
					  'transaction_credit', 'closing_debit', 'closing_credit']:
				supp_total[k] += row[k]

		if suppliers:
			data.append(supp_total)

	return data
