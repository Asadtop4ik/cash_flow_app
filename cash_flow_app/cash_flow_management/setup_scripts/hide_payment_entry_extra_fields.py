#!/usr/bin/env python3
"""
Hide unnecessary fields in Payment Entry
- custom_branch (Filial)
- paid_from_account_currency (Account Currency From - always USD)
- taxes section
- paid_from_account_balance (Account Balance From - confusing for operator)
"""
import frappe

def hide_payment_entry_extra_fields():
    fields_to_hide = [
        # Currency fields - system is USD only
        "paid_from_account_currency",
        "paid_to_account_currency",
        
        # Taxes section - not used in installment payments
        "taxes",
        "apply_tax_withholding_amount",
        "tax_withholding_category",
        "base_total_taxes_and_charges",
        "total_taxes_and_charges",
        
        # Account Balance - confusing, not needed for operator
        "paid_from_account_balance",
        "paid_to_account_balance",
        
        # Advanced fields
        "cost_center",
        "project",
        "letter_head",
        "print_heading",
    ]
    
    for field in fields_to_hide:
        if not frappe.db.exists("Property Setter", {
            "doctype_or_field": "DocField",
            "doc_type": "Payment Entry",
            "field_name": field,
            "property": "hidden"
        }):
            frappe.get_doc({
                "doctype": "Property Setter",
                "doctype_or_field": "DocField",
                "doc_type": "Payment Entry",
                "field_name": field,
                "property": "hidden",
                "value": "1",
                "property_type": "Check"
            }).insert(ignore_permissions=True)
            print(f"✅ Hidden: {field}")
        else:
            print(f"⏭️  Already hidden: {field}")
    
    frappe.db.commit()
    print(f"\n✅ Total {len(fields_to_hide)} fields hidden!")

if __name__ == "__main__":
    hide_payment_entry_extra_fields()
