# -*- coding: utf-8 -*-
"""
Sales Order PDF Generator - HTML template ishlatadi
"""
import frappe
from frappe import _
from datetime import datetime


@frappe.whitelist()
def generate_contract_pdf(sales_order_name):
    """Sales Order uchun shartnoma PDF yaratish - HTML template ishlatadi"""
    try:
        if not frappe.db.exists("Sales Order", sales_order_name):
            return {"success": False, "message": "Sales Order topilmadi"}
        
        so = frappe.get_doc("Sales Order", sales_order_name)
        customer = frappe.get_doc("Customer", so.customer)
        company = frappe.get_doc("Company", so.company)
        
        # Installment Application
        installment_app = frappe.db.get_value(
            "Installment Application",
            {"sales_order": sales_order_name},
            ["name", "custom_grand_total_with_interest", "monthly_payment", "downpayment_amount", "installment_months"],
            as_dict=True
        )
        
        if not installment_app:
            use_sales_order = True
            installment_app = {
                'name': sales_order_name,
                'total_price': so.grand_total,
                'monthly_payment': so.grand_total,
                'initial_payment': so.advance_paid or 0,
                'installment_period': 1
            }
        else:
            use_sales_order = False
            
        # Ma'lumotlarni tayyorlash
        context = prepare_contract_data(so, customer, company, installment_app, use_sales_order)
        
        # HTML template orqali PDF yaratish
        html = frappe.render_template("cash_flow_app/cash_flow_management/print_format/shartnoma/shartnoma.html", context)
        
        # PDF yaratish
        from frappe.utils.pdf import get_pdf
        pdf = get_pdf(html)
        
        # PDF ni saqlash
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"shartnoma_{so.name}_{timestamp}.pdf"
        
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": pdf_filename,
            "attached_to_doctype": "Sales Order",
            "attached_to_name": so.name,
            "folder": "Home/Attachments",
            "is_private": 1,
            "content": pdf
        })
        file_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        return {
            "success": True,
            "file_url": file_doc.file_url,
            "message": "Shartnoma PDF muvaffaqiyatli yaratildi!"
        }
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Sales Order PDF Xatosi")
        return {"success": False, "message": f"Xatolik: {str(e)}"}


def prepare_contract_data(so, customer, company, installment_app, use_sales_order):
    """Ma'lumotlarni HTML template uchun tayyorlash"""
    from frappe.utils import flt
    
    # Sana
    date_str = so.transaction_date.strftime("%d.%m.%Y") if so.transaction_date else ""
    date_day = so.transaction_date.strftime("%d") if so.transaction_date else ""
    
    months_uz = {
        "01": "Yanvar", "02": "Fevral", "03": "Mart", "04": "Aprel",
        "05": "May", "06": "Iyun", "07": "Iyul", "08": "Avgust",
        "09": "Sentabr", "10": "Oktabr", "11": "Noyabr", "12": "Dekabr"
    }
    month_uz = months_uz.get(so.transaction_date.strftime("%m"), "") if so.transaction_date else ""
    year_uz = so.transaction_date.strftime("%Y") if so.transaction_date else ""
    date_full_uz = f"«{date_day}» {month_uz} {year_uz}"
    
    # Customer
    customer_name = customer.customer_name or customer.name
    customer_phone = customer.get('custom_phone') or customer.get('custom_phone_1') or ""
    customer_pinfl = customer.get('custom_pinfl') or ""
    
    customer_passport = ""
    if customer.get('custom_passport_series'):
        customer_passport = customer.get('custom_passport_series')
        if customer.get('custom_passport'):
            customer_passport = f"{customer.get('custom_passport_series')} {customer.get('custom_passport')}"
    
    customer_address = customer.get('custom_residence_address') or customer.get('custom_passport_address') or ""
    
    # Items va installment_months uchun Installment Application doc olish
    items = []
    installment_period = 1
    
    # Installment Application'dan installment_months va items olish
    inst_app_doc = frappe.get_doc("Installment Application", installment_app['name'])
    installment_period = int(inst_app_doc.get('installment_months', 0))
    if not installment_period:
        installment_period = int(inst_app_doc.get('har_oy_gayi_sana_tollanadi', 1))
    
    # Items ni har doim Installment Application dan olish (foyda bilan)
    # Umumiy foyda har bir itemga taqsimlanadi
    total_amount = flt(inst_app_doc.get('total_amount', 0))
    grand_total_with_interest = flt(inst_app_doc.get('custom_grand_total_with_interest', 0))
    total_interest = grand_total_with_interest - total_amount
    
    for idx, item in enumerate(inst_app_doc.items, 1):
        quantity = int(flt(item.get('qty', 1)))
        rate = flt(item.get('rate', 0))
        amount = flt(item.get('amount', 0))
        
        # Har bir item uchun foydani proporsional hisoblash
        if total_amount > 0:
            item_interest = (amount / total_amount) * total_interest
            price_with_interest = rate + (item_interest / quantity)
            total_with_interest = amount + item_interest
        else:
            price_with_interest = rate
            total_with_interest = amount
        
        items.append({
            'idx': idx,
            'item_name': item.get('item_name', ''),
            'quantity': quantity,
            'price': int(price_with_interest),
            'total': int(total_with_interest)
        })
    
    # Narxlar
    total_price = int(flt(installment_app.get('custom_grand_total_with_interest', 0)))
    monthly_payment = int(flt(installment_app.get('monthly_payment', 0)))
    initial_payment = int(flt(installment_app.get('downpayment_amount', 0)))
    remaining_amount = total_price - initial_payment
    
    # To'lov jadvali
    payment_schedule = []
    schedule_items = frappe.get_all(
        "Payment Schedule",
        filters={"parent": installment_app.get('name')},
        fields=["due_date", "payment_amount"],
        order_by="due_date"
    )
    
    for idx, item in enumerate(schedule_items, 1):
        payment_schedule.append({
            'idx': idx,
            'date': frappe.utils.formatdate(item.due_date, "dd.MM.yyyy") if item.due_date else "",
            'amount': int(flt(item.payment_amount))
        })
    
    return {
        'so': so,
        'customer': customer,
        'company': company,
        'customer_name': customer_name,
        'customer_phone': customer_phone,
        'customer_pinfl': customer_pinfl,
        'customer_passport': customer_passport,
        'customer_address': customer_address,
        'date_str': date_str,
        'date_full_uz': date_full_uz,
        'items': items,
        'total_price': total_price,
        'monthly_payment': monthly_payment,
        'initial_payment': initial_payment,
        'remaining_amount': remaining_amount,
        'installment_months': installment_period,
        'payment_schedule': payment_schedule
    }
