"""
Fixture force sync utilities for cash_flow_app
Ensures Custom Fields and other fixtures auto-update on migrate
"""

import frappe
from frappe.modules.import_file import import_file_by_path
import os


def force_sync_custom_fields():
	"""
	Force import Custom Fields after migrate.
	Called via after_migrate hook to ensure Custom Fields stay in sync.
	"""
	try:
		fixture_path = frappe.get_app_path("cash_flow_app", "fixtures", "custom_field.json")
		
		if not os.path.exists(fixture_path):
			frappe.log_error(f"Custom Field fixture not found: {fixture_path}")
			return
		
		frappe.flags.in_migrate = True
		
		# Import with force=True to bypass timestamp check
		import_file_by_path(
			fixture_path,
			force=True,
			data_import=True,
			reset_permissions=True
		)
		
		frappe.db.commit()
		print("✅ Custom Fields synced successfully")
		
	except Exception as e:
		# Don't break migrate if fixture sync fails
		frappe.log_error(
			message=str(e),
			title="Custom Field Force Sync Failed"
		)
		print(f"⚠️  Custom Field sync failed: {e}")


def force_sync_property_setters():
	"""
	Force import Property Setters after migrate.
	Property Setters don't have migration_hash, so force import needed.
	"""
	try:
		fixture_path = frappe.get_app_path("cash_flow_app", "fixtures", "property_setter.json")
		
		if not os.path.exists(fixture_path):
			return
		
		frappe.flags.in_migrate = True
		
		import_file_by_path(
			fixture_path,
			force=True,
			data_import=True,
			reset_permissions=True
		)
		
		frappe.db.commit()
		print("✅ Property Setters synced successfully")
		
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title="Property Setter Force Sync Failed"
		)
		print(f"⚠️  Property Setter sync failed: {e}")


def force_sync_all_fixtures():
	"""
	Force import ALL fixtures that don't have migration_hash.
	
	Fixtures with migration issues:
	- Custom Field
	- Property Setter
	- DocPerm
	- Item Group
	- Mode of Payment
	- Role
	- UOM
	- Workspace
	"""
	fixtures_to_sync = [
		"custom_field.json",
		"property_setter.json",
		"docperm.json",  # Add DocPerm to prevent duplicates
		# Add others if needed:
		# "item_group.json",
		# "mode_of_payment.json",
	]
	
	for fixture_file in fixtures_to_sync:
		try:
			fixture_path = frappe.get_app_path("cash_flow_app", "fixtures", fixture_file)
			
			if not os.path.exists(fixture_path):
				continue
			
			print(f"🔄 Syncing {fixture_file}...")
			
			frappe.flags.in_migrate = True
			import_file_by_path(
				fixture_path,
				force=True,
				data_import=True,
				reset_permissions=True
			)
			
			print(f"✅ {fixture_file} synced")
			
		except Exception as e:
			frappe.log_error(
				message=f"Fixture: {fixture_file}\nError: {str(e)}",
				title=f"Force Sync Failed: {fixture_file}"
			)
			print(f"⚠️  {fixture_file} sync failed: {e}")
	
	frappe.db.commit()
	print("✅ All fixtures sync completed")


def force_sync_docperms():
	"""
	Force import DocPerm to prevent duplicate permissions.
	
	Problem: When you change permissions via UI, Frappe creates
	new records with random names. This causes duplicates in fixtures.
	
	Solution: DELETE all existing Operator DocPerms, then import clean fixture.
	"""
	try:
		fixture_path = frappe.get_app_path("cash_flow_app", "fixtures", "docperm.json")
		
		if not os.path.exists(fixture_path):
			return
		
		print("🗑️  Deleting existing Operator DocPerms...")
		
		# CRITICAL: Delete ALL Operator DocPerms first
		# This prevents duplicates since DocPerm has random names
		frappe.db.sql("""
			DELETE FROM `tabDocPerm`
			WHERE role = 'Operator'
		""")
		frappe.db.commit()
		
		print("✅ Old DocPerms deleted")
		
		# Now import clean fixture
		frappe.flags.in_migrate = True
		
		import_file_by_path(
			fixture_path,
			force=True,
			data_import=True,
			reset_permissions=True
		)
		
		frappe.db.commit()
		
		# Verify
		count = frappe.db.count('DocPerm', {'role': 'Operator'})
		print(f"✅ DocPerm synced successfully ({count} permissions)")
		
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title="DocPerm Force Sync Failed"
		)
		print(f"⚠️  DocPerm sync failed: {e}")


def force_sync_reports():
	"""
	Force import Report fixtures to sync UI changes (add_total_row, etc.)
	
	Report has migration_hash, but UI changes (like add_total_row setting)
	are not always reflected without force import.
	"""
	try:
		fixture_path = frappe.get_app_path("cash_flow_app", "fixtures", "report.json")
		
		if not os.path.exists(fixture_path):
			return
		
		frappe.flags.in_migrate = True
		
		import_file_by_path(
			fixture_path,
			force=True,
			data_import=True,
			reset_permissions=True
		)
		
		frappe.db.commit()
		print("✅ Report fixtures synced successfully")
		
	except Exception as e:
		frappe.log_error(
			message=str(e),
			title="Report Force Sync Failed"
		)
		print(f"⚠️  Report sync failed: {e}")


