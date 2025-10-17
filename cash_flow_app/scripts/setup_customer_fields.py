"""
Script to create Property Setters for hiding Customer fields
Run with: bench --site asadstack.com execute cash_flow_app.scripts.setup_customer_fields.run
"""

import frappe

def run():
    """Create Property Setters to hide unnecessary Customer fields"""
    
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
        # Additional fields from user request
        "internal_customer_section",  # Internal Customer section
        "more_info",  # More Information section
        "lead_name",  # From Lead
        "opportunity_name",  # From Opportunity
        "prospect_name",  # From Prospect
        "custom_auto_debit"  # Avtomatik Yechib Olish checkbox
    ]
    
    for field_name in fields_to_hide:
        property_setter_name = f"Customer-{field_name}-hidden"
        
        # Check if already exists
        if frappe.db.exists("Property Setter", property_setter_name):
            print(f"✓ Property Setter already exists: {property_setter_name}")
            continue
        
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
        print(f"✓ Created Property Setter: {property_setter_name}")
    
    frappe.db.commit()
    print("\n✅ All Customer field Property Setters created successfully!")
    print("Now run: bench --site asadstack.com export-fixtures")
