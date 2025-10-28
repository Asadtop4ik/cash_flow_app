# Copyright (c) 2025, Your Company
# API for Payment Entry

import frappe
from frappe.utils import getdate, nowdate, date_diff

@frappe.whitelist()
def get_mode_account(mode_of_payment, company):
    """Get default account for mode of payment"""
    if not mode_of_payment or not company:
        return None
    
    accounts = frappe.get_all(
        "Mode of Payment Account",
        filters={
            "parent": mode_of_payment,
            "company": company
        },
        fields=["default_account"]
    )
    
    if accounts:
        return accounts[0].default_account
    
    return None

@frappe.whitelist()
def get_customer_contracts(customer):
    """Get active contracts for customer"""
    if not customer:
        return []
    
    contracts = frappe.get_all(
        "Sales Order",
        filters={
            "customer": customer,
            "docstatus": 1,
            "status": ["not in", ["Completed", "Cancelled"]]
        },
        fields=["name", "transaction_date", "grand_total", "customer_name"],
        order_by="transaction_date desc"
    )
    
    return contracts

@frappe.whitelist()
def on_payment_submit(doc, method):
	"""Payment Entry submit bo'lganda customer classification avtomatik o'zgaradi"""
	if doc.party_type == "Customer" and doc.party:
		update_customer_classification(doc.party)

def update_customer_classification(customer_name):
	"""Customer classification qiladi (A, B yoki C)"""
	if not customer_name:
		return

	try:
		# Faqat to'lanmagan invoicelarni olish
		overdue_invoices = frappe.db.sql("""
            SELECT
                name,
                due_date,
                outstanding_amount,
                DATEDIFF(CURDATE(), due_date) as days_overdue
            FROM
                `tabSales Invoice`
            WHERE
                customer = %(customer)s
                AND docstatus = 1
                AND status != 'Paid'
                AND outstanding_amount > 0
                AND due_date < CURDATE()
            ORDER BY
                days_overdue DESC
            LIMIT 1
        """, {"customer": customer_name}, as_dict=1)

		# Installment Application dan ham tekshirish
		overdue_installments = frappe.db.sql("""
            SELECT
                ip.name,
                ip.due_date,
                ip.amount - IFNULL(ip.paid_amount, 0) as outstanding,
                DATEDIFF(CURDATE(), ip.due_date) as days_overdue
            FROM
                `tabInstallment Payment` ip
            INNER JOIN
                `tabInstallment Application` ia ON ip.parent = ia.name
            WHERE
                ia.customer = %(customer)s
                AND ia.docstatus = 1
                AND ip.status != 'Paid'
                AND (ip.amount - IFNULL(ip.paid_amount, 0)) > 0
                AND ip.due_date < CURDATE()
            ORDER BY
                days_overdue DESC
            LIMIT 1
        """, {"customer": customer_name}, as_dict=1)

		# Eng katta kechikishni topish
		max_days_overdue = 0

		if overdue_invoices:
			max_days_overdue = max(max_days_overdue, overdue_invoices[0].days_overdue)

		if overdue_installments:
			max_days_overdue = max(max_days_overdue, overdue_installments[0].days_overdue)

		# Classification logic
		new_classification = get_classification(max_days_overdue)

		# Customer ni update qilish
		set_customer_classification(customer_name, new_classification)

		# Log qilish
		frappe.logger().info(
			f"Customer '{customer_name}' classification updated to '{new_classification}' "
			f"(Max overdue: {max_days_overdue} days)"
		)

	except Exception as e:
		frappe.log_error(
			message=f"Customer classification update error: {str(e)}",
			title=f"Customer Classification Error - {customer_name}"
		)


def get_classification(days_overdue):
	"""
	Classification logic:
	- A: 0 kun kechikish (vaqtida to'laydi)
	- B: 1-30 kun kechikish (oz-oz kechiktiradi)
	- C: 30+ kun kechikish (jiddiy kechiktiruvchi)
	"""
	if days_overdue > 30:
		return "C"
	elif days_overdue >= 1:
		return "B"
	else:
		return "A"


def set_customer_classification(customer_name, classification):
	"""Customer classification ni saqlaydi"""
	try:
		customer = frappe.get_doc("Customer", customer_name)

		if customer.get("customer_classification") != classification:
			old_classification = customer.get("customer_classification", "A")

			# Update qilish
			customer.customer_classification = classification
			customer.flags.ignore_permissions = True
			customer.flags.ignore_validate = True
			customer.flags.ignore_mandatory = True
			customer.save()

			# Comment qo'shish
			customer.add_comment(
				"Info",
				f"Classification changed: {old_classification} → {classification}"
			)

			frappe.db.commit()

			frappe.msgprint(
				f"Customer '{customer_name}' classification updated to '{classification}'",
				alert=True,
				indicator="green"
			)

	except Exception as e:
		frappe.log_error(
			message=f"Customer '{customer_name}' save error: {str(e)}",
			title="Customer Classification Update Error"
		)


@frappe.whitelist()
def update_all_customers_classification():
	"""Barcha customerlarning classification ni tekshiradi (Scheduled)"""
	customers = frappe.get_all("Customer", fields=["name"])

	for customer in customers:
		try:
			update_customer_classification(customer.name)
		except Exception as e:
			frappe.log_error(
				message=f"Scheduled classification update error for {customer.name}: {str(e)}",
				title="Customer Classification - Scheduled Error"
			)

	frappe.db.commit()

