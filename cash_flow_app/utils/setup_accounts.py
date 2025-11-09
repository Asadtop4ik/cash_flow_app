"""
Setup accounts and mode of payment for the default company dynamically
"""
import frappe
from frappe import _


def setup_cash_accounts():
	"""
	Create Cash - B account hierarchy and Naqd B mode of payment
	for the first/default company. This runs after installation.
	"""
	# Get the first company (default company created during ERPNext setup)
	companies = frappe.get_all("Company", fields=["name", "abbr"], limit=1)
	
	if not companies:
		frappe.logger().warning("No company found. Skipping account creation.")
		return
	
	company = companies[0]["name"]
	abbr = companies[0]["abbr"]
	
	frappe.logger().info(f"Setting up accounts for company: {company} ({abbr})")
	
	# Account hierarchy to create
	accounts = [
		{
			"account_name": "Application of Funds (Assets)",
			"parent_account": None,
			"is_group": 1,
			"root_type": "Asset",
			"account_type": "",
		},
		{
			"account_name": "Current Assets",
			"parent_account": "Application of Funds (Assets)",
			"is_group": 1,
			"root_type": "Asset",
			"account_type": "",
		},
		{
			"account_name": "Cash In Hand",
			"parent_account": "Current Assets",
			"is_group": 1,
			"root_type": "Asset",
			"account_type": "Cash",
		},
		{
			"account_name": "Cash - B",
			"parent_account": "Cash In Hand",
			"is_group": 0,
			"root_type": "Asset",
			"account_type": "Cash",
		},
	]
	
	cash_b_account = None
	
	for account_data in accounts:
		account_name = f"{account_data['account_name']} - {abbr}"
		
		# Skip if account already exists
		if frappe.db.exists("Account", account_name):
			frappe.logger().info(f"Account {account_name} already exists")
			if account_data["account_name"] == "Cash - B":
				cash_b_account = account_name
			continue
		
		# Build parent account name with abbreviation
		parent_account = None
		if account_data["parent_account"]:
			parent_account = f"{account_data['parent_account']} - {abbr}"
			
			# Check if parent exists
			if not frappe.db.exists("Account", parent_account):
				frappe.logger().warning(f"Parent account {parent_account} does not exist. Skipping {account_name}")
				continue
		
		try:
			# Create account
			account = frappe.get_doc({
				"doctype": "Account",
				"account_name": account_data["account_name"],
				"company": company,
				"parent_account": parent_account,
				"is_group": account_data["is_group"],
				"root_type": account_data["root_type"],
				"account_type": account_data["account_type"],
				"account_currency": "USD",
			})
			account.insert(ignore_permissions=True)
			frappe.logger().info(f"Created account: {account_name}")
			
			if account_data["account_name"] == "Cash - B":
				cash_b_account = account_name
			
		except Exception as e:
			frappe.logger().error(f"Error creating account {account_name}: {str(e)}")
			continue
	
	# Create Mode of Payment: Naqd B
	if cash_b_account:
		_create_mode_of_payment(company, cash_b_account)
	
	frappe.db.commit()
	frappe.logger().info("Account and Mode of Payment setup completed")


def _create_mode_of_payment(company, account):
	"""Create Naqd B mode of payment with Cash - B account"""
	mode_name = "Naqd B"
	
	if frappe.db.exists("Mode of Payment", mode_name):
		frappe.logger().info(f"Mode of Payment {mode_name} already exists")
		return
	
	try:
		mode = frappe.get_doc({
			"doctype": "Mode of Payment",
			"mode_of_payment": mode_name,
			"type": "Cash",
			"enabled": 1,
			"accounts": [{
				"company": company,
				"default_account": account
			}]
		})
		mode.insert(ignore_permissions=True)
		frappe.logger().info(f"Created Mode of Payment: {mode_name}")
	except Exception as e:
		frappe.logger().error(f"Error creating Mode of Payment {mode_name}: {str(e)}")
