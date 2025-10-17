#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Test Data Creator for Cash Flow App
Creates sample data for testing all features
Run: bench --site asadstack.com console
     >>> from create_test_data import create_test_data
     >>> create_test_data()
"""

import frappe
from frappe.utils import today, add_days, add_months, flt


def create_test_data():
	"""Create complete test data for UI testing"""
	frappe.set_user("Administrator")
	
	print("\n" + "="*60)
	print("🚀 CASH FLOW APP - TEST DATA YARATISH")
	print("="*60 + "\n")
	
	# 1. Create Counterparty Categories
	print("1️⃣  Counterparty Categories yaratilmoqda...")
	create_counterparty_categories()
	
	# 2. Create Test Customers
	print("\n2️⃣  Test Customers yaratilmoqda...")
	customers = create_test_customers()
	
	# 3. Create Test Items
	print("\n3️⃣  Test Items yaratilmoqda...")
	items = create_test_items()
	
	# 4. Create Test Sales Order (Shartnoma)
	print("\n4️⃣  Test Sales Order (Shartnoma) yaratilmoqda...")
	sales_order = create_test_sales_order(customers[0], items)
	
	# 5. Create Test Payment Entries (Kassa Kirim/Chiqim)
	print("\n5️⃣  Test Payment Entries yaratilmoqda...")
	pe_receive = create_test_payment_entry_receive(customers[0])
	pe_pay = create_test_payment_entry_pay()
	
	print("\n" + "="*60)
	print("✅ TEST DATA MUVAFFAQIYATLI YARATILDI!")
	print("="*60)
	
	print("\n📋 YARATILGAN HUJJATLAR:")
	print(f"   • Counterparty Categories: 11 ta")
	print(f"   • Customers: {len(customers)} ta")
	print(f"   • Items: {len(items)} ta")
	print(f"   • Sales Order: {sales_order}")
	print(f"   • Payment Entry (Kirim): {pe_receive}")
	print(f"   • Payment Entry (Chiqim): {pe_pay}")
	
	print("\n🎯 UI TEST QILISH UCHUN:")
	print(f"   1. Sales Order → {sales_order} → Print → Shartnoma")
	print(f"   2. Payment Entry → {pe_receive} → Print → Kassa Kvitansiya (GREEN)")
	print(f"   3. Payment Entry → {pe_pay} → Print → Kassa Kvitansiya (RED)")
	print(f"   4. Report → Daily Cash Flow")
	print(f"   5. Report → Outstanding Installments")
	print("\n")


def create_counterparty_categories():
	"""Create Counterparty Categories if not exist"""
	categories = [
		# Income
		{"name": "Klient", "type": "Income", "desc": "Mijozlardan tushgan to'lovlar"},
		{"name": "Boshqa to'lov", "type": "Income", "desc": "Boshqa manbalardан kirgan pul"},
		{"name": "Uslugadan foyda", "type": "Income", "desc": "Xizmat ko'rsatishdan olingan foyda"},
		{"name": "Boshqa foyda", "type": "Income", "desc": "Qo'shimcha daromadlar"},
		{"name": "Investor", "type": "Income", "desc": "Investor qo'ygan mablag'"},
		
		# Expense
		{"name": "Hodim", "type": "Expense", "desc": "Xodimlarga to'lovlar (maosh)"},
		{"name": "Postavshik", "type": "Expense", "desc": "Yetkazib beruvchilarga to'lovlar"},
		{"name": "Xarajat", "type": "Expense", "desc": "Umumiy xarajatlar"},
		{"name": "Investor chiqimi", "type": "Expense", "desc": "Investorga qaytarish"},
		{"name": "Komunal", "type": "Expense", "desc": "Kommunal to'lovlar"},
		{"name": "Bank", "type": "Expense", "desc": "Bank xizmatlari"},
	]
	
	for cat in categories:
		if not frappe.db.exists("Counterparty Category", cat["name"]):
			doc = frappe.get_doc({
				"doctype": "Counterparty Category",
				"category_name": cat["name"],
				"category_type": cat["type"],
				"description": cat["desc"],
				"is_active": 1
			})
			doc.insert()
			print(f"   ✓ {cat['name']} ({cat['type']})")
		else:
			print(f"   → {cat['name']} (mavjud)")


def create_test_customers():
	"""Create test customers"""
	customers = [
		{"name": "TEST-MIJOZ-001", "full_name": "Ahmadov Aziz", "mobile": "+998901234567"},
		{"name": "TEST-MIJOZ-002", "full_name": "Karimova Dilnoza", "mobile": "+998901234568"},
		{"name": "TEST-MIJOZ-003", "full_name": "Toshmatov Jasur", "mobile": "+998901234569"},
	]
	
	created = []
	for cust in customers:
		if not frappe.db.exists("Customer", cust["name"]):
			doc = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": cust["full_name"],
				"customer_type": "Individual",
				"customer_group": "Individual",
				"territory": "All Territories",
				"mobile_no": cust["mobile"]
			})
			doc.insert()
			print(f"   ✓ {doc.name} - {cust['full_name']}")
			created.append(doc.name)
		else:
			print(f"   → {cust['name']} (mavjud)")
			created.append(cust['name'])
	
	return created


def create_test_items():
	"""Create test items"""
	items = [
		{"code": "PHONE-IP14", "name": "iPhone 14 Pro 256GB", "rate": 1200.00},
		{"code": "PHONE-SM-S23", "name": "Samsung S23 Ultra", "rate": 1100.00},
		{"code": "LAPTOP-HP", "name": "HP Pavilion 15", "rate": 800.00},
	]
	
	created = []
	for item in items:
		if not frappe.db.exists("Item", item["code"]):
			doc = frappe.get_doc({
				"doctype": "Item",
				"item_code": item["code"],
				"item_name": item["name"],
				"item_group": "Products",
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"standard_rate": item["rate"],
				"valuation_rate": item["rate"]
			})
			doc.insert()
			print(f"   ✓ {item['code']} - {item['name']}")
			created.append(item["code"])
		else:
			print(f"   → {item['code']} (mavjud)")
			created.append(item['code'])
	
	return created


def create_test_sales_order(customer, items):
	"""Create test Sales Order with payment schedule"""
	# Check if already exists
	existing = frappe.db.get_value("Sales Order", {
		"customer": customer,
		"docstatus": 1,
		"naming_series": "CON-.YYYY.-.#####"
	})
	
	if existing:
		print(f"   → {existing} (mavjud)")
		return existing
	
	# Get company and currency
	company = frappe.defaults.get_defaults().company or frappe.get_all("Company", limit=1)[0].name
	
	doc = frappe.get_doc({
		"doctype": "Sales Order",
		"naming_series": "CON-.YYYY.-.#####",
		"customer": customer,
		"transaction_date": today(),
		"delivery_date": add_days(today(), 30),
		"company": company,
		"currency": "USD",
		"items": [
			{
				"item_code": items[0],
				"qty": 1,
				"rate": 1200.00,
				"delivery_date": add_days(today(), 30)
			}
		]
	})
	
	doc.insert()
	
	# Add payment schedule manually
	doc.payment_schedule = []
	
	# Downpayment (30%)
	doc.append("payment_schedule", {
		"due_date": today(),
		"invoice_portion": 30.0,
		"payment_amount": 360.00,
		"paid_amount": 360.00  # Marked as paid
	})
	
	# Monthly payments (12 months)
	monthly = 70.00  # (1200 - 360) / 12
	for month in range(1, 13):
		doc.append("payment_schedule", {
			"due_date": add_months(today(), month),
			"invoice_portion": 70.0 / 12,
			"payment_amount": monthly
		})
	
	doc.save()
	doc.submit()
	
	print(f"   ✓ {doc.name} - {customer}")
	return doc.name


def create_test_payment_entry_receive(customer):
	"""Create test Payment Entry (Receive - Kassa Kirim)"""
	company = frappe.defaults.get_defaults().company or frappe.get_all("Company", limit=1)[0].name
	
	# Get default accounts
	cash_account = frappe.get_value("Account", {
		"account_type": "Cash",
		"company": company,
		"is_group": 0
	}, "name")
	
	receivable_account = frappe.get_value("Account", {
		"account_type": "Receivable",
		"company": company,
		"is_group": 0
	}, "name")
	
	if not cash_account or not receivable_account:
		print("   ⚠️  Cash/Receivable accounts topilmadi. Payment Entry yaratilmadi.")
		return None
	
	doc = frappe.get_doc({
		"doctype": "Payment Entry",
		"payment_type": "Receive",
		"party_type": "Customer",
		"party": customer,
		"posting_date": today(),
		"company": company,
		"paid_from": receivable_account,
		"paid_to": cash_account,
		"paid_amount": 360.00,
		"received_amount": 360.00,
		"mode_of_payment": "Naqd",
		"custom_counterparty_category": "Klient",
		"remarks": "Test boshlang'ich to'lov (downpayment)"
	})
	
	doc.insert()
	doc.submit()
	
	print(f"   ✓ {doc.name} - KIRIM (Receive) - {customer}")
	return doc.name


def create_test_payment_entry_pay():
	"""Create test Payment Entry (Pay - Kassa Chiqim)"""
	company = frappe.defaults.get_defaults().company or frappe.get_all("Company", limit=1)[0].name
	
	# Get default accounts
	cash_account = frappe.get_value("Account", {
		"account_type": "Cash",
		"company": company,
		"is_group": 0
	}, "name")
	
	expense_account = frappe.get_value("Account", {
		"root_type": "Expense",
		"company": company,
		"is_group": 0
	}, "name")
	
	if not cash_account or not expense_account:
		print("   ⚠️  Cash/Expense accounts topilmadi. Payment Entry yaratilmadi.")
		return None
	
	doc = frappe.get_doc({
		"doctype": "Payment Entry",
		"payment_type": "Pay",
		"posting_date": today(),
		"company": company,
		"paid_from": cash_account,
		"paid_to": expense_account,
		"paid_amount": 150.00,
		"received_amount": 150.00,
		"mode_of_payment": "Naqd",
		"custom_counterparty_category": "Xarajat",
		"remarks": "Test ofis xarajatlari"
	})
	
	doc.insert()
	doc.submit()
	
	print(f"   ✓ {doc.name} - CHIQIM (Pay)")
	return doc.name


if __name__ == "__main__":
	create_test_data()
