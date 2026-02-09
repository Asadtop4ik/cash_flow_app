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
		# Auto-fill supplier from Payment Entry if not provided
		if self.payment_reference and not self.supplier:
			self.supplier = frappe.db.get_value(
				"Payment Entry",
				self.payment_reference,
				"party"
			)
