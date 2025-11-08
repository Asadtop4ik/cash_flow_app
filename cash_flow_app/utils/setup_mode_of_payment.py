"""
Setup Mode of Payment with default accounts
Called after migrate to ensure Mode of Payment has correct Cash accounts
"""

import frappe
from frappe import _


def setup_mode_of_payment_accounts():
	"""
	Setup default Cash account for Mode of Payment
	This runs after migrate to ensure server has correct configuration
	"""
	try:
		print("\n" + "="*70)
		print("   Setting up Mode of Payment accounts...")
		print("="*70 + "\n")
		
		# Get all companies
		companies = frappe.get_all("Company", fields=["name", "default_currency"])
		
		for company in companies:
			print(f"Processing company: {company.name}")
			
			# Get default Cash account for this company
			cash_account = frappe.db.get_value("Account", {
				"account_type": "Cash",
				"company": company.name,
				"is_group": 0
			}, "name")
			
			if not cash_account:
				print(f"  ⚠️  No Cash account found for {company.name}, skipping...")
				continue
			
			print(f"  ✅ Cash account: {cash_account}")
			
			# Mode of Payments to setup
			mode_of_payments = ["Naqd", "Terminal/Click"]
			
			for mop_name in mode_of_payments:
				# Check if Mode of Payment exists
				if not frappe.db.exists("Mode of Payment", mop_name):
					print(f"  ⚠️  Mode of Payment '{mop_name}' not found, skipping...")
					continue
				
				# Get Mode of Payment document
				mop = frappe.get_doc("Mode of Payment", mop_name)
				
				# Check if account already exists for this company
				existing_account = None
				for acc in mop.accounts:
					if acc.company == company.name:
						existing_account = acc
						break
				
				if existing_account:
					# Update if different
					if existing_account.default_account != cash_account:
						existing_account.default_account = cash_account
						mop.save(ignore_permissions=True)
						print(f"  ✅ Updated '{mop_name}' account to: {cash_account}")
					else:
						print(f"  ℹ️  '{mop_name}' already has correct account")
				else:
					# Add new account row
					mop.append("accounts", {
						"company": company.name,
						"default_account": cash_account
					})
					mop.save(ignore_permissions=True)
					print(f"  ✅ Added '{mop_name}' account: {cash_account}")
		
		frappe.db.commit()
		
		print("\n" + "="*70)
		print("   ✅ Mode of Payment accounts setup completed!")
		print("="*70 + "\n")
		
	except Exception as e:
		print(f"\n❌ Error setting up Mode of Payment accounts: {e}")
		frappe.log_error(f"Mode of Payment Setup Error: {e}", "Setup Mode of Payment")
