# -*- coding: utf-8 -*-
# financial_control_tower_api.py
# Whitelisted Python API for Financial Control Tower
# Place in: your_app/your_app/api/financial_control_tower_api.py
#
# ═══════════════════════════════════════════════════════════════════════════════
# ARCHITECTURE CHANGE LOG (v3):
#   - CRITICAL FIX: Active/Closed contracts now count Sales Orders, not customers
#   - Active = Sales Orders with status NOT IN ('Completed', 'Cancelled', 'Closed', 'Draft') AND docstatus = 1
#   - Closed = Sales Orders with status = 'Completed' AND docstatus = 1
#   - Strict docstatus filtering: ALWAYS exclude docstatus = 2 (Cancelled) and docstatus = 0 (Draft)
# ═══════════════════════════════════════════════════════════════════════════════

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate, add_months
from datetime import datetime, date
import calendar


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN ENDPOINT: Intelligence View (KPIs + Tier Tables)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@frappe.whitelist()
def get_intelligence_data():
	"""
	Returns all data for View 1: Intelligence Dashboard.
	Single endpoint → single round-trip. All SQL uses docstatus = 1 ONLY.

	Response shape:
	{
		"success": True,
		"kpis": { invested_capital, total_debt, debt_a, debt_b, debt_c, ... },
		"roi": { roi_percentage, total_interest, invested_capital, chart_data },
		"tiers": {
			"A": [ { customer, customer_name, total_debt }, ... ],
			"B": [ ... ],
			"C": [ ... ]
		}
	}
	"""
	try:
		kpis = _compute_kpis()
		roi_data = _compute_roi(kpis)
		tier_tables = _compute_customer_tiers()

		# ── Reconcile KPI debt buckets from actual tier data ──────────
		# This ensures KPI cards and tier tables are numerically consistent.
		debt_a = sum(flt(r["total_debt"]) for r in tier_tables.get("A", []))
		debt_b = sum(flt(r["total_debt"]) for r in tier_tables.get("B", []))
		debt_c = sum(flt(r["total_debt"]) for r in tier_tables.get("C", []))

		kpis["debt_a"] = debt_a
		kpis["debt_b"] = debt_b
		kpis["debt_c"] = debt_c
		kpis["total_debt"] = debt_a + debt_b + debt_c

		# Active/closed counts are now computed in _compute_kpis() and NOT overwritten

		return {
			"success": True,
			"kpis": kpis,
			"roi": roi_data,
			"tiers": tier_tables
		}
	except Exception as e:
		frappe.log_error(f"Financial Control Tower - Intelligence Error: {str(e)}")
		return {"success": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN ENDPOINT: Periodic View (Date-range filtered charts)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@frappe.whitelist()
def get_periodic_data(from_date=None, to_date=None):
	"""
	Returns data for View 2: Periodic Analysis.
	Date-range filtered monthly investment + collection efficiency charts.
	Now also includes net_profit and contract_count arrays.
	"""
	try:
		if not from_date:
			from_date = add_months(nowdate(), -12)
		if not to_date:
			to_date = nowdate()

		from_date = getdate(from_date)
		to_date = getdate(to_date)

		monthly_investment = _get_monthly_investment(from_date, to_date)
		collection_efficiency = _get_collection_efficiency(from_date, to_date)
		net_profit = _get_monthly_net_profit(from_date, to_date)
		contract_count = _get_monthly_contract_count(from_date, to_date)

		return {
			"success": True,
			"monthly_investment": monthly_investment,
			"collection_efficiency": collection_efficiency,
			"net_profit": net_profit,
			"contract_count": contract_count,
			"date_range": {
				"from": str(from_date),
				"to": str(to_date)
			}
		}
	except Exception as e:
		frappe.log_error(f"Financial Control Tower - Periodic Error: {str(e)}")
		return {"success": False, "error": str(e)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTERNAL: KPI Computation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _compute_kpis():
	"""
	Computes base KPIs from submitted documents only.
	Note: debt_a/b/c and total_debt are overwritten by get_intelligence_data()
	after tier computation to ensure single-source-of-truth consistency.

	KPI Architecture:
	┌─────────────────────────────────────────────────────────────────┐
	│ 1. Invested Capital = Σ(total_amount - downpayment_amount)     │
	│ 2. Total Interest   = Σ(custom_total_interest)                 │
	│ 3. Total Contracts  = COUNT(submitted IAs)                     │
	│ 4. Active Contracts = COUNT(Sales Orders NOT completed/closed) │
	│ 5. Closed Contracts = COUNT(Sales Orders with status=Completed)│
	│ 6-8. debt_a/b/c     = overwritten from tier aggregation        │
	└─────────────────────────────────────────────────────────────────┘
	"""

	invested_result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(
                COALESCE(ia.total_amount, 0) - COALESCE(ia.downpayment_amount, 0)
            ), 0) AS invested_capital,
            COALESCE(SUM(ia.custom_total_interest), 0) AS total_interest,
            COUNT(*) AS total_contracts
        FROM `tabInstallment Application` ia
        WHERE ia.docstatus = 1
    """, as_dict=True)[0]

	invested_capital = flt(invested_result.invested_capital)
	total_interest = flt(invested_result.total_interest)
	total_contracts = invested_result.total_contracts or 0

	# ── Active contracts: Sales Orders NOT completed/cancelled/closed/draft ──
	active_count = _count_active_sales_orders()

	# ── Closed contracts: Sales Orders with status = 'Completed' ──
	closed_count = _count_closed_sales_orders()

	return {
		"invested_capital": invested_capital,
		"total_debt": 0,  # overwritten by caller
		"debt_a": 0,  # overwritten by caller
		"debt_b": 0,  # overwritten by caller
		"debt_c": 0,  # overwritten by caller
		"active_contracts": active_count,
		"closed_contracts": closed_count,
		"total_interest": total_interest,
		"total_contracts": total_contracts
	}


def _count_active_sales_orders():
	"""
	Count Sales Orders that are ACTIVE:
	- docstatus = 1 (Submitted)
	- status NOT IN ('Completed', 'Cancelled', 'Closed', 'Draft')

	This excludes:
	- Draft orders (docstatus = 0)
	- Cancelled orders (docstatus = 2)
	- Completed, Cancelled, or Closed orders (by status field)
	"""
	result = frappe.db.sql("""
        SELECT COUNT(*) AS active_count
        FROM `tabSales Order`
        WHERE docstatus = 1
          AND status NOT IN ('Completed', 'Cancelled', 'Closed', 'Draft')
    """, as_dict=True)

	return result[0].active_count if result else 0


def _count_closed_sales_orders():
	"""
	Count Sales Orders that are CLOSED/COMPLETED:
	- docstatus = 1 (Submitted)
	- status = 'Completed'

	This ensures we only count properly completed orders,
	not cancelled or draft orders.
	"""
	result = frappe.db.sql("""
        SELECT COUNT(*) AS closed_count
        FROM `tabSales Order`
        WHERE docstatus = 1
          AND status = 'Completed'
    """, as_dict=True)

	return result[0].closed_count if result else 0


def _compute_roi(kpis):
	"""
	ROI = (Total Interest / Invested Capital) × 100
	Division-by-zero safe.
	"""
	invested = flt(kpis.get("invested_capital", 0))
	interest = flt(kpis.get("total_interest", 0))

	if invested == 0:
		roi_pct = 0
	else:
		roi_pct = round((interest / invested) * 100, 2)

	return {
		"roi_percentage": roi_pct,
		"total_interest": interest,
		"invested_capital": invested,
		"chart_data": {
			"interest": interest,
			"principal": invested,
			"total": invested + interest
		}
	}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTERNAL: Customer Tier Tables (Re-architected v2)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _compute_customer_tiers():
	"""
	Builds 3 tier lists grouped by Customer.customer_classification.

	┌──────────────────────────────────────────────────────────────────────┐
	│ GROUPING: By CUSTOMER, not by contract.                            │
	│                                                                      │
	│ True Debt per customer =                                            │
	│   Σ(IA.custom_grand_total_with_interest)    [all submitted IAs]    │
	│ - Σ(PE.received_amount WHERE type='Receive') [payments received]   │
	│ + Σ(PE.received_amount WHERE type='Pay')     [refunds add back]    │
	│                                                                      │
	│ Classification: Customer.customer_classification (A, B, or C)      │
	│ Only customers with positive remaining debt are included.           │
	└──────────────────────────────────────────────────────────────────────┘

	Returns: { "A": [...], "B": [...], "C": [...] }
	Each entry: { customer, customer_name, classification, total_debt,
				  total_billed, total_paid, contract_count }
	"""

	rows = frappe.db.sql("""
        SELECT
            ia.customer,
            ia.customer_name,
            COALESCE(cust.customer_classification, '') AS classification,

            /* ── Billed: sum of all submitted IA grand totals ────────── */
            COALESCE(SUM(ia.custom_grand_total_with_interest), 0) AS total_billed,

            /* ── Net Paid: Receive minus Pay (refunds) ───────────────── */
            COALESCE(pe_agg.net_paid, 0) AS net_paid,

            /* ── True Debt = Billed - Net Paid ───────────────────────── */
            (
                COALESCE(SUM(ia.custom_grand_total_with_interest), 0)
                - COALESCE(pe_agg.net_paid, 0)
            ) AS total_debt,

            COUNT(ia.name) AS contract_count

        FROM `tabInstallment Application` ia

        /* ── Join Customer master for classification field ────────────── */
        LEFT JOIN `tabCustomer` cust ON cust.name = ia.customer

        /* ── Subquery: Aggregate ALL payments per Customer ────────────
             Receive → subtract from debt (positive net_paid)
             Pay (refund) → add back to debt (negative net_paid)
             Groups by party (Customer), NOT by individual contract.
        */
        LEFT JOIN (
            SELECT
                pe.party AS customer_ref,
                SUM(
                    CASE
                        WHEN pe.payment_type = 'Receive' THEN pe.received_amount
                        WHEN pe.payment_type = 'Pay'     THEN -pe.received_amount
                        ELSE 0
                    END
                ) AS net_paid
            FROM `tabPayment Entry` pe
            WHERE pe.docstatus = 1
              AND pe.party_type = 'Customer'
              AND pe.custom_contract_reference IS NOT NULL
              AND pe.custom_contract_reference != ''
            GROUP BY pe.party
        ) pe_agg ON pe_agg.customer_ref = ia.customer

        WHERE ia.docstatus = 1

        GROUP BY ia.customer, ia.customer_name, cust.customer_classification

        /* Only customers with positive remaining debt */
        HAVING total_debt > 0

        ORDER BY total_debt DESC
    """, as_dict=True)

	tiers = {"A": [], "B": [], "C": []}

	for row in rows:
		classification = (row.classification or "").strip().upper()

		entry = {
			"customer": row.customer,
			"customer_name": row.customer_name or row.customer,
			"classification": classification,
			"total_billed": flt(row.total_billed),
			"total_paid": flt(row.net_paid),
			"total_debt": flt(row.total_debt),
			"contract_count": row.contract_count or 0
		}

		if classification == "A":
			tiers["A"].append(entry)
		elif classification == "B":
			tiers["B"].append(entry)
		elif classification == "C":
			tiers["C"].append(entry)
		else:
			# ── Fallback: unclassified customers go to Tier A ────────
			# This prevents data loss. Log for audit.
			entry["classification"] = "A"
			tiers["A"].append(entry)
			frappe.logger('fct').warning(
				f"FCT: Customer '{row.customer}' has no classification, defaulted to A"
			)

	return tiers


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTERNAL: Periodic / Time-Series Data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _get_monthly_investment(from_date, to_date):
	"""
	Monthly investment = Σ(total_amount - downpayment_amount) per month.
	Returns list of {month, year, label, amount}.
	"""
	result = frappe.db.sql("""
        SELECT
            YEAR(ia.transaction_date) AS yr,
            MONTH(ia.transaction_date) AS mo,
            COALESCE(SUM(
                COALESCE(ia.total_amount, 0) - COALESCE(ia.downpayment_amount, 0)
            ), 0) AS invested
        FROM `tabInstallment Application` ia
        WHERE ia.docstatus = 1
          AND DATE(ia.transaction_date) BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY YEAR(ia.transaction_date), MONTH(ia.transaction_date)
        ORDER BY yr, mo
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

	return [
		{
			"year": r.yr,
			"month": r.mo,
			"label": f"{calendar.month_abbr[r.mo]} {r.yr}",
			"amount": flt(r.invested)
		}
		for r in result
	]


def _get_collection_efficiency(from_date, to_date):
	"""
	Monthly comparison: Expected (Payment Schedule) vs Actual (Payment Entry).
	FULL OUTER JOIN simulated via separate queries + merge.
	"""

	expected = frappe.db.sql("""
        SELECT
            YEAR(ps.due_date) AS yr,
            MONTH(ps.due_date) AS mo,
            COALESCE(SUM(ps.payment_amount), 0) AS expected_amount
        FROM `tabPayment Schedule` ps
        INNER JOIN `tabSales Order` so ON so.name = ps.parent
        WHERE so.docstatus = 1
          AND ps.due_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY YEAR(ps.due_date), MONTH(ps.due_date)
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

	actual = frappe.db.sql("""
        SELECT
            YEAR(pe.posting_date) AS yr,
            MONTH(pe.posting_date) AS mo,
            COALESCE(SUM(pe.received_amount), 0) AS actual_amount
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1
          AND pe.payment_type = 'Receive'
          AND pe.custom_contract_reference IS NOT NULL
          AND pe.custom_contract_reference != ''
          AND pe.posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY YEAR(pe.posting_date), MONTH(pe.posting_date)
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

	month_map = {}

	for r in expected:
		key = f"{r.yr}-{r.mo:02d}"
		month_map.setdefault(key, {
			"year": r.yr, "month": r.mo,
			"label": f"{calendar.month_abbr[r.mo]} {r.yr}",
			"expected": 0, "actual": 0
		})
		month_map[key]["expected"] = flt(r.expected_amount)

	for r in actual:
		key = f"{r.yr}-{r.mo:02d}"
		month_map.setdefault(key, {
			"year": r.yr, "month": r.mo,
			"label": f"{calendar.month_abbr[r.mo]} {r.yr}",
			"expected": 0, "actual": 0
		})
		month_map[key]["actual"] = flt(r.actual_amount)

	sorted_months = sorted(month_map.values(), key=lambda x: (x["year"], x["month"]))

	for m in sorted_months:
		if m["expected"] > 0:
			m["efficiency_pct"] = round((m["actual"] / m["expected"]) * 100, 1)
		else:
			m["efficiency_pct"] = 100.0 if m["actual"] > 0 else 0

	return sorted_months


def _get_monthly_net_profit(from_date, to_date):
	"""
	Monthly Net Profit = Σ(custom_grand_total_with_interest - total_amount) per month.
	Based on Submitted (docstatus: 1) Installment Applications.
	Returns list of {month, year, label, amount}.
	"""
	result = frappe.db.sql("""
        SELECT
            YEAR(ia.transaction_date) AS yr,
            MONTH(ia.transaction_date) AS mo,
            COALESCE(SUM(
                COALESCE(ia.custom_grand_total_with_interest, 0) - COALESCE(ia.total_amount, 0)
            ), 0) AS net_profit
        FROM `tabInstallment Application` ia
        WHERE ia.docstatus = 1
          AND DATE(ia.transaction_date) BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY YEAR(ia.transaction_date), MONTH(ia.transaction_date)
        ORDER BY yr, mo
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

	return [
		{
			"year": r.yr,
			"month": r.mo,
			"label": f"{calendar.month_abbr[r.mo]} {r.yr}",
			"amount": flt(r.net_profit)
		}
		for r in result
	]


def _get_monthly_contract_count(from_date, to_date):
	"""
	Monthly Contract Count = COUNT of Submitted Installment Applications per month.
	Returns list of {month, year, label, count}.
	"""
	result = frappe.db.sql("""
        SELECT
            YEAR(ia.transaction_date) AS yr,
            MONTH(ia.transaction_date) AS mo,
            COUNT(*) AS contract_count
        FROM `tabInstallment Application` ia
        WHERE ia.docstatus = 1
          AND DATE(ia.transaction_date) BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY YEAR(ia.transaction_date), MONTH(ia.transaction_date)
        ORDER BY yr, mo
    """, {"from_date": from_date, "to_date": to_date}, as_dict=True)

	return [
		{
			"year": r.yr,
			"month": r.mo,
			"label": f"{calendar.month_abbr[r.mo]} {r.yr}",
			"count": r.contract_count or 0
		}
		for r in result
	]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REAL-TIME: Document Event Handler (hooks.py dan chaqiriladi)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def on_document_change(doc, method=None):
	"""
	Called by hooks.py doc_events when:
	  - Payment Entry: on_submit, on_cancel
	  - Installment Application: on_submit, on_cancel
	  - Sales Order: on_submit, on_cancel

	Two actions:
	  1. Clear server-side cache → next API call returns fresh data
	  2. Push WebSocket event → all open browsers auto-refresh
	"""
	try:
		_clear_fct_cache()

		frappe.publish_realtime(
			event='fct_data_changed',
			message={
				'doctype': doc.doctype,
				'docname': doc.name,
				'method': method or 'unknown',
				'timestamp': str(frappe.utils.now_datetime()),
				'user': frappe.session.user
			},
			after_commit=True
		)

		frappe.logger('fct').info(
			f"FCT realtime: {doc.doctype} {doc.name} ({method}) → cache cleared, WebSocket pushed"
		)

	except Exception as e:
		frappe.log_error(
			f"FCT on_document_change error: {str(e)}",
			'Financial Control Tower'
		)


def _clear_fct_cache():
	"""Clear all Financial Control Tower cache keys."""
	cache_keys = [
		'fct_intelligence_data',
		'fct_periodic_data',
		'fct_kpis',
		'fct_roi',
		'fct_tiers',
		'sales_dashboard_data',
		'sales_dashboard_kpi',
		'sales_dashboard_charts',
	]
	for key in cache_keys:
		try:
			frappe.cache().delete_value(key)
		except Exception:
			pass
