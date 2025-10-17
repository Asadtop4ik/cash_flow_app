#!/usr/bin/env python3
"""
Setup Mode of Payment options
Creates: Naqd, Terminal/Click
"""
import frappe

def setup_mode_of_payment():
    modes = [
        {
            "name": "Naqd",
            "type": "Cash"
        },
        {
            "name": "Terminal/Click", 
            "type": "Bank"
        }
    ]
    
    for mode in modes:
        if not frappe.db.exists("Mode of Payment", mode["name"]):
            doc = frappe.get_doc({
                "doctype": "Mode of Payment",
                "mode_of_payment": mode["name"],
                "type": mode["type"],
                "enabled": 1
            })
            doc.insert(ignore_permissions=True)
            print(f"✅ Created Mode of Payment: {mode['name']}")
        else:
            print(f"⏭️  Mode of Payment already exists: {mode['name']}")
    
    frappe.db.commit()
    print("\n✅ Mode of Payment setup completed!")

if __name__ == "__main__":
    setup_mode_of_payment()
