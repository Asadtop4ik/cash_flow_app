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

        # To'lovlar tarixi (custom_contract_reference orqali)
        # ✅ Pay va Receive turlarini ajratib olish
        payments = {}
        pay_data = frappe.db.sql("""
            SELECT
                custom_contract_reference AS contract_id,
                posting_date,
                paid_amount,
                mode_of_payment,
                name AS payment_id,
                payment_type
            FROM `tabPayment Entry`
            WHERE custom_contract_reference IN %s
              AND docstatus = 1
              AND payment_type IN ('Receive', 'Pay')
            ORDER BY posting_date DESC
        """, (so_ids,), as_dict=True)

        for p in pay_data:
            contract = p.contract_id
            # ✅ Pay bo'lsa manfiy, Receive bo'lsa musbat
            amount = flt(p.paid_amount) if p.payment_type == 'Receive' else -flt(p.paid_amount)
            payments.setdefault(contract, []).append({
                "date": formatdate(p.posting_date, "dd.MM.yyyy") if p.posting_date else "",
                "amount": amount,
                "display_amount": flt(p.paid_amount),  # Ko'rsatish uchun original summa
                "method": p.mode_of_payment or "Naqd",
                "payment_id": p.payment_id,
                "payment_type": p.payment_type  # Receive yoki Pay
            })

        # To'langan summa (Payment Entry dan hisoblash - eng ishonchli usul)
        # ✅ Receive qo'shiladi, Pay ayiriladi
        paid_amounts = {}
        for contract_id in so_ids:
            total_paid = sum(p["amount"] for p in payments.get(contract_id, []))
            paid_amounts[contract_id] = total_paid

        # Keyingi to'lov - TO'G'RI HISOB-KITOB
        next_pay = {}

        # Har bir shartnoma uchun to'lov jadvalini olish
        all_schedules = frappe.db.sql("""
            SELECT parent, due_date, payment_amount, idx,
                   DATEDIFF(due_date, CURDATE()) AS days_left
            FROM `tabPayment Schedule`
            WHERE parent IN %s
            ORDER BY parent, idx
        """, (so_ids,), as_dict=True)

        # Shartnomalar bo'yicha guruhlash
        schedule_by_contract = {}
        for row in all_schedules:
            schedule_by_contract.setdefault(row.parent, []).append(row)

        # Har bir shartnoma uchun keyingi to'lanmagan oyni topish
        for contract_id, schedule_rows in schedule_by_contract.items():
            total_paid = paid_amounts.get(contract_id, 0)
            remaining_payment = total_paid

            for row in schedule_rows:
                month_amount = flt(row.payment_amount)

                if remaining_payment >= month_amount:
                    # Bu oy to'liq to'langan
                    remaining_payment -= month_amount
                else:
                    # Bu oy to'lanmagan yoki qisman to'langan
                    outstanding = month_amount - remaining_payment
                    days = int(row.days_left or 0)
                    status = "overdue" if days < 0 else ("today" if days == 0 else ("soon" if days <= 3 else "upcoming"))

                    next_pay[contract_id] = {
                        "due_date": formatdate(row.due_date, "dd.MM.yyyy"),
                        "amount": month_amount,
                        "outstanding": outstanding,
                        "days_left": days,
                        "status": status,
                        "status_uz": "Kechikkan" if days < 0 else ("Bugun" if days == 0 else "Yaqinda")
                    }
                    break

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
# 5. KEYINGI TO'LOVLAR - TO'G'RI HISOB-KITOB
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_upcoming_payments(customer_id: str):
    """
    Mijozning keyingi to'lovlarini TO'G'RI hisoblash.

    Har bir shartnoma uchun:
    1. Jami to'langan summani Payment Entry dan olish
    2. Birinchi TO'LANMAGAN oyni topish
    3. Qoldiq summani hisoblash
    """
    try:
        # Barcha shartnomalarni olish
        contracts = frappe.db.sql("""
            SELECT name, transaction_date
            FROM `tabSales Order`
            WHERE customer = %s AND docstatus = 1 AND status != 'Cancelled'
        """, customer_id, as_dict=True)

        if not contracts:
            return {"success": True, "payments": []}

        result = []

        for contract in contracts:
            contract_id = contract.name

            # 1. To'lov jadvalini olish
            schedule_rows = frappe.db.sql("""
                SELECT idx, due_date, payment_amount,
                       DATEDIFF(due_date, CURDATE()) AS days_left
                FROM `tabPayment Schedule`
                WHERE parent = %s ORDER BY idx
            """, contract_id, as_dict=True)

            if not schedule_rows:
                continue

            # 2. Jami to'langan summani olish (custom_contract_reference orqali)
            # ✅ Receive qo'shiladi, Pay ayiriladi (customerga pul qaytarilsa)
            total_paid_result = frappe.db.sql("""
                SELECT COALESCE(
                    SUM(CASE WHEN payment_type = 'Receive' THEN paid_amount ELSE -paid_amount END),
                    0
                ) as total_paid
                FROM `tabPayment Entry`
                WHERE custom_contract_reference = %s
                  AND docstatus = 1
                  AND payment_type IN ('Receive', 'Pay')
            """, contract_id)

            total_paid = flt(total_paid_result[0][0]) if total_paid_result else 0

            # 3. Birinchi to'lanmagan oyni topish
            remaining_payment = total_paid

            for row in schedule_rows:
                month_amount = flt(row.payment_amount)

                if remaining_payment >= month_amount:
                    # Bu oy to'liq to'langan - keyingisiga o'tish
                    remaining_payment -= month_amount
                else:
                    # Bu oy to'lanmagan yoki qisman to'langan
                    outstanding = month_amount - remaining_payment
                    days = int(row.days_left or 0)

                    result.append({
                        "contract_id": contract_id,
                        "contract_date": formatdate(contract.transaction_date, "dd.MM.yyyy"),
                        "due_date": formatdate(row.due_date, "dd.MM.yyyy"),
                        "amount": month_amount,
                        "outstanding": outstanding,
                        "days_left": days,
                        "status": "overdue" if days < 0 else ("today" if days == 0 else "upcoming"),
                        "status_text": f"{abs(days)} kun kechikkan" if days < 0 else f"{days} kun qoldi"
                    })
                    break  # Faqat birinchi to'lanmagan oyni olish

        # Sanasi bo'yicha tartiblash
        result.sort(key=lambda x: x.get("days_left", 0))

        return {"success": True, "payments": result}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Get Upcoming Payments Error")
        return {"success": False, "message": "Xato"}


