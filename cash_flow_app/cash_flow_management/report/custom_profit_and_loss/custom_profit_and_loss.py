# Copyright (c) 2024, Your Company
# License: MIT

import frappe
import json
import os
from frappe import _
from frappe.utils import flt, getdate, add_months, get_first_day, get_last_day
from datetime import datetime

# O'zbek oy nomlari
UZBEK_MONTHS = {
	1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel",
	5: "May", 6: "Iyun", 7: "Iyul", 8: "Avgust",
	9: "Sentyabr", 10: "Oktyabr", 11: "Noyabr", 12: "Dekabr"
}

# ═══════════════════════════════════════════════════════════════════
# RANGLAR — Armada_reporting_-_P_L.pdf bazasidan, ochroq variant
# ─────────────────────────────────────────────────────────────────
#   #D8705B  → Asosiy ko'rsatkichlar (PDF #CC4125 + 25% oq)
#   #666666  → THEAD / Check (PDF #434343 + 35% oq)
#   #FFD966  → Sektsiya: Jami harajatlar (PDF aynan)
#   #FFF1CC  → Kichik sektsiya (PDF aynan)
#   #F3F3F3  → Zebra-even leaf qatorlar (PDF aynan)
#   #FF0000  → Manfiy raqam matni (PDF aynan)
# ═══════════════════════════════════════════════════════════════════

_STYLE_KEY        = "font-weight: bold; background-color: #D8705B; color: #ffffff;"
_STYLE_SECTION    = "font-weight: bold; background-color: #FFD966; color: #1a1a1a;"
_STYLE_SUBSECTION = "font-weight: bold; background-color: #FFF1CC; color: #1a1a1a;"
_STYLE_PERCENT    = "font-style: italic; color: #666666; background-color: #ffffff;"
_STYLE_CHECK      = "font-weight: bold; background-color: #666666; color: #ffffff;"


def format_money(amount):
	"""Pul summani $1,234 formatida qaytarish (yaxlitlangan)"""
	if amount == 0:
		return "$0"
	return "${:,.0f}".format(round(flt(amount)))


def get_balance_sheet_net_profit(from_date, to_date):
	"""
	Balance Sheet reportidagi Sof Foyda ni hisoblash.
	Bu funksiya operational_balance_sheet.py dagi logikani takrorlaydi.
	"""
	interest_result = frappe.db.sql("""
		SELECT IFNULL(SUM(custom_total_interest), 0) as total
		FROM `tabInstallment Application`
		WHERE docstatus = 1
		AND DATE(transaction_date) BETWEEN %s AND %s
	""", (from_date, to_date), as_dict=1)

	interest = flt(interest_result[0].total if interest_result else 0)

	expenses = 0

	categories = frappe.db.sql("""
		SELECT name, category_name, category_type, custom_expense_type
		FROM `tabCounterparty Category`
		WHERE is_active = 1
	""", as_dict=1)

	category_map = {c["name"]: c for c in categories}

	payment_entries = frappe.db.sql("""
		SELECT
			custom_counterparty_category,
			paid_amount,
			party_type,
			party_name
		FROM `tabPayment Entry`
		WHERE docstatus = 1
		AND DATE(posting_date) BETWEEN %s AND %s
		AND custom_counterparty_category IS NOT NULL
		AND party_type = 'Employee'
		AND party_name = 'Xarajat'
	""", (from_date, to_date), as_dict=1)

	for pe in payment_entries:
		category = category_map.get(pe.get("custom_counterparty_category"))

		if (category
			and category.get("custom_expense_type") == "Xarajat"
			and pe.get("party_type") == "Employee"
			and pe.get("party_name") == "Xarajat"):
			amount = flt(pe["paid_amount"])

			if category.get("category_type") == "Income":
				amount = -amount

			expenses += amount

	return interest - expenses


# ═══════════════════════════════════════════════════════════════════
# PRINT HTML
# ═══════════════════════════════════════════════════════════════════

