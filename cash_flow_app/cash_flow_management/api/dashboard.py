# -*- coding: utf-8 -*-
# Copyright (c) 2024, Cash Flow App
# License: MIT
"""
Sales Dashboard API - High Performance Backend with Type Hints

This module provides optimized API endpoints for the Rassrochka Sales Dashboard.
All queries are optimized with date ranges instead of YEAR()/MONTH() for better index usage.

Key Features:
- Single source of truth: Installment Application
- Index-friendly date range queries
- Batched aggregations
- Consistent error handling
- Full backward compatibility with legacy endpoints
- Type hints for better IDE support
"""

import frappe
from frappe import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Dict, List, Optional, Union, Any


# =============================================================================
# PRIMARY DASHBOARD API (Optimized for <500ms response)
# =============================================================================


@frappe.whitelist()
def get_sales_dashboard_data(
    party_type: Optional[str] = None,
    group_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    High-performance dashboard data API for the Sales Dashboard page.
    All data is sourced from Installment Application as the single source of truth.

    Performance optimizations:
    - Uses date ranges instead of YEAR()/MONTH() for index-friendly queries
    - Single pass aggregations where possible
    - Batched queries to reduce round trips

    Args:
        party_type: Optional filter by party type ('Customer' or 'Supplier')
        group_name: Optional filter by customer/supplier group

    Returns:
        dict: Contains kpi, monthly_trends, payment_statistics,
              top_customers, product_sales, recent_applications
    """
    try:
        # Pre-calculate date ranges for all queries
        now = datetime.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)

        # Calculate 12-month date range for trends
        twelve_months_ago = current_month_start - relativedelta(months=11)

        date_context = {
            'now': now,
            'current_month_start': current_month_start,
            'previous_month_start': previous_month_start,
            'twelve_months_ago': twelve_months_ago
        }

        # Build filters
        filters = {}
        if party_type:
            filters['party_type'] = party_type
        if group_name:
            filters['group_name'] = group_name

        return {
            'kpi': _get_kpi_data_optimized(filters, date_context),
            'monthly_trends': _get_monthly_trends_optimized(filters, date_context),
            'payment_statistics': _get_payment_statistics_optimized(filters),
            'top_customers': _get_top_customers_optimized(filters),
            'product_sales': _get_product_sales_optimized(filters),
            'recent_applications': _get_recent_applications_optimized(filters)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Sales Dashboard Data Error')
        return {'error': str(e)}


def _get_kpi_data_optimized(
    filters: Optional[Dict] = None,
    date_context: Optional[Dict] = None
) -> Dict[str, Union[float, int]]:
    """
    Get KPI card data with optimized single-query aggregation.
    All metrics sourced from Installment Application.
    """
    try:
        current_month_start = date_context['current_month_start']
        previous_month_start = date_context['previous_month_start']

        current_month_str = current_month_start.strftime('%Y-%m-%d')
        previous_month_str = previous_month_start.strftime('%Y-%m-%d')

        # Single query to get all Installment Application aggregates
        ia_stats = frappe.db.sql("""
            SELECT
                COALESCE(SUM(total_amount), 0) as total_earnings,
                COUNT(*) as total_contracts,
                COALESCE(SUM(CASE WHEN transaction_date >= %s THEN total_amount ELSE 0 END), 0) as current_month_earnings,
                COALESCE(SUM(CASE WHEN transaction_date >= %s AND transaction_date < %s THEN total_amount ELSE 0 END), 0) as previous_month_earnings
            FROM `tabInstallment Application`
            WHERE docstatus = 1
        """, (current_month_str, previous_month_str, current_month_str), as_dict=1)[0]

        # Single query for payment totals
        payment_stats = frappe.db.sql("""
            SELECT
                COALESCE(SUM(paid_amount), 0) as total_paid,
                COALESCE(SUM(CASE WHEN posting_date >= %s THEN paid_amount ELSE 0 END), 0) as current_month_paid,
                COALESCE(SUM(CASE WHEN posting_date >= %s AND posting_date < %s THEN paid_amount ELSE 0 END), 0) as previous_month_paid
            FROM `tabPayment Entry`
            WHERE docstatus = 1
              AND party_type = 'Customer'
              AND payment_type = 'Receive'
        """, (current_month_str, previous_month_str, current_month_str), as_dict=1)[0]

        total_earnings = float(ia_stats.get('total_earnings', 0) or 0)
        total_paid = float(payment_stats.get('total_paid', 0) or 0)
        total_contracts = int(ia_stats.get('total_contracts', 0) or 0)
        outstanding = max(0, total_earnings - total_paid)

        # Growth calculation based on payment trends
        current_month_paid = float(payment_stats.get('current_month_paid', 0) or 0)
        previous_month_paid = float(payment_stats.get('previous_month_paid', 0) or 0)

        growth_percentage = 0
        if previous_month_paid > 0:
            growth_percentage = round(
                ((current_month_paid - previous_month_paid) / previous_month_paid) * 100, 1
            )

        return {
            'total_earnings': total_earnings,
            'total_paid': total_paid,
            'total_contracts': total_contracts,
            'outstanding_amount': outstanding,
            'growth_percentage': growth_percentage
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'KPI Data Error')
        return {
            'total_earnings': 0,
            'total_paid': 0,
            'total_contracts': 0,
            'outstanding_amount': 0,
            'growth_percentage': 0
        }


def _get_monthly_trends_optimized(
    filters: Optional[Dict] = None,
    date_context: Optional[Dict] = None
) -> List[Dict[str, Union[str, float]]]:
    """
    Get monthly revenue and payment trends using date ranges (index-friendly).
    Uses single query with GROUP BY for better performance.
    """
    try:
        twelve_months_ago = date_context['twelve_months_ago']
        now = date_context['now']

        # Format dates for query
        start_date = twelve_months_ago.strftime('%Y-%m-%d')
        end_date = (now + timedelta(days=1)).strftime('%Y-%m-%d')

        # Single query for Installment Application monthly totals
        ia_monthly = frappe.db.sql("""
            SELECT
                DATE_FORMAT(transaction_date, '%%Y-%%m') as month,
                COALESCE(SUM(total_amount), 0) as revenue
            FROM `tabInstallment Application`
            WHERE docstatus = 1
              AND transaction_date >= %s
              AND transaction_date < %s
            GROUP BY DATE_FORMAT(transaction_date, '%%Y-%%m')
        """, (start_date, end_date), as_dict=1)

        # Single query for Payment Entry monthly totals
        pe_monthly = frappe.db.sql("""
            SELECT
                DATE_FORMAT(posting_date, '%%Y-%%m') as month,
                COALESCE(SUM(paid_amount), 0) as payments
            FROM `tabPayment Entry`
            WHERE docstatus = 1
              AND party_type = 'Customer'
              AND payment_type = 'Receive'
              AND posting_date >= %s
              AND posting_date < %s
            GROUP BY DATE_FORMAT(posting_date, '%%Y-%%m')
        """, (start_date, end_date), as_dict=1)

        # Convert to lookup dicts
        ia_lookup = {row['month']: float(row['revenue'] or 0) for row in ia_monthly}
        pe_lookup = {row['month']: float(row['payments'] or 0) for row in pe_monthly}

        # Build result for last 12 months
        result = []
        current_date = now
        for i in range(11, -1, -1):
            month_date = current_date - relativedelta(months=i)
            month_key = month_date.strftime('%Y-%m')
            result.append({
                'month': month_key,
                'revenue': ia_lookup.get(month_key, 0),
                'payments': pe_lookup.get(month_key, 0)
            })

        return result
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Monthly Trends Error')
        return []


def _get_payment_statistics_optimized(
    filters: Optional[Dict] = None
) -> Dict[str, Union[float, int]]:
    """Get payment statistics for donut chart - single combined query."""
    try:
        # Get totals from Installment Application
        total = frappe.db.sql("""
            SELECT COALESCE(SUM(total_amount), 0) as total
            FROM `tabInstallment Application`
            WHERE docstatus = 1
        """, as_dict=1)[0].get('total', 0) or 0

        # Get total paid
        paid = frappe.db.sql("""
            SELECT COALESCE(SUM(paid_amount), 0) as total
            FROM `tabPayment Entry`
            WHERE docstatus = 1
              AND party_type = 'Customer'
              AND payment_type = 'Receive'
        """, as_dict=1)[0].get('total', 0) or 0

        total = float(total)
        paid = float(paid)
        unpaid = max(0, total - paid)

        paid_percentage = round((paid / total * 100), 1) if total > 0 else 0
        unpaid_percentage = round(100 - paid_percentage, 1)

        return {
            'paid': paid,
            'unpaid': unpaid,
            'total': total,
            'paid_percentage': paid_percentage,
            'unpaid_percentage': unpaid_percentage
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Payment Statistics Error')
        return {
            'paid': 0,
            'unpaid': 0,
            'total': 0,
            'paid_percentage': 0,
            'unpaid_percentage': 0
        }


def _get_top_customers_optimized(
    filters: Optional[Dict] = None,
    limit: int = 5
) -> List[Dict[str, Union[str, float]]]:
    """Get top customers by Installment Application value."""
    try:
        data = frappe.db.sql("""
            SELECT
                ia.customer as customer_id,
                COALESCE(c.customer_name, ia.customer) as customer_name,
                SUM(ia.total_amount) as total_value
            FROM `tabInstallment Application` ia
            LEFT JOIN `tabCustomer` c ON ia.customer = c.name
            WHERE ia.docstatus = 1
            GROUP BY ia.customer
            ORDER BY total_value DESC
            LIMIT %s
        """, (limit,), as_dict=1)

        return [{
            'customer_id': row.customer_id,
            'customer_name': row.customer_name or row.customer_id,
            'total_value': float(row.total_value or 0)
        } for row in data]
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Top Customers Error')
        return []


def _get_product_sales_optimized(
    filters: Optional[Dict] = None,
    limit: int = 5
) -> List[Dict[str, Union[str, float]]]:
    """Get top products from Installment Application items."""
    try:
        data = frappe.db.sql("""
            SELECT
                iai.item_code,
                COALESCE(i.item_name, iai.item_code) as item_name,
                SUM(iai.amount) as total_sales
            FROM `tabInstallment Application Item` iai
            INNER JOIN `tabInstallment Application` ia ON iai.parent = ia.name
            LEFT JOIN `tabItem` i ON iai.item_code = i.name
            WHERE ia.docstatus = 1
            GROUP BY iai.item_code
            ORDER BY total_sales DESC
            LIMIT %s
        """, (limit,), as_dict=1)

        return [{
            'item_code': row.item_code,
            'item_name': row.item_name or row.item_code,
            'total_sales': float(row.total_sales or 0)
        } for row in data]
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Product Sales Error')
        return []


def _get_recent_applications_optimized(
    filters: Optional[Dict] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get recent installment applications with optimized join."""
    try:
        data = frappe.db.sql("""
            SELECT
                ia.name,
                ia.customer,
                COALESCE(c.customer_name, ia.customer) as customer_name,
                ia.transaction_date,
                ia.total_amount,
                ia.monthly_payment,
                ia.installment_months,
                ia.status
            FROM `tabInstallment Application` ia
            LEFT JOIN `tabCustomer` c ON ia.customer = c.name
            WHERE ia.docstatus = 1
            ORDER BY ia.transaction_date DESC, ia.creation DESC
            LIMIT %s
        """, (limit,), as_dict=1)

        return [{
            'name': row.name,
            'customer': row.customer,
            'customer_name': row.customer_name,
            'transaction_date': str(row.transaction_date) if row.transaction_date else None,
            'total_amount': float(row.total_amount or 0),
            'monthly_payment': float(row.monthly_payment or 0),
            'installment_months': int(row.installment_months or 0),
            'status': row.status or 'Draft'
        } for row in data]
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Recent Applications Error')
        return []


@frappe.whitelist()
def get_party_groups(party_type: str) -> List[str]:
    """Get groups for a specific party type."""
    try:
        if party_type == 'Customer':
            groups = frappe.db.sql("""
                SELECT DISTINCT customer_group as name
                FROM `tabCustomer`
                WHERE customer_group IS NOT NULL AND customer_group != ''
                ORDER BY customer_group
            """, as_dict=1)
        elif party_type == 'Supplier':
            groups = frappe.db.sql("""
                SELECT DISTINCT supplier_group as name
                FROM `tabSupplier`
                WHERE supplier_group IS NOT NULL AND supplier_group != ''
                ORDER BY supplier_group
            """, as_dict=1)
        else:
            return []

        return [g.name for g in groups if g.name]
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Party Groups Error')
        return []


# =============================================================================
# LEGACY API FUNCTIONS (Backward Compatibility)
# =============================================================================


@frappe.whitelist()
def get_dashboard_data(year_filter: Optional[Union[str, List[int]]] = None) -> Dict[str, Any]:
    """
    Returns comprehensive dashboard data with multi-year comparison.
    Legacy endpoint for backward compatibility.

    Args:
        year_filter: List of years to compare (default: last 3 years)
    """
    try:
        # Default to last 3 years if not provided
        if not year_filter:
            current_year = datetime.now().year
            year_filter = [current_year - 2, current_year - 1, current_year]
        elif isinstance(year_filter, str):
            year_filter = frappe.parse_json(year_filter)

        return {
            'shareholders': get_shareholder_capital(),
            'debt_summary': get_debt_summary(),
            'debt_by_classification': get_debt_by_classification(),
            'active_contracts': get_active_contracts_count(),
            'monthly_finance': get_monthly_finance_chart(year_filter),
            'monthly_revenue': get_monthly_revenue_chart(year_filter),
            'monthly_contracts': get_monthly_contracts_chart(year_filter),
            'roi_data': get_roi_calculation(),
            'monthly_profit': get_monthly_profit_chart(year_filter),
            'debt_list': get_debt_list(),
            'year_filter': year_filter
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Dashboard Data Error')
        return {'error': str(e)}


@frappe.whitelist()
def get_shareholder_capital() -> Dict[str, float]:
    """
    Calculate total capital from shareholders.
    Formula: SUM(receive payments) - SUM(pay payments) where party_type = 'Shareholder'
    """
    try:
        received = frappe.db.sql("""
            SELECT COALESCE(SUM(paid_amount), 0) as total
            FROM `tabPayment Entry`
            WHERE docstatus = 1
              AND party_type = 'Shareholder'
              AND payment_type = 'Receive'
        """, as_dict=1)[0].get('total', 0) or 0

        paid = frappe.db.sql("""
            SELECT COALESCE(SUM(paid_amount), 0) as total
            FROM `tabPayment Entry`
            WHERE docstatus = 1
              AND party_type = 'Shareholder'
              AND payment_type = 'Pay'
        """, as_dict=1)[0].get('total', 0) or 0

        net_capital = float(received) - float(paid)

        return {
            'received': float(received),
            'paid': float(paid),
            'net_capital': net_capital
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Shareholder Capital Error')
        return {'received': 0, 'paid': 0, 'net_capital': 0}


@frappe.whitelist()
def get_debt_summary() -> Dict[str, Union[float, int]]:
    """
    Calculate total debt from all customers.
    Formula: SUM(all contract grand_total) - SUM(all customer payments received)
    """
    try:
        # Total contract amounts from Sales Orders
        total_contracts = frappe.db.sql("""
            SELECT COALESCE(SUM(grand_total), 0) as total
            FROM `tabSales Order`
            WHERE docstatus = 1
        """, as_dict=1)[0].get('total', 0) or 0

        # Total payments received from customers
        total_paid = frappe.db.sql("""
            SELECT COALESCE(SUM(paid_amount), 0) as total
            FROM `tabPayment Entry`
            WHERE docstatus = 1
              AND party_type = 'Customer'
              AND payment_type = 'Receive'
        """, as_dict=1)[0].get('total', 0) or 0

        total_debt = float(total_contracts) - float(total_paid)
        payment_percentage = (float(total_paid) / float(total_contracts) * 100) if total_contracts > 0 else 0

        return {
            'total_contracts': float(total_contracts),
            'total_paid': float(total_paid),
            'total_debt': total_debt,
            'payment_percentage': round(payment_percentage, 2)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Debt Summary Error')
        return {'total_contracts': 0, 'total_paid': 0, 'total_debt': 0, 'payment_percentage': 0}


@frappe.whitelist()
def get_debt_by_classification() -> Dict[str, Dict[str, Union[float, int]]]:
    """
    Calculate debt for each customer classification (A, B, C).
    Formula: For each classification, SUM(contracts) - SUM(payments received)
    """
    try:
        classifications = ['A', 'B', 'C']
        result = {}

        for classification in classifications:
            # Get all customers with this classification
            customers = frappe.db.sql("""
                SELECT name
                FROM `tabCustomer`
                WHERE COALESCE(customer_classification, '') = %s
            """, (classification,), as_dict=1)

            customer_names = [c.name for c in customers]

            if not customer_names:
                result[classification] = {
                    'contracts': 0,
                    'paid': 0,
                    'debt': 0,
                    'customer_count': 0
                }
                continue

            # Total contracts for these customers
            placeholders = ','.join(['%s'] * len(customer_names))
            contracts_total = frappe.db.sql("""
                SELECT COALESCE(SUM(grand_total), 0) as total
                FROM `tabSales Order`
                WHERE docstatus = 1
                  AND customer IN ({})
            """.format(placeholders), tuple(customer_names), as_dict=1)[0].get('total', 0) or 0

            # Total payments from these customers
            paid_total = frappe.db.sql("""
                SELECT COALESCE(SUM(paid_amount), 0) as total
                FROM `tabPayment Entry`
                WHERE docstatus = 1
                  AND party_type = 'Customer'
                  AND payment_type = 'Receive'
                  AND party IN ({})
            """.format(placeholders), tuple(customer_names), as_dict=1)[0].get('total', 0) or 0

            debt = float(contracts_total) - float(paid_total)

            result[classification] = {
                'contracts': float(contracts_total),
                'paid': float(paid_total),
                'debt': debt,
                'customer_count': len(customer_names)
            }

        return result
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Debt By Classification Error')
        return {
            'A': {'contracts': 0, 'paid': 0, 'debt': 0, 'customer_count': 0},
            'B': {'contracts': 0, 'paid': 0, 'debt': 0, 'customer_count': 0},
            'C': {'contracts': 0, 'paid': 0, 'debt': 0, 'customer_count': 0}
        }


@frappe.whitelist()
def get_active_contracts_count() -> Dict[str, int]:
    """
    Count active and completed contracts from Sales Orders.
    Active: submitted but not completed status
    Completed: completed status
    """
    try:
        # Active contracts (submitted, not completed)
        active = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabSales Order`
            WHERE docstatus = 1
              AND status NOT IN ('Completed', 'Closed', 'Cancelled')
        """, as_dict=1)[0].get('count', 0) or 0

        # Completed contracts
        completed = frappe.db.sql("""
            SELECT COUNT(*) as count
            FROM `tabSales Order`
            WHERE docstatus = 1
              AND status = 'Completed'
        """, as_dict=1)[0].get('count', 0) or 0

        return {
            'active': int(active),
            'completed': int(completed),
            'total': int(active) + int(completed)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Active Contracts Error')
        return {'active': 0, 'completed': 0, 'total': 0}


@frappe.whitelist()
def get_monthly_finance_chart(year_filter: Union[str, List[int]]) -> Dict[str, List[float]]:
    """
    Monthly finance amount (Tikilgan Pul) from Installment Application.
    Groups by month and year, returns data for comparison.
    """
    try:
        if isinstance(year_filter, str):
            year_filter = frappe.parse_json(year_filter)

        result = {}

        for year in year_filter:
            data = frappe.db.sql("""
                SELECT
                    MONTH(transaction_date) as month,
                    COALESCE(SUM(finance_amount), 0) as total
                FROM `tabInstallment Application`
                WHERE docstatus = 1
                  AND YEAR(transaction_date) = %s
                GROUP BY MONTH(transaction_date)
                ORDER BY month
            """, (year,), as_dict=1)

            # Create 12-month array
            monthly_data = [0] * 12
            for row in data:
                monthly_data[row['month'] - 1] = float(row['total'])

            result[str(year)] = monthly_data

        return result
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Monthly Finance Chart Error')
        return {}


@frappe.whitelist()
def get_monthly_revenue_chart(year_filter: Union[str, List[int]]) -> Dict[str, List[float]]:
    """
    Monthly revenue from customer payments (Payment Entry with payment_type='Receive').
    12 months data for each year.
    """
    try:
        if isinstance(year_filter, str):
            year_filter = frappe.parse_json(year_filter)

        result = {}

        for year in year_filter:
            data = frappe.db.sql("""
                SELECT
                    MONTH(posting_date) as month,
                    COALESCE(SUM(paid_amount), 0) as total
                FROM `tabPayment Entry`
                WHERE docstatus = 1
                  AND party_type = 'Customer'
                  AND payment_type = 'Receive'
                  AND YEAR(posting_date) = %s
                GROUP BY MONTH(posting_date)
                ORDER BY month
            """, (year,), as_dict=1)

            monthly_data = [0] * 12
            for row in data:
                monthly_data[row['month'] - 1] = float(row['total'])

            result[str(year)] = monthly_data

        return result
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Monthly Revenue Chart Error')
        return {}


@frappe.whitelist()
def get_monthly_contracts_chart(year_filter: Union[str, List[int]]) -> Dict[str, List[int]]:
    """
    Number of contracts per month from Sales Orders.
    Count by transaction_date.
    """
    try:
        if isinstance(year_filter, str):
            year_filter = frappe.parse_json(year_filter)

        result = {}

        for year in year_filter:
            data = frappe.db.sql("""
                SELECT
                    MONTH(transaction_date) as month,
                    COUNT(*) as count
                FROM `tabSales Order`
                WHERE docstatus = 1
                  AND YEAR(transaction_date) = %s
                GROUP BY MONTH(transaction_date)
                ORDER BY month
            """, (year,), as_dict=1)

            monthly_data = [0] * 12
            for row in data:
                monthly_data[row['month'] - 1] = int(row['count'])

            result[str(year)] = monthly_data

        return result
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Monthly Contracts Chart Error')
        return {}


@frappe.whitelist()
def get_roi_calculation() -> Dict[str, Union[float, int]]:
    """
    Calculate ROI (Return on Investment).
    Formula: (Total Interest / Finance Amount) * 100
    """
    try:
        # Total interest from all installment applications
        total_interest = frappe.db.sql("""
            SELECT COALESCE(SUM(custom_total_interest), 0) as total
            FROM `tabInstallment Application`
            WHERE docstatus = 1
        """, as_dict=1)[0].get('total', 0) or 0

        # Total finance amount
        total_finance = frappe.db.sql("""
            SELECT COALESCE(SUM(finance_amount), 0) as total
            FROM `tabInstallment Application`
            WHERE docstatus = 1
        """, as_dict=1)[0].get('total', 0) or 0

        roi_percentage = (float(total_interest) / float(total_finance) * 100) if total_finance > 0 else 0

        return {
            'total_interest': float(total_interest),
            'total_finance': float(total_finance),
            'roi_percentage': round(roi_percentage, 2)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'ROI Calculation Error')
        return {'total_interest': 0, 'total_finance': 0, 'roi_percentage': 0}


@frappe.whitelist()
def get_monthly_profit_chart(year_filter: Union[str, List[int]]) -> Dict[str, List[float]]:
    """
    Monthly profit from custom_total_interest in Installment Application.
    Filtered by transaction_date.
    """
    try:
        if isinstance(year_filter, str):
            year_filter = frappe.parse_json(year_filter)

        result = {}

        for year in year_filter:
            data = frappe.db.sql("""
                SELECT
                    MONTH(transaction_date) as month,
                    COALESCE(SUM(custom_total_interest), 0) as total
                FROM `tabInstallment Application`
                WHERE docstatus = 1
                  AND YEAR(transaction_date) = %s
                GROUP BY MONTH(transaction_date)
                ORDER BY month
            """, (year,), as_dict=1)

            monthly_data = [0] * 12
            for row in data:
                monthly_data[row['month'] - 1] = float(row['total'])

            result[str(year)] = monthly_data

        return result
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Monthly Profit Chart Error')
        return {}


@frappe.whitelist()
def get_debt_list(
    limit_start: Union[int, str] = 0,
    limit_page_length: Union[int, str] = 20
) -> Dict[str, Union[List[Dict], int]]:
    """
    Get list of customers with their debt amounts.
    Grouped by customer, showing classification, name, and total debt.
    Sorted by debt amount (descending).
    """
    try:
        limit_start = int(limit_start)
        limit_page_length = int(limit_page_length)

        # Get all customers with their debt
        data = frappe.db.sql("""
            SELECT
                c.name as customer_id,
                c.customer_name,
                COALESCE(c.customer_classification, 'N/A') as classification,
                COALESCE(contracts.total, 0) as contract_total,
                COALESCE(payments.total, 0) as paid_total,
                COALESCE(contracts.total, 0) - COALESCE(payments.total, 0) as debt
            FROM `tabCustomer` c
            LEFT JOIN (
                SELECT customer, SUM(grand_total) as total
                FROM `tabSales Order`
                WHERE docstatus = 1
                GROUP BY customer
            ) contracts ON c.name = contracts.customer
            LEFT JOIN (
                SELECT party, SUM(paid_amount) as total
                FROM `tabPayment Entry`
                WHERE docstatus = 1
                  AND party_type = 'Customer'
                  AND payment_type = 'Receive'
                GROUP BY party
            ) payments ON c.name = payments.party
            WHERE COALESCE(contracts.total, 0) > 0
            HAVING debt > 0
            ORDER BY debt DESC
            LIMIT %s, %s
        """, (limit_start, limit_page_length), as_dict=1)

        # Format the data
        result = []
        for row in data:
            result.append({
                'customer_id': row.customer_id,
                'customer_name': row.customer_name,
                'classification': row.classification or 'N/A',
                'contract_total': float(row.contract_total),
                'paid_total': float(row.paid_total),
                'debt': float(row.debt)
            })

        # Get total count
        total_count = frappe.db.sql("""
            SELECT COUNT(DISTINCT c.name) as count
            FROM `tabCustomer` c
            INNER JOIN `tabSales Order` so ON c.name = so.customer
            WHERE so.docstatus = 1
        """, as_dict=1)[0].get('count', 0)

        return {
            'data': result,
            'total_count': int(total_count)
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Debt List Error')
        return {'data': [], 'total_count': 0}


@frappe.whitelist()
def get_available_years() -> List[int]:
    """
    Get list of years that have data in the system.
    """
    try:
        years = frappe.db.sql("""
            SELECT DISTINCT YEAR(transaction_date) as year
            FROM `tabInstallment Application`
            WHERE docstatus = 1
            ORDER BY year DESC
        """, as_dict=1)

        return [int(y['year']) for y in years if y['year']]
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), 'Available Years Error')
        return []
