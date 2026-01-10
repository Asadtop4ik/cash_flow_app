# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, get_last_day, get_first_day
from datetime import datetime
from collections import defaultdict


def execute(filters=None):
	"""Main execution function"""
	if not filters:
		filters = {}

	validate_filters(filters)
	columns = get_columns(filters)
	data_loader = OperationalBalanceData(filters)
	raw_data = data_loader.load_all_data()
	data = build_tree_structure(raw_data, filters)

	return columns, data


def validate_filters(filters):
	"""Validate and set default filters"""
	if not filters.get("from_date"):
		filters["from_date"] = get_first_day(getdate())
	if not filters.get("to_date"):
		filters["to_date"] = get_last_day(getdate())
	if not filters.get("periodicity"):
		filters["periodicity"] = "Monthly"

	filters["from_date"] = getdate(filters["from_date"])
	filters["to_date"] = getdate(filters["to_date"])

	if filters["from_date"] > filters["to_date"]:
		frappe.throw(_("From Date cannot be after To Date"))


def get_columns(filters):
	"""Generate dynamic columns based on periodicity"""
	columns = [
		{
			"label": _("Hisob"),
			"fieldname": "account",
			"fieldtype": "Data",
			"width": 350
		}
	]

	periods = get_periods(filters)
	for period in periods:
		columns.append({
			"label": period["label"],
			"fieldname": period["key"],
			"fieldtype": "Currency",
			"width": 150
		})

	return columns