_KEY_ACCOUNTS = {
	"Savdo", "Tannarx", "Yalpi foyda",
	"Sof foyda", "Operatsion foyda",
}

_PERCENT_ACCOUNTS = {"Rentabillik", "Sof Rentabillik"}

_SUBSECTION_ACCOUNTS = {
	"Administrativ", "Tijorat",
	"Boshqa daromad", "Boshqa xarajatlar",
}


def _derive_css_class(row):
	"""
	Presentation layer: account nomi va indent ga qarab CSS class.
	Hech qanday biznes logika yo'q — faqat ko'rinish.
	"""
	account = (row.get("account") or "").strip()
	indent  = row.get("indent", 0)

	if account == "Shartnomalar soni":
		return "row_count"
	if account in _KEY_ACCOUNTS:
		return "row_key"
	if account in _PERCENT_ACCOUNTS:
		return "row_percent"
	if account == "Jami harajatlar":
		return "row_section"
	if account in _SUBSECTION_ACCOUNTS:
		return "row_subsection"
	if "Check" in account and "P&L" in account:
		return "row_check"
	if indent == 1:
		return "row_leaf"
	return "row_leaf"


def _fmt_cell(val, is_count=False):
	"""Qiymatni display uchun dict ga aylantirish."""
	if val is None or val == "":
		return {"value": "—", "negative": False, "zero": True,
				"is_percent": False, "is_total": False}

	str_val = str(val).strip()

	if str_val.endswith("%"):
		return {"value": str_val, "negative": False,
				"zero": str_val in ("0%", "0.0%"),
				"is_percent": True, "is_total": False}

	if is_count:
		try:
			v = int(str_val)
			return {"value": str(v), "negative": v < 0,
					"zero": v == 0, "is_percent": False, "is_total": False}
		except (ValueError, TypeError):
			return {"value": str_val, "negative": False,
					"zero": False, "is_percent": False, "is_total": False}

	try:
		clean = (str_val.replace("$", "").replace(",", "")
				 .replace("\u00a0", "").replace(" ", "").strip())
		num     = float(clean)
		rounded = round(num)
		if rounded == 0:
			return {"value": "—", "negative": False, "zero": True,
					"is_percent": False, "is_total": False}
		abs_str = "{:,}".format(abs(rounded)).replace(",", "\u00a0")
		display = ("- $ " if rounded < 0 else "$ ") + abs_str
		return {"value": display, "negative": rounded < 0,
				"zero": False, "is_percent": False, "is_total": False}
	except (ValueError, TypeError):
		return {"value": str_val, "negative": False,
				"zero": False, "is_percent": False, "is_total": False}


@frappe.whitelist()
def get_print_html(filters=None):
	"""P&L ni to'liq HTML ko'rinishida render qilish."""
	if isinstance(filters, str):
		filters = json.loads(filters)
	if not filters:
		filters = {}

	columns, data = execute(filters)

	period_cols = [c for c in columns
				   if c.get("fieldname") not in ("account", "total")]
	has_total   = any(c.get("fieldname") == "total" for c in columns)

	enriched = []
	leaf_counter = 0

	for row in data:
		css_class = _derive_css_class(row)
		is_count  = (css_class == "row_count")
		indent_px = int(row.get("indent", 0)) * 16

		# Zebra faqat leaf uchun
		zebra = ""
		if css_class == "row_leaf":
			leaf_counter += 1
			zebra = "even" if leaf_counter % 2 == 0 else "odd"

		# Check qatori holati
		check_class = ""
		if css_class == "row_check" and period_cols:
			raw = str(row.get(period_cols[0]["fieldname"], "0"))
			raw = raw.replace("$","").replace(",","").replace("\u00a0","").replace(" ","").strip()
			try:
				check_class = "zero" if abs(float(raw)) < 1 else "nonzero"
			except ValueError:
				check_class = "nonzero"

		cells = []
		for col in period_cols:
			cell = _fmt_cell(row.get(col["fieldname"], ""), is_count=is_count)
			cell["is_total"] = False
			cells.append(cell)

		if has_total:
			total_cell = _fmt_cell(row.get("total", ""), is_count=is_count)
			total_cell["is_total"] = True
			cells.append(total_cell)

		enriched.append({
			"account":     row.get("account", ""),
			"css_class":   css_class,
			"zebra":       zebra,
			"indent_px":   indent_px,
			"check_class": check_class,
			"cells":       cells,
		})

	from_label   = filters.get("from_date", "")
	to_label     = filters.get("to_date", "")
	period_label = f"{from_label} — {to_label}"

	html_path = os.path.join(os.path.dirname(__file__), "custom_profit_and_loss.html")
	with open(html_path, "r", encoding="utf-8") as f:
		template_str = f.read()

	context = {
		"value_columns": period_cols,
		"has_total":     has_total,
		"data":          enriched,
		"filters":       filters,
		"period_label":  period_label,
	}

	return frappe.render_template(template_str, context)


