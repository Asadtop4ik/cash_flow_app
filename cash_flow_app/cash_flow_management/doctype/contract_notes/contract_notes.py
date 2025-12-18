# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ContractNotes(Document):
	def before_save(self):
		if self.is_new():
			self.created_by_user = frappe.session.user
		self.modified_by_user = frappe.session.user

	def validate(self):
		if self.contract_reference and not self.customer:
			self.customer = frappe.db.get_value(
				"Installment Application",
				self.contract_reference,
				"customer"
			)
