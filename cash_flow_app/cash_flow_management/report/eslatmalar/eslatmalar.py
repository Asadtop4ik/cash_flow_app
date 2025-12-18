# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days


def execute(filters=None):
	"""Eslatmalar - Qarzdorlik guruhlari va izohlar"""
	if not filters:
		filters = {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	"""Report columns definition"""
	return [
		{
			"fieldname": "group_header",
			"label": _("Guruh"),
			"fieldtype": "Data",
			"width": 200
		},
		{
			"fieldname": "contract_link",
			"label": _("Shartnoma"),
			"fieldtype": "Link",
			"options": "Installment Application",
			"width": 120
		},
		{
			"fieldname": "customer_link",
			"label": _("Klient"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "current_month_payment",
			"label": _("Shu Oy To'lovi"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "due_amount",
			"label": _("Yana To'lashi Kerak"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "remaining_debt",
			"label": _("Qolgan Qarz"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "note_text",
			"label": _("So'nggi Izoh"),
			"fieldtype": "Data",
			"width": 250
		},
		{
			"fieldname": "note_category",
			"label": _("Kategoriya"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "note_date",
			"label": _("Izoh Sanasi"),
			"fieldtype": "Date",
			"width": 100
		}
	]


def get_data(filters):
	"""Get report data with notes"""
	today = getdate(nowdate())
	one_week_later = add_days(today, 7)
	two_weeks_ago = add_days(today, -14)

	applications = frappe.get_all(
		"Installment Application",
		filters={"docstatus": 1},
		fields=["name", "customer", "custom_grand_total_with_interest", "sales_order"]
	)

	groups = {
		"overdue_2weeks": [],
		"overdue_more": [],
		"today": [],
		"week": [],
		"later": []
	}

	for app in applications:
		payment_schedule = frappe.get_all(
			"Payment Schedule",
			filters={
				"parent": app.name,
				"parenttype": "Installment Application"
			},
			fields=["due_date", "payment_amount"],
			order_by="due_date"
		)

		if not payment_schedule:
			continue

		total_paid = get_total_payments(app.sales_order) if app.sales_order else 0
		contract_total = flt(app.custom_grand_total_with_interest)
		remaining_debt = contract_total - total_paid

		if remaining_debt <= 0:
			continue

		cumulative_paid = total_paid
		next_unpaid_item = None
		overdue_amount = 0

		for schedule_item in payment_schedule:
			due_date = getdate(schedule_item.due_date)
			payment_amount = flt(schedule_item.payment_amount)

			if cumulative_paid >= payment_amount:
				cumulative_paid -= payment_amount
				continue
			else:
				unpaid_amount = payment_amount - cumulative_paid
				cumulative_paid = 0

				if due_date < today:
					overdue_amount = unpaid_amount
					continue
				else:
					next_unpaid_item = {
						"due_date": due_date,
						"amount": unpaid_amount,
						"schedule_amount": payment_amount
					}
					break

		if not next_unpaid_item and overdue_amount > 0:
			next_unpaid_item = {
				"due_date": getdate(payment_schedule[-1].due_date),
				"amount": overdue_amount,
				"schedule_amount": flt(payment_schedule[-1].payment_amount)
			}

		if not next_unpaid_item:
			continue

		latest_note = get_latest_note(app.name)

		due_date = next_unpaid_item["due_date"]
		current_payment = next_unpaid_item["schedule_amount"]
		due_amount = next_unpaid_item["amount"]

		row = {
			"contract_link": app.name,
			"customer_link": app.customer,
			"current_month_payment": current_payment,
			"due_amount": due_amount,
			"remaining_debt": remaining_debt,
			"note_text": latest_note.get("note_text", "") if latest_note else "",
			"note_category": latest_note.get("note_category", "") if latest_note else "",
			"note_date": latest_note.get("note_date", "") if latest_note else ""
		}

		if due_date < today:
			if due_date >= two_weeks_ago:
				groups["overdue_2weeks"].append(row)
			else:
				groups["overdue_more"].append(row)
		elif due_date == today:
			groups["today"].append(row)
		elif due_date <= one_week_later:
			groups["week"].append(row)
		else:
			groups["later"].append(row)

	data = []

	group_configs = [
		("overdue_more", "1. 2 HAFTADAN KO'P O'TIB KETGANLAR (14+ kun)"),
		("overdue_2weeks", "2. 2 HAFTA O'TIB KETGANLAR (0-14 kun)"),
		("today", "3. BUGUN BERADIGANLAR"),
		("week", "4. BIR HAFTA ICHIDA BERADIGANLAR"),
		("later", "5. KEYIN BERADIGANLAR (1 haftadan keyin)")
	]

	for group_key, group_title in group_configs:
		if groups[group_key]:
			data.append({
				"group_header": group_title,
				"contract_link": "",
				"customer_link": "",
				"current_month_payment": None,
				"due_amount": None,
				"remaining_debt": None,
				"note_text": "",
				"note_category": "",
				"note_date": "",
				"indent": 0,
				"bold": 1
			})

			for row in groups[group_key]:
				row["group_header"] = ""
				row["indent"] = 1
				data.append(row)

			data.append({
				"group_header": "",
				"contract_link": "",
				"customer_link": "JAMI:",
				"current_month_payment": sum(
					[flt(r.get("current_month_payment", 0)) for r in groups[group_key]]),
				"due_amount": sum([flt(r.get("due_amount", 0)) for r in groups[group_key]]),
				"remaining_debt": sum(
					[flt(r.get("remaining_debt", 0)) for r in groups[group_key]]),
				"note_text": "",
				"note_category": "",
				"note_date": "",
				"indent": 1,
				"bold": 1
			})

	return data


def get_total_payments(sales_order):
	"""Get total payments"""
	if not sales_order:
		return 0

	payments = frappe.db.sql("""
		SELECT SUM(paid_amount) as total_paid
		FROM `tabPayment Entry`
		WHERE custom_contract_reference = %s
			AND docstatus = 1
			AND payment_type = 'Receive'
	""", (sales_order,), as_dict=1)

	return flt(payments[0].total_paid) if payments and payments[0].total_paid else 0


def get_latest_note(contract_reference):
	"""Get latest note for contract"""
	try:
		notes = frappe.get_all(
			"Contract Notes",
			filters={"contract_reference": contract_reference},
			fields=["name", "note_text", "note_category", "note_date"],
			order_by="creation desc",
			limit=1
		)

		return notes[0] if notes else None
	except Exception as e:
		frappe.log_error(f"Get note error: {str(e)}")
		return None


@frappe.whitelist()
def save_note(contract_reference, note_text, note_category="Eslatma"):
	"""Save a new contract note"""
	try:
		if not contract_reference:
			return {"success": False, "message": "Shartnoma ko'rsatilmagan"}

		if not note_text or not note_text.strip():
			return {"success": False, "message": "Izoh matni bo'sh"}

		if not frappe.db.exists("Installment Application", contract_reference):
			return {"success": False, "message": f"Shartnoma topilmadi: {contract_reference}"}

		doc = frappe.new_doc("Contract Notes")
		doc.contract_reference = contract_reference
		doc.note_text = note_text.strip()
		doc.note_category = note_category or "Eslatma"
		doc.note_date = nowdate()

		doc.save(ignore_permissions=True)
		frappe.db.commit()

		return {
			"success": True,
			"message": "Izoh saqlandi",
			"note_id": doc.name
		}

	except Exception as e:
		frappe.log_error(f"Note save error: {str(e)}", "Save Note Error")
		return {"success": False, "message": f"Xatolik: {str(e)}"}


@frappe.whitelist()
def get_contract_notes(contract_reference):
	"""Get all notes for a contract"""
	try:
		notes = frappe.get_all(
			"Contract Notes",
			filters={"contract_reference": contract_reference},
			fields=["name", "note_text", "note_category", "note_date", "created_by_user"],
			order_by="creation desc"
		)

		return {"success": True, "notes": notes}

	except Exception as e:
		frappe.log_error(f"Get notes error: {str(e)}")
		return {"success": False, "message": str(e), "notes": []}
