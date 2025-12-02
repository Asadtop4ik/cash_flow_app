import frappe
from frappe import _
from datetime import datetime, timedelta


@frappe.whitelist()
def get_dashboard_data(party_type=None, group_name=None):
    """
    Returns dashboard data. Optional filters:
      - party_type: 'Customer' or 'Supplier'
      - group_name: name of the group to filter by
    """
    try:
        return {
            'kpi': get_kpi_data(party_type=party_type, group_name=group_name),
            'monthly_trends': get_monthly_trends(party_type=party_type, group_name=group_name),
            'top_customers': get_top_customers(party_type=party_type, group_name=group_name),
            'payment_statistics': get_payment_statistics(party_type=party_type, group_name=group_name),
            'product_sales': get_product_sales(),
            'status_breakdown': get_status_breakdown(),
            'recent_applications': get_recent_applications(party_type=party_type, group_name=group_name),
            'payment_timeline': get_payment_timeline(party_type=party_type, group_name=group_name)
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'Dashboard Data Error')
        return {"error": "Failed to load dashboard data"}


@frappe.whitelist()
def get_party_groups(party_type):
    """
    Return list of groups for the given party_type ('Customer' or 'Supplier')
    """
    try:
        if not party_type:
            return []
        if party_type.lower() == 'customer':
            groups = frappe.db.sql("SELECT name FROM `tabCustomer Group` ORDER BY name", as_dict=1)
        elif party_type.lower() == 'supplier':
            groups = frappe.db.sql("SELECT name FROM `tabSupplier Group` ORDER BY name", as_dict=1)
        else:
            return []

        return [g.get('name') for g in groups]
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'Party Groups Error')
        return []


def _build_ia_filters(party_type, group_name):
    """Helper - returns SQL filter string and params for Installment Application queries"""
    filters = "WHERE ia.docstatus = 1"
    params = {}
    if party_type and group_name:
        if party_type.lower() == 'customer':
            filters += " AND ia.customer_group = %(group)s"
            params['group'] = group_name
        elif party_type.lower() == 'supplier':
            filters += " AND ia.supplier_group = %(group)s"
            params['group'] = group_name
    return filters, params


@frappe.whitelist()
def get_kpi_data(party_type=None, group_name=None):
    """KPI numbers with optional filtering by group"""
    try:
        filters, params = _build_ia_filters(party_type, group_name)

        total_contracts = frappe.db.sql(f"""
            SELECT
                COUNT(*) as count,
                SUM(total_amount) as total_amount,
                SUM(finance_amount) as finance_amount,
                SUM(downpayment_amount) as downpayment,
                SUM(total_amount) as total_with_interest
            FROM `tabInstallment Application` ia
            {filters}
        """, params, as_dict=1)[0] or {}

        # Payments: if filters present join to IA to scope payments
        if params:
            total_paid = frappe.db.sql(f"""
                SELECT
                    COUNT(pe.name) as payment_count,
                    SUM(pe.paid_amount) as total_paid
                FROM `tabPayment Entry` pe
                LEFT JOIN `tabInstallment Application` ia ON pe.custom_installment_application = ia.name
                WHERE pe.docstatus = 1
                  AND ia.name IS NOT NULL
                  AND ({'ia.customer_group = %(group)s' if party_type.lower() == 'customer' else 'ia.supplier_group = %(group)s'})
            """, params, as_dict=1)[0] or {}
        else:
            total_paid = frappe.db.sql("""
                SELECT
                    COUNT(*) as payment_count,
                    SUM(paid_amount) as total_paid
                FROM `tabPayment Entry`
                WHERE docstatus = 1
            """, as_dict=1)[0] or {}

        outstanding = (total_contracts.get('finance_amount') or 0) - (total_paid.get('total_paid') or 0)
        growth = calculate_growth()

        avg_monthly = frappe.db.sql("""
            SELECT AVG(monthly_payment) as avg_payment
            FROM `tabInstallment Application`
            WHERE docstatus = 1
        """, as_dict=1)[0].get('avg_payment', 0) or 0

        return {
            'total_earnings': float(total_contracts.get('total_with_interest') or 0),
            'total_contracts': int(total_contracts.get('count') or 0),
            'total_paid': float(total_paid.get('total_paid') or 0),
            'outstanding_amount': float(outstanding or 0),
            'downpayment_collected': float(total_contracts.get('downpayment') or 0),
            'payment_count': int(total_paid.get('payment_count') or 0),
            'growth_percentage': float(growth or 0),
            'avg_monthly_payment': float(avg_monthly or 0)
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'KPI Data Error')
        return {
            'total_earnings': 0,
            'total_contracts': 0,
            'total_paid': 0,
            'outstanding_amount': 0,
            'downpayment_collected': 0,
            'payment_count': 0,
            'growth_percentage': 0,
            'avg_monthly_payment': 0
        }


