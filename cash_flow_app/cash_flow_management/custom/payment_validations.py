# Copyright (c) 2025, AsadStack
# Negative Balance Validation for Payment Entry

import frappe
from frappe import _
from frappe.utils import flt


def validate_negative_balance(doc, method=None):
	"""
	Validate that cash account doesn't go negative
	Only for Pay transactions (outgoing money)
	"""
	if doc.payment_type != "Pay":
		return
	
	# Get cash account
	cash_account = doc.paid_from
	
	if not cash_account:
		return
	
	# Get current balance
	current_balance = get_account_balance(cash_account, doc.posting_date, doc.company)
	
	# Check if payment would cause negative balance
	payment_amount = flt(doc.paid_amount)
	
	if current_balance < payment_amount:
		shortage = payment_amount - current_balance
		frappe.throw(
			_("Insufficient balance in account {0}.<br>"
			  "Current Balance: <b>{1} USD</b><br>"
			  "Payment Amount: <b>{2} USD</b><br>"
			  "Shortage: <b style='color: red;'>{3} USD</b><br><br>"
			  "Please add funds or reduce the payment amount.").format(
				cash_account,
				"{:,.2f}".format(current_balance),
				"{:,.2f}".format(payment_amount),
				"{:,.2f}".format(shortage)
			),
			title=_("Negative Balance Not Allowed")
		)


def get_account_balance(account, posting_date, company):
	"""
	Get account balance as of posting_date
	"""
	from erpnext.accounts.utils import get_balance_on
	
	try:
		balance = get_balance_on(
			account=account,
			date=posting_date,
			company=company,
			in_account_currency=True
		)
		return flt(balance)
	except Exception as e:
		frappe.logger().error(f"Error getting balance for {account}: {str(e)}")
		return 0.0


def validate_payment_schedule_paid_amount(doc, method=None):
	"""
	Validate that paid_amount in payment schedule doesn't exceed payment_amount
	For Sales Order payment schedules
	"""
	if doc.doctype != "Sales Order":
		return
	
	for schedule in doc.get("payment_schedule", []):
		paid = flt(schedule.get("paid_amount") or 0)
		payment = flt(schedule.get("payment_amount") or 0)
		
		if paid > payment:
			frappe.throw(
				_("Row #{0}: Paid amount ({1} USD) cannot exceed payment amount ({2} USD)").format(
					schedule.idx,
					"{:,.2f}".format(paid),
					"{:,.2f}".format(payment)
				),
				title=_("Invalid Paid Amount")
			)


def warn_on_overdue_payments(doc, method=None):
	"""
	Warning when creating payment entry for a customer with overdue payments
	"""
	if doc.payment_type != "Receive" or not doc.party:
		return
	
	if doc.party_type != "Customer":
		return
	
	# Check for overdue payments
	from frappe.utils import today, date_diff, add_days
	
	# ✅ SMART LOGIC: Only show overdue for ACTIVE contracts (within 1 year)
	# Historical contracts (>365 days old) should not trigger warning
	one_year_ago = add_days(today(), -365)
	
	overdue_schedules = frappe.db.sql("""
		SELECT
			so.name,
			so.transaction_date,
			ps.due_date,
			ps.payment_amount,
			ps.paid_amount,
			(ps.payment_amount - IFNULL(ps.paid_amount, 0)) as outstanding
		FROM
			`tabPayment Schedule` ps
		INNER JOIN
			`tabSales Order` so ON ps.parent = so.name
		WHERE
			so.customer = %(customer)s
			AND so.docstatus = 1
			AND ps.parenttype = 'Sales Order'
			AND ps.due_date < %(today)s
			AND (ps.payment_amount - IFNULL(ps.paid_amount, 0)) > 0
			AND so.transaction_date >= %(one_year_ago)s
		ORDER BY
			ps.due_date ASC
		LIMIT 5
	""", {
		"customer": doc.party,
		"today": today(),
		"one_year_ago": one_year_ago
	}, as_dict=1)
	
	if overdue_schedules:
		total_overdue = sum(flt(s.outstanding) for s in overdue_schedules)
		
		message = _("<b>Warning:</b> This customer has overdue payments!<br><br>")
		message += "<table style='width: 100%; border-collapse: collapse;'>"
		message += "<tr style='background-color: #f5f5f5;'>"
		message += "<th style='padding: 8px; border: 1px solid #ddd;'>Contract</th>"
		message += "<th style='padding: 8px; border: 1px solid #ddd;'>Due Date</th>"
		message += "<th style='padding: 8px; border: 1px solid #ddd;'>Days Overdue</th>"
		message += "<th style='padding: 8px; border: 1px solid #ddd;'>Outstanding (USD)</th>"
		message += "</tr>"
		
		for schedule in overdue_schedules:
			days_overdue = date_diff(today(), schedule.due_date)
			message += f"<tr>"
			message += f"<td style='padding: 8px; border: 1px solid #ddd;'>{schedule.name}</td>"
			message += f"<td style='padding: 8px; border: 1px solid #ddd;'>{schedule.due_date}</td>"
			message += f"<td style='padding: 8px; border: 1px solid #ddd; color: red;'>{days_overdue} days</td>"
			message += f"<td style='padding: 8px; border: 1px solid #ddd;'>{schedule.outstanding:,.2f}</td>"
			message += f"</tr>"
		
		message += "</table>"
		message += f"<br><b>Total Overdue: {total_overdue:,.2f} USD</b>"
		
		frappe.msgprint(
			message,
			title=_("Overdue Payments"),
			indicator="orange"
		)
