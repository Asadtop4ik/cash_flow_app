# Copyright (c) 2025, Ruxshona and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	summary = get_summary(data)

	return columns, data, None, None, summary


def get_columns():
	"""Define report columns - only 2 columns"""
	return [
		{
			"fieldname": "kassa_name",
			"label": _("Kassa Nomi"),
			"fieldtype": "Link",
			"options": "Cash Register",
			"width": 300
		},
		{
			"fieldname": "qoldiq_summa",
			"label": _("Qoldiq summa (USD)"),
			"fieldtype": "Currency",
			"width": 300
		}
	]


def get_data(filters):
	"""Get kassa balance data from Payment Entry"""

	query = """
        SELECT
            cr.name as kassa_name,
            COALESCE(SUM(CASE
                WHEN pe.payment_type = 'Receive' THEN pe.paid_amount
                WHEN pe.payment_type = 'Pay' THEN -pe.paid_amount
                ELSE 0
            END), 0) as qoldiq_summa
        FROM
            `tabCash Register` cr
        LEFT JOIN
            `tabPayment Entry` pe ON pe.custom_cashier = cr.name
            AND pe.docstatus = 1
        WHERE
            cr.status = 'Active'
        GROUP BY
            cr.name
        ORDER BY
            cr.name
    """

	data = frappe.db.sql(query, as_dict=1)

	return data


def get_summary(data):
	"""Calculate total net balance for summary at top"""
	if not data:
		return []

	total_balance = sum([d.get('qoldiq_summa', 0) for d in data])

	return [
		{
			"value": total_balance,
			"indicator": "Green" if total_balance >= 0 else "Red",
			"label": "Qoldiq summa (USD)",
			"datatype": "Currency",
			"currency": "USD"
		}
	]
