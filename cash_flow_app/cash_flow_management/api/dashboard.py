import frappe
from frappe import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


@frappe.whitelist()
def get_dashboard_data(year_filter=None):
	"""
	Returns comprehensive dashboard data with multi-year comparison
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
		return {"error": str(e)}


@frappe.whitelist()
def get_shareholder_capital():
	"""
	Calculate total capital from shareholders
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
def get_debt_summary():
	"""
	Calculate total debt from all customers
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
		payment_percentage = (
				float(total_paid) / float(total_contracts) * 100) if total_contracts > 0 else 0

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
def get_debt_by_classification():
	"""
	Calculate debt for each customer classification (A, B, C)
	Formula: For each classification, SUM(contracts) - SUM(payments received)
	"""
	try:
		classifications = ['A', 'B', 'C']
		result = {}

		for classification in classifications:
			# Get all customers with this classification
			# Note: field is customer_classification NOT custom_classification
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
			contracts_total = frappe.db.sql("""
                SELECT COALESCE(SUM(grand_total), 0) as total
                FROM `tabSales Order`
                WHERE docstatus = 1
                  AND customer IN ({})
            """.format(','.join(['%s'] * len(customer_names))),
											tuple(customer_names), as_dict=1)[0].get('total',
																					 0) or 0

			# Total payments from these customers
			paid_total = frappe.db.sql("""
                SELECT COALESCE(SUM(paid_amount), 0) as total
                FROM `tabPayment Entry`
                WHERE docstatus = 1
                  AND party_type = 'Customer'
                  AND payment_type = 'Receive'
                  AND party IN ({})
            """.format(','.join(['%s'] * len(customer_names))),
									   tuple(customer_names), as_dict=1)[0].get('total', 0) or 0

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
		return {'A': {'contracts': 0, 'paid': 0, 'debt': 0, 'customer_count': 0},
				'B': {'contracts': 0, 'paid': 0, 'debt': 0, 'customer_count': 0},
				'C': {'contracts': 0, 'paid': 0, 'debt': 0, 'customer_count': 0}}


@frappe.whitelist()
def get_active_contracts_count():
	"""
	Count active and completed contracts from Sales Orders
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
def get_monthly_finance_chart(year_filter):
	"""
	Monthly finance amount (Tikilgan Pul) from Installment Application
	Groups by month and year, returns data for comparison
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
def get_monthly_revenue_chart(year_filter):
	"""
	Monthly revenue from customer payments (Payment Entry with payment_type='Receive')
	12 months data for each year
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
def get_monthly_contracts_chart(year_filter):
	"""
	Number of contracts per month from Sales Orders
	Count by transaction_date
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
def get_roi_calculation():
	"""
	Calculate ROI (Return on Investment)
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

		roi_percentage = (
				float(total_interest) / float(total_finance) * 100) if total_finance > 0 else 0

		return {
			'total_interest': float(total_interest),
			'total_finance': float(total_finance),
			'roi_percentage': round(roi_percentage, 2)
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'ROI Calculation Error')
		return {'total_interest': 0, 'total_finance': 0, 'roi_percentage': 0}


@frappe.whitelist()
def get_monthly_profit_chart(year_filter):
	"""
	Monthly profit from custom_total_interest in Installment Application
	Filtered by transaction_date
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
def get_debt_list(limit_start=0, limit_page_length=20):
	"""
	Get list of customers with their debt amounts
	Grouped by customer, showing classification, name, and total debt
	Sorted by debt amount (descending)
	"""
	try:
		# Get all customers with their debt
		# Note: field is customer_classification NOT custom_classification
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
def get_available_years():
	"""
	Get list of years that have data in the system
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
