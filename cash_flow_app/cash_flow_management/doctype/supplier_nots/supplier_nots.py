# Copyright (c) 2026, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SupplierNots(Document):
	def before_save(self):
		if self.is_new():
			self.created_by_user = frappe.session.user
		self.modified_by_user = frappe.session.user

	def validate(self):
		# Auto-fill supplier based on reference document
		if not self.supplier and self.reference_name and self.reference_type:
			if self.reference_type == "Payment Entry":
				self.supplier = frappe.db.get_value(
					"Payment Entry",
					self.reference_name,
					"party"
				)
			elif self.reference_type == "Installment Application":
				# Installment Application dan supplier olish (agar mavjud bo'lsa)
				# Yoki birinchi item dan custom_supplier olish
				items = frappe.get_all(
					"Installment Application Item",
					filters={"parent": self.reference_name},
					fields=["custom_supplier"],
					limit=1
				)
				if items and items[0].custom_supplier:
					self.supplier = items[0].custom_supplier
