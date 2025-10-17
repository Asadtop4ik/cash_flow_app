#!/usr/bin/env python3
"""
Fix Mode of Payment - Add default accounts
"""
import frappe

def fix_mode_of_payment_accounts():
    # Get default cash account from Cash Settings
    cash_settings = frappe.get_single("Cash Settings")
    default_cash_account = cash_settings.get("default_cash_account")
    
    print(f"\n=== Cash Settings ===")
    print(f"Default Cash Account: {default_cash_account}")
    
    if not default_cash_account:
        print("\n⚠️ ERROR: Cash Settings'da default_cash_account topilmadi!")
        print("Iltimos, Cash Settings'da default_cash_account ni sozlang.")
        return
    
    # Get company
    company = frappe.defaults.get_user_default("Company") or "AsadStack"
    
    # Setup Mode of Payment accounts
    modes = ["Naqd", "Terminal/Click"]
    
    for mode_name in modes:
        if not frappe.db.exists("Mode of Payment", mode_name):
            print(f"\n⚠️ Mode of Payment '{mode_name}' topilmadi!")
            continue
        
        mode_doc = frappe.get_doc("Mode of Payment", mode_name)
        
        # Clear existing accounts
        mode_doc.accounts = []
        
        # Add default account for company
        mode_doc.append("accounts", {
            "company": company,
            "default_account": default_cash_account
        })
        
        mode_doc.save(ignore_permissions=True)
        
        print(f"\n✅ Updated: {mode_name}")
        print(f"   Company: {company}")
        print(f"   Default Account: {default_cash_account}")
    
    frappe.db.commit()
    print("\n✅ Mode of Payment accounts configured successfully!")

if __name__ == "__main__":
    fix_mode_of_payment_accounts()
