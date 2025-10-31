app_name = "cash_flow_app"
app_title = "Cash Flow Management"
app_publisher = "AsadStack"
app_description = "USD-only cash and installment management for ERPNext"
app_email = "asadbek.backend@gmail.com"
app_license = "mit"

doc_events = {
    "Item": {
        "before_naming": "cash_flow_app.cash_flow_management.overrides.item_autoname.autoname_item",
        "before_save": "cash_flow_app.cash_flow_management.overrides.item_hooks.before_save_item",
        "validate": "cash_flow_app.cash_flow_management.overrides.item_hooks.validate_item",
        "on_update": "cash_flow_app.cash_flow_management.overrides.item_update_sync.on_update_item"
    },
    "Installment Application": {
        "on_submit": [
            "cash_flow_app.cash_flow_management.custom.supplier_debt_tracking.update_supplier_debt_on_submit",
            "cash_flow_app.cash_flow_management.overrides.payment_entry_linkage.on_submit_installment_application"
        ],
        "on_cancel": "cash_flow_app.cash_flow_management.custom.supplier_debt_tracking.update_supplier_debt_on_cancel_installment"
    },
	"Payment Entry": {
		"autoname": "cash_flow_app.cash_flow_management.overrides.payment_entry_hooks.autoname_payment_entry",
		"onload": "cash_flow_app.cash_flow_management.overrides.payment_entry_defaults.onload_payment_entry",
		"validate": [
			"cash_flow_app.cash_flow_management.overrides.payment_entry_hooks.validate_payment_entry",
			"cash_flow_app.cash_flow_management.custom.payment_validations.validate_negative_balance",
			"cash_flow_app.cash_flow_management.custom.payment_validations.warn_on_overdue_payments"
		],
		"on_submit": [
			"cash_flow_app.cash_flow_management.overrides.payment_entry_linkage.on_submit_payment_entry",
			"cash_flow_app.cash_flow_management.api.payment_entry.on_payment_submit",
			"cash_flow_app.cash_flow_management.overrides.payment_entry_linkage.publish_customer_dashboard_refresh",
			"cash_flow_app.cash_flow_management.custom.supplier_debt_tracking.update_supplier_debt_on_payment"
		],
		"on_cancel": [
			"cash_flow_app.cash_flow_management.overrides.payment_entry_linkage.on_cancel_payment_entry",
			"cash_flow_app.cash_flow_management.custom.supplier_debt_tracking.update_supplier_debt_on_cancel_payment"

		]
    },
    "Sales Order": {
        "validate": "cash_flow_app.cash_flow_management.custom.payment_validations.validate_payment_schedule_paid_amount",
        "before_cancel": "cash_flow_app.cash_flow_management.overrides.payment_entry_linkage.on_cancel_sales_order"
    }
}

reports = {
    "Customer Payment Report": "cash_flow_app.cash_flow_management.report.customer_payment.all_customer_payment"
}

# Scheduled jobs (opsional - daily classification update)
scheduler_events = {
    "daily": [
        "cash_flow_app.cash_flow_management.api.payment_entry.update_all_customers_classification"
    ]
}
# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "cash_flow_app",
# 		"logo": "/assets/cash_flow_app/logo.png",
# 		"title": "Cash Flow Management",
# 		"route": "/cash_flow_app",
# 		"has_permission": "cash_flow_app.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/cash_flow_app/css/cash_flow_app.css"
# app_include_js = "/assets/cash_flow_app/js/cash_flow_app.js"

# include js, css files in header of web template
# web_include_css = "/assets/cash_flow_app/css/cash_flow_app.css"
# web_include_js = "/assets/cash_flow_app/js/cash_flow_app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "cash_flow_app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Item": "public/js/item.js",
    "Sales Order": "public/js/sales_order.js",
    "Payment Entry": "public/js/payment_entry.js",
    "Customer": "public/js/customer.js",
    "Supplier": "public/js/supplier.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "cash_flow_app/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "cash_flow_app.utils.jinja_methods",
# 	"filters": "cash_flow_app.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "cash_flow_app.install.before_install"

# Fixtures
# --------

fixtures = [
    {"dt": "Custom Field", "filters": [["dt", "in", [
        "Address",
        "Contact",
        "Customer",
        "Installment Application",
        "Installment Application Item",
        "Item",
        "Payment Entry",
        "Payment Schedule",
        "Print Settings",
        "Sales Order",
        "Supplier"
    ]]]},
    # ❌ REMOVED: Cash Register fixtures - users will create their own cash registers
    # {"dt": "Cash Register"},
    {"dt": "Property Setter", "filters": [["doc_type", "in", [
        "Customer",
        "Delivery Note",
        "Delivery Note Item",
        "Installment Application",
        "Installment Application Item",
        "Item",
        "Item Barcode",
        "Job Card",
        "Material Request",
        "Packed Item",
        "Payment Entry",
        "Pick List",
        "POS Invoice",
        "POS Invoice Item",
        "Purchase Invoice",
        "Purchase Invoice Item",
        "Purchase Order",
        "Purchase Receipt",
        "Purchase Receipt Item",
        "Quotation",
        "Sales Invoice",
        "Sales Invoice Item",
        "Sales Order",
        "Stock Entry",
        "Stock Entry Detail",
        "Stock Reconciliation",
        "Stock Reconciliation Item",
        "Supplier",
        "Supplier Quotation"
    ]]]},
    # ❌ REMOVED: Counterparty Category fixtures - users will create their own categories
    # {"dt": "Counterparty Category"},
    {"dt": "Mode of Payment", "filters": [["name", "in", ["Naqd", "Terminal/Click"]]]},  # Keep Mode of Payment - same everywhere
]
# after_install = "cash_flow_app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "cash_flow_app.uninstall.before_uninstall"
# after_uninstall = "cash_flow_app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "cash_flow_app.utils.before_app_install"
# after_app_install = "cash_flow_app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "cash_flow_app.utils.before_app_uninstall"
# after_app_uninstall = "cash_flow_app.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "cash_flow_app.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"cash_flow_app.tasks.all"
# 	],
# 	"daily": [
# 		"cash_flow_app.tasks.daily"
# 	],
# 	"hourly": [
# 		"cash_flow_app.tasks.hourly"
# 	],
# 	"weekly": [
# 		"cash_flow_app.tasks.weekly"
# 	],
# 	"monthly": [
# 		"cash_flow_app.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "cash_flow_app.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "cash_flow_app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "cash_flow_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["cash_flow_app.utils.before_request"]
# after_request = ["cash_flow_app.utils.after_request"]

# Job Events
# ----------
# before_job = ["cash_flow_app.utils.before_job"]
# after_job = ["cash_flow_app.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"cash_flow_app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