# ═══════════════════════════════════════════════════════════════════
# EXECUTE
# ═══════════════════════════════════════════════════════════════════

def execute(filters=None):
	if not filters:
		filters = {}

	if not filters.get("from_date"):
		filters["from_date"] = "2025-01-01"
	if not filters.get("to_date"):
		filters["to_date"] = str(datetime.now().date())
	if not filters.get("periodicity"):
		filters["periodicity"] = "Monthly"

	from_date = getdate(filters["from_date"])
	to_date   = getdate(filters["to_date"])

	if from_date > to_date:
		frappe.throw(_("'From Date' sanasi 'To Date' sanasidan katta bo'lmasligi kerak"))

	columns = get_columns(filters)
	data    = get_data(filters)

	return columns, data


def get_columns(filters):
	columns = [{
		"fieldname": "account",
		"label":     _("Ko'rsatkich"),
		"fieldtype": "Data",
		"width":     300
	}]

	for period in get_period_list(filters):
		columns.append({
			"fieldname": period["key"],
			"label":     period["label"],
			"fieldtype": "Data",
			"width":     150
		})

	columns.append({
		"fieldname": "total",
		"label":     _("Jami"),
		"fieldtype": "Data",
		"width":     150
	})

	return columns


def get_period_list(filters):
	from_date    = getdate(filters["from_date"])
	to_date      = getdate(filters["to_date"])
	periodicity  = filters.get("periodicity", "Monthly")
	period_list  = []

	if periodicity == "Yearly":
		current_year = from_date.year
		end_year     = to_date.year
		while current_year <= end_year:
			year_start   = datetime(current_year, 1, 1).date()
			year_end     = datetime(current_year, 12, 31).date()
			actual_start = max(year_start, from_date)
			actual_end   = min(year_end, to_date)
			period_list.append({
				"key":       str(current_year),
				"label":     str(current_year),
				"from_date": actual_start,
				"to_date":   actual_end
			})
			current_year += 1
	else:
		current = get_first_day(from_date)
		end     = get_first_day(to_date)
		while current <= end:
			month_end    = get_last_day(current)
			actual_start = max(current, from_date)
			actual_end   = min(month_end, to_date)
			month_name   = UZBEK_MONTHS.get(current.month)
			period_list.append({
				"key":       current.strftime("%Y-%m"),
				"label":     f"{month_name} {current.year}",
				"from_date": actual_start,
				"to_date":   actual_end
			})
			current = add_months(current, 1)

	return period_list


