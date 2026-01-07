# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, get_last_day, get_first_day
from datetime import datetime, timedelta
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
	"""Data loader class"""

	def __init__(self, filters):
		self.filters = filters
		self.from_date = filters["from_date"]
		self.to_date = filters["to_date"]
		self.periods = get_periods(filters)

	def load_all_data(self):
		"""Load all data at once"""
		return {
			"cash_accounts": self.load_cash_accounts(),
			"sales_orders": self.load_sales_orders(),
			"payment_entries": self.load_payment_entries(),
			"installment_applications": self.load_installment_applications(),
			"installment_application_items": self.load_installment_application_items(),
			"counterparty_categories": self.load_counterparty_categories()
		}

	def load_cash_accounts(self):
		"""Load cash and bank account balances"""
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
                AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
            )
            WHERE acc.account_type = 'Cash'
                AND acc.is_group = 0
            ORDER BY acc.name, pe.posting_date
        """
		return frappe.db.sql(query, {
			"from_date": self.from_date,
			"to_date": self.to_date
		}, as_dict=1)

	def load_sales_orders(self):
		"""Load sales orders"""
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
                AND so.transaction_date BETWEEN %(from_date)s AND %(to_date)s
            ORDER BY cg.customer_group_name, so.customer, so.transaction_date
        """, {"from_date": self.from_date, "to_date": self.to_date}, as_dict=1)

	def load_payment_entries(self):
		"""Load all payment entries"""
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
                AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
            ORDER BY pe.party_type, pe.party, pe.posting_date
        """, {"from_date": self.from_date, "to_date": self.to_date}, as_dict=1)

	def load_installment_applications(self):
		"""Load installment applications"""
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
                AND ia.transaction_date BETWEEN %(from_date)s AND %(to_date)s
            ORDER BY cg.customer_group_name, ia.customer, ia.transaction_date
        """, {"from_date": self.from_date, "to_date": self.to_date}, as_dict=1)

	def load_installment_application_items(self):
		"""Load installment application items with supplier info"""
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
                AND ia.transaction_date BETWEEN %(from_date)s AND %(to_date)s
                AND item.custom_supplier IS NOT NULL
                AND item.custom_supplier != ''
            ORDER BY sg.supplier_group_name, item.custom_supplier, ia.transaction_date
        """, {"from_date": self.from_date, "to_date": self.to_date}, as_dict=1)

	def load_counterparty_categories(self):
		"""Load counterparty categories"""
		return frappe.db.sql("""
            SELECT name, category_name, category_type, custom_expense_type
            FROM `tabCounterparty Category`
            WHERE is_active = 1
        """, as_dict=1)


def build_tree_structure(raw_data, filters):
	"""Build hierarchical tree structure in CORRECT ORDER"""
	periods = get_periods(filters)
	data = []

	def create_row(account, indent=0, is_group=False, **kwargs):
		row = {"account": account, "indent": indent, "is_group": is_group}
		for period in periods:
			row[period["key"]] = 0
		row.update(kwargs)
		return row

	# ============================================================
	# SECTION 1: AKTIVLAR
	# ============================================================

	# Create AKTIVLAR parent row (will be added FIRST)
	aktivlar_row = create_row("AKTIVLAR", indent=0, is_group=True)
	data.append(aktivlar_row)  # ADD IMMEDIATELY!

	# 1.1 PUL
	pul_row = create_row("Pul", indent=1, is_group=True)
	data.append(pul_row)  # ADD IMMEDIATELY after AKTIVLAR!

	# 1.1.1 Cash Accounts (children of Pul)
	cash_accounts = group_by_account(raw_data["cash_accounts"])

	for account_name, transactions in sorted(cash_accounts.items()):
		account_row = create_row(account_name, indent=2)
		for period in periods:
			balance = sum(
				flt(t["amount"]) for t in transactions
				if t.get("posting_date") and getdate(t["posting_date"]) >= period["from_date"]
				and getdate(t["posting_date"]) <= period["to_date"]
			)
			account_row[period["key"]] = balance
			pul_row[period["key"]] += balance
			aktivlar_row[period["key"]] += balance
		data.append(account_row)  # ADD each cash account

	# 1.2 DEBITORKA
	debitorka_row = create_row("Debitorka", indent=1, is_group=True)
	data.append(debitorka_row)

	# 1.2.1 Mijozlar (bizning mijozlardan oladigan pulimiz)
	debitorka_mijozlar_row = create_row("Mijozlar", indent=2, is_group=True)
	data.append(debitorka_mijozlar_row)

	customer_groups = defaultdict(lambda: defaultdict(list))
	for so in raw_data["sales_orders"]:
		group = so.get("customer_group_name") or "Boshqa"
		customer_groups[group][so["customer"]].append(so)

	for pe in raw_data["payment_entries"]:
		if pe["party_type"] == "Customer" and pe["payment_type"] == "Pay":
			group = pe.get("group_name") or "Boshqa"
			customer_groups[group][pe["party"]].append(pe)

	for group_name in sorted(customer_groups.keys()):
		group_row = create_row(group_name, indent=3, is_group=True)
		data.append(group_row)

		for customer in sorted(customer_groups[group_name].keys()):
			customer_row = create_row(customer, indent=4)

			for period in periods:
				so_total = sum(
					flt(so["grand_total"]) for so in customer_groups[group_name][customer]
					if isinstance(so, dict) and so.get("grand_total")
					and getdate(so["transaction_date"]) >= period["from_date"]
					and getdate(so["transaction_date"]) <= period["to_date"]
				)

				pe_pay = sum(
					flt(pe["paid_amount"]) for pe in customer_groups[group_name][customer]
					if isinstance(pe, dict) and pe.get("payment_type") == "Pay"
					and getdate(pe["posting_date"]) >= period["from_date"]
					and getdate(pe["posting_date"]) <= period["to_date"]
				)

				balance = so_total - pe_pay
				customer_row[period["key"]] = balance
				group_row[period["key"]] += balance
				debitorka_mijozlar_row[period["key"]] += balance
				debitorka_row[period["key"]] += balance
				aktivlar_row[period["key"]] += balance

			data.append(customer_row)

	# 1.2.2 Yetkazib beruvchilar (Avanslar)
	debitorka_suppliers_row = create_row("Yetkazib beruvchilar (Avanslar)", indent=2,
										 is_group=True)
	data.append(debitorka_suppliers_row)

	supplier_groups = defaultdict(lambda: defaultdict(list))
	for pe in raw_data["payment_entries"]:
		if pe["party_type"] == "Supplier" and pe["payment_type"] == "Pay":
			group = pe.get("group_name") or "Boshqa"
			supplier_groups[group][pe["party"]].append(pe)

	for group_name in sorted(supplier_groups.keys()):
		group_row = create_row(group_name, indent=3, is_group=True)
		data.append(group_row)

		for supplier in sorted(supplier_groups[group_name].keys()):
			supplier_row = create_row(supplier, indent=4)

			for period in periods:
				balance = sum(
					flt(pe["paid_amount"]) for pe in supplier_groups[group_name][supplier]
					if getdate(pe["posting_date"]) >= period["from_date"]
					and getdate(pe["posting_date"]) <= period["to_date"]
				)
				supplier_row[period["key"]] = balance
				group_row[period["key"]] += balance
				debitorka_suppliers_row[period["key"]] += balance
				debitorka_row[period["key"]] += balance
				aktivlar_row[period["key"]] += balance

			data.append(supplier_row)

	# ============================================================
	# SECTION 2: JAMI KREDITORKA
	# ============================================================

	jami_kreditorka_row = create_row("JAMI KREDITORKA", indent=0, is_group=True)
	data.append(jami_kreditorka_row)

	# 2.1 KREDITORKA (sub-section)
	kreditorka_subsection_row = create_row("Kreditorka", indent=1, is_group=True)
	data.append(kreditorka_subsection_row)

	# 2.1.1 Mijozlar (Avanslar)
	kreditorka_mijozlar_row = create_row("Mijozlar (Avanslar)", indent=2, is_group=True)
	data.append(kreditorka_mijozlar_row)

	customer_payables = defaultdict(lambda: defaultdict(list))
	for pe in raw_data["payment_entries"]:
		if pe["party_type"] == "Customer" and pe["payment_type"] == "Receive":
			group = pe.get("group_name") or "Boshqa"
			customer_payables[group][pe["party"]].append(pe)

	for group_name in sorted(customer_payables.keys()):
		group_row = create_row(group_name, indent=3, is_group=True)
		data.append(group_row)

		for customer in sorted(customer_payables[group_name].keys()):
			customer_row = create_row(customer, indent=4)

			for period in periods:
				balance = sum(
					flt(pe["received_amount"]) for pe in customer_payables[group_name][customer]
					if getdate(pe["posting_date"]) >= period["from_date"]
					and getdate(pe["posting_date"]) <= period["to_date"]
				)
				customer_row[period["key"]] = balance
				group_row[period["key"]] += balance
				kreditorka_mijozlar_row[period["key"]] += balance
				kreditorka_subsection_row[period["key"]] += balance

			data.append(customer_row)

	# 2.1.2 Yetkazib beruvchilar (Qarzlar)
	kreditorka_suppliers_row = create_row("Yetkazib beruvchilar (Qarzlar)", indent=2,
										  is_group=True)
	data.append(kreditorka_suppliers_row)

	# Kreditorka = IA Items (qty * rate) + PE Receive
	supplier_kreditorka = defaultdict(lambda: defaultdict(list))

	# Add IA Items
	for ia_item in raw_data["installment_application_items"]:
		group = ia_item.get("supplier_group_name") or "Boshqa"
		supplier_kreditorka[group][ia_item["supplier"]].append(ia_item)

	# Add PE Receive
	for pe in raw_data["payment_entries"]:
		if pe["party_type"] == "Supplier" and pe["payment_type"] == "Receive":
			group = pe.get("group_name") or "Boshqa"
			supplier_kreditorka[group][pe["party"]].append(pe)

	for group_name in sorted(supplier_kreditorka.keys()):
		group_row = create_row(group_name, indent=3, is_group=True)
		data.append(group_row)

		for supplier in sorted(supplier_kreditorka[group_name].keys()):
			supplier_row = create_row(supplier, indent=4)

			for period in periods:
				# IA Items amount
				ia_amount = sum(
					flt(item["amount"]) for item in supplier_kreditorka[group_name][supplier]
					if isinstance(item, dict) and item.get("amount")
					and getdate(item["transaction_date"]) >= period["from_date"]
					and getdate(item["transaction_date"]) <= period["to_date"]
				)

				# PE Receive amount
				pe_receive = sum(
					flt(pe["received_amount"]) for pe in supplier_kreditorka[group_name][supplier]
					if isinstance(pe, dict) and pe.get("payment_type") == "Receive"
					and getdate(pe["posting_date"]) >= period["from_date"]
					and getdate(pe["posting_date"]) <= period["to_date"]
				)

				balance = ia_amount + pe_receive
				supplier_row[period["key"]] = balance
				group_row[period["key"]] += balance
				kreditorka_suppliers_row[period["key"]] += balance
				kreditorka_subsection_row[period["key"]] += balance

			data.append(supplier_row)

	# 2.2 USTAV KAPITALI
	ustav_row = create_row("Ustav Kapitali", indent=1, is_group=True)

	for period in periods:
		receive = sum(
			flt(pe["received_amount"]) for pe in raw_data["payment_entries"]
			if pe["party_type"] == "Shareholder" and pe["payment_type"] == "Receive"
			and getdate(pe["posting_date"]) >= period["from_date"]
			and getdate(pe["posting_date"]) <= period["to_date"]
		)
		pay = sum(
			flt(pe["paid_amount"]) for pe in raw_data["payment_entries"]
			if pe["party_type"] == "Shareholder" and pe["payment_type"] == "Pay"
			and getdate(pe["posting_date"]) >= period["from_date"]
			and getdate(pe["posting_date"]) <= period["to_date"]
		)
		balance = receive - pay
		ustav_row[period["key"]] = balance

	data.append(ustav_row)

	# 2.3 SOF FOYDA
	sof_foyda_row = create_row("Sof Foyda", indent=1, is_group=True)

	for period in periods:
		interest = sum(
			flt(ia["custom_total_interest"]) for ia in raw_data["installment_applications"]
			if getdate(ia["transaction_date"]) >= period["from_date"]
			and getdate(ia["transaction_date"]) <= period["to_date"]
		)

		# Harajatlarni to'g'ri hisoblash - Custom P&L bilan bir xil logika
		expenses = 0
		for pe in raw_data["payment_entries"]:
			if (getdate(pe["posting_date"]) >= period["from_date"]
				and getdate(pe["posting_date"]) <= period["to_date"]
				and pe.get("custom_counterparty_category")):

				# Counterparty Category ma'lumotlarini olish
				category = next(
					(cc for cc in raw_data["counterparty_categories"]
					 if cc["name"] == pe["custom_counterparty_category"]),
					None
				)

				if category and category.get("custom_expense_type") == "Xarajat":
					amount = flt(pe["paid_amount"])

					# Agar category_type Income bo'lsa, manfiy qilamiz
					if category.get("category_type") == "Income":
						amount = -amount

					expenses += amount

		profit = interest - expenses
		sof_foyda_row[period["key"]] = profit

	data.append(sof_foyda_row)

	# Calculate JAMI KREDITORKA total
	for period in periods:
		jami_kreditorka_row[period["key"]] = (
			kreditorka_subsection_row[period["key"]] +
			ustav_row[period["key"]] +
			sof_foyda_row[period["key"]]
		)

	# ============================================================
	# SECTION 3: BALANS
	# ============================================================

	balans_row = create_row("BALANS", indent=0, is_group=True)

	for period in periods:
		difference = aktivlar_row[period["key"]] - jami_kreditorka_row[period["key"]]
		balans_row[period["key"]] = difference

	data.append(balans_row)

	return data


def group_by_account(transactions):
	"""Group transactions by account"""
	grouped = defaultdict(list)
	for t in transactions:
		if t.get("account_name"):
			grouped[t["account_name"]].append(t)
	return grouped
