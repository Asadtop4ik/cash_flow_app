import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data()
    return columns, data


def get_columns():
    return [
        {
            "label": "Sales Order",
            "fieldname": "sales_order",
            "fieldtype": "Link",
            "options": "Sales Order",
            "width": 180,
        },
        {
            "label": "Customer",
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 200,
        },
        {
            "label": "SO Date",
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": "Grand Total",
            "fieldname": "grand_total",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 140,
        },
        {
            "label": "Total Paid",
            "fieldname": "total_paid",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 140,
        },
        {
            "label": "Overpaid Amount",
            "fieldname": "overpaid_amount",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 150,
        },
        {
            "label": "No. of Payments",
            "fieldname": "payment_count",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": "Currency",
            "fieldname": "currency",
            "fieldtype": "Data",
            "hidden": 1,
            "width": 80,
        },
    ]


def get_data():
    return frappe.db.sql(
        """
        SELECT
            so.name                                AS sales_order,
            so.customer                            AS customer,
            so.transaction_date                    AS transaction_date,
            so.grand_total                         AS grand_total,
            so.currency                            AS currency,
            SUM(pe.paid_amount)                    AS total_paid,
            SUM(pe.paid_amount) - so.grand_total   AS overpaid_amount,
            COUNT(pe.name)                         AS payment_count
        FROM
            `tabSales Order` so
        LEFT JOIN
            `tabPayment Entry` pe
                ON  pe.custom_contract_reference = so.name
                AND pe.docstatus = 1
        WHERE
            so.docstatus = 1
        GROUP BY
            so.name,
            so.customer,
            so.transaction_date,
            so.grand_total,
            so.currency
        HAVING
            SUM(pe.paid_amount) > so.grand_total
        ORDER BY
            overpaid_amount DESC
        """,
        as_dict=True,
    )
