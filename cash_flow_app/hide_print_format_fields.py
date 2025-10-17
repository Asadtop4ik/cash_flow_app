#!/usr/bin/env python3
"""
Hide sensitive business data from Sales Order print format:
1. Interest percentage (custom_interest_percentage) 
2. Product cost prices (custom_cost_price_usd)

Client should only see: Product name, quantity, total amount
"""

import frappe

def hide_print_format_fields():
    """Hide business-sensitive fields from client-facing print formats"""
    
    print("\n" + "="*60)
    print("HIDING SENSITIVE FIELDS FROM PRINT FORMAT")
    print("="*60 + "\n")
    
    # Fields to hide - business-sensitive data
    fields_to_hide = [
        {
            'doctype': 'Sales Order',
            'field': 'custom_total_interest',
            'label': 'Foyda Summasi (Total Interest)'
        },
        {
            'doctype': 'Sales Order',
            'field': 'custom_contract_type',
            'label': 'Shartnoma Turi (Contract Type - shows Installment/Cash)'
        },
        {
            'doctype': 'Item',
            'field': 'custom_cost_price_usd',
            'label': 'Tan Narx (Cost Price USD)'
        }
    ]
    
    hidden_count = 0
    
    for field_info in fields_to_hide:
        try:
            # Update Custom Field directly
            custom_field_name = f"{field_info['doctype']}-{field_info['field']}"
            
            if frappe.db.exists('Custom Field', custom_field_name):
                frappe.db.set_value('Custom Field', custom_field_name, 'print_hide', 1)
                print(f"✅ Hidden - {field_info['doctype']}: {field_info['label']}")
                print(f"   Field: {field_info['field']}")
                hidden_count += 1
            else:
                print(f"⚠️  Field not found: {custom_field_name}")
            
        except Exception as e:
            print(f"❌ ERROR for {field_info['doctype']}.{field_info['field']}: {str(e)}")
    
    frappe.db.commit()
    
    print("\n" + "-"*60)
    print(f"✅ PRINT FORMAT CLEANED: {hidden_count} sensitive fields hidden")
    print("-"*60)
    print("\nℹ️  Client print will now show:")
    print("   ✓ Product name (custom_product_name)")
    print("   ✓ Quantity")
    print("   ✓ Grand total with interest (Jami To'lov)")
    print("   ✓ Downpayment amount (Boshlang'ich To'lov)")
    print("\nℹ️  Hidden from client:")
    print("   ✗ Total interest amount (Foyda Summasi)")
    print("   ✗ Contract type (Installment vs Cash)")
    print("   ✗ Product cost prices (Tan Narx)")
    print()

if __name__ == '__main__':
    frappe.init(site='asadstack.com')
    frappe.connect()
    hide_print_format_fields()
    frappe.destroy()
