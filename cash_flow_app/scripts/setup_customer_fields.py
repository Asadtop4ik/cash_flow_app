""""
Setup script for Customer customizations
Lokatsiya: cash_flow_app/cash_flow_management/custom/setup_customer_fields.py
"""

import frappe


def run():
    """
    Customer DocType ni customize qilish:
    1. Keraksiz fieldlarni yashirish (Property Setter)
    2. Customer Type field qo'shish (Custom Field)
    """

    # STEP 1: Customer Type field qo'shish
    setup_customer_type_field()

    # STEP 2: Keraksiz fieldlarni yashirish
    hide_unnecessary_customer_fields()

    frappe.db.commit()
    print("\n✅ Barcha Customer customizations tugadi!")


def setup_customer_type_field():
    """
    Customer DocType ga 'customer_type' field qo'shadi
    """

    # Agar field mavjud bo'lsa, o'tkazib yuborish
    if frappe.db.exists("Custom Field", {"dt": "Customer", "fieldname": "customer_type"}):
        print("⚠️ Customer Type field allaqachon mavjud")
        return

    try:
        # Custom field yaratish
        custom_field = frappe.new_doc("Custom Field")
        custom_field.dt = "Customer"
        custom_field.fieldname = "customer_type"
        custom_field.label = "Customer Type"
        custom_field.fieldtype = "Select"
        custom_field.options = "A\nB\nC"
        custom_field.default = "A"
        custom_field.description = (
            "A: Vaqtida to'laydiganlar | "
            "B: Kechiktirganlardan o'zganganlar | "
            "C: 30+ kun kechiktirganlar"
        )
        custom_field.insert_after = "credit_limit"
        custom_field.insert()

        print("✅ Customer Type field yaratildi!")

    except Exception as e:
        print(f"❌ Customer Type field yaratishda xato: {str(e)}")


def hide_unnecessary_customer_fields():
    """
    Customer formadan keraksiz fieldlarni yashirish
    """

    fields_to_hide = [
        "salutation",
        "auto_repeat_detail",
        "customer_group",
        "territory",
        "sales_team",
        "account_manager",
        "default_currency",
        "default_bank_account",
        "default_price_list",
        "internal_customer",  # Is Internal Customer checkbox
        "represents_company",
        "companies",
        "default_company",
        # Additional fields
        "internal_customer_section",  # Internal Customer section
        "more_info",  # More Information section
        "lead_name",  # From Lead
        "opportunity_name",  # From Opportunity
        "prospect_name",  # From Prospect
        "custom_auto_debit"  # Avtomatik Yechib Olish checkbox
    ]

    hidden_count = 0

    for field_name in fields_to_hide:
        property_setter_name = f"Customer-{field_name}-hidden"

        # Check if already exists
        if frappe.db.exists("Property Setter", property_setter_name):
            print(f"✓ Property Setter allaqachon mavjud: {property_setter_name}")
            continue

        try:
            # Create new Property Setter
            ps = frappe.get_doc({
                "doctype": "Property Setter",
                "name": property_setter_name,
                "doctype_or_field": "DocField",
                "doc_type": "Customer",
                "field_name": field_name,
                "property": "hidden",
                "value": "1",
                "property_type": "Check"
            })
            ps.insert(ignore_permissions=True)
            print(f"✓ Property Setter yaratildi: {property_setter_name}")
            hidden_count += 1

        except Exception as e:
            print(f"⚠️ {field_name} yashirishda xato: {str(e)}")

    print(f"\n✅ {hidden_count} ta field yashirildi!")


if __name__ == "__main__":
    run()
