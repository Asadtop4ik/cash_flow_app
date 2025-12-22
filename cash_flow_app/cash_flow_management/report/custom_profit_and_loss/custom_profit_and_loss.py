# Copyright (c) 2024, Your Company
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_months, get_first_day, get_last_day
from datetime import datetime

# O'zbek oy nomlari
UZBEK_MONTHS = {
	1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
	5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
	9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr"
}


def format_money(amount):
	"""Pul summani $1,234.56 formatida qaytarish"""
	if amount == 0:
		return "$0.00"
	return "${:,.2f}".format(flt(amount))


def execute(filters=None):
	"""
	Asosiy funksiya - Custom Profit and Loss reportni bajaradi

	Filterlar:
	  - from_date: Boshlanish sanasi
	  - to_date: Tugash sanasi
	  - periodicity: "Monthly" yoki "Yearly"
	"""
	# Default qiymatlar
	if not filters:
		filters = {}

	if not filters.get("from_date"):
		filters["from_date"] = "2025-01-01"
	if not filters.get("to_date"):
		filters["to_date"] = str(datetime.now().date())
	if not filters.get("periodicity"):
		filters["periodicity"] = "Monthly"

	# Sanalarni tekshirish
	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])

	if from_date > to_date:
		frappe.throw(_("'From Date' sanasi 'To Date' sanasidan katta bo'lmasligi kerak"))

	# Ma'lumotlarni olish
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data


def get_columns(filters):
	"""Ustunlar"""
	columns = [{
		"fieldname": "account",
		"label": _("Ko'rsatkich"),
		"fieldtype": "Data",
		"width": 300
	}]

	period_list = get_period_list(filters)

	for period in period_list:
		columns.append({
			"fieldname": period["key"],
			"label": period["label"],
			"fieldtype": "Data",
			"width": 150
		})

	columns.append({
		"fieldname": "total",
		"label": _("Jami"),
		"fieldtype": "Data",
		"width": 150
	})

	return columns


def get_period_list(filters):
	"""
	Period ro'yxatini yaratadi

	Agar periodicity=Yearly bo'lsa:
	  - from_date dan to_date gacha bo'lgan har bir yilni alohida ustun qiladi
	  - Misol: 12.05.2024 dan 07.07.2025 gacha => [2024, 2025]

	Agar periodicity=Monthly bo'lsa:
	  - from_date dan to_date gacha bo'lgan har bir oyni alohida ustun qiladi
	  - Misol: 12.05.2024 dan 07.07.2025 gacha => [May 2024, Iyun 2024, ..., Iyul 2025]
	"""
	from_date = getdate(filters["from_date"])
	to_date = getdate(filters["to_date"])
	periodicity = filters.get("periodicity", "Monthly")

	period_list = []

	if periodicity == "Yearly":
		# Yillik hisobot - har bir yil alohida ustunda
		current_year = from_date.year
		end_year = to_date.year

		while current_year <= end_year:
			# Yilning boshlanishi va tugashi
			year_start = datetime(current_year, 1, 1).date()
			year_end = datetime(current_year, 12, 31).date()

			# Faqat tanlangan oraliqda bo'lgan qismini olish
			actual_start = max(year_start, from_date)
			actual_end = min(year_end, to_date)

			period_list.append({
				"key": str(current_year),
				"label": str(current_year),
				"from_date": actual_start,
				"to_date": actual_end
			})
			current_year += 1
	else:
		# Oylik hisobot - har bir oy alohida ustunda
		current = get_first_day(from_date)
		end = get_first_day(to_date)

		while current <= end:
			month_end = get_last_day(current)

			# Faqat tanlangan oraliqda bo'lgan qismini olish
			actual_start = max(current, from_date)
			actual_end = min(month_end, to_date)

			month_name = UZBEK_MONTHS.get(current.month)

			period_list.append({
				"key": current.strftime("%Y-%m"),
				"label": f"{month_name} {current.year}",
				"from_date": actual_start,
				"to_date": actual_end
			})
			current = add_months(current, 1)

	return period_list


