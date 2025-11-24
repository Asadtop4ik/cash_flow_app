import frappe
from frappe.utils import flt


def execute():
	"""
	Barcha supplier'larning qarz ma'lumotlarini qayta hisoblash.

	Mantiq:
	- custom_total_debt = Installment Application + Payment Entry (Receive)
	- custom_paid_amount = Payment Entry (Pay)
	- custom_remaining_debt = custom_total_debt - custom_paid_amount
	"""
	suppliers = frappe.get_all("Supplier", fields=["name"])

	for s in suppliers:
		supplier_name = s.name

		# 1. Installment Application - KREDIT (biz supplier'dan qarz oldik)
		installment_total = frappe.db.sql("""
			SELECT COALESCE(SUM(item.qty * item.rate), 0) as total
			FROM `tabInstallment Application` ia
			INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
			WHERE ia.docstatus = 1
			AND item.custom_supplier = %s
		""", (supplier_name,), as_dict=True)[0].total or 0

		# 2. Payment Entry Receive - KREDIT (supplier bizga pul qaytardi)
		receive_total = frappe.db.sql("""
			SELECT COALESCE(SUM(paid_amount), 0) as total
			FROM `tabPayment Entry`
			WHERE party = %s
			AND party_type = 'Supplier'
			AND payment_type = 'Receive'
			AND docstatus = 1
		""", (supplier_name,), as_dict=True)[0].total or 0

		# 3. Payment Entry Pay - DEBIT (biz supplier'ga to'ladik)
		pay_total = frappe.db.sql("""
			SELECT COALESCE(SUM(paid_amount), 0) as total
			FROM `tabPayment Entry`
			WHERE party = %s
			AND party_type = 'Supplier'
			AND payment_type = 'Pay'
			AND docstatus = 1
		""", (supplier_name,), as_dict=True)[0].total or 0

		# Hisoblash
		total_debt = flt(installment_total) + flt(receive_total)
		paid_amount = flt(pay_total)
		remaining_debt = total_debt - paid_amount

		# Yangilash
		frappe.db.set_value("Supplier", supplier_name, {
			"custom_total_debt": total_debt,
			"custom_paid_amount": paid_amount,
			"custom_remaining_debt": remaining_debt
		}, update_modified=False)

	frappe.db.commit()
	print(f"✅ {len(suppliers)} ta supplier qayta hisoblandi")
