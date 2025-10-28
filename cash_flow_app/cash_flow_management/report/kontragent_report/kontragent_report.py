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
        {"label": _("Party"), "fieldname": "party", "fieldtype": "Data", "width": 200},
        {"label": _("Party Type"), "fieldname": "party_type", "fieldtype": "Data", "width": 120},
        {"label": _("Opening Credit"), "fieldname": "opening_credit", "fieldtype": "Currency", "width": 130},
        {"label": _("Opening Debit"), "fieldname": "opening_debit", "fieldtype": "Currency", "width": 130},
        {"label": _("Transaction Credit"), "fieldname": "transaction_credit", "fieldtype": "Currency", "width": 130},
        {"label": _("Transaction Debit"), "fieldname": "transaction_debit", "fieldtype": "Currency", "width": 130},
        {"label": _("Closing Credit"), "fieldname": "closing_credit", "fieldtype": "Currency", "width": 130},
        {"label": _("Closing Debit"), "fieldname": "closing_debit", "fieldtype": "Currency", "width": 130},
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    opening_data = get_opening_balance(filters, conditions)
    transaction_data = get_transactions(filters, conditions)

    result = []
    all_parties = set(opening_data.keys()) | set(transaction_data.keys())

    for key in all_parties:
        party, party_type = key.split("|||")

        opening = opening_data.get(key, {"credit": 0, "debit": 0})
        txn = transaction_data.get(key, {"credit": 0, "debit": 0})

        opening_credit = flt(opening["credit"])
        opening_debit = flt(opening["debit"])
        transaction_credit = flt(txn["credit"])
        transaction_debit = flt(txn["debit"])

        closing_credit, closing_debit = 0, 0

        # ========================= CUSTOMER =========================
        if party_type == "Customer":
            # Customer bizdan tovar oladi (debit), to‘lov qiladi (credit)
            opening_balance = opening_debit - opening_credit
            movement = transaction_debit - transaction_credit
            closing_balance = opening_balance + movement

            if closing_balance >= 0:
                closing_debit = closing_balance  # mijoz hali qarzdor
            else:
                closing_credit = abs(closing_balance)  # ortiqcha to‘lagan

        # ========================= SUPPLIER =========================
        elif party_type == "Supplier":
            # Supplier bizga tovar beradi (credit), biz unga to‘lov qilamiz (debit)
            opening_balance = opening_credit - opening_debit
            movement = transaction_credit - transaction_debit
            closing_balance = opening_balance + movement

            if closing_balance >= 0:
                closing_credit = closing_balance  # biz hali qarzdormiz
            else:
                closing_debit = abs(closing_balance)  # ortiqcha to‘lov qilingan

        # ========================= EMPLOYEE / SHAREHOLDER =========================
        else:
            # Oddiy hisob: debet va kreditni to‘plab chiqamiz
            closing_credit = max(0, (opening_credit + transaction_credit) - (opening_debit + transaction_debit))
            closing_debit = max(0, (opening_debit + transaction_debit) - (opening_credit + transaction_credit))

        result.append({
            "party": party,
            "party_type": party_type,
            "opening_credit": opening_credit,
            "opening_debit": opening_debit,
            "transaction_credit": transaction_credit,
            "transaction_debit": transaction_debit,
            "closing_credit": closing_credit,
            "closing_debit": closing_debit,
        })

    # Tartiblash
    result = sorted(result, key=lambda x: x["party"])

    # Total qator
    if result:
        result.append({
            "party": _("Total"),
            "party_type": "",
            "opening_credit": sum(flt(r["opening_credit"]) for r in result),
            "opening_debit": sum(flt(r["opening_debit"]) for r in result),
            "transaction_credit": sum(flt(r["transaction_credit"]) for r in result),
            "transaction_debit": sum(flt(r["transaction_debit"]) for r in result),
            "closing_credit": sum(flt(r["closing_credit"]) for r in result),
            "closing_debit": sum(flt(r["closing_debit"]) for r in result),
        })

    return result


def get_opening_balance(filters, conditions):
    where_clause = " AND ".join(conditions + ["gle.posting_date < %(from_date)s"])
    query = f"""
        SELECT
            gle.party,
            gle.party_type,
            SUM(gle.credit_in_account_currency) AS credit,
            SUM(gle.debit_in_account_currency) AS debit
        FROM `tabGL Entry` gle
        WHERE {where_clause}
          AND gle.party IS NOT NULL AND gle.party != ''
          AND gle.is_cancelled = 0
        GROUP BY gle.party, gle.party_type
    """
    data = frappe.db.sql(query, filters, as_dict=True)
    result = {}
    for d in data:
        key = f"{d.party}|||{d.party_type}"
        result[key] = {"credit": flt(d.credit), "debit": flt(d.debit)}
    return result


def get_transactions(filters, conditions):
    where_clause = " AND ".join(conditions + [
        "gle.posting_date >= %(from_date)s",
        "gle.posting_date <= %(to_date)s",
    ])
    query = f"""
        SELECT
            gle.party,
            gle.party_type,
            SUM(gle.credit_in_account_currency) AS credit,
            SUM(gle.debit_in_account_currency) AS debit
        FROM `tabGL Entry` gle
        WHERE {where_clause}
          AND gle.party IS NOT NULL AND gle.party != ''
          AND gle.is_cancelled = 0
        GROUP BY gle.party, gle.party_type
    """
    data = frappe.db.sql(query, filters, as_dict=True)
    result = {}
    for d in data:
        key = f"{d.party}|||{d.party_type}"
        result[key] = {"credit": flt(d.credit), "debit": flt(d.debit)}
    return result


def get_conditions(filters):
    conditions = []
    if filters.get("company"):
        conditions.append("gle.company = %(company)s")
    if filters.get("party_type"):
        conditions.append("gle.party_type = %(party_type)s")
    if filters.get("party"):
        conditions.append("gle.party = %(party)s")
    return conditions
