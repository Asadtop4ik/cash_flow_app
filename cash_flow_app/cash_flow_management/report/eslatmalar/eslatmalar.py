# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_days


def execute(filters=None):
	"""
	Qarzdorlik Guruhlari - Klientlarni to'lov sanalariga qarab guruhlarga ajratish
	"""
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
			"width": 150
		},
		{
			"fieldname": "customer_link",
			"label": _("Klient"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 180
		},
		{
			"fieldname": "current_month_payment",
			"label": _("Shu Oy To'lovi"),
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "due_amount",
			"label": _("Yana To'lashi Kerak"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "total_contract_amount",
			"label": _("Shartnoma Summasi"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "remaining_debt",
			"label": _("Qolgan Qarz"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "note",
			"label": _("Izoh"),
			"fieldtype": "Small Text",
			"width": 200,
			"editable": 1
		}
	]


def get_data(filters):
	"""Get report data with grouped customers by payment due dates"""
	today = getdate(nowdate())
	one_week_later = add_days(today, 7)
	two_weeks_ago = add_days(today, -14)

	# Get all submitted Installment Applications
	applications = frappe.get_all(
		"Installment Application",
		filters={"docstatus": 1},
		fields=["name", "customer", "custom_grand_total_with_interest", "sales_order", "notes"]
	)

	# Group data by categories
	groups = {
		"overdue_2weeks": [],  # 2 hafta o'tib ketganlar (0-14 kun)
		"overdue_more": [],    # 2 haftadan ko'p o'tib ketganlar (14+ kun)
		"today": [],           # Bugun beradiganlar
		"week": [],            # Bir hafta ichida
		"later": []            # Keyin beradiganlar
	}

	for app in applications:
		print(f"Processing contract: {app.name}, Sales Order: {app.sales_order}")

		# Get payment schedule for this application
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

		# Calculate total payments made for this contract
		total_paid = get_total_payments(app.sales_order) if app.sales_order else 0
		print(f"  Total paid: {total_paid}")

		# Calculate contract total and remaining debt
		contract_total = flt(app.custom_grand_total_with_interest)
		remaining_debt = contract_total - total_paid
		print(f"  Contract total: {contract_total}, Remaining debt: {remaining_debt}")

		# If fully paid, skip this contract
		if remaining_debt <= 0:
			print(f"  Skipping - fully paid")
			continue

		# Find the next unpaid installment
		cumulative_paid = total_paid
		next_unpaid_item = None
		overdue_amount = 0

		for schedule_item in payment_schedule:
			due_date = getdate(schedule_item.due_date)
			payment_amount = flt(schedule_item.payment_amount)

			if cumulative_paid >= payment_amount:
				# This installment is fully paid
				cumulative_paid -= payment_amount
				continue
			else:
				# This is the next unpaid installment
				unpaid_amount = payment_amount - cumulative_paid
				cumulative_paid = 0

				# Check if there are overdue amounts from previous installments
				if due_date < today:
					overdue_amount = unpaid_amount
					# Continue to find if there are more overdue items
					continue
				else:
					# This is the current/next due installment
					next_unpaid_item = {
						"due_date": due_date,
						"amount": unpaid_amount,
						"schedule_amount": payment_amount
					}
					break

		# If no unpaid item found but there are overdue amounts, use the last overdue
		if not next_unpaid_item and overdue_amount > 0:
			next_unpaid_item = {
				"due_date": getdate(payment_schedule[-1].due_date),  # Last schedule item
				"amount": overdue_amount,
				"schedule_amount": flt(payment_schedule[-1].payment_amount)
			}

		# If still no unpaid item, skip (shouldn't happen)
		if not next_unpaid_item:
			continue

		# Now categorize based on the next unpaid item's due date
		due_date = next_unpaid_item["due_date"]
		current_payment = next_unpaid_item["schedule_amount"]
		due_amount = next_unpaid_item["amount"]

		# Get notes directly from database to avoid cache issues
		notes_value = frappe.db.get_value("Installment Application", app.name, "notes") or ""

		row = {
			"contract_link": app.name,
			"customer_link": app.customer,
			"current_month_payment": current_payment,
			"due_amount": due_amount,
			"total_contract_amount": contract_total,
			"remaining_debt": remaining_debt,
			"note": notes_value
		}

		# Categorize by due date
		if due_date < today:
			# Calculate how many days overdue
			if due_date >= two_weeks_ago:
				# 14 kun yoki undan kam o'tib ketgan
				groups["overdue_2weeks"].append(row)
			else:
				# 14 kundan ko'p o'tib ketgan
				groups["overdue_more"].append(row)
		elif due_date == today:
			groups["today"].append(row)
		elif due_date <= one_week_later:
			groups["week"].append(row)
		else:
			groups["later"].append(row)

	# Build final data with group headers and subtotals
	data = []

	# 1. 2 haftadan ko'p o'tib ketganlar (More than 2 weeks overdue)
	if groups["overdue_more"]:
		data.append({
			"group_header": "1. 2 HAFTADAN KO'P O'TIB KETGANLAR (14+ kun)",
			"contract_link": "",
			"customer_link": "",
			"current_month_payment": None,
			"due_amount": None,
			"total_contract_amount": None,
			"remaining_debt": None,
			"indent": 0,
			"bold": 1
		})
		for row in groups["overdue_more"]:
			row["group_header"] = ""
			row["indent"] = 1
			data.append(row)

		# Subtotal
		data.append({
			"group_header": "",
			"contract_link": "",
			"customer_link": "JAMI:",
			"current_month_payment": sum([flt(r.get("current_month_payment", 0)) for r in groups["overdue_more"]]),
			"due_amount": sum([flt(r.get("due_amount", 0)) for r in groups["overdue_more"]]),
			"total_contract_amount": sum([flt(r.get("total_contract_amount", 0)) for r in groups["overdue_more"]]),
			"remaining_debt": sum([flt(r.get("remaining_debt", 0)) for r in groups["overdue_more"]]),
			"indent": 1,
			"bold": 1
		})

	# 2. 2 hafta o'tib ketganlar (2 weeks or less overdue)
	if groups["overdue_2weeks"]:
		data.append({
			"group_header": "2. 2 HAFTA O'TIB KETGANLAR (0-14 kun)",
			"contract_link": "",
			"customer_link": "",
			"current_month_payment": None,
			"due_amount": None,
			"total_contract_amount": None,
			"remaining_debt": None,
			"indent": 0,
			"bold": 1
		})
		for row in groups["overdue_2weeks"]:
			row["group_header"] = ""
			row["indent"] = 1
			data.append(row)

		# Subtotal
		data.append({
			"group_header": "",
			"contract_link": "",
			"customer_link": "JAMI:",
			"current_month_payment": sum([flt(r.get("current_month_payment", 0)) for r in groups["overdue_2weeks"]]),
			"due_amount": sum([flt(r.get("due_amount", 0)) for r in groups["overdue_2weeks"]]),
			"total_contract_amount": sum([flt(r.get("total_contract_amount", 0)) for r in groups["overdue_2weeks"]]),
			"remaining_debt": sum([flt(r.get("remaining_debt", 0)) for r in groups["overdue_2weeks"]]),
			"indent": 1,
			"bold": 1
		})

	# 3. Bugun beradiganlar (Today)
	if groups["today"]:
		data.append({
			"group_header": "3. BUGUN BERADIGANLAR",
			"contract_link": "",
			"customer_link": "",
			"current_month_payment": None,
			"due_amount": None,
			"total_contract_amount": None,
			"remaining_debt": None,
			"indent": 0,
			"bold": 1
		})
		for row in groups["today"]:
			row["group_header"] = ""
			row["indent"] = 1
			data.append(row)

		# Subtotal
		data.append({
			"group_header": "",
			"contract_link": "",
			"customer_link": "JAMI:",
			"current_month_payment": sum([flt(r.get("current_month_payment", 0)) for r in groups["today"]]),
			"due_amount": sum([flt(r.get("due_amount", 0)) for r in groups["today"]]),
			"total_contract_amount": sum([flt(r.get("total_contract_amount", 0)) for r in groups["today"]]),
			"remaining_debt": sum([flt(r.get("remaining_debt", 0)) for r in groups["today"]]),
			"indent": 1,
			"bold": 1
		})

	# 4. Bir hafta ichida beradiganlar (This Week)
	if groups["week"]:
		data.append({
			"group_header": "4. BIR HAFTA ICHIDA BERADIGANLAR",
			"contract_link": "",
			"customer_link": "",
			"current_month_payment": None,
			"due_amount": None,
			"total_contract_amount": None,
			"remaining_debt": None,
			"indent": 0,
			"bold": 1
		})
		for row in groups["week"]:
			row["group_header"] = ""
			row["indent"] = 1
			data.append(row)

		# Subtotal
		data.append({
			"group_header": "",
			"contract_link": "",
			"customer_link": "JAMI:",
			"current_month_payment": sum([flt(r.get("current_month_payment", 0)) for r in groups["week"]]),
			"due_amount": sum([flt(r.get("due_amount", 0)) for r in groups["week"]]),
			"total_contract_amount": sum([flt(r.get("total_contract_amount", 0)) for r in groups["week"]]),
			"remaining_debt": sum([flt(r.get("remaining_debt", 0)) for r in groups["week"]]),
			"indent": 1,
			"bold": 1
		})

	# 5. Keyin beradiganlar (Later)
	if groups["later"]:
		data.append({
			"group_header": "5. KEYIN BERADIGANLAR (1 haftadan keyin)",
			"contract_link": "",
			"customer_link": "",
			"current_month_payment": None,
			"due_amount": None,
			"total_contract_amount": None,
			"remaining_debt": None,
			"indent": 0,
			"bold": 1
		})
		for row in groups["later"]:
			row["group_header"] = ""
			row["indent"] = 1
			data.append(row)

		# Subtotal
		data.append({
			"group_header": "",
			"contract_link": "",
			"customer_link": "JAMI:",
			"current_month_payment": sum([flt(r.get("current_month_payment", 0)) for r in groups["later"]]),
			"due_amount": sum([flt(r.get("due_amount", 0)) for r in groups["later"]]),
			"total_contract_amount": sum([flt(r.get("total_contract_amount", 0)) for r in groups["later"]]),
			"remaining_debt": sum([flt(r.get("remaining_debt", 0)) for r in groups["later"]]),
			"indent": 1,
			"bold": 1
		})

	return data


def get_total_payments(sales_order):
	"""
	Get total payments made for a Sales Order via Payment Entry custom_contract_reference
	FAQAT Receive tipidagi to'lovlarni hisoblaydi (qarzdorlik kamayadi)
	"""
	if not sales_order:
		return 0

	# Get total paid_amount from Payment Entries with matching custom_contract_reference
	payments = frappe.db.sql("""
		SELECT SUM(paid_amount) as total_paid
		FROM `tabPayment Entry`
		WHERE custom_contract_reference = %s
			AND docstatus = 1
			AND payment_type = 'Receive'
	""", (sales_order,), as_dict=1)

	return flt(payments[0].total_paid) if payments and payments[0].total_paid else 0
