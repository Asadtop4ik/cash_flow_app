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

	# Period columns
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

	# Exclude Closed, Cancelled, Completed
	contracts = frappe.db.sql("""
		SELECT
			name,
			customer,
			custom_grand_total_with_interest,
			downpayment_amount,
			finance_amount,
			monthly_payment,
			installment_months,
			status
		FROM `tabInstallment Application`
		WHERE status NOT IN ('Closed', 'Cancelled', 'Completed')
		{customer_filter}
		ORDER BY customer, name
	""".format(
		customer_filter=f"AND customer IN ({','.join(['%s'] * len(customers))})" if customers else ""
	), tuple(customers) if customers else (), as_dict=1)

	if not contracts:
		return []

	# Get unique customers
	customer_names = list(set([c.customer for c in contracts]))

	# Bulk fetch customer classifications
	customer_classifications = get_customer_classifications(customer_names)

	# Bulk fetch all payment schedules
	contract_names = [c.name for c in contracts]
	payment_schedules = get_all_payment_schedules(contract_names)

	# Bulk fetch all customer payments
	all_customer_payments = get_all_customer_payments(customer_names)

	data = []
	totals = {
		"classification": "TOTAL",
		"customer_name": "",
		"contract_link": "",
		"total_amount": 0,
		"down_payment": 0,
		"finance_amount": 0,
		"total_finance_amount": 0,
		"monthly_payment": 0,
		"total_paid": 0,
		"remaining": 0
	}

	for contract in contracts:
		# Get customer classification
		customer_classification = customer_classifications.get(contract.customer, "A")

		# Filter by classification if specified
		if classifications and customer_classification not in classifications:
			continue

		# Get payment schedule for THIS CONTRACT
		schedule = payment_schedules.get(contract.name, [])

		# Get all payments for this customer
		customer_payments = all_customer_payments.get(contract.customer, [])

		# Calculate total schedule amount
		total_schedule_amount = sum(flt(s["payment_amount"]) for s in schedule)

		# Calculate total paid (ALL customer payments, not limited to schedule)
		total_paid_all = sum(flt(p["paid_amount"]) for p in customer_payments)

		# Remaining = schedule - actual paid
		remaining = total_schedule_amount - total_paid_all

		# Only show contracts with remaining > 0
		if remaining <= 0:
			continue

		# Calculate total finance amount
		total_finance_amount = flt(contract.monthly_payment) * flt(contract.installment_months)

		row = {
			"classification": customer_classification,
			"customer_name": contract.customer,
			"contract_link": contract.name,
			"total_amount": flt(contract.custom_grand_total_with_interest),
			"down_payment": contract.downpayment_amount,
			"finance_amount": contract.finance_amount,
			"total_finance_amount": total_finance_amount,
			"monthly_payment": contract.monthly_payment,
			"total_paid": total_paid_all,
			"remaining": remaining
		}

		# Add period data
		if report_type == "Monthly":
			period_data = get_monthly_payment_status_fixed(schedule, customer_payments, from_date,
														   to_date)
			row.update(period_data)
			# Add to totals
			for key, val in period_data.items():
				if key not in totals:
					totals[key] = 0
		else:
			period_data = get_daily_payment_status(schedule, customer_payments, from_date, to_date)
			row.update(period_data)

		# Add to totals
		totals["total_amount"] += flt(contract.custom_grand_total_with_interest)
		totals["down_payment"] += flt(contract.downpayment_amount)
		totals["finance_amount"] += flt(contract.finance_amount)
		totals["total_finance_amount"] += total_finance_amount
		totals["monthly_payment"] += flt(contract.monthly_payment)
		totals["total_paid"] += total_paid_all
		totals["remaining"] += remaining

		data.append(row)

	# Add totals row
	if data:
		data.append(totals)

	return data


def get_customer_classifications(customer_names):
	"""Bulk fetch customer classifications"""
	if not customer_names:
		return {}

	customers = frappe.db.sql("""
		SELECT name, customer_classification
		FROM `tabCustomer`
		WHERE name IN ({})
	""".format(','.join(['%s'] * len(customer_names))), tuple(customer_names), as_dict=1)

	return {c.name: c.customer_classification or "A" for c in customers}


