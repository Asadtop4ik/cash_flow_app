"""
Script to create custom fields for Item DocType
Run with: bench --site asadstack.com execute cash_flow_app.scripts.setup_item_custom_fields.run
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    """Create custom fields for Item DocType"""
    
    custom_fields = {
        "Item": [
            {
                "fieldname": "custom_product_name",
                "label": "Mahsulot nomi",
                "fieldtype": "Data",
                "insert_after": "item_code",
                "reqd": 1,
                "in_list_view": 1,
                "bold": 1,
                "translatable": 0
            },
            {
                "fieldname": "custom_imei",
                "label": "IMEI",
                "fieldtype": "Data",
                "insert_after": "custom_product_name",
                "reqd": 0,
                "in_list_view": 1,
                "translatable": 0
            },
            {
                "fieldname": "custom_price_usd",
                "label": "Narx (USD)",
                "fieldtype": "Currency",
                "insert_after": "custom_imei",
                "reqd": 1,
                "in_list_view": 1,
                "bold": 1,
                "options": "USD",
                "precision": "2"
            },
            {
                "fieldname": "custom_icloud",
                "label": "iCloud",
                "fieldtype": "Data",
                "insert_after": "custom_price_usd",
                "reqd": 0,
                "translatable": 0
            },
            {
                "fieldname": "custom_phone_number",
                "label": "Telefon raqam",
                "fieldtype": "Data",
                "insert_after": "custom_icloud",
                "reqd": 0,
                "translatable": 0
            },
            {
                "fieldname": "custom_notes",
                "label": "Izoh",
                "fieldtype": "Text",
                "insert_after": "custom_phone_number",
                "reqd": 0,
                "translatable": 0
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    
    print("\n✅ All Item custom fields created successfully!")
