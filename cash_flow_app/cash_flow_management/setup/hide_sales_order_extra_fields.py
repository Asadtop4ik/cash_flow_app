"""
Hide unnecessary Sales Order fields:
- price_list, ignore_pricing_rule
- currency, currency section
- po_no (Customer PO)
- total_taxes_and_charges
- disable_rounded_total
- in_words
- rounding_adjustment, rounded_total
"""

import frappe

def hide_sales_order_extra_fields():
    """Hide pricing, currency, and totals fields"""
    
    fields_to_hide = [
        # Pricing
        "price_list",
        "ignore_pricing_rule",
        
        # Currency (default USD ko'rsatiladi)
        "currency_and_price_list",
        
        # Customer PO
        "po_no",
        "po_date",
        
        # Taxes
        "total_taxes_and_charges",
        "base_total_taxes_and_charges",
        
        # Rounding
        "disable_rounded_total",
        "rounding_adjustment",
        "base_rounding_adjustment",
        "rounded_total",
        "base_rounded_total",
        
        # In Words
        "in_words",
        "base_in_words",
        
        # Payment Terms (we use payment_schedule instead)
        "payment_terms_template",
        
        # Other
        "group_same_items",
        "language"
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
    print(f"✅ Sales Order: {len(property_setters)} fields hidden!")

if __name__ == "__main__":
    hide_sales_order_extra_fields()
