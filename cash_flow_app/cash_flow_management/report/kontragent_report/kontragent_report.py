import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		filters = {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Party"),
			"fieldname": "party",
			"fieldtype": "Dynamic Link",
			"options": "party_type",
			"width": 150
		},
		{
			"label": _("Type"),
			"fieldname": "party_type",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Party Group"),
			"fieldname": "party_group",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Op. Debit"),
			"fieldname": "opening_debit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Op. Credit"),
			"fieldname": "opening_credit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Tr. Debit"),
			"fieldname": "transaction_debit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Tr. Credit"),
			"fieldname": "transaction_credit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Cl. Debit"),
			"fieldname": "closing_debit",
			"fieldtype": "Currency",
			"width": 100
		},
		{
			"label": _("Cl. Credit"),
			"fieldname": "closing_credit",
			"fieldtype": "Currency",
			"width": 100
		}
	]


def get_data(filters):
	from_date = filters.get('from_date') or '2025-01-01'
	to_date = filters.get('to_date') or '2025-12-31'
	party_type_filter = filters.get('party_type') or ''
	party_filter = filters.get('party') or ''
	party_group_filter = filters.get('party_group') or ''

	data = []

	# CUSTOMERS - Sales Order asosida
	if not party_type_filter or party_type_filter == 'Customer':
		# Customer group filter uchun qo'shimcha shart
		group_join = ""
		group_condition = ""
		if party_group_filter:
			group_join = "INNER JOIN `tabCustomer` c ON c.name = so.customer"
			group_condition = f"AND c.customer_group = '{party_group_filter}'"

		customers = frappe.db.sql("""
			SELECT DISTINCT so.customer
			FROM `tabSales Order` so
			{group_join}
			WHERE so.docstatus = 1
			AND so.customer IS NOT NULL
			AND so.customer != ''
			{party_condition}
			{group_condition}
			ORDER BY so.customer
		""".format(
			group_join=group_join,
			party_condition=f"AND so.customer = '{party_filter}'" if party_filter else "",
			group_condition=group_condition
		), as_dict=True)

		cust_total = {
			'party': "Jami",
			'party_type': 'CUSTOMER TOTAL',
			'party_group': '',
			'opening_debit': 0,
			'opening_credit': 0,
			'transaction_debit': 0,
			'transaction_credit': 0,
			'closing_debit': 0,
			'closing_credit': 0
		}

		for c in customers:
			# Customer Group ni olish
			customer_group = frappe.db.get_value('Customer', c['customer'], 'customer_group') or ''

			# Sales Order summalarini olish (DEBIT - klient bizdan qarz)
			sales_data = frappe.db.sql("""
				SELECT
					SUM(CASE WHEN transaction_date < %s THEN rounded_total ELSE 0 END) as opening_sales,
					SUM(CASE WHEN transaction_date >= %s AND transaction_date <= %s THEN rounded_total ELSE 0 END) as period_sales,
					SUM(CASE WHEN transaction_date <= %s THEN rounded_total ELSE 0 END) as total_sales
				FROM `tabSales Order`
				WHERE customer = %s
				AND docstatus = 1
			""", (from_date, from_date, to_date, to_date, c['customer']), as_dict=True)[0]

			# Klient to'lovlari - Receive (CREDIT - klient bizga to'ladi)
			receive_data = frappe.db.sql("""
				SELECT
					SUM(CASE WHEN posting_date < %s THEN paid_amount ELSE 0 END) as opening_receive,
					SUM(CASE WHEN posting_date >= %s AND posting_date <= %s THEN paid_amount ELSE 0 END) as period_receive,
					SUM(CASE WHEN posting_date <= %s THEN paid_amount ELSE 0 END) as total_receive
				FROM `tabPayment Entry`
				WHERE party = %s
				AND party_type = 'Customer'
				AND payment_type = 'Receive'
				AND docstatus = 1
			""", (from_date, from_date, to_date, to_date, c['customer']), as_dict=True)[0]

			# Biz klientga qaytargan pul - Pay (DEBIT - bizdan chiqdi)
			pay_data = frappe.db.sql("""
				SELECT
					SUM(CASE WHEN posting_date < %s THEN paid_amount ELSE 0 END) as opening_pay,
					SUM(CASE WHEN posting_date >= %s AND posting_date <= %s THEN paid_amount ELSE 0 END) as period_pay,
					SUM(CASE WHEN posting_date <= %s THEN paid_amount ELSE 0 END) as total_pay
				FROM `tabPayment Entry`
				WHERE party = %s
				AND party_type = 'Customer'
				AND payment_type = 'Pay'
				AND docstatus = 1
			""", (from_date, from_date, to_date, to_date, c['customer']), as_dict=True)[0]

			# DEBIT = Sales Order + Pay (biz qaytargan pul)
			# CREDIT = Receive (klient to'lagan)
			opening_sales = flt(sales_data.get('opening_sales'))
			opening_receive = flt(receive_data.get('opening_receive'))
			opening_pay = flt(pay_data.get('opening_pay'))
			opening_debit_total = opening_sales + opening_pay
			opening_credit_total = opening_receive
			opening_balance = opening_debit_total - opening_credit_total

			# Transaction: faqat davr ichidagi
			period_sales = flt(sales_data.get('period_sales'))
			period_receive = flt(receive_data.get('period_receive'))
			period_pay = flt(pay_data.get('period_pay'))
			period_debit = period_sales + period_pay
			period_credit = period_receive

			# Closing balance
			total_sales = flt(sales_data.get('total_sales'))
			total_receive = flt(receive_data.get('total_receive'))
			total_pay = flt(pay_data.get('total_pay'))
			closing_debit_total = total_sales + total_pay
			closing_credit_total = total_receive
			closing_balance = closing_debit_total - closing_credit_total

			row = {
				'party': c['customer'],
				'party_type': 'Customer',
				'party_group': customer_group,
				'opening_debit': opening_balance if opening_balance > 0 else 0,
				'opening_credit': abs(opening_balance) if opening_balance < 0 else 0,
				'transaction_debit': period_debit,
				'transaction_credit': period_credit,
				'closing_debit': closing_balance if closing_balance > 0 else 0,
				'closing_credit': abs(closing_balance) if closing_balance < 0 else 0
			}
			data.append(row)

			for k in ['opening_debit', 'opening_credit', 'transaction_debit',
					  'transaction_credit', 'closing_debit', 'closing_credit']:
				cust_total[k] += row[k]

		if customers:
			data.append(cust_total)
			data.append({
				'party': '', 'party_type': '', 'party_group': '',
				'opening_debit': 0, 'opening_credit': 0,
				'transaction_debit': 0, 'transaction_credit': 0,
				'closing_debit': 0, 'closing_credit': 0
			})

	# SUPPLIERS - Installment Application + Payment Entry asosida
	if not party_type_filter or party_type_filter == 'Supplier':
		# Barcha supplier'larni Installment Application va Payment Entry dan olish
		# Supplier group filter uchun qo'shimcha shart
		group_join = ""
		group_condition = ""
		if party_group_filter:
			group_join = "INNER JOIN `tabSupplier` s ON s.name = suppliers.supplier"
			group_condition = f"AND s.supplier_group = '{party_group_filter}'"

		suppliers = frappe.db.sql("""
			SELECT DISTINCT suppliers.supplier
			FROM (
				SELECT DISTINCT item.custom_supplier as supplier
				FROM `tabInstallment Application` ia
				INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
				WHERE ia.docstatus = 1
				AND item.custom_supplier IS NOT NULL
				AND item.custom_supplier != ''
				UNION
				SELECT DISTINCT party as supplier
				FROM `tabPayment Entry`
				WHERE party_type = 'Supplier'
				AND docstatus = 1
				AND party IS NOT NULL
				AND party != ''
			) as suppliers
			{group_join}
			WHERE 1=1
			{party_condition}
			{group_condition}
			ORDER BY suppliers.supplier
		""".format(
			group_join=group_join,
			party_condition=f"AND suppliers.supplier = '{party_filter}'" if party_filter else "",
			group_condition=group_condition
		), as_dict=True)

		supp_total = {
			'party': "Jami",
			'party_type': 'SUPPLIER TOTAL',
			'party_group': '',
			'opening_debit': 0,
			'opening_credit': 0,
			'transaction_debit': 0,
			'transaction_credit': 0,
			'closing_debit': 0,
			'closing_credit': 0
		}

		for s in suppliers:
			supplier_name = s['supplier']

			# Supplier Group ni olish
			supplier_group = frappe.db.get_value('Supplier', supplier_name, 'supplier_group') or ''

			# 1. Installment Application - CREDIT (biz supplier'dan qarz oldik)
			installment_data = frappe.db.sql("""
				SELECT
					SUM(CASE WHEN DATE(ia.transaction_date) < %s THEN (item.qty * item.rate) ELSE 0 END) as opening_installment,
					SUM(CASE WHEN DATE(ia.transaction_date) >= %s AND DATE(ia.transaction_date) <= %s THEN (item.qty * item.rate) ELSE 0 END) as period_installment,
					SUM(CASE WHEN DATE(ia.transaction_date) <= %s THEN (item.qty * item.rate) ELSE 0 END) as total_installment
				FROM `tabInstallment Application` ia
				INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
				WHERE ia.docstatus = 1
				AND item.custom_supplier = %s
			""", (from_date, from_date, to_date, to_date, supplier_name), as_dict=True)[0]

			# 2. Payment Entry Pay - DEBIT (biz supplier'ga to'ladik)
			pay_data = frappe.db.sql("""
				SELECT
					SUM(CASE WHEN posting_date < %s THEN paid_amount ELSE 0 END) as opening_pay,
					SUM(CASE WHEN posting_date >= %s AND posting_date <= %s THEN paid_amount ELSE 0 END) as period_pay,
					SUM(CASE WHEN posting_date <= %s THEN paid_amount ELSE 0 END) as total_pay
				FROM `tabPayment Entry`
				WHERE party = %s
				AND party_type = 'Supplier'
				AND payment_type = 'Pay'
				AND docstatus = 1
			""", (from_date, from_date, to_date, to_date, supplier_name), as_dict=True)[0]

			# 3. Payment Entry Receive - CREDIT (supplier bizga pul qaytardi)
			receive_data = frappe.db.sql("""
				SELECT
					SUM(CASE WHEN posting_date < %s THEN paid_amount ELSE 0 END) as opening_receive,
					SUM(CASE WHEN posting_date >= %s AND posting_date <= %s THEN paid_amount ELSE 0 END) as period_receive,
					SUM(CASE WHEN posting_date <= %s THEN paid_amount ELSE 0 END) as total_receive
				FROM `tabPayment Entry`
				WHERE party = %s
				AND party_type = 'Supplier'
				AND payment_type = 'Receive'
				AND docstatus = 1
			""", (from_date, from_date, to_date, to_date, supplier_name), as_dict=True)[0]

			# CREDIT = Installment + Receive (biz qarz oldik + supplier qaytardi)
			# DEBIT = Pay (biz to'ladik)
			opening_installment = flt(installment_data.get('opening_installment'))
			opening_receive = flt(receive_data.get('opening_receive'))
			opening_pay = flt(pay_data.get('opening_pay'))
			opening_credit_total = opening_installment + opening_receive
			opening_debit_total = opening_pay
			opening_balance = opening_credit_total - opening_debit_total

			# Transaction: faqat davr ichidagi
			period_installment = flt(installment_data.get('period_installment'))
			period_receive = flt(receive_data.get('period_receive'))
			period_pay = flt(pay_data.get('period_pay'))
			period_credit = period_installment + period_receive
			period_debit = period_pay

			# Closing balance
			total_installment = flt(installment_data.get('total_installment'))
			total_receive = flt(receive_data.get('total_receive'))
			total_pay = flt(pay_data.get('total_pay'))
			closing_credit_total = total_installment + total_receive
			closing_debit_total = total_pay
			closing_balance = closing_credit_total - closing_debit_total

			row = {
				'party': supplier_name,
				'party_type': 'Supplier',
				'party_group': supplier_group,
				'opening_debit': abs(opening_balance) if opening_balance < 0 else 0,
				'opening_credit': opening_balance if opening_balance > 0 else 0,
				'transaction_debit': period_debit,
				'transaction_credit': period_credit,
				'closing_debit': abs(closing_balance) if closing_balance < 0 else 0,
				'closing_credit': closing_balance if closing_balance > 0 else 0
			}
			data.append(row)

			for k in ['opening_debit', 'opening_credit', 'transaction_debit',
					  'transaction_credit', 'closing_debit', 'closing_credit']:
				supp_total[k] += row[k]

		if suppliers:
			data.append(supp_total)

	return data
