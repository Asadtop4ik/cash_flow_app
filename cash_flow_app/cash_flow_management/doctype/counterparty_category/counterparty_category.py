# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CounterpartyCategory(Document):
    def validate(self):
        """Validate before save"""
        self.validate_unique_name()
        self.validate_category_type()
    
    def validate_unique_name(self):
        """Check if category name is unique"""
        if self.is_new():
            existing = frappe.db.exists("Counterparty Category", {
                "category_name": self.category_name,
                "name": ["!=", self.name]
            })
            if existing:
                frappe.throw(
                    f"Counterparty Category '{self.category_name}' already exists",
                    title="Duplicate Category"
                )
    
    def validate_category_type(self):
        """Validate category type"""
        valid_types = ["Income", "Expense"]
        if self.category_type not in valid_types:
            frappe.throw(
                f"Category Type must be one of: {', '.join(valid_types)}",
                title="Invalid Type"
            )
    
    def on_trash(self):
        """Prevent deletion if used in transactions"""
        linked_pe = frappe.db.count("Payment Entry", {
            "custom_counterparty_category": self.name,
            "docstatus": ["<", 2]
        })
        
        if linked_pe > 0:
            frappe.throw(
                f"Cannot delete. This category is used in {linked_pe} Payment Entry records.",
                title="Cannot Delete"
            )

@frappe.whitelist()
def get_categories_by_type(category_type):
    """Get active categories filtered by type (Income/Expense)"""
    return frappe.get_all(
        "Counterparty Category",
        filters={
            "category_type": category_type,
            "is_active": 1
        },
        fields=["name", "category_name", "category_type"],
        order_by="category_name"
    )