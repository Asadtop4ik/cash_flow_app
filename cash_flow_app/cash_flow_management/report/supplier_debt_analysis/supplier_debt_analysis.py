# Copyright (c) 2025, Cash Flow App and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

def execute(filters=None):
    """
    Supplier Debt Analysis Report - Moliyaviy hisoblar
    Kredit (qarz) va Debit (to'lov) asosida Outstanding hisoblash
    """
    # Supplier majburiy
    if not filters.get("supplier"):
        frappe.throw(_("Please select a Supplier"))

    columns = get_columns()
    data = get_data(filters)
    summary = get_summary(data, filters)
    chart = None

    return columns, data, None, chart, summary, None

def get_columns():
    """Define report columns - yanada kengaytirilgan kenglik bilan"""
    return [
        {
            "label": "Sana",
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 200  # Kenglikni yanada oshirildi
        },
        {
            "label": "Hujjat",
            "fieldname": "document",
            "fieldtype": "Dynamic Link",
            "options": "document_type",
            "width": 250  # Kenglikni yanada oshirildi
        },
        {
            "label": "Mahsulot",
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 250  # Kenglikni yanada oshirildi
        },
        {
            "label": "Kredit",
            "fieldname": "kredit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 200  # Kenglikni yanada oshirildi
        },
        {
            "label": "Debit",
            "fieldname": "debit",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 200  # Kenglikni yanada oshirildi
        },
        {
            "label": "Qoldiq",
            "fieldname": "outstanding",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 200  # Kenglikni yanada oshirildi
        },
        {
            "label": "Izoh",
            "fieldname": "notes",
            "fieldtype": "Small Text",
            "width": 300  # Kenglikni yanada oshirildi
        },
        {
            "label": "To'lov usuli",
            "fieldname": "mode_of_payment",
            "fieldtype": "Data",
            "width": 200  # Kenglikni yanada oshirildi
        }
    ]

