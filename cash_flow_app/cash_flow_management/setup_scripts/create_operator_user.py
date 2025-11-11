#!/usr/bin/env python3
"""
Create Operator user with email operator@gmail.com and password Mypassword111!
Assign Operator role
"""
import frappe

def create_operator_user():
    print("\n" + "=" * 70)
    print(" " * 20 + "👤 CREATING OPERATOR USER")
    print("=" * 70)

    email = "operator@gmail.com"
    password = "Mypassword111!"

    if frappe.db.exists("User", email):
        print(f"✅ User {email} already exists")
        return

    # Create user
    user = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": "Operator",
        "last_name": "User",
        "send_welcome_email": 0,
        "user_type": "System User"
    })

    user.insert(ignore_permissions=True)

    # Set password
    user.set_password(password)

    # Add Operator role
    user.add_roles("Operator")

    user.save(ignore_permissions=True)

    frappe.db.commit()

    print(f"✅ Operator user created: {email}")
    print(f"   Password: {password}")
    print(f"   Role: Operator")

    print("\n" + "=" * 70)
    print(" " * 25 + "✅ USER CREATED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    create_operator_user()