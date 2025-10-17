#!/usr/bin/env python3
"""
Add mode_of_payment field to Installment Application
"""

import frappe

def add_mode_of_payment_field():
    """Add mode_of_payment field to Installment Application"""
    
    print("\n" + "="*60)
    print("ADDING MODE OF PAYMENT TO INSTALLMENT APPLICATION")
    print("="*60 + "\n")
    
    field_name = "Installment Application-mode_of_payment"
    
    if frappe.db.exists('Custom Field', field_name):
        print(f"✓ Field already exists: mode_of_payment")
        return
    
    try:
        custom_field = frappe.get_doc({
            'doctype': 'Custom Field',
            'dt': 'Installment Application',
            'fieldname': 'mode_of_payment',
            'label': 'Mode of Payment',
            'fieldtype': 'Link',
            'options': 'Mode of Payment',
            'insert_after': 'cost_center',
            'reqd': 1,
            'in_list_view': 0,
            'in_standard_filter': 1,
            'default': 'Naqd'
        })
        custom_field.insert()
        print(f"✅ Created: mode_of_payment")
        
        frappe.db.commit()
        
        print("\n" + "="*60)
        print("✅ MODE OF PAYMENT FIELD ADDED")
        print("="*60)
        print("\nℹ️  Field details:")
        print("   • fieldname: mode_of_payment")
        print("   • fieldtype: Link → Mode of Payment")
        print("   • required: Yes")
        print("   • default: Naqd")
        print()
        
    except Exception as e:
        print(f"❌ Error creating field: {e}")

if __name__ == '__main__':
    frappe.init(site='asadstack.com')
    frappe.connect()
    add_mode_of_payment_field()
    frappe.destroy()
