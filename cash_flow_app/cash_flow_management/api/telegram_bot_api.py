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

    # ✅ XAVFSIZLIK: Bir passport faqat bitta Telegram ID ga bog'lanadi
    if telegram_chat_id:
        existing_telegram_id = customer.custom_telegram_id

        # Agar allaqachon bog'langan bo'lsa va boshqa Telegram ID bo'lsa - XATO
        if existing_telegram_id and str(existing_telegram_id) != str(telegram_chat_id):
            return {
                "success": False,
                "message": "Bu passport allaqachon boshqa Telegram accountga bog'langan",
                "message_uz": f"❌ Xavfsizlik: Bu passport {passport_series} allaqachon boshqa accountga bog'langan.\n\n"
                             f"Agar bu sizning passportingiz bo'lsa, administrator bilan bog'laning.",
                "error_code": "PASSPORT_ALREADY_LINKED"
            }

        # Agar hali bog'lanmagan bo'lsa - bog'lash
        if not existing_telegram_id:
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

        # To'lovlar tarixi (Payment Entry Reference orqali - to'g'ri usul)
        payments = {}
        pay_data = frappe.db.sql("""
            SELECT
                per.reference_name AS contract_id,
                pe.posting_date,
                per.allocated_amount AS paid_amount,
                pe.mode_of_payment,
                pe.name AS payment_id
            FROM `tabPayment Entry` pe
            INNER JOIN `tabPayment Entry Reference` per
                ON per.parent = pe.name
            WHERE per.reference_doctype = 'Sales Order'
              AND per.reference_name IN %s
              AND pe.docstatus = 1
              AND pe.payment_type = 'Receive'
            ORDER BY pe.posting_date DESC
        """, (so_ids,), as_dict=True)

        for p in pay_data:
            contract = p.contract_id
            payments.setdefault(contract, []).append({
                "date": formatdate(p.posting_date, "dd.MM.yyyy") if p.posting_date else "",
                "amount": flt(p.paid_amount),
                "method": p.mode_of_payment or "Naqd",
                "payment_id": p.payment_id
            })

        # To'langan summa (Payment Entry dan hisoblash - eng ishonchli usul)
        paid_amounts = {}
        for contract_id in so_ids:
            total_paid = sum(p["amount"] for p in payments.get(contract_id, []))
            paid_amounts[contract_id] = total_paid

        # Keyingi to'lov (downpayment ni o'tkazib yuborish)
        next_pay = {}
        next_data = frappe.db.sql("""
            SELECT parent, due_date, payment_amount, outstanding, idx,
                   DATEDIFF(due_date, CURDATE()) AS days_left
            FROM `tabPayment Schedule`
            WHERE parent IN %s
              AND outstanding > 0
              AND idx > 1
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

            # ✅ To'g'ri to'langan summa - Payment Entry dan
            actual_paid = flt(paid_amounts.get(so.name, 0))

            contracts.append({
                "contract_id": so.name,
                "contract_date": formatdate(so.transaction_date, "dd.MM.yyyy"),
                "total_amount": flt(so.total),
                "downpayment": flt(so.downpayment),
                "paid": actual_paid,
                "remaining": flt(so.total) - actual_paid,
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


# ============================================================
# 7. TO'LOVLAR TARIXI + MAHSULOTLAR (Telegram bot uchun)
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_payment_history_with_products(contract_id: str):
    try:
        # 1. Shartnoma asosiy ma'lumotlari
        so = frappe.db.get_value(
            "Sales Order",
            contract_id,
            [
                "name",
                "transaction_date",
                "custom_grand_total_with_interest",
                "docstatus"
            ],
            as_dict=True
        )

        if not so or so.docstatus != 1:
            return {
                "success": False,
                "message": "Shartnoma topilmadi yoki bekor qilingan"
            }

        # 2. Mahsulotlar (Installment Application dan)
        ia = frappe.db.get_value(
            "Installment Application",
            {"sales_order": contract_id},
            [
                "name",
                "total_amount",
                "custom_total_interest"
            ],
            as_dict=True
        )

        products = []
        if ia:
            items = frappe.db.sql("""
                SELECT
                    item_name,
                    qty,
                    amount AS base_amount,
                    custom_imei AS imei,
                    custom_notes AS notes
                FROM `tabInstallment Application Item`
                WHERE parent = %s
            """, ia.name, as_dict=True)

            base_total = flt(ia.total_amount or 0)
            total_interest = flt(ia.custom_total_interest or 0)

            for item in items:
                # Har bir mahsulot uchun foizni hisoblash
                ratio = flt(item.base_amount) / base_total if base_total else 0
                interest_part = total_interest * ratio
                final_price = (flt(item.base_amount) + interest_part) / flt(item.qty) if item.qty else 0

                products.append({
                    "name": item.item_name,
                    "qty": flt(item.qty),
                    "price": flt(final_price, 2),
                    "total_price": flt(item.base_amount) + interest_part,
                    "imei": item.imei or "",
                    "notes": item.notes or ""
                })

        # 3. To'lovlar tarixi (Payment Entry Reference orqali)
        payments_data = frappe.db.sql("""
            SELECT
                pe.name AS payment_id,
                pe.posting_date,
                per.allocated_amount AS paid_amount,
                pe.mode_of_payment
            FROM `tabPayment Entry` pe
            INNER JOIN `tabPayment Entry Reference` per
                ON per.parent = pe.name
            WHERE per.reference_doctype = 'Sales Order'
              AND per.reference_name = %s
              AND pe.docstatus = 1
              AND pe.payment_type = 'Receive'
            ORDER BY pe.posting_date DESC
        """, contract_id, as_dict=True)

        payments = []
        total_paid = 0
        for p in payments_data:
            payment_amount = flt(p.paid_amount)
            total_paid += payment_amount
            payments.append({
                "date": formatdate(p.posting_date, "dd.MM.yyyy"),
                "amount": payment_amount,
                "method": p.mode_of_payment or "Naqd",
                "payment_id": p.payment_id
            })

        # 4. Natija
        return {
            "success": True,
            "contract": {
                "contract_id": so.name,
                "contract_date": formatdate(so.transaction_date, "dd.MM.yyyy"),
                "total_amount": flt(so.custom_grand_total_with_interest),
                "paid": total_paid,
                "remaining": flt(so.custom_grand_total_with_interest) - total_paid
            },
            "products": products,
            "payments": payments,
            "total_paid": total_paid,
            "total_payments": len(payments)
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Payment History Error")
        return {
            "success": False,
            "message": "Server xatosi - to'lovlar tarixini yuklashda muammo"
        }


# ============================================================
# 8. ESLATMALAR (REMINDERS) - Telegram bot button uchun
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_reminders_by_telegram_id(telegram_id: str):
    """
    Telegram ID orqali customerning eslatmalarini olish.

    Bu funksiya "Eslatmalar" button bosilganda ishga tushadi.
    """
    if not telegram_id:
        return {
            "success": False,
            "message": "Telegram ID yo'q",
            "error_code": "NO_TELEGRAM_ID"
        }

    try:
        # 1. Telegram ID orqali customerni topish
        customer = frappe.db.get_value(
            "Customer",
            {"custom_telegram_id": str(telegram_id)},
            ["name", "customer_name"],
            as_dict=True
        )

        if not customer:
            return {
                "success": False,
                "message": "Bu Telegram hisobi ERPNext mijoziga bog'lanmagan",
                "message_uz": "❌ Sizning Telegram hisobingiz ERPNext mijoziga bog'lanmagan.\n\nAvval /start bosib, passport raqamingizni kiriting.",
                "error_code": "NOT_LINKED"
            }

        # 2. Eslatmalar - yaqin muddat to'lovlari (30 kun ichida)
        reminders = frappe.db.sql("""
            SELECT
                ps.parent AS contract_id,
                so.transaction_date,
                ps.due_date,
                ps.payment_amount,
                ps.outstanding,
                ps.idx,
                DATEDIFF(ps.due_date, CURDATE()) AS days_left
            FROM `tabPayment Schedule` ps
            JOIN `tabSales Order` so ON so.name = ps.parent
            WHERE so.customer = %s
              AND so.docstatus = 1
              AND ps.outstanding > 0
              AND ps.idx > 1
              AND ps.due_date BETWEEN CURDATE() - INTERVAL 1 DAY AND CURDATE() + INTERVAL 30 DAY
            ORDER BY ps.due_date ASC
        """, customer.name, as_dict=True)

        result = []
        for row in reminders:
            days = int(row.days_left or 0)

            # Status va prioritet aniqlash
            if days < -1:
                status = "critically_overdue"
                status_uz = f"{abs(days)} kun kechikkan ⚠️"
                priority = "critical"
            elif days == -1:
                status = "overdue"
                status_uz = "1 kun kechikkan ⚠️"
                priority = "high"
            elif days == 0:
                status = "today"
                status_uz = "Bugun to'lash kerak! 🔴"
                priority = "urgent"
            elif days == 1:
                status = "tomorrow"
                status_uz = "Ertaga to'lash kerak 🟡"
                priority = "high"
            elif days <= 3:
                status = "soon"
                status_uz = f"{days} kun qoldi 🟢"
                priority = "medium"
            else:
                status = "upcoming"
                status_uz = f"{days} kun qoldi"
                priority = "low"

            result.append({
                "contract_id": row.contract_id,
                "contract_date": formatdate(row.transaction_date, "dd.MM.yyyy"),
                "due_date": formatdate(row.due_date, "dd.MM.yyyy"),
                "amount": flt(row.payment_amount),
                "outstanding": flt(row.outstanding),
                "days_left": days,
                "status": status,
                "status_uz": status_uz,
                "priority": priority,
                "payment_number": row.idx
            })

        return {
            "success": True,
            "customer_id": customer.name,
            "customer_name": customer.customer_name,
            "reminders": result,
            "total_reminders": len(result),
            "message": "Eslatmalar yuklandi"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Reminders Error")
        return {
            "success": False,
            "message": "Server xatosi - eslatmalarni yuklashda muammo"
        }


# ============================================================
# 9. TOLOV TARIXI - Telegram ID orqali
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_payment_history_by_telegram_id(telegram_id: str):
    """
    Telegram ID orqali customerning barcha to'lovlar tarixini olish.

    Bu funksiya "Tolov tarixi" button bosilganda ishga tushadi.
    """
    if not telegram_id:
        return {
            "success": False,
            "message": "Telegram ID yo'q",
            "error_code": "NO_TELEGRAM_ID"
        }

    try:
        # 1. Telegram ID orqali customerni topish
        customer = frappe.db.get_value(
            "Customer",
            {"custom_telegram_id": str(telegram_id)},
            ["name", "customer_name"],
            as_dict=True
        )

        if not customer:
            return {
                "success": False,
                "message": "Bu Telegram hisobi ERPNext mijoziga bog'lanmagan",
                "message_uz": "❌ Sizning Telegram hisobingiz ERPNext mijoziga bog'lanmagan.\n\nAvval /start bosib, passport raqamingizni kiriting.",
                "error_code": "NOT_LINKED"
            }

        # 2. Barcha shartnomalarni olish
        contracts = frappe.db.sql("""
            SELECT name, transaction_date, custom_grand_total_with_interest
            FROM `tabSales Order`
            WHERE customer = %s AND docstatus = 1 AND status != 'Cancelled'
            ORDER BY transaction_date DESC
        """, customer.name, as_dict=True)

        if not contracts:
            return {
                "success": True,
                "customer_id": customer.name,
                "customer_name": customer.customer_name,
                "contracts": [],
                "message": "Shartnomalar topilmadi"
            }

        so_ids = [c.name for c in contracts]

        # 3. Barcha to'lovlarni olish
        payments_data = frappe.db.sql("""
            SELECT
                per.reference_name AS contract_id,
                pe.name AS payment_id,
                pe.posting_date,
                per.allocated_amount AS paid_amount,
                pe.mode_of_payment,
                pe.remarks
            FROM `tabPayment Entry` pe
            INNER JOIN `tabPayment Entry Reference` per
                ON per.parent = pe.name
            WHERE per.reference_doctype = 'Sales Order'
              AND per.reference_name IN %s
              AND pe.docstatus = 1
              AND pe.payment_type = 'Receive'
            ORDER BY pe.posting_date DESC
        """, (so_ids,), as_dict=True)

        # 4. Shartnomalar bo'yicha guruhlash
        contracts_with_payments = []
        for contract in contracts:
            contract_payments = [
                {
                    "payment_id": p.payment_id,
                    "date": formatdate(p.posting_date, "dd.MM.yyyy"),
                    "amount": flt(p.paid_amount),
                    "method": p.mode_of_payment or "Naqd",
                    "remarks": p.remarks or ""
                }
                for p in payments_data if p.contract_id == contract.name
            ]

            total_paid = sum(p["amount"] for p in contract_payments)

            contracts_with_payments.append({
                "contract_id": contract.name,
                "contract_date": formatdate(contract.transaction_date, "dd.MM.yyyy"),
                "total_amount": flt(contract.custom_grand_total_with_interest),
                "paid": total_paid,
                "remaining": flt(contract.custom_grand_total_with_interest) - total_paid,
                "payments": contract_payments,
                "total_payments": len(contract_payments)
            })

        return {
            "success": True,
            "customer_id": customer.name,
            "customer_name": customer.customer_name,
            "contracts": contracts_with_payments,
            "total_contracts": len(contracts_with_payments),
            "message": "To'lovlar tarixi yuklandi"
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Payment History By Telegram ID Error")
        return {
            "success": False,
            "message": "Server xatosi - to'lovlar tarixini yuklashda muammo"
        }


# ============================================================
# 10. SHARTNOMALARIM - Telegram ID orqali
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_my_contracts_by_telegram_id(telegram_id: str):
    """
    Telegram ID orqali customerning barcha shartnomalarini olish.

    Bu funksiya "Mening shartnomalarim" button bosilganda ishga tushadi.
    """
    if not telegram_id:
        return {
            "success": False,
            "message": "Telegram ID yo'q",
            "error_code": "NO_TELEGRAM_ID"
        }

    try:
        # 1. Telegram ID orqali customerni topish
        customer = frappe.db.get_value(
            "Customer",
            {"custom_telegram_id": str(telegram_id)},
            ["name", "customer_name"],
            as_dict=True
        )

        if not customer:
            return {
                "success": False,
                "message": "Bu Telegram hisobi ERPNext mijoziga bog'lanmagan",
                "message_uz": "❌ Sizning Telegram hisobingiz ERPNext mijoziga bog'lanmagan.\n\nAvval /start bosib, passport raqamingizni kiriting.",
                "error_code": "NOT_LINKED"
            }

        # 2. get_customer_contracts_detailed funksiyasidan foydalanish
        contracts_result = get_customer_contracts_detailed(customer.name)

        if not contracts_result.get("success"):
            return contracts_result

        # 3. Natijaga customer ma'lumotlarini qo'shish
        contracts_result["customer_id"] = customer.name
        contracts_result["customer_name"] = customer.customer_name
        contracts_result["total_contracts"] = len(contracts_result.get("contracts", []))

        return contracts_result

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get My Contracts By Telegram ID Error")
        return {
            "success": False,
            "message": "Server xatosi - shartnomalarni yuklashda muammo"
        }


# ============================================================
# 11. AVTOMATIK ESLATMALAR (SCHEDULED NOTIFICATIONS)
# ============================================================

def send_payment_reminders():
    """
    Har kuni avtomatik ravishda eslatmalarni yuborish.

    Bu funksiya scheduled job sifatida ishga tushadi (har kuni 09:00 da).

    ESLATMA VAQTLARI:
    - 3 kun oldin
    - 1 kun oldin
    - To'lov kuni
    - 1 kun keyin (kechikkan)
    """
    try:
        import requests
        from frappe.utils import now_datetime

        # Telegram bot API URL ni config dan olish
        bot_token = frappe.db.get_single_value("Cash Flow Settings", "telegram_bot_token")

        if not bot_token:
            frappe.log_error("Telegram bot token topilmadi", "Payment Reminder Error")
            return

        # To'lov sanalari bo'yicha eslatmalar
        reminder_configs = [
            {"days": 3, "message_template": "⏰ Eslatma: {days} kun ichida to'lov muddati tugaydi!"},
            {"days": 1, "message_template": "⚠️ Muhim: Ertaga to'lov muddati tugaydi!"},
            {"days": 0, "message_template": "🔴 DIQQAT: Bugun to'lov muddati!"},
            {"days": -1, "message_template": "❌ To'lov muddati o'tgan! Iltimos, tezda to'lang!"}
        ]

        for config in reminder_configs:
            days = config["days"]
            target_date = add_days(today(), days)

            # Shu sanada to'lov qilishi kerak bo'lgan customerlar
            payments = frappe.db.sql("""
                SELECT
                    ps.parent AS contract_id,
                    ps.due_date,
                    ps.payment_amount,
                    ps.outstanding,
                    ps.idx,
                    so.customer,
                    c.customer_name,
                    c.custom_telegram_id
                FROM `tabPayment Schedule` ps
                JOIN `tabSales Order` so ON so.name = ps.parent
                JOIN `tabCustomer` c ON c.name = so.customer
                WHERE ps.due_date = %s
                  AND ps.outstanding > 0
                  AND ps.idx > 1
                  AND so.docstatus = 1
                  AND c.custom_telegram_id IS NOT NULL
                  AND c.custom_telegram_id != ''
                ORDER BY c.name
            """, target_date, as_dict=True)

            # Har bir customer uchun eslatma yuborish
            for payment in payments:
                telegram_id = payment.custom_telegram_id

                if not telegram_id:
                    continue

                # Xabar tayyorlash
                message = _format_reminder_message(payment, config["message_template"], days)

                # Telegram bot API ga yuborish
                try:
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    data = {
                        "chat_id": telegram_id,
                        "text": message,
                        "parse_mode": "HTML"
                    }

                    response = requests.post(url, json=data, timeout=10)

                    if response.status_code == 200:
                        # Log qilish - muvaffaqiyatli yuborildi
                        _log_notification(
                            customer_id=payment.customer,
                            telegram_id=telegram_id,
                            contract_id=payment.contract_id,
                            notification_type=f"reminder_day_{days}",
                            status="sent",
                            message=message
                        )
                    else:
                        # Xato
                        frappe.log_error(
                            f"Telegram API xatosi: {response.text}",
                            f"Reminder Send Failed - {payment.customer}"
                        )

                except Exception as send_error:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f"Reminder Send Error - {payment.customer}"
                    )

        frappe.db.commit()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Send Payment Reminders Error")


def _format_reminder_message(payment, template, days):
    """Eslatma xabarini formatlash"""
    abs_days = abs(days)

    message = f"""
<b>💳 TO'LOV ESLATMASI</b>

{template.format(days=abs_days)}

━━━━━━━━━━━━━━━━━━━━
<b>📄 Shartnoma:</b> {payment.contract_id}
<b>📅 To'lov sanasi:</b> {formatdate(payment.due_date, "dd.MM.yyyy")}
<b>💰 To'lov summasi:</b> {frappe.utils.fmt_money(payment.payment_amount, currency="UZS")}
<b>📊 Qoldiq:</b> {frappe.utils.fmt_money(payment.outstanding, currency="UZS")}
<b>🔢 To'lov №:</b> {payment.idx - 1}
━━━━━━━━━━━━━━━━━━━━

Iltimos, to'lovni o'z vaqtida amalga oshiring!

Savollar uchun: /help
"""

    return message.strip()


def _log_notification(customer_id, telegram_id, contract_id, notification_type, status, message):
    """Notification logini saqlash"""
    try:
        # Notification Log doctype yaratish kerak (agar bo'lmasa)
        # Hozircha faqat frappe.log_error ga yozamiz
        log_message = f"""
Customer: {customer_id}
Telegram ID: {telegram_id}
Contract: {contract_id}
Type: {notification_type}
Status: {status}
Message: {message}
"""
        frappe.log_error(log_message, "Notification Sent Log")

    except Exception as e:
        pass


@frappe.whitelist(allow_guest=True)
def get_customers_needing_reminders(days: int = 3):
    """
    Test uchun - qaysi customerlar eslatma olishi kerakligini ko'rish.

    Bu funksiya manual test qilish uchun.
    """
    try:
        target_date = add_days(today(), int(days))

        customers = frappe.db.sql("""
            SELECT
                ps.parent AS contract_id,
                ps.due_date,
                ps.payment_amount,
                ps.outstanding,
                ps.idx,
                so.customer,
                c.customer_name,
                c.custom_telegram_id,
                c.custom_phone_1
            FROM `tabPayment Schedule` ps
            JOIN `tabSales Order` so ON so.name = ps.parent
            JOIN `tabCustomer` c ON c.name = so.customer
            WHERE ps.due_date = %s
              AND ps.outstanding > 0
              AND ps.idx > 1
              AND so.docstatus = 1
            ORDER BY c.name
        """, target_date, as_dict=True)

        result = []
        for customer in customers:
            result.append({
                "customer_id": customer.customer,
                "customer_name": customer.customer_name,
                "telegram_id": customer.custom_telegram_id or "Bog'lanmagan",
                "phone": customer.custom_phone_1 or "",
                "contract_id": customer.contract_id,
                "due_date": formatdate(customer.due_date, "dd.MM.yyyy"),
                "amount": flt(customer.payment_amount),
                "outstanding": flt(customer.outstanding),
                "payment_number": customer.idx - 1,
                "has_telegram": bool(customer.custom_telegram_id)
            })

        return {
            "success": True,
            "target_date": formatdate(target_date, "dd.MM.yyyy"),
            "days": days,
            "customers": result,
            "total": len(result),
            "with_telegram": sum(1 for c in result if c["has_telegram"]),
            "without_telegram": sum(1 for c in result if not c["has_telegram"])
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Customers Needing Reminders Error")
        return {
            "success": False,
            "message": "Server xatosi"
        }
