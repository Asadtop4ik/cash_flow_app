#!/usr/bin/env python3
"""
Add custom_next_payment_date and custom_next_payment_amount fields to Sales Order
"""

import frappe

def create_next_payment_fields():
    """Create next payment tracking fields in Sales Order"""
    
    print("\n" + "="*60)
    print("CREATING NEXT PAYMENT FIELDS IN SALES ORDER")
    print("="*60 + "\n")
    
    fields = [
        {
            'fieldname': 'custom_next_payment_date',
            'label': 'Next Payment Date',
            'fieldtype': 'Date',
            'insert_after': 'custom_grand_total_with_interest',
            'read_only': 1,
            'in_list_view': 0,
            'in_standard_filter': 1
        },
        {
            'fieldname': 'custom_next_payment_amount',
            'label': 'Next Payment (USD)',
            'fieldtype': 'Currency',
            'options': 'USD',
            'insert_after': 'custom_next_payment_date',
            'read_only': 1,
            'in_list_view': 0,
            'precision': 2
        }
    ]
    
    for field_data in fields:
        field_name = f"Sales Order-{field_data['fieldname']}"
        
        if frappe.db.exists('Custom Field', field_name):
            print(f"✓ Field already exists: {field_data['fieldname']}")
            continue
        
        try:
            custom_field = frappe.get_doc({
                'doctype': 'Custom Field',
                'dt': 'Sales Order',
                **field_data
            })
            custom_field.insert()
            print(f"✅ Created: {field_data['fieldname']}")
        except Exception as e:
            print(f"❌ Error creating {field_data['fieldname']}: {e}")
    
    frappe.db.commit()
    
    print("\n" + "="*60)
    print("✅ NEXT PAYMENT FIELDS CREATED")
    print("="*60)
    print("\nℹ️  Fields added:")
    print("   • custom_next_payment_date (Date)")
    print("   • custom_next_payment_amount (Currency USD)")
    print()

if __name__ == '__main__':
    frappe.init(site='asadstack.com')
    frappe.connect()
    create_next_payment_fields()
    frappe.destroy()
