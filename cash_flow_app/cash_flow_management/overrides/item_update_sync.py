"""
Item Update Sync
When Item is updated, sync changes to Installment Application Item child table
"""

import frappe
from frappe import _

def on_update_item(doc, method=None):
    """
    Sync Item changes to Installment Application Item
    Updates IMEI and other fields in draft Installment Applications
    """
    if not doc.custom_imei:
        return
    
    try:
        # Find all Installment Application Items that reference this Item
        # Only update DRAFT documents (docstatus = 0)
        installment_items = frappe.db.sql("""
            SELECT 
                iai.name,
                iai.parent,
                ia.docstatus,
                ia.amended_from
            FROM 
                `tabInstallment Application Item` iai
            INNER JOIN 
                `tabInstallment Application` ia ON iai.parent = ia.name
            WHERE 
                iai.item_code = %(item_code)s
                AND ia.docstatus = 0
        """, {'item_code': doc.name}, as_dict=1)
        
        if not installment_items:
            return
        
        updated_count = 0
        for item in installment_items:
            # Update the child table row (use 'imei' not 'custom_imei')
            frappe.db.set_value(
                'Installment Application Item',
                item.name,
                'imei',
                doc.custom_imei,
                update_modified=False
            )
            updated_count += 1
            
            # Clear cache for parent document
            frappe.clear_cache(doctype='Installment Application', name=item.parent)
        
        if updated_count > 0:
            frappe.db.commit()
            frappe.msgprint(
                _("✅ IMEI yangilandi: {0} ta Installment Application'da").format(updated_count),
                alert=True,
                indicator='green'
            )
            
            frappe.logger().info(
                f"Item {doc.name}: Updated IMEI in {updated_count} Installment Application Items"
            )
    
    except Exception as e:
        frappe.log_error(
            message=f"Error syncing Item {doc.name} to Installment Applications: {str(e)}",
            title="Item Update Sync Error"
        )
