#!/usr/bin/env python3
"""
Hide unnecessary fields in Payment Entry for Pay type
- Taxes section
- Transaction ID section (Cheque/Reference fields)
- Account balances (already hidden for Receive)
"""
import frappe

def hide_payment_entry_pay_fields():
    fields_to_hide = [
        # Transaction ID section - not needed for simple cash payments
        "reference_no",
        "reference_date",
        "clearance_date",
        
        # Additional fields from Receive that should also be hidden
        # (these were already done, but ensuring consistency)
        "taxes",
        "apply_tax_withholding_amount",
        "tax_withholding_category",
        "base_total_taxes_and_charges",
        "total_taxes_and_charges",
        
        # Account balances - confusing for operator
        "paid_from_account_balance",
        "paid_to_account_balance",
        
        # Currency fields - USD only system
        "paid_from_account_currency",
        "paid_to_account_currency",
        
        # Advanced fields not needed
        "cost_center",
        "project",
        "letter_head",
    "print_heading",
    ]
    
    created_count = 0
    existing_count = 0
    
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
            created_count += 1
        else:
            existing_count += 1
    
    # Also hide "paid_from" account field label description to make it clearer
    # We'll keep the field visible but make it read-only since it defaults to Cash - A
    
    print(f"\n=== Summary ===")
    print(f"✅ Newly hidden: {created_count}")
    print(f"⏭️  Already hidden: {existing_count}")
    print(f"Total fields: {len(fields_to_hide)}")
    
    frappe.db.commit()
    print("\n✅ Payment Entry (Pay type) cleanup completed!")

if __name__ == "__main__":
    hide_payment_entry_pay_fields()
