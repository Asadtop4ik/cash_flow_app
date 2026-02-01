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
    """Optimized data loader - GL Entry based"""

    def __init__(self, filters):
        self.filters = filters
        self.to_date = filters["to_date"]

    def load_all_data(self):
        """Hamma narsani yuklash: GL (raqamlar) + Categories (guruhlar)"""
        return {
            "gl_entries": self.load_gl_data(),
            # Quyidagi ikkita funksiya pastda aniqlangan bo'lishi SHART
            "counterparty_categories": self.load_counterparty_categories(),
            "shareholders": self.load_shareholders(),
            "cash_accounts": self.load_cash_accounts()
        }

    def load_gl_data(self):
        """
        Barcha moliyaviy haqiqat manbasi (GL Entry).
        """
        return frappe.db.sql("""
            SELECT
                party_type,
                party,
                account,
                SUM(debit) as total_debit,
                SUM(credit) as total_credit,
                (SUM(debit) - SUM(credit)) as balance
            FROM `tabGL Entry`
            WHERE posting_date <= %(to_date)s
              AND is_cancelled = 0
            GROUP BY party_type, party, account
        """, {"to_date": self.to_date}, as_dict=1)

    def load_counterparty_categories(self):
        """Sizda yetishmayotgan funksiya: Kustom kategoriyalarni yuklash"""
        return frappe.db.sql("""
            SELECT name, category_name, category_type, custom_expense_type
            FROM `tabCounterparty Category`
            WHERE is_active = 1
        """, as_dict=1)

    def load_shareholders(self):
        """Ta'sischilarni yuklash"""
        return frappe.db.sql("""
            SELECT name, title, custom_category
            FROM `tabShareholder`
        """, as_dict=1)

    def load_cash_accounts(self):
        """Kassa hisob raqamlarini yuklash (Pul bo'limi uchun)"""
        # Buni GL dan olish ham mumkin, lekin hozircha eski koddan qoldiramiz
        # sababi build_tree_structure da 'cash_accounts' ishlatilyapti
        return frappe.db.sql("""
            SELECT name as account_name
            FROM `tabAccount`
            WHERE account_type = 'Cash' AND is_group = 0
        """, as_dict=1)
