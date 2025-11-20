# -*- coding: utf-8 -*-
"""
cash_flow_app/cash_flow_management/api/telegram_bot_api.py
Telegram Bot uchun 100% ishlaydigan, sinovdan o'tgan versiya
2025-yil noyabr – oxirgi to'g'rilangan
"""

import frappe
from frappe.utils import flt, formatdate, today, add_days, nowdate, cstr


# ============================================================
# 1. TELEGRAM ID ORQALI KIRISH (birinchi safar emas)
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_customer_by_telegram_id(telegram_id: str):
    if not telegram_id:
        return {"success": False, "message": "Telegram ID yo'q"}

    customer = frappe.db.get_value(
        "Customer",
        {"custom_telegram_id": str(telegram_id)},
        ["name", "customer_name", "custom_phone_1", "custom_passport_series"],
        as_dict=True
    )

    if not customer:
        return {"success": False, "message": "Bu Telegram hisobi tizimga bog'lanmagan"}

    return get_customer_by_id(customer.name, telegram_id)


# ============================================================
# 2. PASSPORT ORQALI KIRISH + AVTO BOG'LASH
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_customer_by_passport(passport_series: str, telegram_chat_id: str = None):
    if not passport_series:
        return {"success": False, "message": "Passport seriyasi kiritilmagan"}

    passport_series = cstr(passport_series).strip().upper()

    customer = frappe.db.get_value(
        "Customer",
        {"custom_passport_series": passport_series},
        ["name", "customer_name", "custom_telegram_id"],
        as_dict=True
    )

    if not customer:
        return {
            "success": False,
            "message": "Mijoz topilmadi",
            "message_uz": f"Passport {passport_series} bo'yicha mijoz topilmadi"
        }

    customer_id = customer.name

    # Telegram ID ni bir marta saqlash
    if telegram_chat_id and not customer.custom_telegram_id:
        frappe.db.set_value(
            "Customer", customer_id, "custom_telegram_id", str(telegram_chat_id)
        )
        frappe.db.commit()

    return get_customer_by_id(customer_id, telegram_chat_id or customer.custom_telegram_id)


# ============================================================
# 3. ASOSIY MA'LUMOTLAR – TO'LIQ
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_customer_by_id(customer_id: str, telegram_chat_id: str = None):
    if not customer_id or not frappe.db.exists("Customer", customer_id):
        return {"success": False, "message": "Mijoz topilmadi"}

    doc = frappe.get_doc("Customer", customer_id)

    # Telegram bog'lash (agar hali bo'lmasa)
    is_new_link = False
    if telegram_chat_id and not doc.custom_telegram_id:
        doc.db_set("custom_telegram_id", str(telegram_chat_id))
        is_new_link = True

    customer = {
        "customer_id": doc.name,
        "customer_name": doc.customer_name or "Noma'lum",
        "phone": doc.custom_phone_1 or "",
        "passport": doc.custom_passport_series or "",
        "classification": doc.customer_classification or "",
        "telegram_id": doc.custom_telegram_id or ""
    }

    contracts = get_customer_contracts_detailed(customer_id)
    upcoming = get_upcoming_payments(customer_id)

    return {
        "success": True,
        "customer": customer,
        "contracts": contracts.get("contracts", []),
        "next_payments": upcoming.get("payments", []),
        "is_new_link": is_new_link,
        "message": "Ma'lumotlar yuklandi"
    }


