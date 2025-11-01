# cash_flow_app/reports/customer_payment_report.py
# ✅ CLEANED - Finance Amount va Status columns o'chirilgan

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
	"""Column definition - Finance Amount va Status o'chirilgan"""
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

	# Add period columns
	from_date = getdate(filters.get("from_date"))
	to_date = getdate(filters.get("to_date"))
	report_type = filters.get("report_type", "Monthly")

	if report_type == "Monthly":
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
		"docstatus": 1,  # Submitted
		"status": ["!=", "Closed"]
	}

	if customers:
		contract_filters["customer"] = ["in", customers]

	# ✅ Get contracts (Installment Application)
	contracts = frappe.db.sql("""
		SELECT
			name,
			customer,
			custom_grand_total_with_interest,
			downpayment_amount,
			monthly_payment,
			installment_months,
			sales_order
		FROM `tabInstallment Application`
		WHERE docstatus = 1
		AND status != 'Closed'
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
	payment_schedules = get_all_payment_schedules(contracts)

	# ✅ FIXED: Get payments using Sales Order mapping
	all_contract_payments = get_all_contract_payments(contracts)

	data = []

	# ✅ TOTALS FOR GRAND TOTAL ROW
	grand_total_amount = 0
	grand_down_payment = 0
	grand_total_finance = 0
	grand_monthly_payment = 0
	grand_total_paid = 0
	grand_remaining = 0

	# For period totals
	period_totals = {}

	for contract in contracts:
		# Get customer classification
		customer_classification = customer_classifications.get(contract.customer, "")

		# Filter by classification if specified
		if classifications and customer_classification not in classifications:
			continue

		# ✅ FIXED: Get payments for THIS CONTRACT using the mapping
		contract_payments = all_contract_payments.get(contract.name, [])
		total_paid = sum(flt(p.get("paid_amount", 0)) for p in contract_payments)

		# Calculate remaining based on contract amount with interest
		contract_amount = flt(contract.custom_grand_total_with_interest)
		remaining = contract_amount - total_paid

		# Only show contracts with remaining balance (not fully paid)
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
			"total_finance_amount": total_finance_amount,
			"monthly_payment": contract.monthly_payment,
			"total_paid": total_paid,
			"remaining": remaining
		}

		# ✅ ACCUMULATE GRAND TOTALS
		grand_total_amount += flt(contract_amount)
		grand_down_payment += flt(contract.downpayment_amount)
		grand_total_finance += flt(total_finance_amount)
		grand_monthly_payment += flt(contract.monthly_payment)
		grand_total_paid += flt(total_paid)
		grand_remaining += flt(remaining)

		# Get payment schedule for this contract
		schedule = payment_schedules.get(contract.name, [])

		# Add period data (showing expected vs paid)
		if report_type == "Monthly":
			period_data = get_monthly_payment_status(schedule, contract_payments, from_date,
													 to_date)
			row.update(period_data)

			# ✅ ACCUMULATE PERIOD TOTALS
			for key, val in period_data.items():
				if key not in period_totals:
					period_totals[key] = 0
				# Only add numeric values
				if val and val != "To'landi" and val != "":
					try:
						period_totals[key] += flt(val)
					except:
						pass
		else:
			period_data = get_daily_payment_status(schedule, contract_payments, from_date, to_date)
			row.update(period_data)

			# ✅ ACCUMULATE PERIOD TOTALS
			for key, val in period_data.items():
				if key not in period_totals:
					period_totals[key] = 0
				# Only add numeric values
				if val and val != "To'landi" and val != "":
					try:
						if "/" in str(val):  # Format: "100/150"
							paid = flt(str(val).split("/")[0])
							period_totals[key] += paid
						else:
							period_totals[key] += flt(val)
					except:
						pass

		data.append(row)

	# ✅ ADD GRAND TOTAL ROW
	if data:
		grand_total_row = {
			"classification": "",
			"customer_name": "",
			"contract_link": "",
			"total_amount": grand_total_amount,
			"down_payment": grand_down_payment,
			"total_finance_amount": grand_total_finance,
			"monthly_payment": grand_monthly_payment,
			"total_paid": grand_total_paid,
			"remaining": grand_remaining
		}

		# Add period totals to grand total row
		for key, val in period_totals.items():
			if val > 0:
				grand_total_row[key] = f"{val:.0f}"
			else:
				grand_total_row[key] = ""

		data.append(grand_total_row)

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

	return {c.name: c.customer_classification for c in customers}


def get_all_payment_schedules(contracts):
	"""
	Bulk fetch all payment schedules

	Maps from Installment Application → Sales Order → Payment Schedule
	"""
	if not contracts:
		return {}

	# Get Sales Order names from contracts
	so_names = [c.sales_order for c in contracts if c.sales_order]
	ia_so_map = {c.name: c.sales_order for c in contracts if c.sales_order}

	if not so_names:
		return {}

	# Get payment schedules from Sales Orders
	schedules = frappe.db.sql("""
		SELECT parent, due_date, payment_amount
		FROM `tabPayment Schedule`
		WHERE parent IN ({})
		ORDER BY due_date
	""".format(','.join(['%s'] * len(so_names))), tuple(so_names), as_dict=1)

	# Map schedules back to contracts
	schedule_dict = {}
	for s in schedules:
		# Find which contract this Sales Order belongs to
		contract_name = [k for k, v in ia_so_map.items() if v == s.parent]
		if contract_name:
			contract_name = contract_name[0]
			if contract_name not in schedule_dict:
				schedule_dict[contract_name] = []
			schedule_dict[contract_name].append({
				"due_date": s.due_date,
				"payment_amount": s.payment_amount
			})

	return schedule_dict


def get_all_contract_payments(contracts):
	"""
	✅ FIXED: Get payments for contracts

	Handles mapping:
	Installment Application → Sales Order → Payment Entry
	"""
	if not contracts:
		return {}

	# Step 1: Create mapping of Sales Order → Installment Application
	so_names = [c.sales_order for c in contracts if c.sales_order]

	if not so_names:
		return {}

	so_to_ia = {c.sales_order: c.name for c in contracts if c.sales_order}

	# Step 2: Get payments using Sales Order reference
	payments = frappe.db.sql("""
		SELECT
			name,
			paid_amount,
			posting_date,
			custom_contract_reference as sales_order_ref
		FROM `tabPayment Entry`
		WHERE
			docstatus = 1
			AND party_type = 'Customer'
			AND custom_contract_reference IN ({})
		ORDER BY posting_date ASC
	""".format(','.join(['%s'] * len(so_names))),
							 tuple(so_names), as_dict=1)

	# Step 3: Map payments back to Installment Application
	payment_dict = {}
	for p in payments:
		so_ref = p.sales_order_ref
		ia_name = so_to_ia.get(so_ref)

		if ia_name:
			if ia_name not in payment_dict:
				payment_dict[ia_name] = []

			payment_dict[ia_name].append({
				"paid_amount": flt(p.paid_amount),
				"posting_date": p.posting_date
			})

	return payment_dict


def get_monthly_payment_status(schedule, payments, from_date, to_date):
	"""Get monthly payment status with expected vs paid - showing remaining to pay"""
	data = {}
	current_date = getdate(from_date)

	# Sort payments by date
	sorted_payments = sorted(payments, key=lambda x: getdate(x["posting_date"]))
	payment_idx = 0
	cumulative_paid = 0

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

		# Calculate expected payment for this month
		expected_this_month = 0
		for s in schedule:
			due_date = getdate(s["due_date"])
			if month_start <= due_date <= month_end:
				expected_this_month += flt(s["payment_amount"])

		# Add payments made during or before this month to cumulative
		while payment_idx < len(sorted_payments):
			p = sorted_payments[payment_idx]
			posting_date = getdate(p["posting_date"])
			if posting_date <= month_end:
				cumulative_paid += flt(p["paid_amount"])
				payment_idx += 1
			else:
				break

		# Calculate cumulative expected up to this month
		cumulative_expected = 0
		for s in schedule:
			due_date = getdate(s["due_date"])
			if due_date <= month_end:
				cumulative_expected += flt(s["payment_amount"])

		# Determine what to show for this month
		if expected_this_month > 0:
			# Calculate remaining debt for this specific month
			remaining_debt = cumulative_expected - cumulative_paid

			if remaining_debt <= 0:
				# Fully paid (including this month)
				data[month_key] = "To'landi"
			else:
				# Show remaining amount to pay for this month
				amount_to_show = min(expected_this_month, remaining_debt)
				data[month_key] = f"{amount_to_show:.0f}"
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

		# Calculate total payments up to this day
		total_paid_until_day = 0
		for p in payments:
			posting_date = getdate(p["posting_date"])
			if posting_date <= current_date:
				total_paid_until_day += flt(p["paid_amount"])

		# Calculate expected total until this day
		expected_until_day = 0
		for s in schedule:
			due_date = getdate(s["due_date"])
			if due_date <= current_date:
				expected_until_day += flt(s["payment_amount"])

		# Format: check if paid enough for this day's obligation
		if expected > 0:
			# If total paid covers expected until this day, mark as paid
			if total_paid_until_day >= expected_until_day:
				data[day_key] = "To'landi"
			else:
				# Calculate actual payment for this specific day
				paid_this_day = 0
				for p in payments:
					posting_date = getdate(p["posting_date"])
					if posting_date == current_date:
						paid_this_day += flt(p["paid_amount"])

				if paid_this_day > 0:
					data[day_key] = f"{paid_this_day:.0f}/{expected:.0f}"
				else:
					data[day_key] = f"{expected:.0f}"
		else:
			data[day_key] = ""

		current_date += timedelta(days=1)

	return data
