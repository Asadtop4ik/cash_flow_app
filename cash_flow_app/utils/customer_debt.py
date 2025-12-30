"""
Customer Debt Tracking Utilities
Automatically update customer total debt (custom_umumiy_qarz)
"""
import frappe
from frappe.utils import flt


def update_customer_debt(customer_name):
	"""
	Update custom_umumiy_qarz field - total debt from all contracts
	Formula: (Installment Applications) + (Pay Payments) - (Receive Payments)

	Args:
		customer_name: Customer name to update debt for
	"""
	if not customer_name:
		return

	# 1. Get total from all submitted Installment Applications
	installment_total = frappe.db.sql("""
		SELECT IFNULL(SUM(custom_grand_total_with_interest), 0) as total
		FROM `tabInstallment Application`
		WHERE customer = %s
		AND docstatus = 1
	""", (customer_name,))[0][0] or 0

	# 2. Get total from Payment Entries where we paid TO customer (Pay type)
	# This INCREASES customer debt (customer owes us more)
	payment_pay_total = frappe.db.sql("""
		SELECT IFNULL(SUM(paid_amount), 0) as total
		FROM `tabPayment Entry`
		WHERE party_type = 'Customer'
		AND party = %s
		AND payment_type = 'Pay'
		AND docstatus = 1
	""", (customer_name,))[0][0] or 0

	# 3. Get total from Payment Entries received FROM customer (Receive type)
	# This DECREASES customer debt (customer paid us)
	payment_receive_total = frappe.db.sql("""
		SELECT IFNULL(SUM(paid_amount), 0) as total
		FROM `tabPayment Entry`
		WHERE party_type = 'Customer'
		AND party = %s
		AND payment_type = 'Receive'
		AND docstatus = 1
	""", (customer_name,))[0][0] or 0

	# 4. Calculate debt
	# Debt = What they owe from contracts + What we paid them - What they paid us
	total_debt = flt(installment_total) + flt(payment_pay_total) - flt(payment_receive_total)

	# 5. Update the field
	frappe.db.set_value("Customer", customer_name, "custom_umumiy_qarz", total_debt, update_modified=False)
	frappe.db.commit()

	frappe.logger().info(
		f"Customer {customer_name} debt updated: "
		f"IA={installment_total}, Pay={payment_pay_total}, Receive={payment_receive_total}, Debt={total_debt}"
	)

	return total_debt


def update_customer_debt_on_installment_submit(doc, method):
	"""Hook: Update customer debt when Installment Application is submitted"""
	if doc.customer:
		frappe.enqueue(
			"cash_flow_app.utils.customer_debt.update_customer_debt",
			customer_name=doc.customer,
			queue="short"
		)


def update_customer_debt_on_installment_cancel(doc, method):
	"""Hook: Update customer debt when Installment Application is cancelled"""
	if doc.customer:
		frappe.enqueue(
			"cash_flow_app.utils.customer_debt.update_customer_debt",
			customer_name=doc.customer,
			queue="short"
		)


def update_customer_debt_on_payment_submit(doc, method):
	"""Hook: Update customer debt when Payment Entry is submitted"""
	# Update for both Pay and Receive types
	if doc.party_type == "Customer" and doc.party and doc.payment_type in ["Receive", "Pay"]:
		frappe.enqueue(
			"cash_flow_app.utils.customer_debt.update_customer_debt",
			customer_name=doc.party,
			queue="short"
		)


def update_customer_debt_on_payment_cancel(doc, method):
	"""Hook: Update customer debt when Payment Entry is cancelled"""
	# Update for both Pay and Receive types
	if doc.party_type == "Customer" and doc.party and doc.payment_type in ["Receive", "Pay"]:
		frappe.enqueue(
			"cash_flow_app.utils.customer_debt.update_customer_debt",
			customer_name=doc.party,
			queue="short"
		)


def update_customer_debt_on_load(doc, method):
	"""Hook: Update customer debt when Customer is loaded/opened"""
	try:
		update_customer_debt(doc.name)
	except Exception as e:
		frappe.log_error(f"Error updating debt on load for {doc.name}: {str(e)}", "Customer Debt Update")


@frappe.whitelist()
def recalculate_all_customer_debts():
	"""
	Utility function to recalculate debt for all customers
	Useful for initial setup or data correction
	"""
	customers = frappe.get_all("Customer", pluck="name")
	updated_count = 0

	for customer_name in customers:
		try:
			update_customer_debt(customer_name)
			updated_count += 1
			frappe.db.commit()  # Commit after each customer
		except Exception as e:
			frappe.log_error(f"Error updating debt for {customer_name}: {str(e)}", "Customer Debt Recalculation")

	frappe.msgprint(f"Updated debt for {updated_count} customers", indicator="green")
	return f"Updated debt for {updated_count} customers"
