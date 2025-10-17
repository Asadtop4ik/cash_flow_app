app_name = "cash_flow_app"
app_title = "Cash Flow Management"
app_publisher = "AsadStack"
app_description = "USD-only cash and installment management for ERPNext"
app_email = "asadbek.backend@gmail.com"
app_license = "mit"

doc_events = {
    "Item": {
        "before_save": "cash_flow_app.cash_flow_management.overrides.item_hooks.before_save_item",
        "validate": "cash_flow_app.cash_flow_management.overrides.item_hooks.validate_item"
    },
    "Payment Entry": {
        "autoname": "cash_flow_app.cash_flow_management.overrides.payment_entry_hooks.autoname_payment_entry",
        "onload": "cash_flow_app.cash_flow_management.overrides.payment_entry_defaults.onload_payment_entry",
        "validate": [
            "cash_flow_app.cash_flow_management.overrides.payment_entry_hooks.validate_payment_entry",
            "cash_flow_app.cash_flow_management.custom.payment_validations.validate_negative_balance",
            "cash_flow_app.cash_flow_management.custom.payment_validations.warn_on_overdue_payments"
        ],
        "on_submit": "cash_flow_app.cash_flow_management.overrides.payment_entry_linkage.on_submit_payment_entry",
        "on_cancel": "cash_flow_app.cash_flow_management.overrides.payment_entry_linkage.on_cancel_payment_entry"
    },
    "Sales Order": {
        "validate": "cash_flow_app.cash_flow_management.custom.payment_validations.validate_payment_schedule_paid_amount"
    }
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
    "Sales Order": "public/js/sales_order.js",
    "Payment Entry": "public/js/payment_entry.js",
    "Customer": "public/js/customer.js"
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
    {
        "dt": "Property Setter",
        "filters": [
            [
                "name", "in", [
                    # Customer fields
                    "Customer-salutation-hidden",
                    "Customer-auto_repeat_detail-hidden",
                    "Customer-customer_group-hidden",
                    "Customer-territory-hidden",
                    "Customer-sales_team-hidden",
                    "Customer-account_manager-hidden",
                    "Customer-default_currency-hidden",
                    "Customer-default_bank_account-hidden",
                    "Customer-default_price_list-hidden",
                    "Customer-internal_customer-hidden",
                    "Customer-represents_company-hidden",
                    "Customer-companies-hidden",
                    "Customer-default_company-hidden",
                    "Customer-internal_customer_section-hidden",
                    "Customer-more_info-hidden",
                    "Customer-lead_name-hidden",
                    "Customer-opportunity_name-hidden",
                    "Customer-prospect_name-hidden",
                    "Customer-custom_auto_debit-hidden",
                    # Item fields - tabs
                    "Item-dashboard_tab-hidden",
                    "Item-inventory_section-hidden",
                    "Item-variants_section-hidden",
                    "Item-accounting-hidden",
                    "Item-purchasing_tab-hidden",
                    "Item-sales_details-hidden",
                    "Item-item_tax_section_break-hidden",
                    "Item-quality_tab-hidden",
                    # Item fields - hide ALL default fields
                    "Item-naming_series-hidden",
                    "Item-item_code-hidden",
                    "Item-item_name-hidden",
                    "Item-item_group-hidden",
                    "Item-stock_uom-hidden",
                    "Item-disabled-hidden",
                    "Item-allow_alternative_item-hidden",
                    "Item-is_stock_item-hidden",
                    "Item-has_variants-hidden",
                    "Item-opening_stock-hidden",
                    "Item-valuation_rate-hidden",
                    "Item-standard_rate-hidden",
                    "Item-is_fixed_asset-hidden",
                    "Item-auto_create_assets-hidden",
                    "Item-is_grouped_asset-hidden",
                    "Item-asset_category-hidden",
                    "Item-asset_naming_series-hidden",
                    "Item-over_delivery_receipt_allowance-hidden",
                    "Item-over_billing_allowance-hidden",
                    "Item-image-hidden",
                    "Item-section_break_11-hidden",
                    "Item-description-hidden",
                    "Item-brand-hidden",
                    "Item-unit_of_measure_conversion-hidden",
                    "Item-uoms-hidden"
                ]
            ]
        ]
    }
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

