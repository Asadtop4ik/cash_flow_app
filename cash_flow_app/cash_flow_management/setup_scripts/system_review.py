#!/usr/bin/env python3
"""
Complete System Review
Checks all configurations, custom fields, hooks, and reports
"""
import frappe

def system_review():
    print("\n" + "=" * 70)
    print(" " * 20 + "🚀 CASH FLOW APP - SYSTEM REVIEW")
    print("=" * 70)
    
    # 1. Mode of Payment
    print("\n📋 1. MODE OF PAYMENT")
    modes = frappe.get_all('Mode of Payment', 
        filters={'enabled': 1},
        fields=['name', 'type'],
        order_by='name')
    for m in modes:
        # Check if account linked
        account = frappe.db.get_value('Mode of Payment Account',
            {'parent': m.name}, 'default_account')
        status = f"✅ {account}" if account else "❌ No account"
        print(f"   {m.name:20} ({m.type:4}) - {status}")
    
    # 2. Cash Settings
    print("\n💰 2. CASH SETTINGS")
    cash_settings = frappe.get_single("Cash Settings")
    print(f"   Default Cash Account: {cash_settings.default_cash_account or '❌ NOT SET'}")
    
    # 3. Custom Fields Count
    print("\n🔧 3. CUSTOM FIELDS")
    doctypes = [
        ('Payment Entry', 3),
        ('Sales Order', 5),
        ('Item', 6)
    ]
    for dt, expected in doctypes:
        count = frappe.db.count('Custom Field', {'dt': dt})
        status = "✅" if count >= expected else "⚠️"
        print(f"   {status} {dt:20} - {count} fields (expected: {expected})")
    
    # 4. Hidden Fields (Property Setters)
    print("\n👁️  4. HIDDEN FIELDS (Property Setters)")
    hide_counts = [
        ('Payment Entry', 33),
        ('Sales Order', 48),
        ('Item', 2)
    ]
    for dt, expected in hide_counts:
        count = frappe.db.count('Property Setter', {
            'doc_type': dt,
            'property': 'hidden',
            'value': '1'
        })
        status = "✅" if count >= expected else "⚠️"
        print(f"   {status} {dt:20} - {count} fields hidden (expected: {expected})")
    
    # 5. Reports
    print("\n📊 5. CUSTOM REPORTS")
    reports = frappe.get_all('Report',
        filters={'module': 'Cash Flow Management'},
        fields=['name', 'report_type'],
        order_by='name')
    for r in reports:
        print(f"   ✅ {r.name:40} ({r.report_type})")
    
    # 6. DocTypes
    print("\n📝 6. CUSTOM DOCTYPES")
    custom_dts = frappe.get_all('DocType',
        filters={'module': 'Cash Flow Management', 'custom': 0},
        fields=['name', 'issingle'],
        order_by='name')
    for dt in custom_dts:
        single = " (Single DocType)" if dt.issingle else ""
        print(f"   ✅ {dt.name}{single}")
    
    # 7. JavaScript Files
    print("\n💻 7. CLIENT SCRIPTS")
    import os
    js_files = [
        ('sales_order.js', 'Sales Order UI enhancements'),
        ('payment_entry.js', 'Payment Entry UI + Installment links')
    ]
    base_path = "/home/asadbek/frappe-bench/apps/cash_flow_app/cash_flow_app/public/js/"
    for js, desc in js_files:
        exists = os.path.exists(base_path + js)
        status = "✅" if exists else "❌"
        print(f"   {status} {js:25} - {desc}")
    
    # 8. Data Check
    print("\n📈 8. CURRENT DATA")
    data_counts = [
        ('Customer', 'Customers'),
        ('Item', 'Products'),
        ('Installment Application', 'Applications'),
        ('Sales Order', 'Contracts'),
        ('Payment Entry', 'Payments')
    ]
    for dt, label in data_counts:
        count = frappe.db.count(dt, {'docstatus': ['!=', 2]})  # Exclude cancelled
        print(f"   {label:25} - {count} records")
    
    print("\n" + "=" * 70)
    print(" " * 25 + "✅ SYSTEM REVIEW COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    system_review()