def get_data(filters):
    """
    Moliyaviy mantiq:
    - Installment Application = KREDIT (qarz oshadi)
    - Payment Entry = DEBIT (qarz kamayadi)
    - Outstanding = Nachalnaya Ostatok + Total Kredit - Total Debit
    """
    supplier = filters.get("supplier")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    # 1. Get Installment Applications (KREDIT - qarz)
    installment_conditions = []
    if from_date:
        installment_conditions.append("AND DATE(ia.transaction_date) >= %(from_date)s")
    if to_date:
        installment_conditions.append("AND DATE(ia.transaction_date) <= %(to_date)s")

    installment_where = " ".join(installment_conditions)

    installments_query = f"""
        SELECT
            'Installment Application' as document_type,
            ia.name as document,
            DATE(ia.transaction_date) as transaction_date,
            item.item_code as item_code,
            COALESCE(item.item_name, '') as item_name,
            (item.qty * item.rate) as kredit,
            0 as debit,
            COALESCE(ia.notes, '') as notes,
            NULL as mode_of_payment,
            ia.creation,
            'USD' as currency
        FROM `tabInstallment Application` ia
        INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
        WHERE ia.docstatus = 1
            AND item.custom_supplier = %(supplier)s
            {installment_where}
        ORDER BY ia.transaction_date, ia.creation
    """

    # 2. Get Payment Entries (DEBIT - to'lov)
    payment_conditions = []
    if from_date:
        payment_conditions.append("AND DATE(pe.posting_date) >= %(from_date)s")
    if to_date:
        payment_conditions.append("AND DATE(pe.posting_date) <= %(to_date)s")

    payment_where = " ".join(payment_conditions)

    payments_query = f"""
        SELECT
            'Payment Entry' as document_type,
            pe.name as document,
            DATE(pe.posting_date) as transaction_date,
            NULL as item_code,
            'To''lov' as item_name,
            0 as kredit,
            pe.paid_amount as debit,
            COALESCE(pe.remarks, '') as notes,
            COALESCE(pe.mode_of_payment, '') as mode_of_payment,
            pe.creation,
            'USD' as currency
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1
            AND pe.party_type = 'Supplier'
            AND pe.party = %(supplier)s
            AND pe.payment_type = 'Pay'
            {payment_where}
        ORDER BY pe.posting_date, pe.creation
    """

    # 3. Execute queries with detailed error logging
    installments = []
    payments = []

    try:
        installments = frappe.db.sql(installments_query, filters, as_dict=1)
        frappe.log_error(
            f"Installments Query Success:\nSupplier: {supplier}\nFound: {len(installments)}\nQuery: {installments_query}\nFilters: {filters}",
            "Supplier Debt Analysis - Installments"
        )
    except Exception as e:
        error_msg = f"Installments Query Failed:\nError: {str(e)}\nQuery: {installments_query}\nFilters: {filters}"
        frappe.log_error(error_msg, "Supplier Debt Analysis - ERROR")
        frappe.msgprint(_("Error loading installments. Check Error Log for details."), indicator='red')

    try:
        payments = frappe.db.sql(payments_query, filters, as_dict=1)
        frappe.log_error(
            f"Payments Query Success:\nSupplier: {supplier}\nFound: {len(payments)}\nQuery: {payments_query}\nFilters: {filters}",
            "Supplier Debt Analysis - Payments"
        )
    except Exception as e:
        error_msg = f"Payments Query Failed:\nError: {str(e)}\nQuery: {payments_query}\nFilters: {filters}"
        frappe.log_error(error_msg, "Supplier Debt Analysis - ERROR")
        frappe.msgprint(_("Error loading payments. Check Error Log for details."), indicator='red')

    # 4. Combine and sort by date
    all_transactions = installments + payments
    all_transactions.sort(key=lambda x: (x.transaction_date, x.creation))

    if not all_transactions:
        frappe.log_error(
            f"No transactions found:\nSupplier: {supplier}\nFrom: {from_date}\nTo: {to_date}\nInstallments: {len(installments)}\nPayments: {len(payments)}",
            "Supplier Debt Analysis - Empty Result"
        )
        return []

    # 5. Calculate Nachalnaya Ostatok (from_date dan oldin qolgan qarz)
    nachalnaya_ostatok = 0
    if from_date:
        nachalnaya_ostatok = get_nachalnaya_ostatok(supplier, from_date)

    # 6. Add initial balance as a transaction if non-zero
    result_data = []
    if nachalnaya_ostatok != 0:
        result_data.append({
            'transaction_date': from_date,
            'document': 'Initial Balance',
            'document_type': 'Balance Adjustment',
            'item_name': 'Boshlang\'ich qoldiq',
            'kredit': nachalnaya_ostatok if nachalnaya_ostatok > 0 else 0,
            'debit': 0 if nachalnaya_ostatok > 0 else abs(nachalnaya_ostatok),
            'outstanding': nachalnaya_ostatok,
            'notes': 'Avtomatik hisoblangan boshlang\'ich qoldiq',
            'mode_of_payment': None,
            'currency': 'USD',
            'is_initial_row': 1
        })

    # 7. Calculate running balance (Outstanding)
    running_outstanding = nachalnaya_ostatok
    for txn in all_transactions:
        kredit = flt(txn.get('kredit', 0))
        debit = flt(txn.get('debit', 0))
        running_outstanding = running_outstanding + kredit - debit
        txn['outstanding'] = running_outstanding
        result_data.append(txn)

    # 8. Add TOTAL row at the end
    if result_data:
        total_kredit = sum([flt(d.get('kredit', 0)) for d in result_data if not d.get('is_initial_row') and not d.get('is_total_row')])
        total_debit = sum([flt(d.get('debit', 0)) for d in result_data if not d.get('is_initial_row') and not d.get('is_total_row')])
        final_outstanding = nachalnaya_ostatok + total_kredit - total_debit

        result_data.append({
            'transaction_date': None,
            'document': None,
            'document_type': None,
            'item_name': 'JAMI',
            'kredit': total_kredit,
            'debit': total_debit,
            'outstanding': final_outstanding,
            'notes': None,
            'mode_of_payment': None,
            'currency': 'USD',
            'is_total_row': 1
        })

    return result_data

