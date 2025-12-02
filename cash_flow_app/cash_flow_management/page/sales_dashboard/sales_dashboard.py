# cash_flow_app/cash_flow_management/page/sales_dashboard/sales_dashboard.py

import frappe


def get_context(context):
	"""
	Sales Dashboard page context
	"""
	context.no_cache = 1
	context.show_sidebar = False

	return context