def get_periods(filters):
	"""Generate period list based on periodicity"""
	periods = []
	periodicity = filters.get("periodicity", "Monthly")
	from_date = filters["from_date"]
	to_date = filters["to_date"]
	current_date = from_date

	if periodicity == "Daily":
		while current_date <= to_date:
			periods.append({
				"key": current_date.strftime("%Y-%m-%d"),
				"label": current_date.strftime("%d/%m/%Y"),
				"from_date": current_date,
				"to_date": current_date
			})
			current_date = add_days(current_date, 1)

	elif periodicity == "Monthly":
		while current_date <= to_date:
			month_end = get_last_day(current_date)
			if month_end > to_date:
				month_end = to_date
			periods.append({
				"key": current_date.strftime("%Y-%m"),
				"label": current_date.strftime("%b %Y"),
				"from_date": get_first_day(current_date),
				"to_date": month_end
			})
			next_month = add_days(month_end, 1)
			current_date = next_month

	elif periodicity == "Quarterly":
		quarter_start = get_quarter_start(from_date)
		while quarter_start <= to_date:
			quarter_end = get_quarter_end(quarter_start)
			if quarter_end > to_date:
				quarter_end = to_date
			quarter_num = ((quarter_start.month - 1) // 3) + 1
			periods.append({
				"key": f"{quarter_start.year}-Q{quarter_num}",
				"label": f"Q{quarter_num} {quarter_start.year}",
				"from_date": quarter_start,
				"to_date": quarter_end
			})
			quarter_start = add_days(quarter_end, 1)

	elif periodicity == "Yearly":
		year = from_date.year
		while year <= to_date.year:
			year_start = datetime(year, 1, 1).date()
			year_end = datetime(year, 12, 31).date()
			if year_start < from_date:
				year_start = from_date
			if year_end > to_date:
				year_end = to_date
			periods.append({
				"key": str(year),
				"label": str(year),
				"from_date": year_start,
				"to_date": year_end
			})
			year += 1

	return periods


def get_quarter_start(date):
	"""Get quarter start date"""
	quarter = ((date.month - 1) // 3) + 1
	month = (quarter - 1) * 3 + 1
	return datetime(date.year, month, 1).date()


def get_quarter_end(quarter_start):
	"""Get quarter end date"""
	month = quarter_start.month + 2
	year = quarter_start.year
	if month > 12:
		month = 12
	return get_last_day(datetime(year, month, 1).date())


class OperationalBalanceData:
	"""Optimized data loader - single query per entity type"""

	def __init__(self, filters):
		self.filters = filters
		self.to_date = filters["to_date"]
		self.periods = get_periods(filters)

	def load_all_data(self):
		"""Load ALL historical data from beginning of time (no date filter in SQL)
		
		Balance Sheet is a cumulative report showing position from business start
		to end of each period. Date filtering is done in Python code per period.
		"""
		return {
			"cash_accounts": self.load_cash_accounts(),
			"sales_orders": self.load_sales_orders(),
			"payment_entries": self.load_payment_entries(),
			"installment_applications": self.load_installment_applications(),
			"installment_application_items": self.load_installment_application_items(),
			"counterparty_categories": self.load_counterparty_categories(),
			"shareholders": self.load_shareholders()
		}

	def load_cash_accounts(self):
		"""Load ALL cash transactions from beginning of time (no date filter)"""
		query = """
			SELECT
				acc.name as account_name,
				pe.posting_date,
				CASE
					WHEN pe.payment_type = 'Receive' AND pe.paid_to = acc.name THEN pe.received_amount
					WHEN pe.payment_type = 'Pay' AND pe.paid_from = acc.name THEN -pe.paid_amount
					WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_to = acc.name THEN pe.received_amount
					WHEN pe.payment_type = 'Internal Transfer' AND pe.paid_from = acc.name THEN -pe.paid_amount
					ELSE 0
				END as amount
			FROM `tabAccount` acc
			LEFT JOIN `tabPayment Entry` pe ON (
				(pe.paid_to = acc.name OR pe.paid_from = acc.name)
				AND pe.docstatus = 1
			)
			WHERE acc.account_type = 'Cash'
				AND acc.is_group = 0
			ORDER BY acc.name, pe.posting_date
		"""
		return frappe.db.sql(query, as_dict=1)

	def load_sales_orders(self):
		"""Load ALL sales orders from beginning (no date filter)"""
		return frappe.db.sql("""
			SELECT
				so.name,
				so.customer,
				so.customer_name,
				so.transaction_date,
				so.grand_total,
				cg.customer_group_name
			FROM `tabSales Order` so
			LEFT JOIN `tabCustomer` c ON c.name = so.customer
			LEFT JOIN `tabCustomer Group` cg ON cg.name = c.customer_group
			WHERE so.docstatus = 1
			ORDER BY cg.customer_group_name, so.customer, so.transaction_date
		""", as_dict=1)

	def load_payment_entries(self):
		"""Load ALL payment entries from beginning (no date filter)"""
		return frappe.db.sql("""
			SELECT
				pe.name,
				pe.posting_date,
				pe.party_type,
				pe.party,
				pe.party_name,
				pe.payment_type,
				pe.paid_amount,
				pe.received_amount,
				pe.custom_counterparty_category,
				CASE
					WHEN pe.party_type = 'Customer' THEN cg.customer_group_name
					WHEN pe.party_type = 'Supplier' THEN sg.supplier_group_name
					ELSE NULL
				END as group_name
			FROM `tabPayment Entry` pe
			LEFT JOIN `tabCustomer` c ON c.name = pe.party AND pe.party_type = 'Customer'
			LEFT JOIN `tabCustomer Group` cg ON cg.name = c.customer_group
			LEFT JOIN `tabSupplier` s ON s.name = pe.party AND pe.party_type = 'Supplier'
			LEFT JOIN `tabSupplier Group` sg ON sg.name = s.supplier_group
			WHERE pe.docstatus = 1
			ORDER BY pe.party_type, pe.party, pe.posting_date
		""", as_dict=1)

	def load_installment_applications(self):
		"""Load ALL installment applications from beginning (no date filter)"""
		return frappe.db.sql("""
			SELECT
				ia.name,
				ia.customer,
				ia.customer_name,
				ia.transaction_date,
				ia.custom_total_interest,
				ia.finance_amount,
				cg.customer_group_name
			FROM `tabInstallment Application` ia
			LEFT JOIN `tabCustomer` c ON c.name = ia.customer
			LEFT JOIN `tabCustomer Group` cg ON cg.name = c.customer_group
			WHERE ia.docstatus = 1
			ORDER BY cg.customer_group_name, ia.customer, ia.transaction_date
		""", as_dict=1)

	def load_installment_application_items(self):
		"""Load ALL installment application items from beginning (no date filter)"""
		return frappe.db.sql("""
			SELECT
				ia.name as parent_ia,
				ia.transaction_date,
				item.custom_supplier as supplier,
				item.qty,
				item.rate,
				(item.qty * item.rate) as amount,
				sg.supplier_group_name
			FROM `tabInstallment Application` ia
			INNER JOIN `tabInstallment Application Item` item ON item.parent = ia.name
			LEFT JOIN `tabSupplier` s ON s.name = item.custom_supplier
			LEFT JOIN `tabSupplier Group` sg ON sg.name = s.supplier_group
			WHERE ia.docstatus = 1
				AND item.custom_supplier IS NOT NULL
				AND item.custom_supplier != ''
			ORDER BY sg.supplier_group_name, item.custom_supplier, ia.transaction_date
		""", as_dict=1)

	def load_counterparty_categories(self):
		"""Load active counterparty categories"""
		return frappe.db.sql("""
			SELECT name, category_name, category_type, custom_expense_type
			FROM `tabCounterparty Category`
			WHERE is_active = 1
		""", as_dict=1)

	def load_shareholders(self):
		"""Load all shareholders with their custom_category"""
		return frappe.db.sql("""
			SELECT name, title, custom_category
			FROM `tabShareholder`
		""", as_dict=1)


def build_tree_structure(raw_data, filters):
	"""Build hierarchical tree with CUMULATIVE balances (Balance Sheet Standard)"""
	periods = get_periods(filters)
	data = []

	def create_row(account, indent=0, is_group=False, **kwargs):
		"""Helper to create row with all period columns initialized"""
		row = {"account": account, "indent": indent, "is_group": is_group}
		for period in periods:
			row[period["key"]] = 0
		row.update(kwargs)
		return row

	# Create category lookup dictionary
	category_dict = {cc["name"]: cc for cc in raw_data["counterparty_categories"]}

	# Create shareholder lookup dictionary
	shareholder_dict = {sh["name"]: sh for sh in raw_data["shareholders"]}

	# ============================================================
	# SECTION 1: AKTIVLAR (ASSETS) - ALL CUMULATIVE
	# ============================================================

	aktivlar_row = create_row("AKTIVLAR", indent=0, is_group=True)
	data.append(aktivlar_row)

	# 1.1 PUL (Cash) - CUMULATIVE
	pul_row = create_row("Pul", indent=1, is_group=True)
	data.append(pul_row)

	cash_accounts = defaultdict(list)
	for t in raw_data["cash_accounts"]:
		if t.get("account_name"):
			cash_accounts[t["account_name"]].append(t)

	for account_name in sorted(cash_accounts.keys()):
		account_row = create_row(account_name, indent=2)
		transactions = cash_accounts[account_name]

		for period in periods:
			# CUMULATIVE: From beginning to period end
			balance = sum(
				flt(t["amount"]) for t in transactions
				if t.get("posting_date") and getdate(t["posting_date"]) <= period["to_date"]
			)
			account_row[period["key"]] = balance
			pul_row[period["key"]] += balance
			aktivlar_row[period["key"]] += balance

		data.append(account_row)

	# 1.2 DEBITORKA (Receivables) - CUMULATIVE
	debitorka_row = create_row("Debitorka", indent=1, is_group=True)
	data.append(debitorka_row)

	# 1.2.1 Mijozlar (Customer Receivables) - CUMULATIVE
	# Logika: Kontragent reportdagi kabi
	# Debit = Sales Order + Payment Pay (biz qaytargan)
	# Credit = Payment Receive (klient to'lagan)
	# Balance = Debit - Credit
	debitorka_mijozlar_row = create_row("Mijozlar", indent=2, is_group=True)
	data.append(debitorka_mijozlar_row)

	customer_groups = defaultdict(lambda: defaultdict(lambda: {"debit": [], "credit": []}))

	# Sales Orders - DEBIT
	for so in raw_data["sales_orders"]:
		group = so.get("customer_group_name") or "Boshqa"
		customer_groups[group][so["customer"]]["debit"].append({
			"type": "sales_order",
			"date": so["transaction_date"],
			"amount": flt(so["grand_total"])
		})

	# Supplier Payables initialization (ishlatiladi Debitorka va Kreditorka'da)
	supplier_payables = defaultdict(lambda: defaultdict(lambda: {"credit": [], "debit": []}))

	# Installment Application Items - CREDIT
	for ia_item in raw_data["installment_application_items"]:
		group = ia_item.get("supplier_group_name") or "Boshqa"
		supplier_payables[group][ia_item["supplier"]]["credit"].append({
			"type": "ia_item",
			"date": ia_item["transaction_date"],
			"amount": flt(ia_item["amount"])
		})

	# Payment Entries - Customer va Supplier
	for pe in raw_data["payment_entries"]:
		if pe["party_type"] == "Customer":
			group = pe.get("group_name") or "Boshqa"
			if pe["payment_type"] == "Pay":
				# Biz klientga qaytargan - DEBIT
				customer_groups[group][pe["party"]]["debit"].append({
					"type": "payment_pay",
					"date": pe["posting_date"],
					"amount": flt(pe["paid_amount"])
				})
			elif pe["payment_type"] == "Receive":
				# Klient bizga to'lagan - CREDIT
				customer_groups[group][pe["party"]]["credit"].append({
					"type": "payment_receive",
					"date": pe["posting_date"],
					"amount": flt(pe["received_amount"])
				})
		elif pe["party_type"] == "Supplier":
			group = pe.get("group_name") or "Boshqa"
			if pe["payment_type"] == "Pay":
				# Biz supplierga to'ladik - DEBIT
				supplier_payables[group][pe["party"]]["debit"].append({
					"type": "payment_pay",
					"date": pe["posting_date"],
					"amount": flt(pe["paid_amount"])
				})
			elif pe["payment_type"] == "Receive":
				# Supplier bizga qaytardi - CREDIT
				supplier_payables[group][pe["party"]]["credit"].append({
					"type": "payment_receive",
					"date": pe["posting_date"],
					"amount": flt(pe["received_amount"])
				})

	for group_name in sorted(customer_groups.keys()):
		group_row = create_row(group_name, indent=3, is_group=True)
		data.append(group_row)

		for customer in sorted(customer_groups[group_name].keys()):
			customer_row = create_row(customer, indent=4)
			debit_transactions = customer_groups[group_name][customer]["debit"]
			credit_transactions = customer_groups[group_name][customer]["credit"]

			for period in periods:
				# CUMULATIVE: Biznes boshidan period oxirigacha
				# Debit = Sales Order + Pay
				total_debit = sum(
					t["amount"] for t in debit_transactions
					if getdate(t["date"]) <= period["to_date"]
				)

				# Credit = Receive
				total_credit = sum(
					t["amount"] for t in credit_transactions
					if getdate(t["date"]) <= period["to_date"]
				)

				# Balance = Debit - Credit
				# Agar musbat -> klient bizdan qarz (Debitorka)
				# Agar manfiy -> biz klientdan qarz (bu kreditorka bo'ladi)
				balance = total_debit - total_credit
				
				# Faqat musbat balanslar Debitorka'da ko'rsatiladi
				if balance > 0:
					customer_row[period["key"]] = balance
					group_row[period["key"]] += balance
					debitorka_mijozlar_row[period["key"]] += balance
					debitorka_row[period["key"]] += balance
					aktivlar_row[period["key"]] += balance
				else:
					customer_row[period["key"]] = 0

			data.append(customer_row)

	# 1.2.2 Yetkazib beruvchilar (Supplier Advances) - CUMULATIVE
	# Manfiy balanslar (biz supplier'ga avans berdik)
	# Bu yerda Credit - Debit < 0 bo'lgan supplierlar ko'rsatiladi
	debitorka_suppliers_row = create_row("Yetkazib beruvchilar (Avanslar)", indent=2,
										 is_group=True)
	data.append(debitorka_suppliers_row)

	# Yuqorida supplier_payables to'ldirilgan
	# Endi faqat manfiy balanslarni (biz avans berdik) ko'rsatamiz
	for group_name in sorted(supplier_payables.keys()):
		group_row = create_row(group_name, indent=3, is_group=True)
		group_has_data = False

		temp_suppliers = []
		for supplier in sorted(supplier_payables[group_name].keys()):
			supplier_row = create_row(supplier, indent=4)
			credit_transactions = supplier_payables[group_name][supplier]["credit"]
			debit_transactions = supplier_payables[group_name][supplier]["debit"]
			has_negative = False

			for period in periods:
				# CUMULATIVE: Biznes boshidan period oxirigacha
				total_credit = sum(
					t["amount"] for t in credit_transactions
					if getdate(t["date"]) <= period["to_date"]
				)

				total_debit = sum(
					t["amount"] for t in debit_transactions
					if getdate(t["date"]) <= period["to_date"]
				)

				# Balance = Credit - Debit
				# Agar manfiy -> biz supplierga avans berdik (Debitorka)
				balance = total_credit - total_debit
				
				if balance < 0:
					# Manfiy balans - avans (musbat qilib ko'rsatamiz)
					supplier_row[period["key"]] = abs(balance)
					group_row[period["key"]] += abs(balance)
					debitorka_suppliers_row[period["key"]] += abs(balance)
					debitorka_row[period["key"]] += abs(balance)
					aktivlar_row[period["key"]] += abs(balance)
					has_negative = True
				else:
					supplier_row[period["key"]] = 0

			if has_negative:
				temp_suppliers.append(supplier_row)
				group_has_data = True

		if group_has_data:
			data.append(group_row)
			data.extend(temp_suppliers)

	# ============================================================
	# SECTION 2: JAMI KREDITORKA - ALL CUMULATIVE
	# ============================================================

	jami_kreditorka_row = create_row("JAMI KREDITORKA", indent=0, is_group=True)
	data.append(jami_kreditorka_row)

	# 2.1 KREDITORKA (Payables) - CUMULATIVE
	kreditorka_subsection_row = create_row("Kreditorka", indent=1, is_group=True)
	data.append(kreditorka_subsection_row)

	# 2.1.1 Mijozlar (Customer Advances) - CUMULATIVE
	# Manfiy balanslar (klient avans bergan)
	# Bu yerda Debit - Credit < 0 bo'lgan mijozlar ko'rsatiladi
	kreditorka_mijozlar_row = create_row("Mijozlar (Avanslar)", indent=2, is_group=True)
	data.append(kreditorka_mijozlar_row)

	# Yuqorida allaqachon customer_groups to'ldirilgan
	# Endi faqat manfiy balanslarni ko'rsatamiz
	for group_name in sorted(customer_groups.keys()):
		group_row = create_row(group_name, indent=3, is_group=True)
		group_has_data = False

		temp_customers = []
		for customer in sorted(customer_groups[group_name].keys()):
			customer_row = create_row(customer, indent=4)
			debit_transactions = customer_groups[group_name][customer]["debit"]
			credit_transactions = customer_groups[group_name][customer]["credit"]
			has_negative = False

			for period in periods:
				# CUMULATIVE: Biznes boshidan period oxirigacha
				total_debit = sum(
					t["amount"] for t in debit_transactions
					if getdate(t["date"]) <= period["to_date"]
				)

				total_credit = sum(
					t["amount"] for t in credit_transactions
					if getdate(t["date"]) <= period["to_date"]
				)

				# Balance = Debit - Credit
				# Agar manfiy -> biz klientdan qarz (Kreditorka)
				balance = total_debit - total_credit
				
				if balance < 0:
					# Manfiy balans - avans (musbat qilib ko'rsatamiz)
					customer_row[period["key"]] = abs(balance)
					group_row[period["key"]] += abs(balance)
					kreditorka_mijozlar_row[period["key"]] += abs(balance)
					kreditorka_subsection_row[period["key"]] += abs(balance)
					has_negative = True
				else:
					customer_row[period["key"]] = 0

			if has_negative:
				temp_customers.append(customer_row)
				group_has_data = True

		if group_has_data:
			data.append(group_row)
			data.extend(temp_customers)

	# 2.1.2 Yetkazib beruvchilar (Supplier Payables) - CUMULATIVE
	# Logika: Kontragent reportdagi kabi
	# Credit = Installment Application + Payment Receive (biz qarz oldik)
	# Debit = Payment Pay (biz to'ladik)
	# Balance = Credit - Debit
	kreditorka_suppliers_row = create_row("Yetkazib beruvchilar (Qarzlar)", indent=2,
										  is_group=True)
	data.append(kreditorka_suppliers_row)

	# supplier_payables allaqachon yuqorida to'ldirilgan

	for group_name in sorted(supplier_payables.keys()):
		group_row = create_row(group_name, indent=3, is_group=True)
		data.append(group_row)

		for supplier in sorted(supplier_payables[group_name].keys()):
			supplier_row = create_row(supplier, indent=4)
			credit_transactions = supplier_payables[group_name][supplier]["credit"]
			debit_transactions = supplier_payables[group_name][supplier]["debit"]

			for period in periods:
				# CUMULATIVE: Biznes boshidan period oxirigacha
				# Credit = Installment + Receive
				total_credit = sum(
					t["amount"] for t in credit_transactions
					if getdate(t["date"]) <= period["to_date"]
				)

				# Debit = Pay
				total_debit = sum(
					t["amount"] for t in debit_transactions
					if getdate(t["date"]) <= period["to_date"]
				)

				# Balance = Credit - Debit
				# Agar musbat -> biz supplierdan qarz (Kreditorka)
				balance = total_credit - total_debit
				
				if balance > 0:
					supplier_row[period["key"]] = balance
					group_row[period["key"]] += balance
					kreditorka_suppliers_row[period["key"]] += balance
					kreditorka_subsection_row[period["key"]] += balance
				else:
					supplier_row[period["key"]] = 0

			data.append(supplier_row)

	# 2.2 USTAV KAPITALI (Share Capital) - CUMULATIVE
	# Filter by Shareholder.custom_category = "Ustav Kapitali"
	ustav_row = create_row("Ustav Kapitali", indent=1, is_group=True)

	for period in periods:
		# CUMULATIVE: From beginning to period end
		# Only Shareholder payments where Shareholder.custom_category = "Ustav Kapitali"
		receive = sum(
			flt(pe["received_amount"]) for pe in raw_data["payment_entries"]
			if pe["party_type"] == "Shareholder"
			and pe["payment_type"] == "Receive"
			and pe.get("party") in shareholder_dict
			and shareholder_dict.get(pe["party"], {}).get("custom_category") == "Ustav Kapitali"
			and getdate(pe["posting_date"]) <= period["to_date"]
		)
		pay = sum(
			flt(pe["paid_amount"]) for pe in raw_data["payment_entries"]
			if pe["party_type"] == "Shareholder"
			and pe["payment_type"] == "Pay"
			and pe.get("party") in shareholder_dict
			and shareholder_dict.get(pe["party"], {}).get("custom_category") == "Ustav Kapitali"
			and getdate(pe["posting_date"]) <= period["to_date"]
		)
		# Receive adds to capital, Pay reduces capital
		balance = receive - pay
		ustav_row[period["key"]] = balance

	data.append(ustav_row)

	# ============================================================
	# 2.3 SOF FOYDA (NET PROFIT) - PROFESSIONAL STRUCTURE
	# Parent: Sof Foyda (Net Profit)
	# Children: Taqsimlangan, Joriy, Dividends
	# Formula: Parent = Taqsimlangan + Joriy - Dividends
	# ============================================================

	# Parent row: Sof Foyda (Net Profit after Dividends)
	net_profit_parent_row = create_row("Sof Foyda", indent=1, is_group=True)
	
	# Child 1: Taqsimlangan Sof Foyda (Retained Earnings from previous periods)
	# Biznes boshlanganidan o'tgan oyning oxirigacha
	retained_earnings_row = create_row("Taqsimlangan Sof Foyda", indent=2)
	
	# Child 2: Joriy Sof Foyda (Current Period Profit)
	# Faqat shu oy ichidagi foyda
	current_profit_row = create_row("Joriy Sof Foyda", indent=2)
	
	# Child 3: Dividends (Manfiy - kapitaldan chiqarilgan)
	# Biznes boshlanganidan shu oyning oxirigacha
	dividends_row = create_row("Dividends", indent=2)
	
	# Shareholder dividends detail rows (indent=3)
	shareholder_dividends = defaultdict(list)
	for pe in raw_data["payment_entries"]:
		if (pe["party_type"] == "Shareholder"
			and pe["payment_type"] == "Pay"
			and pe.get("party") in shareholder_dict
			and shareholder_dict.get(pe["party"], {}).get("custom_category") == "Dividends"):
			shareholder_dividends[pe["party"]].append(pe)

	for i, period in enumerate(periods):
		# ============================================================
		# 1. JORIY SOF FOYDA (Current Period Profit)
		# Faqat shu oy: from_date to to_date
		# ============================================================
		current_interest = sum(
			flt(ia["custom_total_interest"]) for ia in raw_data["installment_applications"]
			if period["from_date"] <= getdate(ia["transaction_date"]) <= period["to_date"]
		)

		current_expenses = 0
		for pe in raw_data["payment_entries"]:
			if (period["from_date"] <= getdate(pe["posting_date"]) <= period["to_date"]
				and pe.get("custom_counterparty_category")):

				category = category_dict.get(pe["custom_counterparty_category"])

				if category and category.get("custom_expense_type") == "Xarajat":
					amount = flt(pe["paid_amount"])

					if category.get("category_type") == "Income":
						amount = -amount

					current_expenses += amount

		current_period_profit = current_interest - current_expenses
		current_profit_row[period["key"]] = current_period_profit

		# ============================================================
		# 2. TAQSIMLANGAN SOF FOYDA (Retained Earnings)
		# O'tgan davrlarning to'plangan foydasi
		# ============================================================
		
		if i == 0:
			# Birinchi period uchun: period boshlanishidan OLDINGI foydalar
			prev_date = add_days(period["from_date"], -1)
			
			# O'tgan davr foydasi
			prev_interest = sum(
				flt(ia["custom_total_interest"]) for ia in raw_data["installment_applications"]
				if getdate(ia["transaction_date"]) <= prev_date
			)
			
			prev_expenses = 0
			for pe in raw_data["payment_entries"]:
				if (getdate(pe["posting_date"]) <= prev_date
					and pe.get("custom_counterparty_category")):

					category = category_dict.get(pe["custom_counterparty_category"])

					if category and category.get("custom_expense_type") == "Xarajat":
						amount = flt(pe["paid_amount"])

						if category.get("category_type") == "Income":
							amount = -amount

						prev_expenses += amount
			
			prev_total_profit = prev_interest - prev_expenses
			
			# O'tgan davr dividendlari
			prev_dividends = sum(
				flt(pe["paid_amount"]) for pe in raw_data["payment_entries"]
				if pe["party_type"] == "Shareholder"
				and pe["payment_type"] == "Pay"
				and pe.get("party") in shareholder_dict
				and shareholder_dict.get(pe["party"], {}).get("custom_category") == "Dividends"
				and getdate(pe["posting_date"]) <= prev_date
			)
			
			retained = prev_total_profit - prev_dividends
		else:
			# Keyingi periodlar: o'tgan period Sof Foyda (Parent)
			prev_period_key = periods[i-1]["key"]
			retained = net_profit_parent_row[prev_period_key]
		
		retained_earnings_row[period["key"]] = retained

		# ============================================================
		# 3. DIVIDENDS (Cumulative, Negative)
		# Biznes boshlanganidan shu oyning oxirigacha
		# ============================================================
		total_dividends_cumulative = sum(
			flt(pe["paid_amount"]) for pe in raw_data["payment_entries"]
			if pe["party_type"] == "Shareholder"
			and pe["payment_type"] == "Pay"
			and pe.get("party") in shareholder_dict
			and shareholder_dict.get(pe["party"], {}).get("custom_category") == "Dividends"
			and getdate(pe["posting_date"]) <= period["to_date"]
		)
		
		# Manfiy ko'rsatiladi (kapitaldan chiqarilgan)
		dividends_row[period["key"]] = -total_dividends_cumulative
		
		# ============================================================
		# 4. SOF FOYDA (Parent) = Retained + Current - Dividends
		# ============================================================
		net_profit_parent_row[period["key"]] = (
			retained + 
			current_period_profit - 
			total_dividends_cumulative
		)

	# Add rows to data
	data.append(net_profit_parent_row)
	data.append(retained_earnings_row)
	data.append(current_profit_row)
	data.append(dividends_row)

	# Add shareholder detail rows under Dividends (indent=3)
	for shareholder in sorted(shareholder_dividends.keys()):
		shareholder_name = shareholder_dict.get(shareholder, {}).get("title") or shareholder
		shareholder_row = create_row(shareholder_name, indent=3)

		for period in periods:
			# CUMULATIVE: Biznes boshlanganidan period oxirigacha
			paid_amount = sum(
				flt(pe["paid_amount"]) for pe in shareholder_dividends[shareholder]
				if pe["payment_type"] == "Pay"
				and getdate(pe["posting_date"]) <= period["to_date"]
			)

			# Manfiy ko'rsatiladi
			shareholder_row[period["key"]] = -paid_amount

		data.append(shareholder_row)

	# ============================================================
	# JAMI KREDITORKA CALCULATION
	# Formula: Kreditorka + Ustav Kapitali + Sof Foyda (includes Dividends)
	# ============================================================
	for period in periods:
		jami_kreditorka_row[period["key"]] = (
			kreditorka_subsection_row[period["key"]] +
			ustav_row[period["key"]] +
			net_profit_parent_row[period["key"]]
			# Note: Dividends already included in net_profit_parent_row
		)

	# ============================================================
	# SECTION 3: BALANS (Balance Check)
	# ============================================================

	balans_row = create_row("BALANS", indent=0, is_group=True)

	for period in periods:
		difference = aktivlar_row[period["key"]] - jami_kreditorka_row[period["key"]]
		balans_row[period["key"]] = difference

	data.append(balans_row)

	return data