# ============================================================
# 4. BATAFSIL SHARTNOMALAR (Mahsulot + To'lov + Keyingi to'lov)
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_customer_contracts_detailed(customer_id: str):
    try:
        # Asosiy shartnomalar
        sales_orders = frappe.db.sql("""
            SELECT
                so.name, so.transaction_date,
                so.custom_grand_total_with_interest AS total,
                so.custom_downpayment_amount AS downpayment,
                so.advance_paid,
                ia.name AS ia_id,
                ia.custom_total_interest,
                ia.total_amount AS base_total
            FROM `tabSales Order` so
            LEFT JOIN `tabInstallment Application` ia ON ia.sales_order = so.name
            WHERE so.customer = %s AND so.docstatus = 1 AND so.status != 'Cancelled'
            ORDER BY so.transaction_date DESC
        """, customer_id, as_dict=True)

        if not sales_orders:
            return {"success": True, "contracts": []}

        so_ids = [so.name for so in sales_orders]
        ia_ids = [so.ia_id for so in sales_orders if so.ia_id]

        # Mahsulotlar (Installment Application)
        products = {}
        if ia_ids:
            items = frappe.db.sql("""
                SELECT parent, item_name, qty, amount AS base_amount, custom_imei AS imei, custom_notes AS notes
                FROM `tabInstallment Application Item`
                WHERE parent IN %s
            """, (ia_ids,), as_dict=True)

            for item in items:
                products.setdefault(item.parent, []).append(item)

        # To'lovlar tarixi
        payments = {}
        pay_data = frappe.db.sql("""
            SELECT custom_contract_reference, posting_date, paid_amount, mode_of_payment
            FROM `tabPayment Entry`
            WHERE custom_contract_reference IN %s AND docstatus = 1 AND payment_type = 'Receive'
            ORDER BY posting_date DESC
        """, (so_ids,), as_dict=True)

        for p in pay_data:
            contract = p.custom_contract_reference
            payments.setdefault(contract, []).append({
                "date": formatdate(p.posting_date, "dd.MM.yyyy") if p.posting_date else "",
                "amount": flt(p.paid_amount),
                "method": p.mode_of_payment or "Naqd"
            })

        # Keyingi to'lov
        next_pay = {}
        next_data = frappe.db.sql("""
            SELECT parent, due_date, payment_amount, outstanding, idx,
                   DATEDIFF(due_date, CURDATE()) AS days_left
            FROM `tabPayment Schedule`
            WHERE parent IN %s AND outstanding > 0
            ORDER BY parent, due_date
        """, (so_ids,), as_dict=True)

        for row in next_data:
            if row.parent not in next_pay:
                days = int(row.days_left or 0)
                status = "overdue" if days < 0 else ("today" if days == 0 else ("soon" if days <= 3 else "upcoming"))
                next_pay[row.parent] = {
                    "due_date": formatdate(row.due_date, "dd.MM.yyyy"),
                    "amount": flt(row.payment_amount),
                    "days_left": days,
                    "status": status,
                    "status_uz": "Kechikkan" if days < 0 else ("Bugun" if days == 0 else "Yaqinda")
                }

        # Yakuniy ro'yxat
        contracts = []
        for so in sales_orders:
            prods = []
            if so.ia_id and so.ia_id in products:
                base_total = flt(so.base_total or 0)
                total_interest = flt(so.custom_total_interest or 0)
                for item in products[so.ia_id]:
                    ratio = flt(item.base_amount) / base_total if base_total else 0
                    interest_part = total_interest * ratio
                    final_price = (flt(item.base_amount) + interest_part) / flt(item.qty) if item.qty else 0
                    prods.append({
                        "name": item.item_name,
                        "qty": flt(item.qty),
                        "price": flt(final_price, 2),
                        "imei": item.imei or "",
                        "notes": item.notes or ""
                    })

            contracts.append({
                "contract_id": so.name,
                "contract_date": formatdate(so.transaction_date, "dd.MM.yyyy"),
                "total_amount": flt(so.total),
                "downpayment": flt(so.downpayment),
                "paid": flt(so.advance_paid),
                "remaining": flt(so.total) - flt(so.advance_paid),
                "products": prods,
                "payments_history": payments.get(so.name, []),
                "next_payment": next_pay.get(so.name),
                "total_payments": len(payments.get(so.name, []))
            })

        return {"success": True, "contracts": contracts}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Telegram API Error")
        return {"success": False, "message": "Server xatosi"}


# ============================================================
# 5. KEYINGI TO'LOVLAR
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_upcoming_payments(customer_id: str):
    try:
        data = frappe.db.sql("""
            SELECT ps.parent AS contract_id, so.transaction_date, ps.due_date, ps.payment_amount,
                   ps.outstanding, ps.idx, DATEDIFF(ps.due_date, CURDATE()) AS days_left
            FROM `tabPayment Schedule` ps
            JOIN `tabSales Order` so ON so.name = ps.parent
            WHERE so.customer = %s AND so.docstatus = 1 AND ps.outstanding > 0
            ORDER BY ps.due_date
        """, customer_id, as_dict=True)

        result = []
        seen = set()
        for row in data:
            if row.contract_id in seen:
                continue
            seen.add(row.contract_id)
            days = int(row.days_left or 0)
            result.append({
                "contract_id": row.contract_id,
                "contract_date": formatdate(row.transaction_date, "dd.MM.yyyy"),
                "due_date": formatdate(row.due_date, "dd.MM.yyyy"),
                "amount": flt(row.payment_amount),
                "days_left": days,
                "status": "overdue" if days < 0 else ("today" if days == 0 else "upcoming"),
                "status_text": f"{abs(days)} kun kechikkan" if days < 0 else f"{days} kun qoldi"
            })

        return {"success": True, "payments": result}
    except Exception as e:
        return {"success": False, "message": "Xato"}


# ============================================================
# 6. TO'LOV JADVALI (bitta shartnoma)
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_payment_schedule(contract_id: str):
    rows = frappe.db.sql("""
        SELECT idx, due_date, payment_amount, paid_amount, outstanding,
               DATEDIFF(due_date, CURDATE()) AS days_left
        FROM `tabPayment Schedule`
        WHERE parent = %s ORDER BY idx
    """, contract_id, as_dict=True)

    schedule = []
    for r in rows:
        days = int(r.days_left or 0)
        status = "paid" if flt(r.outstanding) == 0 else ("partial" if flt(r.paid_amount) > 0 else "unpaid")
        schedule.append({
            "month": r.idx,
            "due_date": formatdate(r.due_date, "dd.MM.yyyy"),
            "amount": flt(r.payment_amount),
            "paid": flt(r.paid_amount),
            "outstanding": flt(r.outstanding),
            "status": status,
            "is_overdue": days < 0 and flt(r.outstanding) > 0
        })

    return {"success": True, "schedule": schedule}
