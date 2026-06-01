# Copyright (c) 2024, Ruxshona and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """
    Report ustunlari — kengliklar ma'lumot hajmiga moslashtirilgan.

    Kenglik tanlash mantig'i:
      - Link (ID, mijoz)     : 120-130 px
      - Currency (summa)     : 105-120 px
      - Int (oy soni)        : 75  px
      - Percent (foiz)       : 95  px
    """
    return [
        {
            "fieldname": "name",
            "label": _("Shartnoma ID"),
            "fieldtype": "Link",
            "options": "Installment Application",
            "width": 130
        },
        {
            "fieldname": "customer",
            "label": _("Mijoz"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 130
        },
        {
            "fieldname": "contract_amount",
            "label": _("Shartnoma Summasi"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "cost_price",
            "label": _("Tavar Tannarxi"),
            "fieldtype": "Currency",
            "width": 110
        },
        {
            "fieldname": "initial_payment",
            "label": _("Boshlang'ich To'lov"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "net_profit",
            "label": _("Toza Savdo"),
            "fieldtype": "Currency",
            "width": 105
        },
        {
            "fieldname": "remaining_amount",
            "label": _("Tannarx"),
            "fieldtype": "Currency",
            "width": 105
        },
        # ── Installment Application fieldlari ──────────────────────────────
        {
            "fieldname": "installment_months",
            "label": _("Necha Oy"),
            "fieldtype": "Int",
            "width": 75
        },
        {
            "fieldname": "custom_total_interest",
            "label": _("Foyda Summasi (USD)"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "custom_profit_percentage",
            "label": _("Marja Foiz (%)"),
            "fieldtype": "Percent",
            "width": 95
        },
        {
            "fieldname": "custom_finance_profit_percentage",
            "label": _("Ustama Foiz (%)"),
            "fieldtype": "Percent",
            "width": 95
        },
    ]


def get_data(filters):
    """Ma'lumotlarni olish"""

    conditions = []
    values = {}

    # Faqat submit bo'lgan shartnomalar
    conditions.append("ia.docstatus = 1")

    if filters.get("from_date"):
        conditions.append("DATE(ia.transaction_date) >= %(from_date)s")
        values["from_date"] = filters.get("from_date")

    if filters.get("to_date"):
        conditions.append("DATE(ia.transaction_date) <= %(to_date)s")
        values["to_date"] = filters.get("to_date")

    if filters.get("installment_application"):
        conditions.append("ia.name = %(installment_application)s")
        values["installment_application"] = filters.get("installment_application")

    if filters.get("customer"):
        conditions.append("ia.customer = %(customer)s")
        values["customer"] = filters.get("customer")

    where_clause = "WHERE " + " AND ".join(conditions)

    query = """
        SELECT
            ia.name,
            ia.customer,
            COALESCE(ia.custom_grand_total_with_interest, 0)   AS contract_amount,
            COALESCE(ia.total_amount, 0)                       AS cost_price,
            COALESCE(ia.downpayment_amount, 0)                 AS initial_payment,
            (COALESCE(ia.custom_grand_total_with_interest, 0)
             - COALESCE(ia.finance_amount, 0))                 AS net_profit,
            (COALESCE(ia.total_amount, 0)
             - COALESCE(ia.downpayment_amount, 0))             AS remaining_amount,

            COALESCE(ia.installment_months, 0)                          AS installment_months,
            COALESCE(ia.custom_total_interest, 0)                       AS custom_total_interest,
            COALESCE(ia.custom_profit_percentage, 0)                    AS custom_profit_percentage,
            COALESCE(ia.custom_finance_profit_percentage, 0)            AS custom_finance_profit_percentage

        FROM
            `tabInstallment Application` ia
        {where_clause}
        ORDER BY
            ia.transaction_date DESC, ia.name DESC
    """.format(where_clause=where_clause)

    return frappe.db.sql(query, values=values, as_dict=1)