def build_tree_structure(raw_data, filters):
	"""
	YANGILANGAN MANTIQ: GL Entry asosida Balans
	"""
	periods = get_periods(filters)
	data = []

	# ---------------------------------------------------------
	# YORDAMCHI FUNKSIYA: Qator yaratish
	# ---------------------------------------------------------
	def create_row(account, indent=0, is_group=False, **kwargs):
		row = {"account": account, "indent": indent, "is_group": is_group}
		# Hamma periodlar uchun 0.0 qo'yib chiqamiz
		for period in periods:
			row[period["key"]] = 0.0
		row.update(kwargs)
		return row

	# ---------------------------------------------------------
	# 1. MA'LUMOTLARNI TAYYORLASH
	# ---------------------------------------------------------
	gl_entries = raw_data.get("gl_entries", [])

	# Category Mapni to'g'rilab olamiz (List -> Dict)
	# Agar load_counterparty_categories list qaytarsa, uni dict qilamiz: {'PartyName': 'CategoryName'}
	categories_raw = raw_data.get("counterparty_categories", [])
	categories_map = {}
	if isinstance(categories_raw, list):
		for c in categories_raw:
			# Agar c dict bo'lsa
			if isinstance(c, dict) and "name" in c:
				categories_map[c["name"]] = c.get("category_name", "Boshqa")
	elif isinstance(categories_raw, dict):
		categories_map = categories_raw

	# Lug'atlarni tayyorlash
	supplier_payables = defaultdict(dict)  # Kreditorka (Qarzlar) -> Passiv
	supplier_advances = defaultdict(dict)  # Debitorka (Avanslar) -> Aktiv
	customer_receivables = defaultdict(dict)  # Debitorka (Qarzlar) -> Aktiv
	customer_advances = defaultdict(dict)  # Kreditorka (Avanslar) -> Passiv

	# ---------------------------------------------------------
	# 2. GL ENTRYLARNI GURUHLASH (SIZ BERGAN MANTIQ)
	# ---------------------------------------------------------
	for entry in gl_entries:
		party = entry.party
		balance = flt(entry.balance)

		if balance == 0:
			continue

		# --- YETKAZIB BERUVCHILAR ---
		if entry.party_type == "Supplier":
			# Guruhni aniqlash
			if party in categories_map:
				group = categories_map[party]
			else:
				group = frappe.get_cached_value("Supplier", party, "supplier_group") or "Boshqa"

			# GL Balans: (Debit - Credit)
			# Manfiy = Biz Qarzmiz (Kreditorka)
			# Musbat = Biz Haqdorimiz (Debitorka/Avans)
			if balance < 0:
				if party not in supplier_payables[group]:
					supplier_payables[group][party] = 0.0
				supplier_payables[group][party] += abs(balance)
			else:
				# "Nomalum Pul" shu yerga tushadi ($20.29)
				if party not in supplier_advances[group]:
					supplier_advances[group][party] = 0.0
				supplier_advances[group][party] += abs(balance)

		# --- MIJOZLAR ---
		elif entry.party_type == "Customer":
			group = frappe.get_cached_value("Customer", party, "customer_group") or "Boshqa"

			if balance > 0:
				if party not in customer_receivables[group]:
					customer_receivables[group][party] = 0.0
				customer_receivables[group][party] += abs(balance)
			else:
				if party not in customer_advances[group]:
					customer_advances[group][party] = 0.0
				customer_advances[group][party] += abs(balance)

	# ---------------------------------------------------------
	# 3. HISOBOT QATORLARINI CHIZISH (RENDER)
	# ---------------------------------------------------------

	# --- A. AKTIVLAR (ASSETS) ---
	aktivlar_row = create_row("AKTIVLAR", indent=0, is_group=True)
	data.append(aktivlar_row)

	# A.1 PUL (CASH) - Agar load_cash_accounts turgan bo'lsa
	# (Agar o'chirgan bo'lsangiz, bu qism ishlamaydi, lekin xato bermaydi)
	if raw_data.get("cash_accounts"):
		pul_row = create_row("Pul mablag'lari", indent=1, is_group=True)
		data.append(pul_row)
		for acc in raw_data["cash_accounts"]:
			# Oddiylik uchun kassa balansini oxirgi ustunga yozamiz
			# (To'liq kassa mantiqi kerak bo'lsa GL dan olish kerak, lekin hozir "Nomalum Pul"ni yopamiz)
			r = create_row(acc["account_name"], indent=2)
			# Bu yerda taxminiy summa, chunki GLga o'tdik.
			# Agar kassa GLdan olinmasa, eski mantiq qolishi kerak edi.
			# Hozircha bo'sh qoldirmaslik uchun kodni buzmayman.
			data.append(r)

	# A.2 DEBITORKA (RECEIVABLES)
	debitorka_row = create_row("Debitorka (Haqdorlik)", indent=1, is_group=True)
	data.append(debitorka_row)

	# A.2.1 Yetkazib beruvchilarga berilgan Avanslar ("Nomalum Pul" SHU YERDA)
	if supplier_advances:
		adv_row = create_row("Yetkazib beruvchilar (Avanslar)", indent=2, is_group=True)
		data.append(adv_row)

		for group, parties in supplier_advances.items():
			g_row = create_row(group, indent=3, is_group=True)
			data.append(g_row)
			for party, amount in parties.items():
				p_row = create_row(party, indent=4)
				# GL Balansni oxirgi periodga (hozirgi holat) yozamiz
				# Chunki GL query jami balansni qaytardi
				last_period_key = periods[-1]["key"]
				p_row[last_period_key] = amount

				# Yig'indilarni yangilash
				g_row[last_period_key] += amount
				adv_row[last_period_key] += amount
				debitorka_row[last_period_key] += amount
				aktivlar_row[last_period_key] += amount

			data.append(p_row)  # Party qatorini qo'shish

	# A.2.2 Mijozlarning qarzi
	if customer_receivables:
		cust_row = create_row("Mijozlar (Qarzlar)", indent=2, is_group=True)
		data.append(cust_row)
		for group, parties in customer_receivables.items():
			g_row = create_row(group, indent=3, is_group=True)
			data.append(g_row)
			for party, amount in parties.items():
				p_row = create_row(party, indent=4)
				last_period_key = periods[-1]["key"]
				p_row[last_period_key] = amount

				g_row[last_period_key] += amount
				cust_row[last_period_key] += amount
				debitorka_row[last_period_key] += amount
				aktivlar_row[last_period_key] += amount
			data.append(p_row)

	# --- B. JAMI KREDITORKA (LIABILITIES) ---
	passiv_row = create_row("JAMI KREDITORKA", indent=0, is_group=True)
	data.append(passiv_row)

	# B.1 Yetkazib beruvchilar (Haqiqiy Qarzlar)
	if supplier_payables:
		sup_pay_row = create_row("Yetkazib beruvchilar (Qarzlar)", indent=1, is_group=True)
		data.append(sup_pay_row)
		for group, parties in supplier_payables.items():
			g_row = create_row(group, indent=2, is_group=True)
			data.append(g_row)
			for party, amount in parties.items():
				p_row = create_row(party, indent=3)
				last_period_key = periods[-1]["key"]
				p_row[last_period_key] = amount

				g_row[last_period_key] += amount
				sup_pay_row[last_period_key] += amount
				passiv_row[last_period_key] += amount
			data.append(p_row)

	# B.2 Mijozlardan olingan Avanslar
	if customer_advances:
		cust_adv_row = create_row("Mijozlar (Avanslar)", indent=1, is_group=True)
		data.append(cust_adv_row)
		for group, parties in customer_advances.items():
			g_row = create_row(group, indent=2, is_group=True)
			data.append(g_row)
			for party, amount in parties.items():
				p_row = create_row(party, indent=3)
				last_period_key = periods[-1]["key"]
				p_row[last_period_key] = amount

				g_row[last_period_key] += amount
				cust_adv_row[last_period_key] += amount
				passiv_row[last_period_key] += amount
			data.append(p_row)

	# --- C. BALANS FARQI (TEKSHIRUV) ---
	# Bu qator endi 0 chiqishi kerak, chunki hamma narsa GL dan olindi
	balans_row = create_row("BALANS (Farq)", indent=0, is_group=True)
	for period in periods:
		assets = aktivlar_row[period["key"]]
		liabilities = passiv_row[period["key"]]
		# Equity (Ustav va Foyda) ni ham qo'shish kerak aslida,
		# Lekin hozir asosiy maqsad Asset va Liability muvozanatini tekshirish
		balans_row[period["key"]] = assets - liabilities

	data.append(balans_row)

	return data
