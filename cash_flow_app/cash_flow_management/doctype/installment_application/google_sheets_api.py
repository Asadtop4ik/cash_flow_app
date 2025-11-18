import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_installment_applications(api_key=None, api_secret=None):
    """Google Sheets uchun Installment Application ma'lumotlarini qaytarish"""
    
    # API autentifikatsiya
    if not api_key or not api_secret:
        frappe.throw(_("API Key va Secret talab qilinadi"))
    
    # API key tekshirish
    try:
        user = frappe.db.get_value("User", 
            {"api_key": api_key, "api_secret": api_secret}, 
            ["name", "enabled"], 
            as_dict=True)
        
        if not user or not user.enabled:
            frappe.throw(_("API autentifikatsiya xato"))
            
        frappe.set_user(user.name)
    except Exception as e:
        frappe.throw(_("API autentifikatsiya xato: {0}").format(str(e)))
    
    # Ma'lumotlarni olish
    try:
        data = frappe.get_all(
            "Installment Application",
            fields=[
                "name",
                "customer",
                "customer_name",
                "transaction_date",
                "status",
                "custom_grand_total_with_interest",
                "downpayment_amount",
                "finance_amount",
                "monthly_payment",
                "installment_months"
            ],
            order_by="creation desc",
            limit_page_length=1000
        )
        
        return {
            "success": True,
            "count": len(data),
            "data": data
        }
    except Exception as e:
        frappe.log_error(f"Google Sheets API Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
def get_payment_schedule(installment_app_id, api_key=None, api_secret=None):
    """To'lov jadvalini olish"""
    
    # API autentifikatsiya
    if not api_key or not api_secret:
        frappe.throw(_("API Key va Secret talab qilinadi"))
    
    try:
        user = frappe.db.get_value("User", 
            {"api_key": api_key, "api_secret": api_secret}, 
            ["name", "enabled"], 
            as_dict=True)
        
        if not user or not user.enabled:
            frappe.throw(_("API autentifikatsiya xato"))
            
        frappe.set_user(user.name)
    except Exception as e:
        frappe.throw(_("API autentifikatsiya xato: {0}").format(str(e)))
    
    # To'lov jadvalini olish
    try:
        doc = frappe.get_doc("Installment Application", installment_app_id)
        
        schedule = []
        for row in doc.payment_schedule:
            schedule.append({
                "due_date": row.due_date,
                "payment_amount": row.payment_amount,
                "status": row.status if hasattr(row, 'status') else None
            })
        
        return {
            "success": True,
            "installment_app": installment_app_id,
            "customer": doc.customer_name,
            "data": schedule
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
