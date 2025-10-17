"""
Script to list Item DocType structure
"""

import frappe

def run():
    meta = frappe.get_meta("Item")
    
    print("=== ITEM DOCTYPE STRUCTURE ===\n")
    
    for field in meta.fields:
        if field.fieldtype == "Tab Break":
            print(f"\n[TAB] {field.label} - fieldname: {field.fieldname}")
        elif field.fieldtype == "Section Break":
            hidden = " (HIDDEN)" if field.hidden else ""
            print(f"  [SECTION] {field.label or 'No Label'} - fieldname: {field.fieldname}{hidden}")
        elif field.fieldtype not in ["Column Break", "HTML"]:
            hidden = " (HIDDEN)" if field.hidden else ""
            reqd = " *" if field.reqd else ""
            print(f"    - {field.fieldname} ({field.fieldtype}): {field.label}{reqd}{hidden}")
