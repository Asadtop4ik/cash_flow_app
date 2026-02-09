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
	"""Define report columns - custom_cashier o'rniga Account"""
	return [
		{
			"label": "Sana",
			"fieldname": "transaction_date",
			"fieldtype": "Date",
			"width": 100
		},
		{
			"label": "Hujjat",
			"fieldname": "document",
			"fieldtype": "Dynamic Link",
			"options": "document_type",
			"width": 200
		},
		{
			"label": "Mahsulot",
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": "Kredit",
			"fieldname": "kredit",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 120
		},
		{
			"label": "Debit",
			"fieldname": "debit",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		},
		{
			"label": "Qoldiq",
			"fieldname": "outstanding",
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150
		},
		{
			"label": "Kassa",
			"fieldname": "cash_account",
			"fieldtype": "Link",
			"options": "Account",
			"width": 150
		},
		{
			"label": "Izoh",
			"fieldname": "note_text",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": "Izoh Kategoriyasi",
			"fieldname": "note_category",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": "Izoh Sanasi",
			"fieldname": "note_date",
			"fieldtype": "Date",
			"width": 100
		}
	]


def get_data(filters):
	"""
	Moliyaviy mantiq:
	- Installment Application = KREDIT (qarz oshadi)
	- Payment Entry = DEBIT (qarz kamayadi)
	- FAQAT docstatus = 1 (Submitted) hisoblanadi
	- Cancelled (docstatus = 2) hisobotda ko'rinmaydi
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
			NULL as cash_account,
			ia.creation,
			'USD' as currency,
			NULL as note_text,
			NULL as note_category,
			NULL as note_date
		FROM `tabInstallment Application` ia
		INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
		WHERE ia.docstatus = 1
			AND item.custom_supplier = %(supplier)s
			{installment_where}
		ORDER BY ia.transaction_date, ia.creation
	"""

	# 2. Get Payment Entries - Pay (DEBIT - biz to'laymiz)
	payment_conditions = []
	if from_date:
		payment_conditions.append("AND DATE(pe.posting_date) >= %(from_date)s")
	if to_date:
		payment_conditions.append("AND DATE(pe.posting_date) <= %(to_date)s")

	payment_where = " ".join(payment_conditions)

	payments_pay_query = f"""
		SELECT
			'Payment Entry' as document_type,
			pe.name as document,
			DATE(pe.posting_date) as transaction_date,
			NULL as item_code,
			'To''lov' as item_name,
			0 as kredit,
			pe.paid_amount as debit,
			COALESCE(pe.remarks, '') as notes,
			COALESCE(pe.paid_from, '') as cash_account,
			pe.creation,
			'USD' as currency,
			sn.note_text as note_text,
			sn.note_category as note_category,
			sn.note_date as note_date
		FROM `tabPayment Entry` pe
		LEFT JOIN (
			SELECT payment_reference, note_text, note_category, note_date
			FROM `tabSupplier Nots` sn1
			WHERE sn1.creation = (
				SELECT MAX(sn2.creation)
				FROM `tabSupplier Nots` sn2
				WHERE sn2.payment_reference = sn1.payment_reference
			)
		) sn ON sn.payment_reference = pe.name
		WHERE pe.docstatus = 1
			AND pe.party_type = 'Supplier'
			AND pe.party = %(supplier)s
			AND pe.payment_type = 'Pay'
			{payment_where}
		ORDER BY pe.posting_date, pe.creation
	"""

	# 3. Get Payment Entries - Receive (KREDIT - supplier bizga to'laydi)
	payments_receive_query = f"""
		SELECT
			'Payment Entry' as document_type,
			pe.name as document,
			DATE(pe.posting_date) as transaction_date,
			NULL as item_code,
			'Qaytarilgan pul' as item_name,
			pe.paid_amount as kredit,
			0 as debit,
			COALESCE(pe.remarks, '') as notes,
			COALESCE(pe.paid_to, '') as cash_account,
			pe.creation,
			'USD' as currency,
			sn.note_text as note_text,
			sn.note_category as note_category,
			sn.note_date as note_date
		FROM `tabPayment Entry` pe
		LEFT JOIN (
			SELECT payment_reference, note_text, note_category, note_date
			FROM `tabSupplier Nots` sn1
			WHERE sn1.creation = (
				SELECT MAX(sn2.creation)
				FROM `tabSupplier Nots` sn2
				WHERE sn2.payment_reference = sn1.payment_reference
			)
		) sn ON sn.payment_reference = pe.name
		WHERE pe.docstatus = 1
			AND pe.party_type = 'Supplier'
			AND pe.party = %(supplier)s
			AND pe.payment_type = 'Receive'
			{payment_where}
		ORDER BY pe.posting_date, pe.creation
	"""

	# 4. Execute queries
	installments = []
	payments_pay = []
	payments_receive = []

	try:
		installments = frappe.db.sql(installments_query, filters, as_dict=1)
	except Exception as e:
		error_msg = f"Installments Query Failed:\nError: {str(e)}"
		frappe.log_error(error_msg, "Supplier Debt Analysis - ERROR")
		frappe.msgprint(_("Error loading installments. Check Error Log for details."),
						indicator='red')

	try:
		payments_pay = frappe.db.sql(payments_pay_query, filters, as_dict=1)
	except Exception as e:
		error_msg = f"Payments Pay Query Failed:\nError: {str(e)}"
		frappe.log_error(error_msg, "Supplier Debt Analysis - ERROR")
		frappe.msgprint(_("Error loading payments (Pay). Check Error Log for details."), indicator='red')

	try:
		payments_receive = frappe.db.sql(payments_receive_query, filters, as_dict=1)
	except Exception as e:
		error_msg = f"Payments Receive Query Failed:\nError: {str(e)}"
		frappe.log_error(error_msg, "Supplier Debt Analysis - ERROR")
		frappe.msgprint(_("Error loading payments (Receive). Check Error Log for details."), indicator='red')

	# 5. Combine and sort by date
	all_transactions = installments + payments_pay + payments_receive
	all_transactions.sort(key=lambda x: (x.transaction_date, x.creation))

	if not all_transactions:
		frappe.log_error(
			f"No transactions found:\nSupplier: {supplier}\nFrom: {from_date}\nTo: {to_date}",
			"Supplier Debt Analysis - Empty Result"
		)
		return []

	# 5. Calculate Nachalnaya Ostatok (from_date dan oldin qolgan qarz)
	nachalnaya_ostatok = 0
	if from_date:
		nachalnaya_ostatok = get_nachalnaya_ostatok(supplier, from_date)

	# 6. Add initial balance row if non-zero
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
			'cash_account': None,
			'currency': 'USD',
			'is_initial_row': 1
		})

	# 7. Calculate running balance (Outstanding)
	running_outstanding = nachalnaya_ostatok

	for txn in all_transactions:
		kredit = flt(txn.get('kredit', 0))
		debit = flt(txn.get('debit', 0))

		# Outstanding formula: Ostatok + Kredit - Debit
		running_outstanding = running_outstanding + kredit - debit
		txn['outstanding'] = running_outstanding

		result_data.append(txn)

	# 8. Add TOTAL row at the end
	if result_data:
		# Initial row ni hisobga olmaslik
		data_without_initial = [d for d in result_data if not d.get('is_initial_row')]

		total_kredit = sum([flt(d.get('kredit', 0)) for d in data_without_initial])
		total_debit = sum([flt(d.get('debit', 0)) for d in data_without_initial])
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
			'cash_account': None,
			'currency': 'USD',
			'is_total_row': 1
		})

	return result_data


