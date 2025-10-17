#!/usr/bin/env python3
"""
Create fresh test data for complete workflow demonstration
"""
import frappe
from frappe.utils import nowdate, add_months, flt

def create_test_data():
    print("\n" + "=" * 70)
    print(" " * 20 + "📝 CREATING FRESH TEST DATA")
    print("=" * 70)
    
    # 1. Create Customers
    print("\n👥 1. CREATING CUSTOMERS")
    customers = [
        {"name": "Алишер Исмоилов", "mobile": "+998901234567"},
        {"name": "Нодира Раҳимова", "mobile": "+998909876543"},
        {"name": "Жамшид Каримов", "mobile": "+998931112233"}
    ]
    
    created_customers = []
    for cust in customers:
        if not frappe.db.exists("Customer", cust["name"]):
            doc = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": cust["name"],
                "customer_type": "Individual",
                "customer_group": "Individual",
                "territory": "All Territories",
                "mobile_no": cust["mobile"],
                "custom_telegram_username": "@" + cust["name"].split()[0].lower()
            })
            doc.insert(ignore_permissions=True)
            created_customers.append(cust["name"])
            print(f"   ✅ {cust['name']}")
        else:
            created_customers.append(cust["name"])
            print(f"   ⏭️  {cust['name']} (exists)")
    
    # 2. Create Items (Products)
    print("\n📦 2. CREATING PRODUCTS")
    items = [
        {"name": "iPhone 15 Pro Max 256GB", "price": 1200, "category": "Telefon"},
        {"name": "Samsung Galaxy S24 Ultra", "price": 1100, "category": "Telefon"},
        {"name": "MacBook Pro M3 14-inch", "price": 2000, "category": "Noutbuk"},
        {"name": "iPad Pro 12.9 M2", "price": 1300, "category": "Planshet"},
        {"name": "Apple Watch Series 9", "price": 450, "category": "Soat"}
    ]
    
    created_items = []
    for item in items:
        # Item naming is auto (ITEM-.YYYY.-.#####)
        doc = frappe.get_doc({
            "doctype": "Item",
            "custom_product_name": item["name"],
            "custom_category": item["category"],
            "custom_purchase_price": item["price"],
            "custom_sale_price": item["price"] + 100,  # +$100 markup
            "custom_installment_price": item["price"] + 200,  # +$200 for installment
            "custom_price_usd": item["price"],  # Required field
            "stock_uom": "Nos"
        })
        doc.insert(ignore_permissions=True)
        created_items.append(doc.name)
        print(f"   ✅ {doc.name}: {item['name']} (${item['price']})")
    
    frappe.db.commit()
    
    print("\n" + "=" * 70)
    print(f" ✅ CREATED: {len(created_customers)} Customers, {len(created_items)} Products")
    print("=" * 70)
    
    return created_customers, created_items

if __name__ == "__main__":
    create_test_data()
