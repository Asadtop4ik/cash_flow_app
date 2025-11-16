import frappe
from frappe.utils import flt, formatdate, getdate, nowdate


# ============================================================
# 1) CUSTOMER SEARCH (PASSPORT)
# ============================================================

@frappe.whitelist()
def get_customer_by_passport(passport_series):
    """ Passport orqali mijozni topish (XATOSIZ) """

    if not passport_series:
        return {"success": False, "message": "Passport raqami kiritilmagan"}

    try:
        customer_list = frappe.db.get_all(
            "Customer",
            filters={"custom_passport_series": passport_series},
            fields=[
                "name",
                "customer_name",
                "custom_phone_1",
                "customer_classification",
                "custom_telegram_id"
            ],
            limit=1
        )

        if not customer_list:
            return {"success": False, "message": "Mijoz topilmadi"}

        customer = customer_list[0]

        # Shartnomalar → SQL orqali eng toza usulda
        contracts = get_customer_contracts(customer["name"])

        # Keyingi to‘lovlar
        next_payment = get_next_installment(customer["name"])

        return {
            "success": True,
            "customer": customer,
            "contracts": contracts,
            "next_payment": next_payment
        }

    except Exception as e:
        frappe.log_error(str(e), "Passport Search Error")
        return {"success": False, "message": f"Xatolik: {e}"}



# ============================================================
# 2) CUSTOMER SEARCH (PHONE)
# ============================================================

@frappe.whitelist()
def get_customer_by_phone(phone):
    """ Telefon orqali qidirish """

    if not phone:
        return {"success": False, "message": "Telefon raqami kiritilmagan"}

    try:
        customer_list = frappe.db.get_all(
            "Customer",
            filters={"custom_phone_1": phone},
            fields=[
                "name",
                "customer_name",
                "custom_passport_series",
                "custom_phone_1",
                "customer_classification",
                "custom_telegram_id"
            ],
            limit=1
        )

        if not customer_list:
            return {"success": False, "message": "Mijoz topilmadi"}

        customer = customer_list[0]

        contracts = get_customer_contracts(customer["name"])
        next_payment = get_next_installment(customer["name"])

        return {
            "success": True,
            "customer": customer,
            "contracts": contracts,
            "next_payment": next_payment
        }

    except Exception as e:
        frappe.log_error(str(e), "Phone Search Error")
        return {"success": False, "message": f"Xatolik: {e}"}



# ============================================================
# 3) CONTRACT LIST (HAR DOIM TO‘G‘RI FORMAT!)
# ============================================================

@frappe.whitelist()
def get_customer_contracts(customer_name):
    """ Mijozga tegishli shartnomalar (SQL orqali eng ishonchli usul) """

    try:
        rows = frappe.db.sql(
            """
            SELECT
                name,
                transaction_date,
                custom_grand_total_with_interest AS total,
                advance_paid AS paid,
                (custom_grand_total_with_interest - advance_paid) AS remaining
            FROM `tabSales Order`
            WHERE customer=%s AND docstatus=1 AND status!='Cancelled'
            ORDER BY transaction_date DESC
            """,
            (customer_name,),
            as_dict=True
        )

        return {
            "success": True,
            "contracts": rows
        }

    except Exception as e:
        frappe.log_error(str(e), "Get Contracts Error")
        return {"success": False, "message": str(e)}



# ============================================================
# 4) CONTRACT SCHEDULE (TO‘LOV TAQSIMOTI)
# ============================================================

@frappe.whitelist()
def get_contract_schedule(contract_id):
    if not contract_id:
        return {"success": False, "message": "Shartnoma ID kiritilmagan"}

    try:
        so = frappe.get_doc("Sales Order", contract_id)
        schedule = []

        for row in so.payment_schedule:

            if flt(row.outstanding) == 0:
                pay_status = "Paid"
            elif flt(row.paid_amount) > 0:
                pay_status = "Partially Paid"
            else:
                pay_status = "Unpaid"

            schedule.append({
                "month": row.idx,
                "due_date": formatdate(row.due_date, "dd.MM.yyyy"),
                "amount": flt(row.payment_amount),
                "paid": flt(row.paid_amount),
                "outstanding": flt(row.outstanding),
                "status": pay_status
            })

        return {"success": True, "schedule": schedule}

    except Exception as e:
        frappe.log_error(str(e), "Contract Schedule Error")
        return {"success": False, "message": str(e)}



# ============================================================
# 5) NEXT PAYMENT CALCULATION (REMINDER SYSTEM)
# ============================================================

@frappe.whitelist()
def get_next_installment(customer_name):
    """ Mijoz uchun keyingi to‘lovlarni topish """

    try:
        so_list = frappe.get_all(
            "Sales Order",
            filters={"customer": customer_name, "docstatus": 1},
            fields=["name"],
            order_by="transaction_date ASC"
        )

        next_rows = []

        for so_item in so_list:
            so = frappe.get_doc("Sales Order", so_item.name)

            for row in so.payment_schedule:
                if flt(row.outstanding) > 0:

                    due = getdate(row.due_date)
                    today = getdate(nowdate())
                    days_left = (due - today).days

                    if days_left < 0:
                        st = "overdue"
                    elif days_left == 0:
                        st = "today"
                    elif days_left <= 3:
                        st = "reminder"
                    else:
                        st = "soon"

                    next_rows.append({
                        "contract": so.name,
                        "month": row.idx,
                        "due_date": formatdate(row.due_date, "dd.MM.yyyy"),
                        "amount": flt(row.payment_amount),
                        "outstanding": flt(row.outstanding),
                        "days_left": days_left,
                        "status": st
                    })

                    break

        return {"success": True, "next_installments": next_rows}

    except Exception as e:
        frappe.log_error(str(e), "Next Installment Error")
        return {"success": False, "message": str(e)}



# ============================================================
# 6) PAYMENT HISTORY
# ============================================================

@frappe.whitelist()
def get_payment_history(contract_id):

    try:
        payments = frappe.db.sql(
            """
            SELECT
                name,
                posting_date,
                paid_amount,
                custom_contract_reference,
                mode_of_payment
            FROM `tabPayment Entry`
            WHERE custom_contract_reference=%s
              AND docstatus=1
              AND payment_type='Receive'
            ORDER BY posting_date DESC
            """,
            (contract_id,),
            as_dict=True
        )

        for p in payments:
            p["date"] = formatdate(p["posting_date"], "dd.MM.yyyy")

        return {"success": True, "payments": payments}

    except Exception as e:
        frappe.log_error(str(e), "Payment History Error")
        return {"success": False, "message": str(e)}



# ============================================================
# 7) TELEGRAM LINKING
# ============================================================

@frappe.whitelist()
def link_telegram_user(customer_name, telegram_id):

    try:
        doc = frappe.get_doc("Customer", customer_name)
        doc.custom_telegram_id = telegram_id
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {"success": True, "message": "Telegram ID bog‘landi"}

    except Exception as e:
        frappe.log_error(str(e), "Telegram Link Error")
        return {"success": False, "message": str(e)}
