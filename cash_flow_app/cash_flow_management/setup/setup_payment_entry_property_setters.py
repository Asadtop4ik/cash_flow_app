"""
Hide unnecessary fields in Payment Entry for cleaner UI
"""

import frappe

def setup_payment_entry_property_setters():
    """Hide unnecessary fields in Payment Entry"""
    
    fields_to_hide = [
        "tax_withholding_category",
        "apply_tax_withholding_amount",
        "base_total_taxes_and_charges",
        "total_taxes_and_charges",
        "bank_account",
        "project",
        "cost_center",
        "letter_head",
        "print_heading",
        "deductions",
        "total_allocated_amount",
        "base_total_allocated_amount",
        "set_exchange_gain_loss",
        "unallocated_amount",
        "difference_amount",
        "custom_remarks"
    ]
    
    sections_to_hide = [
        "deductions_or_loss_section",
        "tax_section",
        "section_break_23"  # Printing Settings section
    ]
    
    property_setters = []
    
    # Hide fields
    for field in fields_to_hide:
        property_setters.append({
            "doctype": "Property Setter",
            "doctype_or_field": "DocField",
            "doc_type": "Payment Entry",
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
            "doc_type": "Payment Entry",
            "field_name": section,
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        })
    
    # Create Property Setters
    for prop in property_setters:
        try:
            # Check if exists
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
            print(f"⚠️ Error creating property setter for {prop['field_name']}: {e}")
    
    frappe.db.commit()
    print(f"✅ Payment Entry: {len(property_setters)} property setters created!")

if __name__ == "__main__":
    setup_payment_entry_property_setters()
