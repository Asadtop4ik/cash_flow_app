app_name = "cash_flow_app"
app_title = "Cash Flow Management"
app_publisher = "AsadStack"
app_description = "USD-only cash and installment management for ERPNext"
app_email = "asadbek.backend@gmail.com"
app_license = "mit"

# After migrate hooks - force sync fixtures without migration_hash
after_migrate = [
	"cash_flow_app.utils.fixtures.force_sync_custom_fields",
	"cash_flow_app.utils.fixtures.force_sync_property_setters",
	"cash_flow_app.utils.fixtures.force_sync_docperms",  # Prevent duplicate permissions
]

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

# ============================================
# FIXTURES - DATABASE CUSTOMIZATIONS EXPORT
# ============================================
# Ushbu ro'yxat `bench export-fixtures` komandasi ishga tushganda 
# qaysi ma'lumotlarni JSON ga export qilishni belgilaydi.
# Bu fixtures SERVER bilan LOCAL ni sync qilish uchun ishlatiladi.

fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", ["Operator"]]]
    },
    
    {
        "dt": "DocPerm",
        "filters": [["role", "=", "Operator"]]
    },
    
    # ============================================
    # 2. CUSTOM FIELDS - Module filter (OPTIMAL!)
    # ============================================
    # SABAB: DocType filter ishlatish boshqa module larni ham export qiladi.
    # Masalan: Customer DocType da ERPNext module custom field lari ham bor.
    # Module filter ishlatib, FAQAT bizning app ga tegishli field larni olamiz.
    # 
    # QANDAY ISHLAYDI:
    # - Siz UI da Custom Field yaratganingizda module = "Cash Flow Management" qo'yasiz
    # - Base DocType (Customer, Payment Entry, etc.) ga qo'shishingizdan qat'iy nazar
    # - Barcha "Cash Flow Management" module field lari export bo'ladi
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "Cash Flow Management"]]
    },
    
    # ============================================
    # 3. PROPERTY SETTERS - Field customizations
    # ============================================
    # Audit: 134 ta Property Setter topildi
    # Customer: 24, Item: 42, Payment Entry: 20, Supplier: 34, etc.
    {
        "dt": "Property Setter",
        "filters": [["doc_type", "in", [
            # Audit: Customer (24), Item (42), Payment Entry (20), Supplier (34)
            # Sales Order (11), Installment Application (3)
            "Customer",
            "Installment Application",
            "Item",
            "Payment Entry",
            "Sales Order",
            "Supplier"
        ]]]
    },
    
    # ============================================
    # 4. UOM (Unit of Measure)
    # ============================================
    # Audit: 240 ta UOM bor, faqat "Dona" ni export qilamiz
    {
        "dt": "UOM",
        "filters": [["name", "in", ["Dona"]]]
    },
    
    # ============================================
    # 5. ITEM GROUP
    # ============================================
    # Audit: "Mahsulotlar" custom group topildi
    {
        "dt": "Item Group",
        "filters": [["name", "=", "Mahsulotlar"]]
    },

]

# ❌ REMOVED: Duplicate doctype_js definition below (line 228)
# It was overriding the main doctype_js at line 103
# This caused Customer.js to not load!
