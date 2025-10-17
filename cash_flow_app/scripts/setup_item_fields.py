"""
Script to create Property Setters for hiding Item fields
Run with: bench --site asadstack.com execute cash_flow_app.scripts.setup_item_fields.run
"""

import frappe

def run():
    """Create Property Setters to hide unnecessary Item fields and tabs"""
    
    # Complete tabs to hide
    tabs_to_hide = [
        "dashboard_tab",  # Dashboard tab
        "inventory_section",  # Inventory tab
        "variants_section",  # Variants tab
        "accounting",  # Accounting tab
        "purchasing_tab",  # Purchasing tab
        "sales_details",  # Sales tab
        "item_tax_section_break",  # Tax tab
        "quality_tab",  # Quality tab
    ]
    
    # ALL default fields in Details tab to hide (user only wants custom fields)
    fields_to_hide = [
        # Basic fields
        "naming_series",
        "item_code",  # Hide Item Code, use custom_product_name instead
        "item_name",  # Hide Item Name
        "item_group",  # Hide Item Group
        "stock_uom",  # Hide Default Unit of Measure
        "disabled",  # Hide Disabled checkbox
        "allow_alternative_item",  # Hide Allow Alternative Item
        "is_stock_item",  # Hide Maintain Stock
        "has_variants",  # Hide Has Variants
        "opening_stock",  # Hide Opening Stock
        "valuation_rate",  # Hide Valuation Rate
        "standard_rate",  # Hide Standard Selling Rate
        "is_fixed_asset",  # Hide Is Fixed Asset
        "auto_create_assets",
        "is_grouped_asset",
        "asset_category",
        "asset_naming_series",
        "over_delivery_receipt_allowance",
        "over_billing_allowance",
        "image",
        # Description section
        "section_break_11",  # Description section
        "description",  # Description field
        "brand",  # Brand field
        # Units of Measure section
        "unit_of_measure_conversion",  # Units of Measure section
        "uoms",  # UOMs table
    ]
    
    all_fields = tabs_to_hide + fields_to_hide
    
    for field_name in all_fields:
        property_setter_name = f"Item-{field_name}-hidden"
        
        # Check if already exists
        if frappe.db.exists("Property Setter", property_setter_name):
            print(f"✓ Property Setter already exists: {property_setter_name}")
            continue
        
        # Create new Property Setter
        ps = frappe.get_doc({
            "doctype": "Property Setter",
            "name": property_setter_name,
            "doctype_or_field": "DocField",
            "doc_type": "Item",
            "field_name": field_name,
            "property": "hidden",
            "value": "1",
            "property_type": "Check"
        })
        ps.insert(ignore_permissions=True)
        print(f"✓ Created Property Setter: {property_setter_name}")
    
    frappe.db.commit()
    print("\n✅ All Item field Property Setters created successfully!")
    print("Now run: bench --site asadstack.com export-fixtures")
