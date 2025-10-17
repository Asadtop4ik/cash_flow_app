#!/usr/bin/env python3
"""
Hide Account Paid From field in Payment Entry
System only uses Cash - A (default), no need to show
"""
import frappe

def hide_paid_from_account():
    field_name = "paid_from"
    
    print("\n=== Hiding Account Paid From ===")
    
    if not frappe.db.exists("Property Setter", {
        "doctype_or_field": "DocField",
        "doc_type": "Payment Entry",
        "field_name": field_name,
        "property": "hidden"
    }):
        frappe.get_doc({
            "doctype": "Property Setter",
            "doctype_or_field": "DocField",
            "doc_type": "Payment Entry",
            "field_name": field_name,
            "property": "hidden",
            "value": "1",
            "property_type": "Check"
        }).insert(ignore_permissions=True)
        print(f"✅ Hidden: {field_name}")
    else:
        print(f"⏭️  Already hidden: {field_name}")
    
    frappe.db.commit()
    print("\n✅ Account Paid From is now hidden!")
    print("   Default: Cash - A (from Cash Settings)")

if __name__ == "__main__":
    hide_paid_from_account()