@frappe.whitelist()
def get_monthly_trends(party_type=None, group_name=None):
    """Return monthly contract and payment trends (last 12 months)"""
    try:
        filters, params = _build_ia_filters(party_type, group_name)
        # Add date constraint
        filters = filters.replace('WHERE', "WHERE transaction_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH) AND")

        data = frappe.db.sql(f"""
            SELECT
                DATE_FORMAT(transaction_date, '%Y-%m') as month,
                COUNT(*) as contract_count,
                SUM(total_amount) as total_amount,
                SUM(finance_amount) as finance_amount,
                SUM(downpayment_amount) as downpayment
            FROM `tabInstallment Application` ia
            {filters}
            GROUP BY month
            ORDER BY month
        """, params, as_dict=1) or []

        # Payments: join to IA if filtering by group, otherwise aggregate directly
        if params:
            payments = frappe.db.sql(f"""
                SELECT
                    DATE_FORMAT(pe.posting_date, '%Y-%m') as month,
                    COUNT(pe.name) as payment_count,
                    SUM(pe.paid_amount) as paid_amount
                FROM `tabPayment Entry` pe
                LEFT JOIN `tabInstallment Application` ia ON pe.custom_installment_application = ia.name
                WHERE pe.docstatus = 1
                  AND pe.posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                  AND ia.name IS NOT NULL
                  AND ({'ia.customer_group = %(group)s' if party_type.lower() == 'customer' else 'ia.supplier_group = %(group)s'})
                GROUP BY month
                ORDER BY month
            """, params, as_dict=1) or []
        else:
            payments = frappe.db.sql("""
                SELECT
                    DATE_FORMAT(posting_date, '%Y-%m') as month,
                    COUNT(*) as payment_count,
                    SUM(paid_amount) as paid_amount
                FROM `tabPayment Entry`
                WHERE docstatus = 1
                  AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                GROUP BY month
                ORDER BY month
            """, as_dict=1) or []

        months_dict = {}
        for item in data:
            months_dict[item['month']] = {
                'month': item['month'],
                'contracts': item['contract_count'],
                'revenue': float(item['total_amount'] or 0),
                'finance': float(item['finance_amount'] or 0),
                'downpayment': float(item['downpayment'] or 0),
                'payments': 0
            }

        for payment in payments:
            if payment['month'] in months_dict:
                months_dict[payment['month']]['payments'] = float(payment['paid_amount'] or 0)
            else:
                months_dict[payment['month']] = {
                    'month': payment['month'],
                    'contracts': 0,
                    'revenue': 0,
                    'finance': 0,
                    'downpayment': 0,
                    'payments': float(payment['paid_amount'] or 0)
                }

        return list(months_dict.values())
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'Monthly Trends Error')
        return []


@frappe.whitelist()
def get_top_customers(party_type=None, group_name=None):
    """Top customers by total contract value (filtered by group if provided)"""
    try:
        filters, params = _build_ia_filters(party_type, group_name)
        data = frappe.db.sql(f"""
            SELECT
                ia.customer,
                ia.customer_name,
                COUNT(*) as contract_count,
                SUM(ia.total_amount) as total_value,
                SUM(ia.finance_amount) as finance_amount
            FROM `tabInstallment Application` ia
            {filters}
            GROUP BY ia.customer
            ORDER BY total_value DESC
            LIMIT 10
        """, params, as_dict=1) or []
        return data
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'Top Customers Error')
        return []


@frappe.whitelist()
def get_payment_statistics(party_type=None, group_name=None):
    """Paid vs unpaid statistics (supports group filtering)"""
    try:
        filters, params = _build_ia_filters(party_type, group_name)
        # total expected from IA
        total_expected = frappe.db.sql(f"""
            SELECT SUM(ia.finance_amount) as total
            FROM `tabInstallment Application` ia
            {filters}
        """, params, as_dict=1)[0].get('total') or 0

        # total paid: if filtering, join payments to IA
        if params:
            total_paid = frappe.db.sql(f"""
                SELECT SUM(pe.paid_amount) as total
                FROM `tabPayment Entry` pe
                LEFT JOIN `tabInstallment Application` ia ON pe.custom_installment_application = ia.name
                WHERE pe.docstatus = 1
                  AND ia.name IS NOT NULL
                  AND ({'ia.customer_group = %(group)s' if party_type.lower() == 'customer' else 'ia.supplier_group = %(group)s'})
            """, params, as_dict=1)[0].get('total') or 0
        else:
            total_paid = frappe.db.sql("""
                SELECT SUM(paid_amount) as total
                FROM `tabPayment Entry`
                WHERE docstatus = 1
            """, as_dict=1)[0].get('total') or 0

        unpaid = max(0, (total_expected or 0) - (total_paid or 0))
        paid_percentage = (total_paid / total_expected * 100) if total_expected > 0 else 0
        unpaid_percentage = 100 - paid_percentage

        return {
            'paid': float(total_paid or 0),
            'unpaid': float(unpaid),
            'paid_percentage': round(paid_percentage, 2),
            'unpaid_percentage': round(unpaid_percentage, 2),
            'total_expected': float(total_expected or 0)
        }
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'Payment Statistics Error')
        return {
            'paid': 0,
            'unpaid': 0,
            'paid_percentage': 0,
            'unpaid_percentage': 0,
            'total_expected': 0
        }


