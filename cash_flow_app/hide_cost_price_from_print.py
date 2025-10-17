#!/usr/bin/env python3
"""
Hide valuation_rate (cost price / tan narx) from Sales Order Item print
"""

import frappe

def hide_cost_price_from_print():
    """Hide valuation_rate from client print format"""
    
    print("\n" + "="*60)
    print("HIDING COST PRICE FROM SALES ORDER PRINT")
    print("="*60 + "\n")
    
    try:
        # Set print_hide=1 for valuation_rate in Sales Order Item
        frappe.db.sql("""
            UPDATE `tabDocField`
            SET print_hide = 1
            WHERE parent = 'Sales Order Item'
            AND fieldname = 'valuation_rate'
        """)
        
        frappe.db.commit()
        
        print("✅ Hidden - Sales Order Item: valuation_rate (Tan Narx / Cost Price)")
        print("\nℹ️  Client print will NOT show:")
        print("   ✗ Valuation Rate (tan narx)")
        print("\nℹ️  Client print will show:")
        print("   ✓ Product name")
        print("   ✓ Quantity")
        print("   ✓ Rate (selling price)")
        print("   ✓ Amount")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
    
    print("\n" + "="*60)

if __name__ == '__main__':
    frappe.init(site='asadstack.com')
    frappe.connect()
    hide_cost_price_from_print()
    frappe.destroy()