def get_all_payment_schedules(contract_names):
	"""Bulk fetch all payment schedules"""
	if not contract_names:
		return {}

	schedules = frappe.db.sql("""
		SELECT parent, due_date, payment_amount
		FROM `tabPayment Schedule`
		WHERE parent IN ({})
		ORDER BY due_date
	""".format(','.join(['%s'] * len(contract_names))), tuple(contract_names), as_dict=1)

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


def get_all_customer_payments(customer_names):
	"""Bulk fetch all customer payments"""
	if not customer_names:
		return {}

	# Get payments by customer
	payments = frappe.db.sql("""
		SELECT
			name,
			paid_amount,
			posting_date,
			party as customer
		FROM `tabPayment Entry`
		WHERE
			docstatus = 1
			AND party_type = 'Customer'
			AND party IN ({})
		ORDER BY posting_date
	""".format(','.join(['%s'] * len(customer_names))), tuple(customer_names), as_dict=1)

	# Group by customer
	payment_dict = {}
	for p in payments:
		if p.customer not in payment_dict:
			payment_dict[p.customer] = []
		payment_dict[p.customer].append(p)

	return payment_dict


def get_monthly_payment_status_fixed(schedule, payments, from_date, to_date):
	"""
	✅ FIXED: Oylik statusa - oldindan to'laganlarni hisoblab chiqish
	"""
	data = {}
	current_date = getdate(from_date)

	# First, distribute all payments across months
	running_balance = sum(flt(p["paid_amount"]) for p in payments)  # Total paid

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

		# Calculate expected payment for this month from schedule
		expected = 0
		for s in schedule:
			due_date = getdate(s["due_date"])
			if month_start <= due_date <= month_end:
				expected += flt(s["payment_amount"])

		# Calculate actual payments made BY/BEFORE end of this month
		paid_until_month_end = 0
		for p in payments:
			posting_date = getdate(p["posting_date"])
			if posting_date <= month_end:
				paid_until_month_end += flt(p["paid_amount"])

		# Calculate what should be paid by END of this month (cumulative)
		expected_cumulative = 0
		temp_date = getdate(from_date)
		while temp_date <= month_end:
			for s in schedule:
				due_date = getdate(s["due_date"])
				if temp_date.replace(day=1) == temp_date.replace(day=1):  # same month
					if due_date <= month_end:
						expected_cumulative += flt(s["payment_amount"])
			break

		# Better approach: sum all scheduled payments up to month end
		expected_cumulative = 0
		for s in schedule:
			due_date = getdate(s["due_date"])
			if due_date <= month_end:
				expected_cumulative += flt(s["payment_amount"])

		# Determine what to show for THIS MONTH
		if expected > 0:
			# Show what was paid FOR THIS MONTH only
			paid_this_month = 0
			for p in payments:
				posting_date = getdate(p["posting_date"])
				if month_start <= posting_date <= month_end:
					paid_this_month += flt(p["paid_amount"])

			if paid_this_month >= expected:
				data[month_key] = "To'landi"
			elif paid_this_month > 0:
				data[month_key] = f"{paid_this_month:.0f}/{expected:.0f}"
			else:
				# Check if this was paid from previous months' overpayment
				paid_up_to_month = 0
				for p in payments:
					posting_date = getdate(p["posting_date"])
					if posting_date <= month_end:
						paid_up_to_month += flt(p["paid_amount"])

				expected_up_to_month = 0
				for s in schedule:
					due_date = getdate(s["due_date"])
					if due_date <= month_end:
						expected_up_to_month += flt(s["payment_amount"])

				# If we have overpayment from before, mark as paid
				if paid_up_to_month >= expected_up_to_month:
					data[month_key] = "To'landi"
				else:
					data[month_key] = f"{expected:.0f}"
		else:
			data[month_key] = ""

		current_date += relativedelta(months=1)

	return data


def get_daily_payment_status(schedule, payments, from_date, to_date):
	"""Get daily payment status"""
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