def get_nachalnaya_ostatok(supplier, from_date):
	"""
	from_date dan OLDIN qolgan qarzni hisoblash
	Formula: (Oldingi Installment Kredit + Oldingi Receive Kredit) - Oldingi Pay Debit = Qoldiq
	FAQAT docstatus = 1 (Submitted) hisoblanadi
	"""
	try:
		from_date = getdate(from_date)

		# 1. Oldingi Installment Kredit (from_date dan oldin qarzlar)
		prev_installment_kredit_query = """
			SELECT COALESCE(SUM(item.qty * item.rate), 0) as total
			FROM `tabInstallment Application` ia
			INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
			WHERE ia.docstatus = 1
				AND item.custom_supplier = %s
				AND DATE(ia.transaction_date) < %s
		"""
		prev_installment_result = frappe.db.sql(prev_installment_kredit_query, (supplier, from_date), as_dict=1)
		prev_installment_kredit = flt(prev_installment_result[0].total) if prev_installment_result else 0

		# 2. Oldingi Pay Debit (from_date dan oldin biz to'lagan to'lovlar)
		prev_pay_debit_query = """
			SELECT COALESCE(SUM(paid_amount), 0) as total
			FROM `tabPayment Entry`
			WHERE docstatus = 1
				AND party_type = 'Supplier'
				AND party = %s
				AND payment_type = 'Pay'
				AND DATE(posting_date) < %s
		"""
		prev_pay_result = frappe.db.sql(prev_pay_debit_query, (supplier, from_date), as_dict=1)
		prev_pay_debit = flt(prev_pay_result[0].total) if prev_pay_result else 0

		# 3. Oldingi Receive Kredit (from_date dan oldin supplier qaytargan pullar)
		prev_receive_kredit_query = """
			SELECT COALESCE(SUM(paid_amount), 0) as total
			FROM `tabPayment Entry`
			WHERE docstatus = 1
				AND party_type = 'Supplier'
				AND party = %s
				AND payment_type = 'Receive'
				AND DATE(posting_date) < %s
		"""
		prev_receive_result = frappe.db.sql(prev_receive_kredit_query, (supplier, from_date), as_dict=1)
		prev_receive_kredit = flt(prev_receive_result[0].total) if prev_receive_result else 0

		# Nachalnaya Ostatok = (Installment Kredit + Receive Kredit) - Pay Debit
		total_kredit = prev_installment_kredit + prev_receive_kredit
		return total_kredit - prev_pay_debit

	except Exception as e:
		frappe.log_error(f"Error calculating Nachalnaya Ostatok: {str(e)}",
						 "Supplier Debt Analysis")
		return 0