def get_nachalnaya_ostatok(supplier, from_date):
    """
    from_date dan OLDIN qolgan qarzni hisoblash
    Formula: Oldingi Kredit - Oldingi Debit = Qoldiq
    """
    try:
        # from_date ni to'g'ri formatga keltirish
        from_date = getdate(from_date)
        frappe.log_error(f"Calculating Nachalnaya Ostatok for Supplier: {supplier}, From Date: {from_date}", "Debug - Initial Balance")

        # Oldingi Kredit (from_date dan oldin qarzlar)
        prev_kredit_query = """
            SELECT COALESCE(SUM(item.qty * item.rate), 0) as total
            FROM `tabInstallment Application` ia
            INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
            WHERE ia.docstatus = 1
                AND item.custom_supplier = %s
                AND DATE(ia.transaction_date) < %s
        """
        prev_kredit_result = frappe.db.sql(prev_kredit_query, (supplier, from_date), as_dict=1)
        prev_kredit = flt(prev_kredit_result[0].total) if prev_kredit_result and prev_kredit_result[0].total is not None else 0
        frappe.log_error(f"Previous Credits: {prev_kredit}", "Debug - Previous Credits")

        # Oldingi Debit (from_date dan oldin to'lovlar)
        prev_debit_query = """
            SELECT COALESCE(SUM(paid_amount), 0) as total
            FROM `tabPayment Entry` pe
            WHERE pe.docstatus = 1
                AND pe.party_type = 'Supplier'
                AND pe.party = %s
                AND DATE(pe.posting_date) < %s
        """
        prev_debit_result = frappe.db.sql(prev_debit_query, (supplier, from_date), as_dict=1)
        prev_debit = flt(prev_debit_result[0].total) if prev_debit_result and prev_debit_result[0].total is not None else 0
        frappe.log_error(f"Previous Debits: {prev_debit}", "Debug - Previous Debits")

        # Nachalnaya Ostatok = Kredit - Debit
        nachalnaya_ostatok = prev_kredit - prev_debit
        frappe.log_error(f"Calculated Nachalnaya Ostatok: {nachalnaya_ostatok}", "Debug - Final Balance")

        return nachalnaya_ostatok

    except Exception as e:
        error_msg = f"Error calculating Nachalnaya Ostatok: {str(e)}\nSupplier: {supplier}\nFrom Date: {from_date}"
        frappe.log_error(error_msg, "Supplier Debt Analysis - ERROR")
        frappe.msgprint(_("Error calculating initial balance. Check Error Log for details."), indicator='red')
        return 0

def get_summary(data, filters):
    """
    Generate summary cards - moliyaviy dashboard
    6 ta card: Nachalnaya, Kredit, Debit, To'lov operatsiyalari, Tovar operatsiyalari, Ostatok
    """
    if not data:
        return []

    # Remove total row for calculation
    data_without_total = [d for d in data if not d.get('is_total_row')]

    if not data_without_total:
        return []

    # Istisno qilish uchun initial row ni olib tashlash
    data_without_initial_and_total = [d for d in data_without_total if not d.get('is_initial_row')]

    supplier = filters.get("supplier")
    from_date = filters.get("from_date")

    # 1. Nachalnaya Ostatok (avvalgi qarz)
    nachalnaya_ostatok = 0
    if from_date:
        nachalnaya_ostatok = get_nachalnaya_ostatok(supplier, from_date)

    # 2. Total Kredit (yangi qarzlar)
    total_kredit = sum([flt(d.get('kredit', 0)) for d in data_without_initial_and_total])

    # 3. Total Debit (yangi to'lovlar)
    total_debit = sum([flt(d.get('debit', 0)) for d in data_without_initial_and_total])

    # 4. Ostatok na Konets (oxirgi qarz qoldig'i)
    ostatok_na_konets = nachalnaya_ostatok + total_kredit - total_debit

    # 5. Oborot po Tovar (tovar tranzaksiyalari soni)
    oborot_po_tovar = len([d for d in data_without_initial_and_total if flt(d.get('kredit', 0)) > 0])

    # 6. Denezhniy Oborot (to'lov tranzaksiyalari soni)
    denezhniy_oborot = len([d for d in data_without_initial_and_total if flt(d.get('debit', 0)) > 0])

    # Summary kartalarni bir qatorda ko'rsatish uchun ro'yxat sifatida qaytarish
    # To'lov operatsiyalari Tovar operatsiyalari oldida tursin, "Oxirgi qoldiq" ham birinchi qatorda
    summary = [
        {
            "value": nachalnaya_ostatok,
            "indicator": "blue",
            "label": "Boshlang'ich qoldiq",
            "datatype": "Currency",
            "currency": "USD"
        },
        {
            "value": total_kredit,
            "indicator": "red",
            "label": "Jami Kredit",
            "datatype": "Currency",
            "currency": "USD"
        },
        {
            "value": total_debit,
            "indicator": "green",
            "label": "Jami Debit",
            "datatype": "Currency",
            "currency": "USD"
        },
        {
            "value": denezhniy_oborot,
            "indicator": "blue",
            "label": "To'lov operatsiyalari",
            "datatype": "Int"
        },
        {
            "value": oborot_po_tovar,
            "indicator": "blue",
            "label": "Tovar operatsiyalari",
            "datatype": "Int"
        },
        {
            "value": ostatok_na_konets,
            "indicator": "orange" if ostatok_na_konets > 0 else "green",
            "label": "Oxirgi qoldiq",
            "datatype": "Currency",
            "currency": "USD"
        }
    ]

    return summary


