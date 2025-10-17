# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CashSettings(Document):
    def validate(self):
        """Validate settings"""
        self.validate_accounts()
        self.validate_cost_center()
    
    def validate_accounts(self):
        """Ensure accounts belong to selected company"""
        if self.default_cash_account:
            acc_company = frappe.db.get_value(
                "Account", 
                self.default_cash_account, 
                "company"
            )
            if acc_company != self.company:
                frappe.throw(
                    f"Default Cash Account must belong to company {self.company}"
                )
        
        if self.default_income_account:
            acc_company = frappe.db.get_value(
                "Account", 
                self.default_income_account, 
                "company"
            )
            if acc_company != self.company:
                frappe.throw(
                    f"Default Income Account must belong to company {self.company}"
                )
    
    def validate_cost_center(self):
        """Ensure cost center belongs to selected company"""
        if self.default_cost_center:
            cc_company = frappe.db.get_value(
                "Cost Center", 
                self.default_cost_center, 
                "company"
            )
            if cc_company != self.company:
                frappe.throw(
                    f"Default Cost Center must belong to company {self.company}"
                )

@frappe.whitelist()
def get_cash_settings():
    """Get cash settings for current session (cached)"""
    if not frappe.db.exists("Cash Settings", "Cash Settings"):
        return {}
    
    settings = frappe.get_cached_doc("Cash Settings", "Cash Settings")
    
    return {
        "company": settings.company,
        "default_cash_account": settings.default_cash_account,
        "default_cost_center": settings.default_cost_center,
        "default_letter_head": settings.default_letter_head,
        "default_income_account": settings.default_income_account,
        "cin_series": settings.cin_series or "CIN-.YYYY.-.#####",
        "cout_series": settings.cout_series or "COUT-.YYYY.-.#####"
    }