def get_summary(data, filters):
	"""
	Generate summary cards - moliyaviy dashboard
	"""
	if not data:
		return []

	# Remove total and initial rows for calculation
	data_without_special = [d for d in data if
							not d.get('is_total_row') and not d.get('is_initial_row')]

	if not data_without_special:
		# Agar faqat initial row bo'lsa
		supplier = filters.get("supplier")
		from_date = filters.get("from_date")

		nachalnaya_ostatok = 0
		if from_date:
			nachalnaya_ostatok = get_nachalnaya_ostatok(supplier, from_date)

		return [
			{
				"value": nachalnaya_ostatok,
				"indicator": "blue",
				"label": "Boshlang'ich qoldiq",
				"datatype": "Currency",
				"currency": "USD"
			},
			{
				"value": 0,
				"indicator": "red",
				"label": "Jami Kredit",
				"datatype": "Currency",
				"currency": "USD"
			},
			{
				"value": 0,
				"indicator": "green",
				"label": "Jami Debit",
				"datatype": "Currency",
				"currency": "USD"
			},
			{
				"value": nachalnaya_ostatok,
				"indicator": "orange" if nachalnaya_ostatok > 0 else "green",
				"label": "Oxirgi qoldiq",
				"datatype": "Currency",
				"currency": "USD"
			}
		]

	supplier = filters.get("supplier")
	from_date = filters.get("from_date")

	# 1. Nachalnaya Ostatok
	nachalnaya_ostatok = 0
	if from_date:
		nachalnaya_ostatok = get_nachalnaya_ostatok(supplier, from_date)

	# 2. Total Kredit
	total_kredit = sum([flt(d.get('kredit', 0)) for d in data_without_special])

	# 3. Total Debit
	total_debit = sum([flt(d.get('debit', 0)) for d in data_without_special])

	# 4. Ostatok na Konets
	ostatok_na_konets = nachalnaya_ostatok + total_kredit - total_debit

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
			"value": ostatok_na_konets,
			"indicator": "orange" if ostatok_na_konets > 0 else "green",
			"label": "Oxirgi qoldiq",
			"datatype": "Currency",
			"currency": "USD"
		}
	]

	return summary


@frappe.whitelist()
def save_supplier_note(payment_reference, note_text, note_category="Eslatma", supplier=None):
	"""Save a new supplier note for Payment Entry"""
	try:
		if not payment_reference:
			return {"success": False, "message": "Payment Entry ko'rsatilmagan"}

		if not note_text or not note_text.strip():
			return {"success": False, "message": "Izoh matni bo'sh"}

		if not frappe.db.exists("Payment Entry", payment_reference):
			return {"success": False, "message": f"Payment Entry topilmadi: {payment_reference}"}

		# Get supplier from Payment Entry if not provided
		if not supplier:
			supplier = frappe.db.get_value("Payment Entry", payment_reference, "party")

		from frappe.utils import nowdate

		doc = frappe.new_doc("Supplier Nots")
		doc.payment_reference = payment_reference
		doc.supplier = supplier
		doc.note_text = note_text.strip()
		doc.note_category = note_category or "Eslatma"
		doc.note_date = nowdate()
		doc.created_by_user = frappe.session.user

		doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {
			"success": True,
			"message": "Izoh saqlandi",
			"note_id": doc.name
		}

	except Exception as e:
		frappe.log_error(f"Supplier Note save error: {str(e)}", "Save Supplier Note Error")
		return {"success": False, "message": f"Xatolik: {str(e)}"}


@frappe.whitelist()
def get_supplier_notes(payment_reference):
	"""Get all notes for a Payment Entry"""
	try:
		notes = frappe.get_all(
			"Supplier Nots",
			filters={"payment_reference": payment_reference},
			fields=["name", "note_text", "note_category", "note_date", "created_by_user"],
			order_by="creation desc"
		)

		return {"success": True, "notes": notes}

	except Exception as e:
		frappe.log_error(f"Get supplier notes error: {str(e)}")
		return {"success": False, "message": str(e), "notes": []}
