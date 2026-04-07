# Copyright (c) 2026, Your Company and contributors
# For license information, please see license.txt
#
# Report   : Sotuv Donasi
# Module   : Cash Flow Management
# Purpose  : Har oy rastrochkaga chiqarilgan mahsulotlar tahlili
#            (faqat submitted + Approved / Sales Order Created shartnomalar)

import frappe
from frappe import _
from frappe.utils import flt


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

def execute(filters=None):
    filters = filters or {}
    columns  = get_columns()
    data     = get_data(filters)
    chart    = get_chart(data)
    summary  = get_summary(data)
    return columns, data, None, chart, summary


# ---------------------------------------------------------------------------
# COLUMNS
# ---------------------------------------------------------------------------

def get_columns():
    return [
        {
            "label"    : _("Shartnoma"),
            "fieldname": "shartnoma",
            "fieldtype": "Link",
            "options"  : "Installment Application",
            "width"    : 170,
        },
        {
            "label"    : _("Sana"),
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width"    : 100,
        },
        {
            "label"    : _("Mijoz"),
            "fieldname": "customer",
            "fieldtype": "Link",
            "options"  : "Customer",
            "width"    : 130,
        },
        {
            "label"    : _("Mijoz Ismi"),
            "fieldname": "customer_name",
            "fieldtype": "Data",
            "width"    : 160,
        },
        {
            "label"    : _("Mahsulot Kodi"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options"  : "Item",
            "width"    : 130,
        },
        {
            "label"    : _("Mahsulot Nomi"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width"    : 200,
        },
        {
            "label"    : _("Miqdor"),
            "fieldname": "qty",
            "fieldtype": "Float",
            "width"    : 80,
        },
        {
            "label"    : _("Narxi (USD)"),
            "fieldname": "rate",
            "fieldtype": "Currency",
            "options"  : "USD",
            "width"    : 120,
        },
        {
            "label"    : _("Jami (USD)"),
            "fieldname": "amount",
            "fieldtype": "Currency",
            "options"  : "USD",
            "width"    : 130,
        },
        {
            "label"    : _("Oylik To'lov (USD)"),
            "fieldname": "monthly_payment",
            "fieldtype": "Currency",
            "options"  : "USD",
            "width"    : 140,
        },
        {
            "label"    : _("Muddat (oy)"),
            "fieldname": "installment_months",
            "fieldtype": "Int",
            "width"    : 100,
        },
        {
            "label"    : _("Jami To'lov + Foiz (USD)"),
            "fieldname": "grand_total_with_interest",
            "fieldtype": "Currency",
            "options"  : "USD",
            "width"    : 170,
        },
    ]


# ---------------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------------

def get_data(filters):
    conditions, values = build_conditions(filters)

    rows = frappe.db.sql(
        """
        SELECT
            ia.name                          AS shartnoma,
            DATE(ia.transaction_date)        AS transaction_date,
            ia.customer                      AS customer,
            ia.customer_name                 AS customer_name,
            iai.item_code                    AS item_code,
            iai.item_name                    AS item_name,
            iai.qty                          AS qty,
            iai.rate                         AS rate,
            iai.amount                       AS amount,
            ia.monthly_payment               AS monthly_payment,
            ia.installment_months            AS installment_months,
            ia.custom_grand_total_with_interest AS grand_total_with_interest
        FROM
            `tabInstallment Application`      ia
        INNER JOIN
            `tabInstallment Application Item` iai
            ON  iai.parent    = ia.name
            AND iai.parenttype = 'Installment Application'
        WHERE
            ia.docstatus = 1
            AND ia.status IN ('Approved', 'Sales Order Created')
            {conditions}
        ORDER BY
            ia.transaction_date DESC,
            ia.name,
            iai.idx
        """.format(conditions=conditions),
        values,
        as_dict=True,
    )

    if not rows:
        return []

    # ── Total row ──────────────────────────────────────────────────────────
    total_qty    = sum(flt(r.qty)    for r in rows)
    total_amount = sum(flt(r.amount) for r in rows)

    rows.append({
        "shartnoma"               : None,
        "transaction_date"        : None,
        "customer"                : None,
        "customer_name"           : _("JAMI"),
        "item_code"               : None,
        "item_name"               : None,
        "qty"                     : total_qty,
        "rate"                    : None,
        "amount"                  : total_amount,
        "monthly_payment"         : None,
        "installment_months"      : None,
        "grand_total_with_interest": None,
        # Frappe'ga bu qatorni bold qilib ko'rsatish uchun:
        "bold"                    : 1,
    })

    return rows


# ---------------------------------------------------------------------------
# CONDITIONS BUILDER
# ---------------------------------------------------------------------------

def build_conditions(filters):
    """
    Returns (conditions_string, values_dict) tuple.
    All filter keys map directly to %(key)s placeholders → SQL injection safe.
    """
    parts  = []
    values = {}

    if filters.get("from_date"):
        parts.append("DATE(ia.transaction_date) >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        parts.append("DATE(ia.transaction_date) <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("customer"):
        parts.append("ia.customer = %(customer)s")
        values["customer"] = filters["customer"]

    if filters.get("item_code"):
        parts.append("iai.item_code = %(item_code)s")
        values["item_code"] = filters["item_code"]

    if filters.get("installment_application"):
        parts.append("ia.name = %(installment_application)s")
        values["installment_application"] = filters["installment_application"]

    conditions = ("AND " + " AND ".join(parts)) if parts else ""
    return conditions, values


# ---------------------------------------------------------------------------
# CHART  –  oylik savdo hajmi (amount) bar chart
# ---------------------------------------------------------------------------

def get_chart(data):
    # Total row (last item, bold=1) ni chart'dan chiqarib tashlaymiz
    rows = [r for r in data if r.get("shartnoma")]

    if not rows:
        return None

    # Oylik guruh: "YYYY-MM" kalit
    monthly = {}
    for row in rows:
        if not row.get("transaction_date"):
            continue
        key = str(row["transaction_date"])[:7]        # "2025-11"
        monthly[key] = monthly.get(key, 0.0) + flt(row["amount"])

    sorted_keys = sorted(monthly.keys())

    return {
        "data": {
            "labels"  : sorted_keys,
            "datasets": [
                {
                    "name"  : _("Savdo Hajmi (USD)"),
                    "values": [monthly[k] for k in sorted_keys],
                }
            ],
        },
        "type"       : "bar",
        "fieldtype"  : "Currency",
        "height"     : 280,
        "colors"     : ["#5e64ff"],
    }


# ---------------------------------------------------------------------------
# SUMMARY  –  report yuqorisidagi KPI kartochkalari
# ---------------------------------------------------------------------------

def get_summary(data):
    rows = [r for r in data if r.get("shartnoma")]

    if not rows:
        return []

    total_amount    = sum(flt(r.get("amount"))    for r in rows)
    total_qty       = sum(flt(r.get("qty"))       for r in rows)
    unique_contracts = len({r["shartnoma"] for r in rows})
    unique_customers = len({r["customer"]  for r in rows if r.get("customer")})

    return [
        {
            "value"    : unique_contracts,
            "label"    : _("Jami Shartnomalar"),
            "datatype" : "Int",
            "indicator": "blue",
        },
        {
            "value"    : unique_customers,
            "label"    : _("Noyob Mijozlar"),
            "datatype" : "Int",
            "indicator": "green",
        },
        {
            "value"    : total_qty,
            "label"    : _("Jami Miqdor"),
            "datatype" : "Float",
            "indicator": "orange",
        },
        {
            "value"    : total_amount,
            "label"    : _("Jami Savdo (USD)"),
            "datatype" : "Currency",
            "indicator": "green",
        },
    ]