@frappe.whitelist()
def get_product_sales():
    """Top product sales"""
    data = frappe.db.sql("""
        SELECT
            soi.item_code,
            soi.item_name,
            COUNT(DISTINCT so.name) as sales_count,
            SUM(soi.amount) as total_sales,
            AVG(soi.rate) as avg_price
        FROM `tabSales Order Item` soi
        LEFT JOIN `tabSales Order` so ON soi.parent = so.name
        WHERE so.docstatus = 1
          AND soi.item_name NOT LIKE '%Foiz%'
          AND soi.item_name NOT LIKE '%Interest%'
        GROUP BY soi.item_code
        ORDER BY total_sales DESC
        LIMIT 10
    """, as_dict=1)
    return data


@frappe.whitelist()
def get_status_breakdown():
    data = frappe.db.sql("""
        SELECT
            status,
            COUNT(*) as count,
            SUM(total_amount) as total_amount
        FROM `tabInstallment Application`
        GROUP BY status
    """, as_dict=1)
    return data


@frappe.whitelist()
def get_recent_applications(party_type=None, group_name=None):
    """Return recent applications optionally filtered by group"""
    try:
        filters, params = _build_ia_filters(party_type, group_name)
        data = frappe.db.sql(f"""
            SELECT
                name,
                customer_name,
                transaction_date,
                total_amount,
                finance_amount,
                monthly_payment,
                installment_months,
                workflow_state as status
            FROM `tabInstallment Application` ia
            {filters}
            ORDER BY transaction_date DESC
            LIMIT 10
        """, params, as_dict=1) or []
        return data
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'Recent Applications Error')
        return []


@frappe.whitelist()
def get_payment_timeline(party_type=None, group_name=None):
    """Payments timeline (last 30 days) optionally filtered by group"""
    try:
        if party_type and group_name:
            # join to IA and filter
            data = frappe.db.sql(f"""
                SELECT
                    pe.name,
                    pe.posting_date,
                    pe.party_name,
                    pe.paid_amount,
                    pe.custom_installment_application,
                    ia.customer_name
                FROM `tabPayment Entry` pe
                LEFT JOIN `tabInstallment Application` ia ON pe.custom_installment_application = ia.name
                WHERE pe.docstatus = 1
                  AND pe.posting_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                  AND ia.name IS NOT NULL
                  AND ({'ia.customer_group = %(group)s' if party_type.lower() == 'customer' else 'ia.supplier_group = %(group)s'})
                ORDER BY pe.posting_date DESC
            """, {'group': group_name}, as_dict=1) or []
        else:
            data = frappe.db.sql("""
                SELECT
                    pe.name,
                    pe.posting_date,
                    pe.party_name,
                    pe.paid_amount,
                    pe.custom_installment_application,
                    ia.customer_name
                FROM `tabPayment Entry` pe
                LEFT JOIN `tabInstallment Application` ia
                    ON pe.custom_installment_application = ia.name
                WHERE pe.docstatus = 1
                  AND pe.posting_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                ORDER BY pe.posting_date DESC
            """, as_dict=1) or []

        return data
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'Payment Timeline Error')
        return []


def calculate_growth():
    """Growth percent last 30 days vs previous"""
    try:
        current = frappe.db.sql("""
            SELECT SUM(total_amount) as total
            FROM `tabInstallment Application`
            WHERE docstatus = 1
              AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """, as_dict=1)[0].get('total', 0) or 0

        previous = frappe.db.sql("""
            SELECT SUM(total_amount) as total
            FROM `tabInstallment Application`
            WHERE docstatus = 1
              AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
              AND transaction_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """, as_dict=1)[0].get('total', 0) or 0

        if previous > 0:
            growth = ((current - previous) / previous) * 100
            return round(growth, 2)
        return 0
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'Calculate Growth Error')
        return 0


@frappe.whitelist()
def get_average_payment_duration():
    """Average installment months"""
    try:
        data = frappe.db.sql("""
            SELECT
                AVG(installment_months) as avg_months,
                MIN(installment_months) as min_months,
                MAX(installment_months) as max_months
            FROM `tabInstallment Application`
            WHERE docstatus = 1
        """, as_dict=1)[0]
        return data
    except Exception:
        frappe.log_error(frappe.get_traceback(), 'Average Payment Duration Error')
        return {}
