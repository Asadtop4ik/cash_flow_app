"""
Add custom_payment_schedule_row field to Payment Entry
This links a payment to a specific payment schedule row
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def add_payment_schedule_field():
    """Add custom_payment_schedule_row field to Payment Entry"""
    
    custom_fields = {
        "Payment Entry": [
            {
                "fieldname": "custom_payment_schedule_row",
                "label": "Payment Schedule Row",
                "fieldtype": "Link",
                "options": "Payment Schedule",
                "insert_after": "custom_contract_reference",
                "read_only": 0,
                "hidden": 0,
                "description": "Which payment schedule row this payment is for (e.g., Month 1, Month 2)",
                "depends_on": "eval:doc.custom_contract_reference"
            },
            {
                "fieldname": "custom_payment_month",
                "label": "Payment Month",
                "fieldtype": "Data",
                "insert_after": "custom_payment_schedule_row",
                "read_only": 1,
                "hidden": 0,
                "description": "Display which month payment this is",
                "depends_on": "eval:doc.custom_contract_reference"
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
    
    print("✅ Added custom_payment_schedule_row field to Payment Entry")

if __name__ == "__main__":
    add_payment_schedule_field()
