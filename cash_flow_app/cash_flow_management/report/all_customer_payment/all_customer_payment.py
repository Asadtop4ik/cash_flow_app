import frappe
from frappe.utils import getdate, add_months, cint
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
				"fieldtype": "Currency",
				"width": 100
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
				"fieldtype": "Currency",
				"width": 80
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

	# Get contracts
	contracts = frappe.get_list(
		"Installment Application",
		filters=contract_filters,
		fields=["name", "customer", "total_amount", "downpayment_amount",
				"finance_amount", "monthly_payment", "status"]
	)

	data = []

	for contract in contracts:
		# Get customer classification
		customer_doc = frappe.get_doc("Customer", contract.customer)
		customer_classification = customer_doc.get("customer_classification", "A")

		# Filter by classification if specified
		if classifications and customer_classification not in classifications:
			continue

		# Get payments for this customer
		payments = get_payments(contract.customer, from_date, to_date)
		total_paid = sum(p.get("paid_amount", 0) for p in payments)
		remaining = contract.finance_amount - total_paid

		# Only show contracts with remaining balance
		if remaining <= 0:
			continue

		row = {
			"classification": customer_classification,
			"customer_name": contract.customer,
			"contract_link": contract.name,
			"total_amount": contract.total_amount,
			"down_payment": contract.downpayment_amount,
			"finance_amount": contract.finance_amount,
			"monthly_payment": contract.monthly_payment,
			"total_paid": total_paid,
			"remaining": remaining
		}

		# Add period data
		if report_type == "Monthly":
			row.update(get_monthly_data(contract.customer, from_date, to_date))
		else:
			row.update(get_daily_data(contract.customer, from_date, to_date))

		data.append(row)

	return data


def get_payments(customer, from_date, to_date):
	"""Get customer payments within date range"""
	payments = frappe.get_list(
		"Payment Entry",
		filters={
			"party": customer,
			"docstatus": 1,
			"posting_date": ["between", [from_date, to_date]]
		},
		fields=["name", "paid_amount", "posting_date"]
	)

	return payments


def get_monthly_data(customer, from_date, to_date):
	"""Get monthly payment data"""
	data = {}
	current_date = getdate(from_date)

	while current_date <= to_date:
		month_key = f"month_{current_date.strftime('%Y_%m')}"

		# Month start and end
		month_start = current_date.replace(day=1)
		if current_date.month == 12:
			month_end = current_date.replace(year=current_date.year + 1, month=1,
											 day=1) - timedelta(days=1)
		else:
			month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(
				days=1)

		# Get payments for this month
		payments = frappe.get_list(
			"Payment Entry",
			filters={
				"party": customer,
				"docstatus": 1,
				"posting_date": ["between", [month_start, month_end]]
			},
			fields=["paid_amount"]
		)

		month_total = sum(p.paid_amount for p in payments)
		data[month_key] = month_total if month_total > 0 else 0

		current_date += relativedelta(months=1)

	return data


def get_daily_data(customer, from_date, to_date):
	"""Get daily payment data"""
	data = {}
	current_date = getdate(from_date)

	while current_date <= to_date:
		day_key = f"day_{current_date.strftime('%Y_%m_%d')}"

		# Get payments for this day
		payments = frappe.get_list(
			"Payment Entry",
			filters={
				"party": customer,
				"docstatus": 1,
				"posting_date": current_date
			},
			fields=["paid_amount"]
		)

		day_total = sum(p.paid_amount for p in payments)
		data[day_key] = day_total if day_total > 0 else 0

		current_date += timedelta(days=1)

	return data