# ============================================================
# 6. TO'LOV JADVALI (bitta shartnoma) - TO'G'RI HISOB-KITOB
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_payment_schedule(contract_id: str):
    """
    To'lov jadvalini TO'G'RI hisoblash.

    MANTIQ:
    1. Payment Entry dan jami to'langan summani olish
    2. To'lovlarni oyma-oy taqsimlash:
       - Agar to'lov >= oy summasi: oy "paid" (to'langan)
       - Agar 0 < to'lov < oy summasi: oy "partial" (qisman)
       - Agar to'lov = 0: oy "unpaid" (to'lanmagan)
       - Ortiqcha summa keyingi oyga o'tkaziladi
    """
    # 1. Oylik to'lov jadvalini olish
    rows = frappe.db.sql("""
        SELECT idx, due_date, payment_amount,
               DATEDIFF(due_date, CURDATE()) AS days_left
        FROM `tabPayment Schedule`
        WHERE parent = %s ORDER BY idx
    """, contract_id, as_dict=True)

    if not rows:
        return {"success": True, "schedule": []}

    # 2. Payment Entry dan JAMI to'langan summani olish (custom_contract_reference orqali)
    # ✅ Receive qo'shiladi, Pay ayiriladi (customerga pul qaytarilsa)
    total_paid_result = frappe.db.sql("""
        SELECT COALESCE(
            SUM(CASE WHEN payment_type = 'Receive' THEN paid_amount ELSE -paid_amount END),
            0
        ) as total_paid
        FROM `tabPayment Entry`
        WHERE custom_contract_reference = %s
          AND docstatus = 1
          AND payment_type IN ('Receive', 'Pay')
    """, contract_id)

    total_paid = flt(total_paid_result[0][0]) if total_paid_result else 0

    # 3. To'lovlarni OYMA-OY taqsimlash
    remaining_payment = total_paid  # Taqsimlash uchun qolgan to'lov
    schedule = []

    for r in rows:
        days = int(r.days_left or 0)
        month_amount = flt(r.payment_amount)

        # Bu oy uchun to'langan summa
        if remaining_payment >= month_amount:
            # To'liq to'langan
            month_paid = month_amount
            month_outstanding = 0
            status = "paid"
            remaining_payment -= month_amount
        elif remaining_payment > 0:
            # Qisman to'langan
            month_paid = remaining_payment
            month_outstanding = month_amount - remaining_payment
            status = "partial"
            remaining_payment = 0
        else:
            # To'lanmagan
            month_paid = 0
            month_outstanding = month_amount
            status = "unpaid"

        # Kechikkan bo'lsa
        is_overdue = days < 0 and month_outstanding > 0

        schedule.append({
            "month": r.idx,
            "due_date": formatdate(r.due_date, "dd.MM.yyyy"),
            "amount": month_amount,
            "paid": month_paid,
            "outstanding": month_outstanding,
            "status": status,
            "is_overdue": is_overdue
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

        # 3. To'lovlar tarixi (custom_contract_reference orqali)
        # ✅ Pay va Receive turlarini hisobga olish
        payments_data = frappe.db.sql("""
            SELECT
                name AS payment_id,
                posting_date,
                paid_amount,
                mode_of_payment,
                payment_type
            FROM `tabPayment Entry`
            WHERE custom_contract_reference = %s
              AND docstatus = 1
              AND payment_type IN ('Receive', 'Pay')
            ORDER BY posting_date DESC
        """, contract_id, as_dict=True)

        payments = []
        total_paid = 0
        for p in payments_data:
            # ✅ Pay bo'lsa ayiriladi, Receive bo'lsa qo'shiladi
            payment_amount = flt(p.paid_amount)
            if p.payment_type == 'Receive':
                total_paid += payment_amount
            else:
                total_paid -= payment_amount  # Pay - customerga pul qaytarildi
            payments.append({
                "date": formatdate(p.posting_date, "dd.MM.yyyy"),
                "amount": payment_amount if p.payment_type == 'Receive' else -payment_amount,
                "display_amount": payment_amount,  # Ko'rsatish uchun original summa
                "method": p.mode_of_payment or "Naqd",
                "payment_id": p.payment_id,
                "payment_type": p.payment_type  # Receive yoki Pay
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
# 8. ESLATMALAR (REMINDERS) - TO'G'RI HISOB-KITOB
# ============================================================

@frappe.whitelist(allow_guest=True)
def get_reminders_by_telegram_id(telegram_id: str):
    """
    Telegram ID orqali customerning eslatmalarini olish.
    TO'G'RI HISOB-KITOB bilan.
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
            SELECT name, transaction_date
            FROM `tabSales Order`
            WHERE customer = %s AND docstatus = 1 AND status != 'Cancelled'
        """, customer.name, as_dict=True)

        if not contracts:
            return {
                "success": True,
                "customer_id": customer.name,
                "customer_name": customer.customer_name,
                "reminders": [],
                "total_reminders": 0,
                "message": "Eslatmalar yuklandi"
            }

        result = []

        for contract in contracts:
            contract_id = contract.name

            # 3. To'lov jadvalini olish (30 kun oralig'i)
            schedule_rows = frappe.db.sql("""
                SELECT idx, due_date, payment_amount,
                       DATEDIFF(due_date, CURDATE()) AS days_left
                FROM `tabPayment Schedule`
                WHERE parent = %s
                  AND idx > 1
                  AND due_date BETWEEN CURDATE() - INTERVAL 1 DAY AND CURDATE() + INTERVAL 30 DAY
                ORDER BY idx
            """, contract_id, as_dict=True)

            if not schedule_rows:
                continue

            # 4. Jami to'langan summani olish (custom_contract_reference orqali)
            # ✅ Receive qo'shiladi, Pay ayiriladi (customerga pul qaytarilsa)
            total_paid_result = frappe.db.sql("""
                SELECT COALESCE(
                    SUM(CASE WHEN payment_type = 'Receive' THEN paid_amount ELSE -paid_amount END),
                    0
                ) as total_paid
                FROM `tabPayment Entry`
                WHERE custom_contract_reference = %s
                  AND docstatus = 1
                  AND payment_type IN ('Receive', 'Pay')
            """, contract_id)

            total_paid = flt(total_paid_result[0][0]) if total_paid_result else 0

            # 5. Oldingi oylarni hisobga olish uchun barcha jadvaldan olish
            all_schedule = frappe.db.sql("""
                SELECT idx, payment_amount
                FROM `tabPayment Schedule`
                WHERE parent = %s ORDER BY idx
            """, contract_id, as_dict=True)

            # 6. Har bir oy uchun to'lovni taqsimlash
            remaining_payment = total_paid
            month_status = {}  # idx -> (paid, outstanding, status)

            for row in all_schedule:
                month_amount = flt(row.payment_amount)
                idx = row.idx

                if remaining_payment >= month_amount:
                    month_status[idx] = (month_amount, 0, "paid")
                    remaining_payment -= month_amount
                elif remaining_payment > 0:
                    month_status[idx] = (remaining_payment, month_amount - remaining_payment, "partial")
                    remaining_payment = 0
                else:
                    month_status[idx] = (0, month_amount, "unpaid")

            # 7. 30 kun oralig'idagi to'lanmagan oylarni eslatmaga qo'shish
            for row in schedule_rows:
                idx = row.idx
                paid, outstanding, status = month_status.get(idx, (0, flt(row.payment_amount), "unpaid"))

                # Faqat to'lanmagan yoki qisman to'langan oylarni ko'rsatish
                if outstanding <= 0:
                    continue

                days = int(row.days_left or 0)

                # Status va prioritet aniqlash
                if days < -1:
                    reminder_status = "critically_overdue"
                    status_uz = f"{abs(days)} kun kechikkan ⚠️"
                    priority = "critical"
                elif days == -1:
                    reminder_status = "overdue"
                    status_uz = "1 kun kechikkan ⚠️"
                    priority = "high"
                elif days == 0:
                    reminder_status = "today"
                    status_uz = "Bugun to'lash kerak! 🔴"
                    priority = "urgent"
                elif days == 1:
                    reminder_status = "tomorrow"
                    status_uz = "Ertaga to'lash kerak 🟡"
                    priority = "high"
                elif days <= 3:
                    reminder_status = "soon"
                    status_uz = f"{days} kun qoldi 🟢"
                    priority = "medium"
                else:
                    reminder_status = "upcoming"
                    status_uz = f"{days} kun qoldi"
                    priority = "low"

                result.append({
                    "contract_id": contract_id,
                    "contract_date": formatdate(contract.transaction_date, "dd.MM.yyyy"),
                    "due_date": formatdate(row.due_date, "dd.MM.yyyy"),
                    "amount": flt(row.payment_amount),
                    "outstanding": outstanding,
                    "days_left": days,
                    "status": reminder_status,
                    "status_uz": status_uz,
                    "priority": priority,
                    "payment_number": idx
                })

        # Sanasi bo'yicha tartiblash
        result.sort(key=lambda x: x.get("days_left", 0))

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

        # 3. Barcha to'lovlarni olish (custom_contract_reference orqali)
        # ✅ Pay va Receive turlarini hisobga olish
        payments_data = frappe.db.sql("""
            SELECT
                custom_contract_reference AS contract_id,
                name AS payment_id,
                posting_date,
                paid_amount,
                mode_of_payment,
                remarks,
                payment_type
            FROM `tabPayment Entry`
            WHERE custom_contract_reference IN %s
              AND docstatus = 1
              AND payment_type IN ('Receive', 'Pay')
            ORDER BY posting_date DESC
        """, (so_ids,), as_dict=True)

        # 4. Shartnomalar bo'yicha guruhlash
        contracts_with_payments = []
        for contract in contracts:
            contract_payments = [
                {
                    "payment_id": p.payment_id,
                    "date": formatdate(p.posting_date, "dd.MM.yyyy"),
                    "amount": flt(p.paid_amount) if p.payment_type == 'Receive' else -flt(p.paid_amount),
                    "display_amount": flt(p.paid_amount),  # Ko'rsatish uchun original summa
                    "method": p.mode_of_payment or "Naqd",
                    "remarks": p.remarks or "",
                    "payment_type": p.payment_type  # Receive yoki Pay
                }
                for p in payments_data if p.contract_id == contract.name
            ]

            # ✅ Pay ayiriladi, Receive qo'shiladi
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
# 11. TO'LOV QABUL QILINGANDA NOTIFICATION YUBORISH
# ============================================================
# ============================================================
# 11. TO'LOV QABUL QILINGANDA NOTIFICATION YUBORISH (TUZATILDI)
# ============================================================

def send_payment_notification(doc, method):
	"""
	Payment Entry submit bo'lganda Telegram ga xabar yuborish.
	TUZATISH: Huquqlar (Permissions) muammosi hal qilindi va Loglar ko'rinadigan qilindi.
	"""
	try:
		# DIAGNOSTIKA LOGI (Ishga tushganini bilish uchun)
		# Agar hamma narsa ishlagach, bu qatorni o'chirib tashlashingiz mumkin
		frappe.log_error(f"🚀 Bot jarayoni boshlandi: {doc.name}", "Telegram Bot Debug")

		import requests

		# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
		# 1. CUSTOMER DAN TELEGRAM ID OLISH
		# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
		customer_id = doc.party

		# Customer ma'lumotlarini olish (cache'dan emas, to'g'ridan-to'g'ri bazadan)
		telegram_id = frappe.db.get_value("Customer", customer_id, "custom_telegram_id")

		if not telegram_id:
			frappe.log_error(
				f"Mijozda Telegram ID yo'q. Customer: {customer_id}",
				"Telegram Bot Skipped"
			)
			return

		# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
		# 2. BOT TOKEN NI OLISH (IGNORE PERMISSIONS) - ENG MUHIM JOYI!
		# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
		# Oddiy userda "Cash Settings"ga kirish huquqi bo'lmasligi mumkin.
		# Shuning uchun System User nomidan o'qiymiz.
		try:
			bot_token = frappe.db.get_single_value("Cash Settings", "telegram_bot_token")
		except Exception:
			# Agar ruxsat bo'lmasa, administrator sifatida olamiz
			doc_settings = frappe.get_doc("Cash Settings")
			bot_token = doc_settings.telegram_bot_token

		if not bot_token:
			frappe.log_error(
				"Cash Settings da Token topilmadi!",
				"Telegram Bot Error"
			)
			return

		# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
		# 3. TELEGRAM GA YUBORISH
		# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
		payment_type = doc.payment_type
		success = _send_via_telegram_api(bot_token, telegram_id, doc, payment_type)

		if success:
			frappe.log_error(f"✅ Xabar yuborildi: {doc.name} -> {telegram_id}",
							 "Telegram Bot Success")
		else:
			frappe.log_error(f"❌ Xabar ketmadi: {doc.name}", "Telegram Bot Failed")

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Telegram Bot Critical Error")


def _send_via_telegram_api(bot_token, telegram_id, doc, payment_type):
	"""Telegram API ga xabar yuborish"""
	import requests

	try:
		# Xabar matni
		if payment_type == "Pay":
			message = f"""🔄 <b>Pul qaytarildi</b>

📄 Shartnoma: <code>{doc.get("custom_contract_reference") or "—"}</code>
💵 Summa: <b>${frappe.utils.fmt_money(doc.paid_amount, currency="USD")}</b>
🧾 ID: <code>{doc.name}</code>
📅 Sana: {formatdate(doc.posting_date, "dd.MM.yyyy")}

ℹ️ Savollar bo'lsa, murojaat qiling."""
		else:
			message = f"""💰 <b>To'lov qabul qilindi!</b>

📄 Shartnoma: <code>{doc.get("custom_contract_reference") or "—"}</code>
💵 Summa: <b>${frappe.utils.fmt_money(doc.paid_amount, currency="USD")}</b>
🧾 ID: <code>{doc.name}</code>
📅 Sana: {formatdate(doc.posting_date, "dd.MM.yyyy")}

✅ Rahmat! Keyingi to'lovlar uchun /start bosing."""

		# So'rov yuborish
		url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
		data = {
			"chat_id": telegram_id,
			"text": message.strip(),
			"parse_mode": "HTML"
		}

		response = requests.post(url, json=data, timeout=5)

		if response.status_code != 200:
			frappe.log_error(f"Telegram Javobi: {response.text}", "Telegram API Error")
			return False

		return True

	except Exception as e:
		frappe.log_error(f"Network Error: {str(e)}", "Telegram Network Error")
		return False

def _send_via_bot_webhook(webhook_url, telegram_id, doc, payment_type):
    """Bot webhook endpoint ga yuborish"""
    import requests

    # Bot kutadigan formatda ma'lumot yuborish
    data = {
        "name": doc.name,
        "party": doc.party,
        "custom_contract_reference": doc.get("custom_contract_reference") or "",
        "paid_amount": flt(doc.paid_amount),
        "posting_date": str(doc.posting_date),
        "mode_of_payment": doc.mode_of_payment or "Naqd",
        "custom_telegram_id": telegram_id,
        "payment_type": payment_type
    }

    # Webhook URL ga POST yuborish
    if not webhook_url.endswith("/webhook/payment-entry"):
        webhook_url = webhook_url.rstrip("/") + "/webhook/payment-entry"

    response = requests.post(webhook_url, json=data, timeout=10)

    if response.status_code != 200:
        frappe.log_error(
            f"Bot webhook error: {response.text}",
            f"Payment Notification Failed - {doc.name}"
        )


# ============================================================
# 12. AVTOMATIK ESLATMALAR (SCHEDULED NOTIFICATIONS) - TO'G'RI HISOB-KITOB
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

    TO'G'RI HISOB-KITOB:
    - Jami to'langan summani Payment Entry dan oladi
    - To'lovlarni oyma-oy taqsimlaydi
    - Faqat haqiqiy qoldiq bo'lgan oylar uchun eslatma yuboradi
    """
    try:
        import requests
        from frappe.utils import now_datetime

        # Telegram bot API URL ni config dan olish (Cash Settings dan)
        bot_token = frappe.db.get_single_value("Cash Settings", "telegram_bot_token")

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

            # Shu sanada to'lov qilishi kerak bo'lgan shartnomalarni olish
            schedule_rows = frappe.db.sql("""
                SELECT
                    ps.parent AS contract_id,
                    ps.due_date,
                    ps.payment_amount,
                    ps.idx,
                    so.customer,
                    c.customer_name,
                    c.custom_telegram_id
                FROM `tabPayment Schedule` ps
                JOIN `tabSales Order` so ON so.name = ps.parent
                JOIN `tabCustomer` c ON c.name = so.customer
                WHERE ps.due_date = %s
                  AND ps.idx > 1
                  AND so.docstatus = 1
                  AND c.custom_telegram_id IS NOT NULL
                  AND c.custom_telegram_id != ''
                ORDER BY c.name
            """, target_date, as_dict=True)

            # Har bir shartnoma uchun to'g'ri qoldiqni hisoblash
            for row in schedule_rows:
                contract_id = row.contract_id
                telegram_id = row.custom_telegram_id

                if not telegram_id:
                    continue

                # Jami to'langan summani olish (custom_contract_reference orqali)
                # ✅ Receive qo'shiladi, Pay ayiriladi (customerga pul qaytarilsa)
                total_paid_result = frappe.db.sql("""
                    SELECT COALESCE(
                        SUM(CASE WHEN payment_type = 'Receive' THEN paid_amount ELSE -paid_amount END),
                        0
                    ) as total_paid
                    FROM `tabPayment Entry`
                    WHERE custom_contract_reference = %s
                      AND docstatus = 1
                      AND payment_type IN ('Receive', 'Pay')
                """, contract_id)

                total_paid = flt(total_paid_result[0][0]) if total_paid_result else 0

                # Barcha jadvaldan oldingi oylarni olish
                all_schedule = frappe.db.sql("""
                    SELECT idx, payment_amount
                    FROM `tabPayment Schedule`
                    WHERE parent = %s ORDER BY idx
                """, contract_id, as_dict=True)

                # To'lovlarni oyma-oy taqsimlash va bu oy uchun qoldiqni aniqlash
                remaining_payment = total_paid
                outstanding_for_this_month = 0

                for sched_row in all_schedule:
                    month_amount = flt(sched_row.payment_amount)

                    if sched_row.idx == row.idx:
                        # Bu oy - qoldiqni hisoblash
                        if remaining_payment >= month_amount:
                            outstanding_for_this_month = 0
                        else:
                            outstanding_for_this_month = month_amount - remaining_payment
                        break
                    else:
                        # Oldingi oylar
                        if remaining_payment >= month_amount:
                            remaining_payment -= month_amount
                        else:
                            remaining_payment = 0

                # Agar bu oy uchun qoldiq bo'lsa, eslatma yuborish
                if outstanding_for_this_month <= 0:
                    continue  # Bu oy to'liq to'langan, eslatma kerak emas

                # Xabar tayyorlash
                payment_data = {
                    "contract_id": contract_id,
                    "due_date": row.due_date,
                    "payment_amount": row.payment_amount,
                    "outstanding": outstanding_for_this_month,
                    "idx": row.idx,
                    "customer": row.customer,
                    "customer_name": row.customer_name
                }

                message = _format_reminder_message(payment_data, config["message_template"], days)

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
                            customer_id=row.customer,
                            telegram_id=telegram_id,
                            contract_id=contract_id,
                            notification_type=f"reminder_day_{days}",
                            status="sent",
                            message=message
                        )
                    else:
                        # Xato
                        frappe.log_error(
                            f"Telegram API xatosi: {response.text}",
                            f"Reminder Send Failed - {row.customer}"
                        )

                except Exception as send_error:
                    frappe.log_error(
                        frappe.get_traceback(),
                        f"Reminder Send Error - {row.customer}"
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
<b>💰 To'lov summasi:</b> ${frappe.utils.fmt_money(payment.payment_amount, currency="USD")}
<b>📊 Qoldiq:</b> ${frappe.utils.fmt_money(payment.outstanding, currency="USD")}
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
    TO'G'RI HISOB-KITOB bilan.
    """
    try:
        target_date = add_days(today(), int(days))

        # Shu sanada to'lov qilishi kerak bo'lgan shartnomalarni olish
        schedule_rows = frappe.db.sql("""
            SELECT
                ps.parent AS contract_id,
                ps.due_date,
                ps.payment_amount,
                ps.idx,
                so.customer,
                c.customer_name,
                c.custom_telegram_id,
                c.custom_phone_1
            FROM `tabPayment Schedule` ps
            JOIN `tabSales Order` so ON so.name = ps.parent
            JOIN `tabCustomer` c ON c.name = so.customer
            WHERE ps.due_date = %s
              AND ps.idx > 1
              AND so.docstatus = 1
            ORDER BY c.name
        """, target_date, as_dict=True)

        result = []

        for row in schedule_rows:
            contract_id = row.contract_id

            # Jami to'langan summani olish (custom_contract_reference orqali)
            # ✅ Receive qo'shiladi, Pay ayiriladi (customerga pul qaytarilsa)
            total_paid_result = frappe.db.sql("""
                SELECT COALESCE(
                    SUM(CASE WHEN payment_type = 'Receive' THEN paid_amount ELSE -paid_amount END),
                    0
                ) as total_paid
                FROM `tabPayment Entry`
                WHERE custom_contract_reference = %s
                  AND docstatus = 1
                  AND payment_type IN ('Receive', 'Pay')
            """, contract_id)

            total_paid = flt(total_paid_result[0][0]) if total_paid_result else 0

            # Barcha jadvaldan oldingi oylarni olish
            all_schedule = frappe.db.sql("""
                SELECT idx, payment_amount
                FROM `tabPayment Schedule`
                WHERE parent = %s ORDER BY idx
            """, contract_id, as_dict=True)

            # To'lovlarni oyma-oy taqsimlash va bu oy uchun qoldiqni aniqlash
            remaining_payment = total_paid
            outstanding_for_this_month = 0

            for sched_row in all_schedule:
                month_amount = flt(sched_row.payment_amount)

                if sched_row.idx == row.idx:
                    # Bu oy - qoldiqni hisoblash
                    if remaining_payment >= month_amount:
                        outstanding_for_this_month = 0
                    else:
                        outstanding_for_this_month = month_amount - remaining_payment
                    break
                else:
                    # Oldingi oylar
                    if remaining_payment >= month_amount:
                        remaining_payment -= month_amount
                    else:
                        remaining_payment = 0

            # Faqat qoldiq bo'lgan oylarni ko'rsatish
            if outstanding_for_this_month <= 0:
                continue

            result.append({
                "customer_id": row.customer,
                "customer_name": row.customer_name,
                "telegram_id": row.custom_telegram_id or "Bog'lanmagan",
                "phone": row.custom_phone_1 or "",
                "contract_id": contract_id,
                "due_date": formatdate(row.due_date, "dd.MM.yyyy"),
                "amount": flt(row.payment_amount),
                "outstanding": outstanding_for_this_month,
                "payment_number": row.idx - 1,
                "has_telegram": bool(row.custom_telegram_id)
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

@frappe.whitelist(allow_guest=True)
def get_all_active_due_payments():
	"""
	Bot uchun maxsus: Barcha aktiv shartnomalarning navbatdagi to'lovini hisoblab qaytaradi.
	Bot bu funksiyani har soatda chaqiradi va kerakli xabarni yuboradi.
	"""
	try:
		# 1. Telegram ID si bor customerlarning aktiv shartnomalarini olamiz
		contracts = frappe.db.sql("""
            SELECT
                so.name,
                so.customer,
                so.transaction_date,
                c.customer_name,
                c.custom_telegram_id
            FROM `tabSales Order` so
            JOIN `tabCustomer` c ON c.name = so.customer
            WHERE so.docstatus = 1
              AND so.status != 'Cancelled'
              AND c.custom_telegram_id IS NOT NULL
              AND c.custom_telegram_id != ''
        """, as_dict=True)

		due_payments = []

		for contract in contracts:
			contract_id = contract.name

			# 2. To'lov jadvalini olamiz
			schedule_rows = frappe.db.sql("""
                SELECT idx, due_date, payment_amount
                FROM `tabPayment Schedule`
                WHERE parent = %s ORDER BY idx
            """, contract_id, as_dict=True)

			if not schedule_rows:
				continue

			# 3. Jami to'langan summani aniqlaymiz
			total_paid_result = frappe.db.sql("""
                SELECT COALESCE(
                    SUM(CASE WHEN payment_type = 'Receive' THEN paid_amount ELSE -paid_amount END),
                    0
                ) as total_paid
                FROM `tabPayment Entry`
                WHERE custom_contract_reference = %s
                  AND docstatus = 1
                  AND payment_type IN ('Receive', 'Pay')
            """, contract_id)

			total_paid = flt(total_paid_result[0][0]) if total_paid_result else 0

			# 4. Navbatdagi to'lanmagan oyni topamiz
			remaining_payment = total_paid

			next_payment_date = None
			next_payment_amount = 0

			for row in schedule_rows:
				month_amount = flt(row.payment_amount)

				if remaining_payment >= month_amount:
					# Bu oy to'liq to'langan, keyingisiga o'tamiz
					remaining_payment -= month_amount
				else:
					# Mana shu oy to'lanmagan yoki qisman to'langan
					outstanding = month_amount - remaining_payment

					# Agar qoldiq juda kichik bo'lsa (tiyinlar), hisobga olmaymiz
					if outstanding > 1:
						next_payment_date = row.due_date
						next_payment_amount = outstanding
						break  # Birinchi qarzdorlikni topdik, tsiklni to'xtatamiz

			# Agar qarzdorlik topilgan bo'lsa, ro'yxatga qo'shamiz
			if next_payment_date:
				due_payments.append({
					"name": contract.name,  # Shartnoma raqami
					"customer": contract.customer,
					"customer_name": contract.customer_name,
					"custom_telegram_id": contract.custom_telegram_id,
					"next_payment_date": str(next_payment_date),  # YYYY-MM-DD format
					"next_payment_amount": next_payment_amount
				})

		return {"data": due_payments}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Bot Get All Due Payments Error")
		return {"data": []}
