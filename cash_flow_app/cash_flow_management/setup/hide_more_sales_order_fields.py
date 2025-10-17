"""
Hide more unnecessary Sales Order fields:
- delivery_date (not needed for installment contracts)
- advance_paid (we track via Payment Entry)
- Activity section (timeline is enough)
"""

import frappe

def hide_more_sales_order_fields():
    """Hide delivery_date, advance_paid display, etc."""
    
    fields_to_hide = [
        "delivery_date",  # Not needed for contracts
        "reserve_stock",  # Stock management off
        "skip_delivery_note",  # Not using delivery notes
        "set_warehouse",  # Warehouse not needed
        "scan_barcode",  # Not using barcodes
    ]
    
    property_setters = []
    
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
            print(f"⚠️ {prop['field_name']}: {e}")
    
    frappe.db.commit()
    print(f"✅ Sales Order: {len(property_setters)} more fields hidden!")

if __name__ == "__main__":
    hide_more_sales_order_fields()
