import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_installment_applications(api_key=None, api_secret=None):
    """Google Sheets uchun Installment Application ma'lumotlarini qaytarish"""
    
    try:
        # API autentifikatsiya
        if api_key and api_secret:
            # User API Key orqali topish
            user = frappe.db.get_value(
                "User",
                {"api_key": api_key, "api_secret": api_secret},
                ["name", "enabled"],
                as_dict=True
            )
            
            if user and user.enabled:
                frappe.set_user(user.name)
            else:
                return {
                    "success": False,
                    "error": "Invalid API credentials"
                }
        
        # Ma'lumotlarni olish
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
        frappe.log_error(frappe.get_traceback(), "Google Sheets API Error")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
def get_payment_schedule(installment_app_id, api_key=None, api_secret=None):
    """To'lov jadvalini olish"""
    
    try:
        # API autentifikatsiya
        if api_key and api_secret:
            user = frappe.db.get_value(
                "User",
                {"api_key": api_key, "api_secret": api_secret},
                ["name", "enabled"],
                as_dict=True
            )
            
            if user and user.enabled:
                frappe.set_user(user.name)
            else:
                return {
                    "success": False,
                    "error": "Invalid API credentials"
                }
        
        # To'lov jadvalini olish
        doc = frappe.get_doc("Installment Application", installment_app_id)
        
        schedule = []
        for row in doc.payment_schedule:
            schedule.append({
                "due_date": str(row.due_date) if row.due_date else None,
                "payment_amount": row.payment_amount,
                "status": getattr(row, 'status', 'Pending')
            })
        
        return {
            "success": True,
            "installment_app": installment_app_id,
            "customer": doc.customer_name,
            "data": schedule
        }
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Google Sheets Payment Schedule Error")
        return {
            "success": False,
            "error": str(e)
        }
