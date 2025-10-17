"""
Setup custom fields for Payment Entry DocType
Adds: counterparty_category, contract_reference, branch
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_payment_entry_custom_fields():
    """Add custom fields to Payment Entry"""
    
    custom_fields = {
        "Payment Entry": [
            {
                "fieldname": "custom_counterparty_category",
                "label": "Counterparty Category",
                "fieldtype": "Link",
                "options": "Counterparty Category",
                "insert_after": "party_name",
                "reqd": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "description": "Kirim/Chiqim kategoriyasi (Klient, Sotuvchi, Xarajat va h.k.)"
            },
            {
                "fieldname": "custom_contract_reference",
                "label": "Shartnoma (Contract)",
                "fieldtype": "Link",
                "options": "Sales Order",
                "insert_after": "custom_counterparty_category",
                "reqd": 0,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "description": "Agar bo'lib to'lash shartnomasi bo'lsa, shu yerda tanlang"
            },
            {
                "fieldname": "custom_branch",
                "label": "Filial",
                "fieldtype": "Data",
                "insert_after": "custom_contract_reference",
                "reqd": 0,
                "description": "Filial nomi (agar bir nechta filial bo'lsa)"
            },
            {
                "fieldname": "custom_section_break_kassa",
                "label": "Kassa Ma'lumotlari",
                "fieldtype": "Section Break",
                "insert_after": "custom_branch",
                "collapsible": 0
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
    
    print("✅ Payment Entry custom fields created successfully!")

if __name__ == "__main__":
    setup_payment_entry_custom_fields()
