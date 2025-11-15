
# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	"""IMEI Qidiruv report kolonkalari"""
	return [
		{
			"label": _("Mahsulot Nomi"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("IMEI / Serial No"),
			"fieldname": "imei",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Supplier Name"),
			"fieldname": "supplier_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Shartnoma"),
			"fieldname": "installment_application",
			"fieldtype": "Link",
			"options": "Installment Application",
			"width": 180
		},
		{
			"label": _("Customer Name"),
			"fieldname": "customer_name",
			"fieldtype": "Data",
			"width": 180
		},
		{
			"label": _("Tan Narxi (USD)"),
			"fieldname": "rate",
			"fieldtype": "Currency",
			"options": "USD",
			"width": 120
		},
		{
			"label": _("Sotilgan Sana"),
			"fieldname": "transaction_date",
			"fieldtype": "Datetime",
			"width": 160
		}
	]


def get_data(filters):
	"""IMEI Qidiruv report ma'lumotlari"""
	conditions = get_conditions(filters)

	query = """
		SELECT
			iai.item_name,
			iai.imei,
			COALESCE(iai.custom_supplier, '') as supplier_name,
			ia.name as installment_application,
			ia.customer_name,
			iai.rate,
			ia.transaction_date
		FROM
			`tabInstallment Application Item` iai
		INNER JOIN
			`tabInstallment Application` ia ON iai.parent = ia.name
		WHERE
			ia.docstatus < 2
			{conditions}
		ORDER BY
			ia.transaction_date DESC
	""".format(conditions=conditions)

	data = frappe.db.sql(query, filters, as_dict=1)
	return data


def get_conditions(filters):
	"""Filtrlar asosida SQL shart yaratish"""
	conditions = ""

	if filters.get("imei"):
		conditions += " AND iai.imei LIKE %(imei)s"
		filters["imei"] = f"%{filters['imei']}%"

	if filters.get("supplier_name"):
		conditions += " AND iai.custom_supplier LIKE %(supplier_name)s"

	if filters.get("customer_name"):
		conditions += " AND ia.customer_name LIKE %(customer_name)s"

	return conditions
