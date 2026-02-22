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
from frappe.utils import flt, getdate, nowdate, add_months,now_datetime
from datetime import datetime, date
import calendar
import json

# ── Cache TTL: 25 hours (ensures stale cache never persists past next cron) ──
CACHE_TTL = 25 * 60 * 60  # 90000 seconds

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN ENDPOINT: Intelligence View (KPIs + Tier Tables)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@frappe.whitelist()
def get_intelligence_data(force_refresh=0):
    """
    Returns all data for View 1: Intelligence Dashboard.

    Cache Strategy:
      - force_refresh=0 (default): Read from cache. If cache miss → compute live.
      - force_refresh=1 (manual button): Always compute live, then update cache.

    The 'force_refresh' param is passed from the JS "Refresh" button.
    Normal page loads always hit cache.
    """
    try:
        force = int(force_refresh or 0)
        if not force:
            cached = frappe.cache().get_value('fct_intelligence_data')
            if cached:
                data = json.loads(cached) if isinstance(cached, str) else cached
                # Inject cache metadata so frontend knows it's cached
                data['_from_cache'] = True
                data['_cached_at'] = frappe.cache().get_value('fct_cache_timestamp') or ''
                return data

        # Cache miss or forced refresh → compute live
        result = _build_and_cache_intelligence()
        result['_from_cache'] = False
        result['_cached_at'] = str(now_datetime())
        return result
    except Exception as e:
        frappe.log_error(f"Financial Control Tower - Intelligence Error: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_periodic_data(from_date=None, to_date=None, force_refresh=0):
    """
    Returns data for View 2: Periodic Analysis.

    Cache Strategy:
      - Caches the DEFAULT date range (last 12 months) at key 'fct_periodic_data'.
      - Custom date ranges are ALWAYS computed live (not cached).
      - force_refresh=1 bypasses cache even for default range.
    """
    try:
        force = int(force_refresh or 0)

        default_from = str(getdate(add_months(nowdate(), -12)))
        default_to = str(getdate(nowdate()))

        if not from_date:
            from_date = default_from
        if not to_date:
            to_date = default_to

        is_default_range = (str(getdate(from_date)) == default_from and
                            str(getdate(to_date)) == default_to)

        # ── Try cache only for default date range ────────────────────────
        if not force and is_default_range:
            cached = frappe.cache().get_value('fct_periodic_data')
            if cached:
                data = json.loads(cached) if isinstance(cached, str) else cached
                data['_from_cache'] = True
                data['_cached_at'] = frappe.cache().get_value('fct_cache_timestamp') or ''
                return data

        # ── Compute live ─────────────────────────────────────────────────
        from_date = getdate(from_date)
        to_date = getdate(to_date)

        result = _build_periodic_result(from_date, to_date)

        # Only cache if it's the default range
        if is_default_range:
            frappe.cache().set_value('fct_periodic_data', json.dumps(result), expires_in_sec=CACHE_TTL)

        result['_from_cache'] = False
        result['_cached_at'] = str(now_datetime())
        return result

    except Exception as e:
        frappe.log_error(f"Financial Control Tower - Periodic Error: {str(e)}")
        return {"success": False, "error": str(e)}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTERNAL: KPI Computation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NEW: Internal builders that compute + cache
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_and_cache_intelligence():
    kpis = _compute_kpis()
    roi_data = _compute_roi(kpis)
    tier_tables = _compute_customer_tiers()

    # Tier debts — alohida SQL, tier listiga bog'liq emas
    tier_debt = _compute_tier_debts()
    kpis["debt_a"] = tier_debt.get("A", 0)
    kpis["debt_b"] = tier_debt.get("B", 0)
    kpis["debt_c"] = tier_debt.get("C", 0)
    # total_debt o'zgarmaydi — _compute_kpis() da hisoblangan

    result = {
        "success": True,
        "kpis": kpis,
        "roi": roi_data,
        "tiers": tier_tables
    }

    frappe.cache().set_value('fct_intelligence_data', json.dumps(result), expires_in_sec=CACHE_TTL)
    frappe.cache().set_value('fct_cache_timestamp', str(now_datetime()), expires_in_sec=CACHE_TTL)

    return result


def _build_periodic_result(from_date, to_date):
    monthly_investment    = _get_monthly_investment(from_date, to_date)
    collection_efficiency = _get_collection_efficiency(from_date, to_date)
    net_profit            = _get_monthly_net_profit(from_date, to_date)
    contract_count        = _get_monthly_contract_count(from_date, to_date)
    monthly_sales         = _get_monthly_sales(from_date, to_date)
    monthly_margin        = _get_monthly_margin(from_date, to_date)

    return {
        "success": True,
        "monthly_investment":    monthly_investment,
        "collection_efficiency": collection_efficiency,
        "net_profit":            net_profit,
        "contract_count":        contract_count,
        "monthly_sales":         monthly_sales,
        "monthly_margin":        monthly_margin,
        "date_range": {
            "from": str(from_date),
            "to":   str(to_date)
        }
    }


def _build_and_cache_periodic():
    """
    Computes default periodic data (last 12 months) and caches it.
    Called by the 23:59 cron job.
    """
    from_date = getdate(add_months(nowdate(), -12))
    to_date = getdate(nowdate())

    result = _build_periodic_result(from_date, to_date)
    frappe.cache().set_value('fct_periodic_data', json.dumps(result), expires_in_sec=CACHE_TTL)

    return result

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NEW: Scheduled Job Entry Point (23:59 Cron)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def rebuild_fct_cache():
    """
    Pre-calculates ALL dashboard data and stores in Redis cache.

    Called by hooks.py scheduler_events at 23:59 daily.
    This is the ONLY time heavy SQL queries run automatically.

    Execution time: ~2-5 seconds (runs 6 SQL queries once).
    Cache TTL: 25 hours (ensures overlap past next cron cycle).
    """
    try:
        frappe.logger('fct').info("FCT Cache Rebuild: Starting 23:59 scheduled job...")

        # ── Build intelligence data (KPIs + ROI + Tiers) ─────────────────
        intel = _build_and_cache_intelligence()
        frappe.logger('fct').info(
            f"FCT Cache Rebuild: Intelligence OK — "
            f"KPIs={bool(intel.get('kpis'))}, "
            f"Tiers A={len(intel.get('tiers',{}).get('A',[]))}, "
            f"B={len(intel.get('tiers',{}).get('B',[]))}, "
            f"C={len(intel.get('tiers',{}).get('C',[]))}"
        )

        # ── Build periodic data (default 12-month range) ────────────────
        periodic = _build_and_cache_periodic()
        frappe.logger('fct').info(
            f"FCT Cache Rebuild: Periodic OK — "
            f"Investment months={len(periodic.get('monthly_investment',[]))}, "
            f"Collection months={len(periodic.get('collection_efficiency',[]))}"
        )

        # ── Store timestamp ──────────────────────────────────────────────
        frappe.cache().set_value('fct_cache_timestamp', str(now_datetime()), expires_in_sec=CACHE_TTL)

        frappe.logger('fct').info("FCT Cache Rebuild: ✅ Complete")

    except Exception as e:
        frappe.log_error(f"FCT Cache Rebuild FAILED: {str(e)}", "Financial Control Tower")
        frappe.logger('fct').error(f"FCT Cache Rebuild: ❌ {str(e)}")

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

    # ── Tikilgan pul: Shareholder Payment Entry ──────────────────────────
    invested_result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(
                CASE
                    WHEN pe.payment_type = 'Receive' THEN pe.received_amount
                    WHEN pe.payment_type = 'Pay'     THEN -pe.received_amount
                    ELSE 0
                END
            ), 0) AS invested_capital
        FROM `tabPayment Entry` pe
        WHERE pe.docstatus = 1
          AND pe.party_type = 'Shareholder'
    """, as_dict=True)[0]

    # ── Foiz va shartnoma soni: Installment Application ──────────────────
    ia_result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(ia.custom_total_interest), 0) AS total_interest,
            COUNT(*) AS total_contracts
        FROM `tabInstallment Application` ia
        WHERE ia.docstatus = 1
    """, as_dict=True)[0]

    invested_capital = flt(invested_result.invested_capital)
    total_interest = flt(ia_result.total_interest)
    total_contracts = ia_result.total_contracts or 0

    # ── Active contracts: Sales Orders NOT completed/cancelled/closed/draft ──
    active_count = _count_active_sales_orders()

    # ── Closed contracts: Sales Orders with status = 'Completed' ──
    closed_count = _count_closed_sales_orders()
    # ── Jami xarajatlar: Employee/Xarajat Payment Entry ─────────────────
    expense_result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(
                CASE
                    WHEN pe.payment_type = 'Pay'     THEN pe.paid_amount
                    WHEN pe.payment_type = 'Receive' THEN -pe.received_amount
                    ELSE 0
                END
            ), 0) AS total_expenses
        FROM `tabPayment Entry` pe
        INNER JOIN `tabCounterparty Category` cc
            ON pe.custom_counterparty_category = cc.name
        WHERE pe.docstatus = 1
          AND cc.custom_expense_type = 'Xarajat'
          AND pe.party_type = 'Employee'
          AND pe.party_name = 'Xarajat'
    """, as_dict=True)[0]

    total_expenses = flt(expense_result.total_expenses)
    net_profit = total_interest - total_expenses
    # ── Jami qarzdorlik: barcha submitted IA - to'lovlar ─────────────────
    debt_result = frappe.db.sql("""
        SELECT
            COALESCE(SUM(ia.custom_grand_total_with_interest), 0) AS total_billed,
            COALESCE(pe_agg.net_paid, 0) AS net_paid,
            (
                COALESCE(SUM(ia.custom_grand_total_with_interest), 0)
                - COALESCE(pe_agg.net_paid, 0)
            ) AS total_debt
        FROM `tabInstallment Application` ia
        LEFT JOIN (
            SELECT
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
              AND (
                  pe.custom_contract_reference IS NOT NULL
                  AND pe.custom_contract_reference != ''
              )
        ) pe_agg ON 1=1
        WHERE ia.docstatus = 1
    """, as_dict=True)[0]

    raw_total_debt = flt(debt_result.total_debt)
    return {
        "invested_capital": invested_capital,
        "total_debt": raw_total_debt,  # overwritten by caller
        "debt_a": 0,  # overwritten by caller
        "debt_b": 0,  # overwritten by caller
        "debt_c": 0,  # overwritten by caller
        "active_contracts": active_count,
        "closed_contracts": closed_count,
        "total_interest": total_interest,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
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
    invested    = flt(kpis.get("invested_capital", 0))
    interest    = flt(kpis.get("total_interest", 0))
    expenses    = flt(kpis.get("total_expenses", 0))
    net_profit  = flt(kpis.get("net_profit", 0))  # interest - expenses

    if invested == 0:
        roi_pct = 0
    else:
        roi_pct = round((net_profit / invested) * 100, 2)

    return {
        "roi_percentage": roi_pct,
        "total_interest": interest,
        "total_expenses": expenses,
        "net_profit": net_profit,
        "invested_capital": invested,
        "chart_data": {
            "interest": net_profit,   # donut ko'k yoyi = sof foyda
            "principal": invested,
            "total": invested + net_profit
        }
    }

def _compute_tier_debts():
    """
    customer_classification bo'yicha jami qarzdorlik.
    net_paid JOIN multiplication muammosi hal qilindi:
    avval customer darajasida debt hisoblanadi,
    keyin classification bo'yicha yig'iladi.
    """
    rows = frappe.db.sql("""
        SELECT
            COALESCE(cust.customer_classification, 'A') AS classification,
            SUM(cust_debt.debt) AS total_debt
        FROM (
            SELECT
                ia.customer,
                (
                    COALESCE(SUM(ia.custom_grand_total_with_interest), 0)
                    - COALESCE(MAX(pe_agg.net_paid), 0)
                ) AS debt
            FROM `tabInstallment Application` ia
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
            GROUP BY ia.customer
        ) cust_debt
        LEFT JOIN `tabCustomer` cust ON cust.name = cust_debt.customer
        GROUP BY COALESCE(cust.customer_classification, 'A')
    """, as_dict=True)

    result = {"A": 0.0, "B": 0.0, "C": 0.0}
    for row in rows:
        cls = (row.classification or "A").strip().upper()
        if cls in result:
            result[cls] = flt(row.total_debt)
        else:
            result["A"] = flt(result["A"]) + flt(row.total_debt)
    return result
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
    FIFO-based collection efficiency.

    1. IA ga bog'liq Payment Schedule dan kutilgan to'lovlar olinadi
    2. Har bir IA uchun barcha to'lovlar FIFO bo'yicha schedule ga yoziladi
    3. Natija due_date OYLI bo'yicha aggregatlanadi (posting_date emas)
    """

    # ── Step 1: Barcha submitted IA lar uchun payment schedule ──────────
    schedules = frappe.db.sql("""
        SELECT
            ps.parent       AS ia_name,
            ps.due_date,
            ps.payment_amount,
            ps.idx
        FROM `tabPayment Schedule` ps
        INNER JOIN `tabInstallment Application` ia ON ia.name = ps.parent
        WHERE ps.parenttype = 'Installment Application'
          AND ia.docstatus = 1
          AND ps.due_date IS NOT NULL
          AND ps.payment_amount > 0
        ORDER BY ps.parent, ps.due_date ASC, ps.idx ASC
    """, as_dict=True)

    if not schedules:
        return []

    # ── Step 2: Har bir IA uchun barcha to'lovlar (posting_date bo'yicha) ─
    payments = frappe.db.sql("""
        SELECT
            ia.name                             AS ia_name,
            pe.posting_date,
            SUM(
                CASE
                    WHEN pe.payment_type = 'Receive' THEN pe.received_amount
                    WHEN pe.payment_type = 'Pay'     THEN -pe.received_amount
                    ELSE 0
                END
            ) AS net_amount
            FROM `tabPayment Entry` pe
            INNER JOIN `tabInstallment Application` ia
            ON ia.sales_order = pe.custom_contract_reference
            WHERE pe.docstatus = 1
                AND pe.party_type = 'Customer'
                AND pe.custom_contract_reference IS NOT NULL
                AND pe.custom_contract_reference != ''
                AND ia.docstatus = 1
            GROUP BY ia.name, pe.posting_date
            ORDER BY ia.name, pe.posting_date ASC
        """, as_dict=True)

    # ── Step 3: IA bo'yicha guruhlash ────────────────────────────────────
    from collections import defaultdict

    # schedules: { ia_name: [ {due_date, payment_amount, idx}, ... ] }
    ia_schedules = defaultdict(list)
    for s in schedules:
        ia_schedules[s.ia_name].append({
            "due_date": s.due_date,
            "scheduled": flt(s.payment_amount),
            "applied": 0.0
        })

    # payments pool: { ia_name: total_paid }
    ia_payments = defaultdict(float)
    for p in payments:
        ia_payments[p.ia_name] += flt(p.net_amount)

    # ── Step 4: FIFO reconcile — har bir IA uchun ───────────────────────
    # due_date oyi bo'yicha: { "YYYY-MM": {expected, actual} }
    month_map = {}

    for ia_name, sched_list in ia_schedules.items():
        balance = ia_payments.get(ia_name, 0.0)

        for row in sched_list:
            scheduled = row["scheduled"]
            applied   = min(balance, scheduled)
            balance   = max(0.0, balance - applied)

            # Oylik kalit — due_date oyi
            d = row["due_date"]
            if isinstance(d, str):
                d = getdate(d)
            key = f"{d.year}-{d.month:02d}"

            if key not in month_map:
                month_map[key] = {
                    "year": d.year,
                    "month": d.month,
                    "label": f"{calendar.month_abbr[d.month]} {d.year}",
                    "expected": 0.0,
                    "actual": 0.0
                }
            month_map[key]["expected"] += scheduled
            month_map[key]["actual"]   += applied

    # ── Step 5: date range filtri ────────────────────────────────────────
    from_key = f"{from_date.year}-{from_date.month:02d}"
    to_key   = f"{to_date.year}-{to_date.month:02d}"

    sorted_months = sorted(
        [m for m in month_map.values()
         if f"{m['year']}-{m['month']:02d}" >= from_key
         and f"{m['year']}-{m['month']:02d}" <= to_key],
        key=lambda x: (x["year"], x["month"])
    )

    # ── Step 6: efficiency % qo'shish ────────────────────────────────────
    for m in sorted_months:
        if m["expected"] > 0:
            m["efficiency_pct"] = round((m["actual"] / m["expected"]) * 100, 1)
        else:
            m["efficiency_pct"] = 100.0 if m["actual"] > 0 else 0.0

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
def _get_monthly_sales(from_date, to_date):
    """
    Oylik savdo = SUM(custom_grand_total_with_interest - downpayment_amount)
    """
    result = frappe.db.sql("""
        SELECT
            YEAR(ia.transaction_date)  AS yr,
            MONTH(ia.transaction_date) AS mo,
            COALESCE(SUM(
                COALESCE(ia.custom_grand_total_with_interest, 0)
                - COALESCE(ia.downpayment_amount, 0)
            ), 0) AS sales
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
            "amount": flt(r.sales)
        }
        for r in result
    ]


def _get_monthly_margin(from_date, to_date):
    """
    Oylik marja % = (custom_total_interest / savdo) * 100
    savdo = custom_grand_total_with_interest - downpayment_amount
    """
    result = frappe.db.sql("""
        SELECT
            YEAR(ia.transaction_date)  AS yr,
            MONTH(ia.transaction_date) AS mo,
            COALESCE(SUM(ia.custom_total_interest), 0) AS total_interest,
            COALESCE(SUM(
                COALESCE(ia.custom_grand_total_with_interest, 0)
                - COALESCE(ia.downpayment_amount, 0)
            ), 0) AS sales
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
            "margin_pct": round(
                (flt(r.total_interest) / flt(r.sales) * 100), 2
            ) if flt(r.sales) > 0 else 0.0
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

        frappe.logger('fct').info(
            f"FCT: Cache invalidated by {doc.doctype} {doc.name} ({method}). "
            f"Dashboard will refresh on next manual load."
        )

    # ── REMOVED: frappe.publish_realtime() ───────────────────────────
    # Previously pushed 'fct_data_changed' which triggered ALL open
    # browsers to fetchGeneral() + fetchPeriodic() simultaneously.
    # This was the primary cause of SQL load spikes.
    #
    # If you want SELECTIVE notification (eg, only the submitting user),
    # uncomment the block below:
    #
    # frappe.publish_realtime(
    #     event='fct_cache_cleared',
    #     message={'doctype': doc.doctype, 'docname': doc.name},
    #     user=frappe.session.user,  # only current user, not broadcast
    #     after_commit=True
    # )

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
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# NEW ENDPOINT: Contract Installment Analysis (v4.1)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# APPEND this entire block to the bottom of:
#   financial_control_tower_api.py
#
# No existing functions are modified.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@frappe.whitelist()
def get_contract_installment_analysis(search_term):
    """
    Fetches contract details + FIFO-reconciled payment schedule.

    Args:
        search_term: Installment Application ID or Customer Name (min 3 chars)

    Returns:
        {
            "success": True,
            "contract": { name, customer, customer_name, grand_total_with_interest, ... },
            "schedule": [
                {
                    "due_date": "2024-03-15",
                    "scheduled_amount": 1000.00,
                    "paid_amount": 1000.00,
                    "balance": 0,
                    "status": "Paid"
                }, ...
            ],
            "summary": { total_scheduled, total_paid, total_balance }
        }
    """
    try:
        if not search_term or len(search_term.strip()) < 3:
            return {"success": False, "error": "Kamida 3 ta belgi kiriting"}

        term = search_term.strip()
        like_term = f"%{term}%"

        # ── Step 1: Find the Installment Application ────────────────────
        ia = frappe.db.sql("""
            SELECT
                ia.name,
                ia.customer,
                ia.customer_name,
                ia.transaction_date,
                ia.total_amount,
                ia.downpayment_amount,
                ia.custom_grand_total_with_interest,
                ia.sales_order,
                ia.custom_total_interest
            FROM `tabInstallment Application` ia
            WHERE ia.docstatus = 1
              AND (
                ia.name LIKE %(term)s
                OR ia.customer_name LIKE %(term)s
                OR ia.customer LIKE %(term)s
              )
            ORDER BY ia.transaction_date DESC
            LIMIT 1
        """, {"term": like_term}, as_dict=True)

        if not ia:
            return {"success": False, "error": "Shartnoma topilmadi"}

        ia = ia[0]

        if not ia.sales_order:
            return {"success": False, "error": "Shartnomaga bog'langan Sales Order yo'q"}

        # ── Step 2: Fetch Payment Schedule from Sales Order ─────────────
        schedule = frappe.db.sql("""
            SELECT
                ps.due_date,
                ps.payment_amount,
                ps.idx
            FROM `tabPayment Schedule` ps
            WHERE ps.parent = %(so)s
              AND ps.parenttype = 'Sales Order'
            ORDER BY ps.due_date ASC, ps.idx ASC
        """, {"so": ia.sales_order}, as_dict=True)

        if not schedule:
            return {
                "success": True,
                "contract": _format_contract(ia),
                "schedule": [],
                "summary": {"total_scheduled": 0, "total_paid": 0, "total_balance": 0}
            }

        # ── Step 3: Fetch ALL Payments linked to this Sales Order ────────
        # Link path: IA → Sales Order ← Payment Entry
        # Method 1: custom_contract_reference stores the Sales Order name
        # Method 2: standard references child table (reference_name = SO)
        payments = frappe.db.sql("""
            SELECT pe.received_amount, pe.posting_date
            FROM `tabPayment Entry` pe
            WHERE pe.docstatus = 1
              AND pe.payment_type = 'Receive'
              AND (
                pe.custom_contract_reference = %(sales_order)s
                OR pe.name IN (
                  SELECT per.parent
                  FROM `tabPayment Entry Reference` per
                  WHERE per.reference_doctype = 'Sales Order'
                    AND per.reference_name = %(sales_order)s
                )
              )
            ORDER BY pe.posting_date ASC, pe.creation ASC
        """, {"sales_order": ia.sales_order}, as_dict=True)

        # ── Step 4: FIFO Payment Reconciliation ─────────────────────────
        reconciled = _fifo_reconcile(schedule, payments)

        return {
            "success": True,
            "contract": _format_contract(ia),
            "schedule": reconciled,
            "summary": {
                "total_scheduled": sum(flt(r["scheduled_amount"]) for r in reconciled),
                "total_paid": sum(flt(r["paid_amount"]) for r in reconciled),
                "total_balance": sum(flt(r["balance"]) for r in reconciled)
            }
        }

    except Exception as e:
        frappe.log_error(f"Contract Analysis Error: {str(e)}", "FCT Contract Search")
        return {"success": False, "error": str(e)}


def _format_contract(ia):
    """Format IA record for frontend consumption."""
    return {
        "name": ia.name,
        "customer": ia.customer,
        "customer_name": ia.customer_name,
        "transaction_date": str(ia.transaction_date),
        "total_amount": flt(ia.total_amount),
        "downpayment": flt(ia.downpayment_amount),
        "grand_total_with_interest": flt(ia.custom_grand_total_with_interest),
        "total_interest": flt(ia.custom_total_interest),
        "sales_order": ia.sales_order
    }


def _fifo_reconcile(schedule, payments):
    """
    FIFO Payment Reconciliation Algorithm.

    ┌──────────────────────────────────────────────────────────────────────┐
    │ 1. Pool all payment amounts into a single running balance           │
    │ 2. Walk through installments in chronological order                 │
    │ 3. For each installment, consume min(balance, scheduled_amount)     │
    │ 4. Carry any surplus forward to the next installment                │
    │                                                                      │
    │ Status Logic:                                                        │
    │   applied == scheduled  → "Paid"                                    │
    │   0 < applied < sched   → "Partially Paid"                         │
    │   applied == 0          → "Unpaid"                                  │
    └──────────────────────────────────────────────────────────────────────┘
    """
    # Pool all payments into a single balance
    balance = sum(flt(p.received_amount) for p in payments)

    reconciled = []

    for row in schedule:
        scheduled = flt(row.payment_amount)

        # Apply whatever we can from the running balance
        applied = min(balance, scheduled)
        balance -= applied
        # Ensure no floating-point drift below zero
        balance = max(0, balance)

        remaining = scheduled - applied

        # Determine status
        if applied >= scheduled and scheduled > 0:
            status = "Paid"
        elif applied > 0:
            status = "Partially Paid"
        else:
            status = "Unpaid"

        reconciled.append({
            "due_date": str(row.due_date),
            "scheduled_amount": scheduled,
            "paid_amount": round(applied, 2),
            "balance": round(remaining, 2),
            "status": status,
            "idx": row.idx
        })

    return reconciled
@frappe.whitelist()
def search_contracts(search_term):
    """Shartnomalarni qidirish — dropdown uchun ro'yxat qaytaradi."""
    if not search_term or len(search_term.strip()) < 2:
        return {"success": True, "contracts": []}

    term = f"%{search_term.strip()}%"

    contracts = frappe.db.sql("""
        SELECT
            ia.name,
            ia.customer,
            ia.customer_name,
            ia.transaction_date,
            ia.custom_grand_total_with_interest
        FROM `tabInstallment Application` ia
        INNER JOIN `tabSales Order` so ON so.name = ia.sales_order
        WHERE ia.docstatus = 1
          AND so.docstatus = 1
          AND so.status NOT IN ('Completed', 'Cancelled', 'Closed', 'Draft')
          AND (
            ia.name LIKE %(term)s
            OR ia.customer_name LIKE %(term)s
            OR ia.customer LIKE %(term)s
          )
        ORDER BY ia.transaction_date DESC
        LIMIT 20
    """, {"term": term}, as_dict=True)

    return {
        "success": True,
        "contracts": [
            {
                "name": c.name,
                "customer": c.customer,
                "customer_name": c.customer_name,
                "date": str(c.transaction_date),
                "total": flt(c.custom_grand_total_with_interest)
            }
            for c in contracts
        ]
    }
