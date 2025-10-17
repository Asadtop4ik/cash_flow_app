#!/usr/bin/env python3
"""
Clean all test data - Start fresh
"""
import frappe

def clean_all_data():
    print("\n" + "=" * 70)
    print(" " * 25 + "🧹 DATA CLEANUP")
    print("=" * 70)
    
    # Define cleanup order (child → parent)
    cleanup_list = [
        ('Payment Entry', 'Payments'),
        ('Sales Order', 'Sales Orders'),
        ('Installment Application', 'Installment Applications'),
        ('Item', 'Items'),
        ('Customer', 'Customers')
    ]
    
    for doctype, label in cleanup_list:
        # Get all documents (including Draft and Cancelled)
        docs = frappe.get_all(doctype, fields=['name', 'docstatus'])
        
        if not docs:
            print(f"\n✅ {label}: No data to clean")
            continue
        
        print(f"\n🔄 Cleaning {label}... ({len(docs)} records)")
        
        deleted_count = 0
        for doc in docs:
            try:
                # Cancel if submitted
                if doc.docstatus == 1:
                    d = frappe.get_doc(doctype, doc.name)
                    d.cancel()
                    print(f"   ⏹️  Cancelled: {doc.name}")
                
                # Delete
                frappe.delete_doc(doctype, doc.name, force=1)
                deleted_count += 1
                print(f"   ❌ Deleted: {doc.name}")
                
            except Exception as e:
                print(f"   ⚠️  Error deleting {doc.name}: {str(e)}")
        
        print(f"   ✅ {label}: {deleted_count}/{len(docs)} deleted")
    
    # Commit
    frappe.db.commit()
    
    print("\n" + "=" * 70)
    print(" " * 20 + "✅ ALL DATA CLEANED - READY FOR FRESH START")
    print("=" * 70)

if __name__ == "__main__":
    clean_all_data()
