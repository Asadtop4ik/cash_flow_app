import frappe
from frappe.utils import getdate, add_months, flt
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from frappe import _


def execute(filters=None):
	"""Report execute function"""
	if not filters:
		filters = {}

	# Default dates if not provided
	if not filters.get("from_date"):
		filters["from_date"] = add_months(frappe.utils.today(), -1)
	if not filters.get("to_date"):
		filters["to_date"] = frappe.utils.today()
	if not filters.get("report_type"):
		filters["report_type"] = "Monthly"

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data


def get_columns(filters):
	"""Column definition"""
	columns = [
		{
			"fieldname": "classification",
			"label": _("Classification"),
			"fieldtype": "Data",
			"width": 100
		},
		{
			"fieldname": "customer_name",
			"label": _("Customer Name"),
			"fieldtype": "Link",
			"options": "Customer",
			"width": 150
		},
		{
			"fieldname": "contract_link",
			"label": _("Contract"),
			"fieldtype": "Link",
			"options": "Installment Application",
			"width": 150
		},
		{
			"fieldname": "total_amount",
			"label": _("Contract Amount"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "down_payment",
			"label": _("Down Payment"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "finance_amount",
			"label": _("Finance Amount"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_finance_amount",
			"label": _("Total Finance Amount"),
			"fieldtype": "Currency",
			"width": 140
		},
		{
			"fieldname": "monthly_payment",
			"label": _("Monthly Payment"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "total_paid",
			"label": _("Total Paid"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "remaining",
			"label": _("Remaining"),
			"fieldtype": "Currency",
			"width": 120
		}
	]

	# Period columns qo'shish
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	report_type = filters.get("report_type", "Monthly")

	if report_type == "Monthly":
		# Oylik columns
		current_date = from_date
		while current_date <= to_date:
			month_year = current_date.strftime("%b %Y")
			columns.append({
				"fieldname": f"month_{current_date.strftime('%Y_%m')}",
				"label": month_year,
				"fieldtype": "Data",
				"width": 120
			})
			current_date += relativedelta(months=1)
	else:
		# Kunlik columns
		current_date = from_date
		while current_date <= to_date:
			day_str = current_date.strftime("%d.%m")
			columns.append({
				"fieldname": f"day_{current_date.strftime('%Y_%m_%d')}",
				"label": day_str,
				"fieldtype": "Data",
				"width": 100
			})
			current_date += timedelta(days=1)

	return columns


def get_data(filters):
	"""Get report data with filters applied"""
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	classifications = filters.get("classification")
	customers = filters.get("customer")
	report_type = filters.get("report_type", "Monthly")

	# Convert string to list if needed
	if classifications and isinstance(classifications, str):
		classifications = [c.strip() for c in classifications.split(",")]
	if customers and isinstance(customers, str):
		customers = [c.strip() for c in customers.split(",")]

	# Build contract filters
	contract_filters = {
		"status": ["!=", "Closed"]
	}

	if customers:
		contract_filters["customer"] = ["in", customers]

	# Get contracts with all necessary fields
	contracts = frappe.get_list(
		"Installment Application",
		filters=contract_filters,
		fields=[
			"name",
			"customer",
			"custom_grand_total_with_interest",
			"downpayment_amount",
			"finance_amount",
			"monthly_payment",
			"installment_months",
			"status"
		]
	)

	# Bulk fetch all data to minimize DB queries
	contract_names = [c.name for c in contracts]

	# Get all payment schedules at once
	payment_schedules = get_all_payment_schedules(contract_names)

	# Get all payments at once
	all_payments = get_all_payments(contract_names)

	# Get all customer classifications at once
	customer_names = list(set([c.customer for c in contracts]))
	customer_classifications = get_customer_classifications(customer_names)

	data = []

	for contract in contracts:
		# Get customer classification
		customer_classification = customer_classifications.get(contract.customer, "A")

		# Filter by classification if specified
		if classifications and customer_classification not in classifications:
			continue

		# Get total paid for this contract (all time)
		contract_payments = all_payments.get(contract.name, [])
		total_paid = sum(p.get("paid_amount", 0) for p in contract_payments)

		# Calculate remaining based on contract amount with interest
		contract_amount = flt(contract.custom_grand_total_with_interest)
		remaining = contract_amount - total_paid

		# Only show contracts with remaining balance
		if remaining <= 0:
			continue

		# Calculate total finance amount (monthly_payment × installment_months)
		total_finance_amount = flt(contract.monthly_payment) * flt(contract.installment_months)

		row = {
			"classification": customer_classification,
			"customer_name": contract.customer,
			"contract_link": contract.name,
			"total_amount": contract_amount,
			"down_payment": contract.downpayment_amount,
			"finance_amount": contract.finance_amount,
			"total_finance_amount": total_finance_amount,
			"monthly_payment": contract.monthly_payment,
			"total_paid": total_paid,
			"remaining": remaining
		}

		# Get payment schedule for this contract
		schedule = payment_schedules.get(contract.name, [])
		payments = contract_payments

		# Add period data
		if report_type == "Monthly":
			row.update(get_monthly_payment_status(schedule, payments, from_date, to_date))
		else:
			row.update(get_daily_payment_status(schedule, payments, from_date, to_date))

		data.append(row)

	return data


def get_customer_classifications(customer_names):
	"""Bulk fetch customer classifications"""
	if not customer_names:
		return {}

	customers = frappe.get_all(
		"Customer",
		filters={"name": ["in", customer_names]},
		fields=["name", "customer_classification"]
	)

	return {c.name: c.customer_classification or "A" for c in customers}


def get_all_payment_schedules(contract_names):
	"""Bulk fetch all payment schedules"""
	if not contract_names:
		return {}

	schedules = frappe.get_all(
		"Payment Schedule",
		filters={"parent": ["in", contract_names]},
		fields=["parent", "due_date", "payment_amount"],
		order_by="due_date"
	)

	# Group by contract
	schedule_dict = {}
	for s in schedules:
		if s.parent not in schedule_dict:
			schedule_dict[s.parent] = []
		schedule_dict[s.parent].append({
			"due_date": s.due_date,
			"payment_amount": s.payment_amount
		})

	return schedule_dict


def get_all_payments(contract_names):
	"""Bulk fetch all payments for contracts"""
	if not contract_names:
		return {}

	# Get payments through references child table
	payments = frappe.db.sql("""
		SELECT
			pe.name,
			pe.paid_amount,
			pe.posting_date,
			ref.reference_name as contract_name
		FROM `tabPayment Entry` pe
		INNER JOIN `tabPayment Entry Reference` ref
			ON ref.parent = pe.name
		WHERE
			pe.docstatus = 1
			AND ref.reference_doctype = 'Installment Application'
			AND ref.reference_name IN %(contracts)s
		ORDER BY pe.posting_date
	""", {"contracts": contract_names}, as_dict=1)

	# Group by contract
	payment_dict = {}
	for p in payments:
		if p.contract_name not in payment_dict:
			payment_dict[p.contract_name] = []
		payment_dict[p.contract_name].append(p)

	return payment_dict


def get_monthly_payment_status(schedule, payments, from_date, to_date):
	"""Get monthly payment status with expected vs paid"""
	data = {}
	current_date = getdate(from_date)

	while current_date <= to_date:
		month_key = f"month_{current_date.strftime('%Y_%m')}"

		# Get month boundaries
		month_start = current_date.replace(day=1)
		if current_date.month == 12:
			month_end = current_date.replace(year=current_date.year + 1, month=1,
											 day=1) - timedelta(days=1)
		else:
			month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(
				days=1)

		# Calculate expected payment for this month (sum of all schedules in this month)
		expected = 0
		for s in schedule:
			due_date = getdate(s["due_date"])
			if month_start <= due_date <= month_end:
				expected += flt(s["payment_amount"])

		# Calculate actual payments for this month
		paid = 0
		for p in payments:
			posting_date = getdate(p["posting_date"])
			if month_start <= posting_date <= month_end:
				paid += flt(p["paid_amount"])

		# Format: "paid/expected" or just expected if not paid
		if expected > 0:
			if paid >= expected:
				data[month_key] = "To'landi"
			elif paid > 0:
				data[month_key] = f"{paid:.0f}/{expected:.0f}"
			else:
				data[month_key] = f"{expected:.0f}"
		else:
			data[month_key] = ""

		current_date += relativedelta(months=1)

	return data


def get_daily_payment_status(schedule, payments, from_date, to_date):
	"""Get daily payment status with expected vs paid"""
	data = {}
	current_date = getdate(from_date)

	while current_date <= to_date:
		day_key = f"day_{current_date.strftime('%Y_%m_%d')}"

		# Calculate expected payment for this day
		expected = 0
		for s in schedule:
			due_date = getdate(s["due_date"])
			if due_date == current_date:
				expected += flt(s["payment_amount"])

		# Calculate actual payments for this day
		paid = 0
		for p in payments:
			posting_date = getdate(p["posting_date"])
			if posting_date == current_date:
				paid += flt(p["paid_amount"])

		# Format: "paid/expected" or just expected if not paid
		if expected > 0:
			if paid >= expected:
				data[day_key] = "To'landi"
			elif paid > 0:
				data[day_key] = f"{paid:.0f}/{expected:.0f}"
			else:
				data[day_key] = f"{expected:.0f}"
		else:
			data[day_key] = ""

		current_date += timedelta(days=1)

	return data
