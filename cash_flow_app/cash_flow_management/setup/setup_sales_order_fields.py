"""
Setup custom fields and property setters for Sales Order
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_sales_order_fields():
    """Add custom fields to Sales Order"""
    
    custom_fields = {
        "Sales Order": [
            {
                "fieldname": "custom_contract_info_section",
                "label": "Shartnoma Ma'lumotlari",
                "fieldtype": "Section Break",
                "insert_after": "customer_name",
                "collapsible": 1
            },
            {
                "fieldname": "custom_contract_type",
                "label": "Shartnoma Turi",
                "fieldtype": "Select",
                "options": "Naqd\nNasiya",
                "insert_after": "custom_contract_info_section",
                "default": "Nasiya",
                "reqd": 0,
                "in_list_view": 1
            },
            {
                "fieldname": "custom_downpayment_amount",
                "label": "Boshlang'ich To'lov (USD)",
                "fieldtype": "Currency",
                "options": "USD",
                "insert_after": "custom_contract_type",
                "read_only": 1,
                "bold": 1
            },
            {
                "fieldname": "custom_total_interest",
                "label": "Foyda Summasi (USD)",
                "fieldtype": "Currency",
                "options": "USD",
                "insert_after": "custom_downpayment_amount",
                "read_only": 1,
                "bold": 1
            },
            {
                "fieldname": "custom_grand_total_with_interest",
                "label": "Jami To'lov (USD)",
                "fieldtype": "Currency",
                "options": "USD",
                "insert_after": "custom_total_interest",
                "read_only": 1,
                "bold": 1
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
    
    print("✅ Sales Order custom fields created!")

def setup_sales_order_property_setters():
    """Hide unnecessary fields in Sales Order"""
    
    fields_to_hide = [
        # Tax section
        "taxes_and_charges",
        "tax_category",
        "shipping_rule",
        "incoterm",
        "named_place",
        "taxes",
        "other_charges_calculation",
        
        # Pricing
        "pricing_rules",
        "apply_discount_on",
        "base_discount_amount",
        "additional_discount_percentage",
        "discount_amount",
        "coupon_code",
        
        # Loyalty
        "loyalty_points",
        "loyalty_amount",
        
        # Sales Team
        "sales_partner",
        "commission_rate",
        "total_commission",
        "sales_team",
        
        # Other
        "source",
        "campaign",
        "auto_repeat"
    ]
    
    sections_to_hide = [
        "pricing_rule_details",
        "packing_list",
        "section_break_77",  # Raw Materials
        "subscription_section"
    ]
    
    property_setters = []
    
    # Hide fields
    for field in fields_to_hide:
        property_setters.append({
            "doctype": "Property Setter",
            "doctype_or_field": "DocField",
            "doc_type": "Sales Order",
            "field_name": field,
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        })
    
    # Hide sections
    for section in sections_to_hide:
        property_setters.append({
            "doctype": "Property Setter",
            "doctype_or_field": "DocField",
            "doc_type": "Sales Order",
            "field_name": section,
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        })
    
    # Create Property Setters
    for prop in property_setters:
        try:
            existing = frappe.db.exists("Property Setter", {
                "doc_type": prop["doc_type"],
                "field_name": prop["field_name"],
                "property": prop["property"]
            })
            
            if existing:
                frappe.db.set_value("Property Setter", existing, "value", prop["value"])
            else:
                doc = frappe.get_doc(prop)
                doc.insert(ignore_permissions=True)
        except Exception as e:
            print(f"⚠️ Error: {prop['field_name']}: {e}")
    
    frappe.db.commit()
    print(f"✅ Sales Order: {len(property_setters)} property setters created!")

if __name__ == "__main__":
    setup_sales_order_fields()
    setup_sales_order_property_setters()