def get_data(filters):
	"""Ma'lumotlar"""
	period_list = get_period_list(filters)
	data = []

	# ===== 1. SHARTNOMALAR SONI =====
	quantity_row = {"account": "Shartnomalar soni", "indent": 0}
	total_qty = 0
	for period in period_list:
		qty = frappe.db.sql("""
			SELECT COUNT(*) as cnt
			FROM `tabInstallment Application`
			WHERE docstatus = 1
			AND DATE(transaction_date) BETWEEN %s AND %s
		""", (period["from_date"], period["to_date"]), as_dict=1)[0].cnt

		quantity_row[period["key"]] = int(qty)
		total_qty += qty
	quantity_row["total"] = int(total_qty)
	data.append(quantity_row)

	# ===== 2. SHARTNOMALAR SUMMASI =====
	revenue_row = {"account": "Savdo", "indent": 0}
	revenue_row_raw = {}
	total_revenue = 0
	for period in period_list:
		result = frappe.db.sql("""
			SELECT IFNULL(SUM(custom_grand_total_with_interest), 0) as total
			FROM `tabInstallment Application`
			WHERE docstatus = 1
			AND DATE(transaction_date) BETWEEN %s AND %s
		""", (period["from_date"], period["to_date"]), as_dict=1)[0].total

		revenue_row_raw[period["key"]] = flt(result)
		revenue_row[period["key"]] = format_money(result)
		total_revenue += flt(result)
	revenue_row["total"] = format_money(total_revenue)
	data.append(revenue_row)

	# ===== 3. MAHSULOTLAR TANNARXI =====
	cost_row = {"account": "Tannarx", "indent": 0}
	total_cost = 0
	for period in period_list:
		result = frappe.db.sql("""
			SELECT IFNULL(SUM(total_amount), 0) as total
			FROM `tabInstallment Application`
			WHERE docstatus = 1
			AND DATE(transaction_date) BETWEEN %s AND %s
		""", (period["from_date"], period["to_date"]), as_dict=1)[0].total

		cost_row[period["key"]] = format_money(result)
		total_cost += flt(result)
	cost_row["total"] = format_money(total_cost)
	data.append(cost_row)

	# ===== 4. FOIZ DAROMADI =====
	margin_row = {"account": "Yalpi foyda ", "indent": 0}
	margin_row_raw = {}
	total_margin = 0
	for period in period_list:
		result = frappe.db.sql("""
			SELECT IFNULL(SUM(custom_total_interest), 0) as total
			FROM `tabInstallment Application`
			WHERE docstatus = 1
			AND DATE(transaction_date) BETWEEN %s AND %s
		""", (period["from_date"], period["to_date"]), as_dict=1)[0].total

		margin_row_raw[period["key"]] = flt(result)
		margin_row[period["key"]] = format_money(result)
		total_margin += flt(result)
	margin_row["total"] = format_money(total_margin)
	data.append(margin_row)

	# ===== 5. FOYDALILIK % =====
	margin_percent_row = {"account": "Rentabillik", "indent": 0}
	for period in period_list:
		margin_val = margin_row_raw[period["key"]]
		revenue_val = revenue_row_raw[period["key"]]

		if revenue_val > 0:
			percent = (margin_val / revenue_val) * 100
			margin_percent_row[period["key"]] = f"{flt(percent, 1)}%"
		else:
			margin_percent_row[period["key"]] = "0%"

	if total_revenue > 0:
		total_percent = (total_margin / total_revenue) * 100
		margin_percent_row["total"] = f"{flt(total_percent, 1)}%"
	else:
		margin_percent_row["total"] = "0%"
	data.append(margin_percent_row)

	# ===== 6. JAMI HARAJATLAR =====
	expense_categories = {}
	operational_row = {"account": "Jami harajatlar", "indent": 0}
	operational_row_raw = {}
	total_expense = 0

	for period in period_list:
		operational_row_raw[period["key"]] = 0

		expenses = frappe.db.sql("""
			SELECT
				cc.category_name,
				cc.category_type,
				SUM(pe.paid_amount) as amount
			FROM `tabPayment Entry` pe
			INNER JOIN `tabCounterparty Category` cc
				ON pe.custom_counterparty_category = cc.name
			WHERE pe.docstatus = 1
			AND cc.category_name != 'Клиент'
			AND pe.party_type != 'Customer'
			AND DATE(pe.posting_date) BETWEEN %s AND %s
			GROUP BY cc.category_name, cc.category_type
		""", (period["from_date"], period["to_date"]), as_dict=1)

		for exp in expenses:
			cat_name = exp.category_name
			amount = flt(exp.amount)

			if exp.category_type == "Income":
				amount = -amount

			if cat_name not in expense_categories:
				expense_categories[cat_name] = {
					"account": f"  {cat_name}",
					"indent": 1
				}
				for p in period_list:
					expense_categories[cat_name][p["key"]] = "$0.00"
				expense_categories[cat_name]["total"] = "$0.00"
				expense_categories[cat_name]["_raw"] = {}
				expense_categories[cat_name]["_raw_total"] = 0

			expense_categories[cat_name]["_raw"][period["key"]] = expense_categories[cat_name]["_raw"].get(period["key"], 0) + amount
			expense_categories[cat_name]["_raw_total"] += amount

			operational_row_raw[period["key"]] += amount
			total_expense += amount

	# Format operational row
	for period in period_list:
		operational_row[period["key"]] = format_money(operational_row_raw[period["key"]])
	operational_row["total"] = format_money(total_expense)
	data.append(operational_row)

	# Format expense categories
	for cat_name in sorted(expense_categories.keys()):
		cat = expense_categories[cat_name]
		for period in period_list:
			cat[period["key"]] = format_money(cat["_raw"].get(period["key"], 0))
		cat["total"] = format_money(cat["_raw_total"])
		del cat["_raw"]
		del cat["_raw_total"]
		data.append(cat)

	# ===== 7. YAKUNIY FOYDA =====
	net_profit_row = {"account": "Sof foyda", "indent": 0}
	net_profit_row_raw = {}
	total_net_profit = 0
	for period in period_list:
		margin_val = margin_row_raw[period["key"]]
		expense_val = operational_row_raw[period["key"]]
		profit = margin_val - expense_val
		net_profit_row_raw[period["key"]] = profit
		net_profit_row[period["key"]] = format_money(profit)
		total_net_profit += profit
	net_profit_row["total"] = format_money(total_net_profit)
	data.append(net_profit_row)

	# ===== 8. YAKUNIY FOYDALILIK % =====
	net_percent_row = {"account": "Sof Rentabillik", "indent": 0}
	for period in period_list:
		profit_val = net_profit_row_raw[period["key"]]
		revenue_val = revenue_row_raw[period["key"]]

		if revenue_val > 0:
			percent = (profit_val / revenue_val) * 100
			net_percent_row[period["key"]] = f"{flt(percent, 1)}%"
		else:
			net_percent_row[period["key"]] = "0%"

	if total_revenue > 0:
		total_percent = (total_net_profit / total_revenue) * 100
		net_percent_row["total"] = f"{flt(total_percent, 1)}%"
	else:
		net_percent_row["total"] = "0%"
	data.append(net_percent_row)

	# ===== 9. CHECK =====
	check_row = {"account": "Check", "indent": 0}
	for period in period_list:
		check_row[period["key"]] = "$0.00"
	check_row["total"] = "$0.00"
	data.append(check_row)

	return data
