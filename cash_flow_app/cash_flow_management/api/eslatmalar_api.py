# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def save_contract_note(contract_id, note_value):
	"""
	Save note for Installment Application
	Works even with submitted documents by using db.set_value
	"""
	try:
		# Log the incoming data
		frappe.logger().info(f"save_contract_note called: contract_id={contract_id}, note_value={note_value}")

		# Validate that the contract exists
		if not frappe.db.exists("Installment Application", contract_id):
			frappe.throw(_("Shartnoma topilmadi: {0}").format(contract_id))

		# Check permissions
		if not frappe.has_permission("Installment Application", "write", contract_id):
			frappe.throw(_("Ruxsat yo'q"))

		# Use db.set_value to bypass submit status check
		frappe.db.set_value("Installment Application", contract_id, "notes", note_value)
		frappe.db.commit()

		# Log success and verify the saved value
		saved_note = frappe.db.get_value("Installment Application", contract_id, "notes")
		frappe.logger().info(f"Note saved successfully. Verified value: {saved_note}")

		return {
			"success": True,
			"message": _("Izoh saqlandi"),
			"saved_value": saved_note
		}

	except Exception as e:
		frappe.log_error(message=str(e), title="Eslatmalar - Izoh saqlash xatosi")
		frappe.logger().error(f"Error saving note: {str(e)}")
		return {
			"success": False,
			"message": _("Xatolik: {0}").format(str(e))
		}
