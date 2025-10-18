#!/usr/bin/env python3
"""Fix Payment Entry custom fields"""
import frappe
from frappe import _

def create_payment_entry_fields():
    frappe.connect()
    
    # Delete existing custom_contract_reference if exists
    existing = frappe.db.exists("Custom Field", {
        "dt": "Payment Entry",
        "fieldname": "custom_contract_reference"
    })
    if existing:
        frappe.delete_doc("Custom Field", existing, force=1)
        print("🗑️  Eski custom_contract_reference o'chirildi")
    
    # Create custom_contract_reference
    doc = frappe.new_doc("Custom Field")
    doc.dt = "Payment Entry"
    doc.fieldname = "custom_contract_reference"
    doc.label = "Shartnoma (Contract)"
    doc.fieldtype = "Link"
    doc.options = "Sales Order"
    doc.insert_after = "party_name"
    doc.depends_on = "eval:doc.party_type=='Customer'"
    doc.bold = 1
    doc.flags.ignore_validate = True
    doc.insert(ignore_permissions=True)
    print("✅ custom_contract_reference yaratildi!")
    
    frappe.db.commit()
    
    # Reload doctype
    frappe.clear_cache(doctype="Payment Entry")
    frappe.reload_doctype("Payment Entry", force=True)
    
    print("\n✅ Payment Entry fieldlari tayyor!")
    print("\nBarcha fieldlar:")
    fields = frappe.get_all("Custom Field",
        filters={"dt": "Payment Entry"},
        fields=["fieldname", "label"],
        order_by="idx"
    )
    for f in fields:
        print(f"  • {f.fieldname:35} - {f.label}")

if __name__ == "__main__":
    create_payment_entry_fields()