def get_data(filters):
	period_list = get_period_list(filters)
	data = []

	# ── 1. SHARTNOMALAR SONI ────────────────────────────────────────
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

	# ── 2. SAVDO ────────────────────────────────────────────────────
	revenue_row = {
		"account": "Savdo",
		"indent":  0,
		"_style":  _STYLE_KEY
	}
	revenue_row_raw = {}
	total_revenue   = 0
	for period in period_list:
		result = frappe.db.sql("""
			SELECT IFNULL(SUM(custom_grand_total_with_interest - downpayment_amount), 0) as total
			FROM `tabInstallment Application`
			WHERE docstatus = 1
			AND DATE(transaction_date) BETWEEN %s AND %s
		""", (period["from_date"], period["to_date"]), as_dict=1)[0].total
		revenue_row_raw[period["key"]] = flt(result)
		revenue_row[period["key"]]     = format_money(result)
		total_revenue                 += flt(result)
	revenue_row["total"] = format_money(total_revenue)
	data.append(revenue_row)

	# ── 3. TANNARX ──────────────────────────────────────────────────
	cost_row = {
		"account": "Tannarx",
		"indent":  0,
		"_style":  _STYLE_KEY
	}
	total_cost = 0
	for period in period_list:
		result = frappe.db.sql("""
			SELECT IFNULL(SUM(finance_amount), 0) as total
			FROM `tabInstallment Application`
			WHERE docstatus = 1
			AND DATE(transaction_date) BETWEEN %s AND %s
		""", (period["from_date"], period["to_date"]), as_dict=1)[0].total
		cost_row[period["key"]] = format_money(result)
		total_cost             += flt(result)
	cost_row["total"] = format_money(total_cost)
	data.append(cost_row)

	# ── 4. YALPI FOYDA ──────────────────────────────────────────────
	margin_row = {
		"account": "Yalpi foyda",
		"indent":  0,
		"_style":  _STYLE_KEY
	}
	margin_row_raw = {}
	total_margin   = 0
	for period in period_list:
		result = frappe.db.sql("""
			SELECT IFNULL(SUM(custom_total_interest), 0) as total
			FROM `tabInstallment Application`
			WHERE docstatus = 1
			AND DATE(transaction_date) BETWEEN %s AND %s
		""", (period["from_date"], period["to_date"]), as_dict=1)[0].total
		margin_row_raw[period["key"]] = flt(result)
		margin_row[period["key"]]     = format_money(result)
		total_margin                 += flt(result)
	margin_row["total"] = format_money(total_margin)
	data.append(margin_row)

	# ── 5. RENTABILLIK ──────────────────────────────────────────────
	margin_percent_row = {
		"account": "Rentabillik",
		"indent":  0,
		"_style":  _STYLE_PERCENT
	}
	for period in period_list:
		margin_val  = margin_row_raw[period["key"]]
		revenue_val = revenue_row_raw[period["key"]]
		if revenue_val > 0:
			margin_percent_row[period["key"]] = f"{flt((margin_val / revenue_val) * 100, 1)}%"
		else:
			margin_percent_row[period["key"]] = "0%"
	if total_revenue > 0:
		margin_percent_row["total"] = f"{flt((total_margin / total_revenue) * 100, 1)}%"
	else:
		margin_percent_row["total"] = "0%"
	data.append(margin_percent_row)

	# ── 6. JAMI HARAJATLAR ──────────────────────────────────────────
	expense_categories = {}
	operational_row = {
		"account": "Jami harajatlar",
		"indent":  0,
		"_style":  _STYLE_SECTION
	}
	operational_row_raw = {}
	total_expense       = 0

	for period in period_list:
		operational_row_raw[period["key"]] = 0

		expenses = frappe.db.sql("""
			SELECT
				cc.name         as category_id,
				cc.category_name,
				cc.category_type,
				SUM(pe.paid_amount) as amount
			FROM `tabPayment Entry` pe
			INNER JOIN `tabCounterparty Category` cc
				ON pe.custom_counterparty_category = cc.name
			WHERE pe.docstatus = 1
			AND cc.custom_expense_type = 'Xarajat'
			AND pe.party_type = 'Employee'
			AND pe.party_name = 'Xarajat'
			AND DATE(pe.posting_date) BETWEEN %s AND %s
			GROUP BY cc.name, cc.category_name, cc.category_type
		""", (period["from_date"], period["to_date"]), as_dict=1)

		for exp in expenses:
			cat_name = exp.category_name
			cat_id   = exp.category_id
			amount   = flt(exp.amount)

			if exp.category_type == "Income":
				amount = -amount

			if cat_name not in expense_categories:
				expense_categories[cat_name] = {
					"account":     f"  {cat_name}",
					"indent":      1,
					"category_id": cat_id,
					"_raw":        {},
					"_raw_total":  0
				}
				for p in period_list:
					expense_categories[cat_name][p["key"]] = "$0"
				expense_categories[cat_name]["total"] = "$0"

			expense_categories[cat_name]["_raw"][period["key"]] = (
				expense_categories[cat_name]["_raw"].get(period["key"], 0) + amount
			)
			expense_categories[cat_name]["_raw_total"] += amount

			operational_row_raw[period["key"]] += amount
			total_expense                      += amount

	for period in period_list:
		operational_row[period["key"]] = format_money(operational_row_raw[period["key"]])
	operational_row["total"] = format_money(total_expense)
	data.append(operational_row)

	# Kategoriya qatorlari — zebra
	for i, cat_name in enumerate(sorted(expense_categories.keys())):
		cat    = expense_categories[cat_name]
		bg     = "#F3F3F3" if i % 2 == 0 else "#ffffff"
		cat["_style"] = f"background-color: {bg}; color: #2c2c2c;"
		for period in period_list:
			cat[period["key"]] = format_money(cat["_raw"].get(period["key"], 0))
		cat["total"] = format_money(cat["_raw_total"])
		del cat["_raw"]
		del cat["_raw_total"]
		data.append(cat)

	# ── 7. SOF FOYDA ────────────────────────────────────────────────
	net_profit_row = {
		"account": "Sof foyda",
		"indent":  0,
		"_style":  _STYLE_KEY
	}
	net_profit_row_raw = {}
	total_net_profit   = 0
	for period in period_list:
		margin_val  = margin_row_raw[period["key"]]
		expense_val = operational_row_raw[period["key"]]
		profit      = margin_val - expense_val
		net_profit_row_raw[period["key"]] = profit
		net_profit_row[period["key"]]     = format_money(profit)
		total_net_profit                 += profit
	net_profit_row["total"] = format_money(total_net_profit)
	data.append(net_profit_row)

	# ── 8. SOF RENTABILLIK ──────────────────────────────────────────
	net_percent_row = {
		"account": "Sof Rentabillik",
		"indent":  0,
		"_style":  _STYLE_PERCENT
	}
	for period in period_list:
		profit_val  = net_profit_row_raw[period["key"]]
		revenue_val = revenue_row_raw[period["key"]]
		if revenue_val > 0:
			net_percent_row[period["key"]] = f"{flt((profit_val / revenue_val) * 100, 1)}%"
		else:
			net_percent_row[period["key"]] = "0%"
	if total_revenue > 0:
		net_percent_row["total"] = f"{flt((total_net_profit / total_revenue) * 100, 1)}%"
	else:
		net_percent_row["total"] = "0%"
	data.append(net_percent_row)

	# ── 9. CHECK (P&L vs Balance Sheet) ─────────────────────────────
	check_row = {
		"account": "Check (P&L vs Balance Sheet)",
		"indent":  0,
		"_style":  _STYLE_CHECK
	}
	total_check_difference = 0

	for period in period_list:
		bs_net_profit = get_balance_sheet_net_profit(period["from_date"], period["to_date"])
		pl_net_profit = net_profit_row_raw[period["key"]]
		difference    = pl_net_profit - bs_net_profit
		check_row[period["key"]] = format_money(difference)
		total_check_difference  += difference

	check_row["total"] = format_money(total_check_difference)
	data.append(check_row)

	return data
