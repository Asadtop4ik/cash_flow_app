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
			"fieldtype": "Data",
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
	"""Get kassa balance data from Payment Entry using paid_from and paid_to"""

	# Payment Type = 'Receive' bo'lsa paid_from dan pul kirib keladi (plus)
	# Payment Type = 'Pay' bo'lsa paid_to ga pul chiqadi (minus)
	query = """
        SELECT
            kassa_name,
            SUM(amount) as qoldiq_summa
        FROM (
            -- Receive: paid_from dan pul kirib keladi
            SELECT
                pe.paid_from as kassa_name,
                pe.paid_amount as amount
            FROM
                `tabPayment Entry` pe
            WHERE
                pe.docstatus = 1
                AND pe.payment_type = 'Receive'
                AND pe.paid_from IS NOT NULL
                AND pe.paid_from != ''

            UNION ALL

            -- Pay: paid_to ga pul ketadi (minus)
            SELECT
                pe.paid_to as kassa_name,
                -pe.paid_amount as amount
            FROM
                `tabPayment Entry` pe
            WHERE
                pe.docstatus = 1
                AND pe.payment_type = 'Pay'
                AND pe.paid_to IS NOT NULL
                AND pe.paid_to != ''

            UNION ALL

            -- Internal Transfer: paid_from dan ayriladi
            SELECT
                pe.paid_from as kassa_name,
                -pe.paid_amount as amount
            FROM
                `tabPayment Entry` pe
            WHERE
                pe.docstatus = 1
                AND pe.payment_type = 'Internal Transfer'
                AND pe.paid_from IS NOT NULL
                AND pe.paid_from != ''

            UNION ALL

            -- Internal Transfer: paid_to ga qo'shiladi
            SELECT
                pe.paid_to as kassa_name,
                pe.received_amount as amount
            FROM
                `tabPayment Entry` pe
            WHERE
                pe.docstatus = 1
                AND pe.payment_type = 'Internal Transfer'
                AND pe.paid_to IS NOT NULL
                AND pe.paid_to != ''
        ) as combined
        GROUP BY
            kassa_name
        ORDER BY
            kassa_name
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
