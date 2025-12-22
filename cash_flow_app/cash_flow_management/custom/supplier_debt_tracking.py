import frappe
from frappe import _
from frappe.utils import flt, today

def update_supplier_debt_on_submit(doc, method=None):
    # print(f"\n🟢 update_supplier_debt_on_submit CALLED for {doc.name}")

    if not doc.items:
        return

    customer_name = doc.customer
    if not customer_name:
        frappe.throw(_("Customer required!"))

    supplier_debts = {}
    total_amount = 0

    for item in doc.items:
        if not item.custom_supplier:
            frappe.throw(_("Supplier required!"))

        supplier = item.custom_supplier
        item_total = flt(item.qty) * flt(item.rate)

        if supplier in supplier_debts:
            supplier_debts[supplier] += item_total
        else:
            supplier_debts[supplier] = item_total

        total_amount += item_total

    print(f"   Total: {total_amount}, Suppliers: {list(supplier_debts.keys())}")

    try:
        posting_date = doc.creation or today()
        create_gl_entries_for_installment(
            doc=doc,
            customer_name=customer_name,
            total_amount=total_amount,
            supplier_debts=supplier_debts,
            posting_date=posting_date
        )
        # print(f"   ✅ GL Entries created")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        frappe.log_error(str(e))

def create_gl_entries_for_installment(doc, customer_name, total_amount, supplier_debts, posting_date):
    company = frappe.defaults.get_user_default('Company') or 'Main'

    receivable_account = frappe.db.get_value(
        'Account',
        {'account_name': 'Debtors', 'company': company, 'is_group': 0},
        'name'
    )
    payable_account = frappe.db.get_value(
        'Account',
        {'account_name': 'Creditors', 'company': company, 'is_group': 0},
        'name'
    )

    # Customer Debit
    gle_cust = frappe.new_doc('GL Entry')
    gle_cust.posting_date = posting_date
    gle_cust.account = receivable_account
    gle_cust.party_type = 'Customer'
    gle_cust.party = customer_name
    gle_cust.debit = total_amount
    gle_cust.company = company
    gle_cust.voucher_type = 'Installment Application'
    gle_cust.voucher_no = doc.name
    gle_cust.insert(ignore_permissions=True)

    # Supplier Credits
    for supplier_name, amount in supplier_debts.items():
        gle_supp = frappe.new_doc('GL Entry')
        gle_supp.posting_date = posting_date
        gle_supp.account = payable_account
        gle_supp.party_type = 'Supplier'
        gle_supp.party = supplier_name
        gle_supp.credit = amount
        gle_supp.company = company
        gle_supp.voucher_type = 'Installment Application'
        gle_supp.voucher_no = doc.name
        gle_supp.insert(ignore_permissions=True)

        # Update supplier
        supplier = frappe.get_doc("Supplier", supplier_name)
        supplier.custom_total_debt = flt(supplier.get("custom_total_debt", 0)) + amount
        supplier.custom_remaining_debt = supplier.custom_total_debt - flt(supplier.get("custom_paid_amount", 0))
        supplier.save(ignore_permissions=True)

def update_supplier_debt_on_cancel_installment(doc, method=None):
    if not doc.items:
        return
    supplier_debts = {}
    for item in doc.items:
        if item.custom_supplier:
            supplier = item.custom_supplier
            item_total = flt(item.qty) * flt(item.rate)
            supplier_debts[supplier] = supplier_debts.get(supplier, 0) + item_total

    for supplier_name, amount in supplier_debts.items():
        supplier = frappe.get_doc("Supplier", supplier_name)
        supplier.custom_total_debt = max(0, flt(supplier.get("custom_total_debt", 0)) - amount)
        supplier.custom_remaining_debt = supplier.custom_total_debt - flt(supplier.get("custom_paid_amount", 0))
        supplier.save(ignore_permissions=True)

def update_supplier_debt_on_payment(doc, method=None):
    """
    Payment Entry submit bo'lganda supplier qarzini yangilash
    Pay: Biz to'laymiz -> custom_paid_amount ortadi, qarz kamayadi
    Receive: Supplier bizga to'laydi -> custom_total_debt ortadi (kredit), qarz ortadi
    """
    if doc.party_type != "Supplier":
        return

    supplier = frappe.get_doc("Supplier", doc.party)

    if doc.payment_type == "Pay":
        # Biz supplier'ga to'ladik - paid_amount ortadi
        supplier.custom_paid_amount = flt(supplier.get("custom_paid_amount", 0)) + flt(doc.paid_amount)
    elif doc.payment_type == "Receive":
        # Supplier bizga to'ladi - bu kredit (qarz ortadi)
        supplier.custom_total_debt = flt(supplier.get("custom_total_debt", 0)) + flt(doc.paid_amount)

    # Qoldiq qarzni hisoblash
    supplier.custom_remaining_debt = flt(supplier.get("custom_total_debt", 0)) - flt(supplier.get("custom_paid_amount", 0))
    supplier.save(ignore_permissions=True)

def update_supplier_debt_on_cancel_payment(doc, method=None):
    """
    Payment Entry cancel bo'lganda supplier qarzini qaytarish
    Pay cancel: custom_paid_amount kamayadi
    Receive cancel: custom_total_debt kamayadi
    """
    if doc.party_type != "Supplier":
        return

    supplier = frappe.get_doc("Supplier", doc.party)

    if doc.payment_type == "Pay":
        # Pay cancel - paid_amount kamayadi
        supplier.custom_paid_amount = max(0, flt(supplier.get("custom_paid_amount", 0)) - flt(doc.paid_amount))
    elif doc.payment_type == "Receive":
        # Receive cancel - total_debt kamayadi
        supplier.custom_total_debt = max(0, flt(supplier.get("custom_total_debt", 0)) - flt(doc.paid_amount))

    # Qoldiq qarzni hisoblash
    supplier.custom_remaining_debt = flt(supplier.get("custom_total_debt", 0)) - flt(supplier.get("custom_paid_amount", 0))
    supplier.save(ignore_permissions=True)
