# Copyright (c) 2025, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def execute(filters=None):
    """Eslatmalar - Qarzdorlik guruhlari va izohlar"""
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    """Report columns definition"""
    return [
        {
            "fieldname": "group_header",
            "label": _("Guruh"),
            "fieldtype": "Data",
            "width": 230
        },
        {
            "fieldname": "contract_link",
            "label": _("Shartnoma"),
            "fieldtype": "Link",
            "options": "Installment Application",
            "width": 130
        },
        {
            "fieldname": "customer_link",
            "label": _("Klient"),
            "fieldtype": "Link",
            "options": "Customer",
            "width": 160
        },
        {
            "fieldname": "current_month_payment",
            "label": _("Shu Oy To'lovi"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "due_amount",
            "label": _("Yana To'lashi Kerak"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "remaining_debt",
            "label": _("Qolgan Qarz"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "overdue_days",
            "label": _("Kechikish (kun)"),
            "fieldtype": "Int",
            "width": 110
        },
        {
            "fieldname": "note_text",
            "label": _("So'nggi Izoh"),
            "fieldtype": "Data",
            "width": 260
        },
        {
            "fieldname": "note_category",
            "label": _("Kategoriya"),
            "fieldtype": "Data",
            "width": 110
        },
        {
            "fieldname": "note_date",
            "label": _("Izoh Sanasi"),
            "fieldtype": "Date",
            "width": 110
        }
    ]


def get_data(filters):
    """
    To'liq optimallashtirilgan report data.
    4 ta bulk query - N+1 muammo yo'q.
    FIFO waterfall - to'lov sanasiga qarab guruh tanlash.
    """
    today = getdate(nowdate())

    # ── BULK QUERY 1: Barcha submitted Installment Applications ─────────────────
    applications = frappe.get_all(
        "Installment Application",
        filters={"docstatus": 1},
        fields=["name", "customer", "custom_grand_total_with_interest", "sales_order"]
    )

    if not applications:
        return []

    app_names    = [a.name for a in applications]
    sales_orders = [a.sales_order for a in applications if a.sales_order]

    if not sales_orders:
        return []

    # sales_order → app.name xaritalash (1:1 kafolatlangan)
    so_to_app = {a.sales_order: a.name for a in applications if a.sales_order}

    # ── BULK QUERY 2: Barcha Payment Schedules ───────────────────────────────────
    all_schedules_raw = frappe.db.sql("""
        SELECT parent, due_date, payment_amount
        FROM `tabPayment Schedule`
        WHERE parent IN %(app_names)s
          AND parenttype = 'Installment Application'
        ORDER BY parent, due_date ASC
    """, {"app_names": app_names}, as_dict=1)

    # { app_name: [ {due_date, payment_amount}, ... ] } — sana bo'yicha tartiblangan
    schedules_map = {}
    for row in all_schedules_raw:
        schedules_map.setdefault(row.parent, []).append(row)

    # ── BULK QUERY 3: Jami to'lovlar sales_order bo'yicha ───────────────────────
    paid_raw = frappe.db.sql("""
        SELECT custom_contract_reference, SUM(paid_amount) AS total_paid
        FROM `tabPayment Entry`
        WHERE custom_contract_reference IN %(sales_orders)s
          AND docstatus = 1
          AND payment_type = 'Receive'
        GROUP BY custom_contract_reference
    """, {"sales_orders": sales_orders}, as_dict=1)

    # { app_name: total_paid } — sales_order orqali app.name ga o'tkazildi
    paid_map = {}
    for r in paid_raw:
        app_name = so_to_app.get(r.custom_contract_reference)
        if app_name:
            paid_map[app_name] = flt(r.total_paid)

    # ── BULK QUERY 4: Har bir shartnoma uchun eng oxirgi izoh ────────────────────
    notes_raw = frappe.db.sql("""
        SELECT cn.contract_reference,
               cn.note_text,
               cn.note_category,
               cn.note_date
        FROM `tabContract Notes` cn
        INNER JOIN (
            SELECT contract_reference, MAX(creation) AS max_creation
            FROM `tabContract Notes`
            WHERE contract_reference IN %(app_names)s
            GROUP BY contract_reference
        ) latest
          ON cn.contract_reference = latest.contract_reference
         AND cn.creation           = latest.max_creation
    """, {"app_names": app_names}, as_dict=1)

    # { app_name: {note_text, note_category, note_date} }
    notes_map = {r.contract_reference: r for r in notes_raw}

    # ── Guruhlar ─────────────────────────────────────────────────────────────────
    groups = {
        "overdue_more":   [],   # 15+ kun kechikkan
        "overdue_2weeks": [],   # 8–14 kun kechikkan
        "overdue_1week":  [],   # 1–7 kun kechikkan
        "today":          [],   # Bugun to'lashi kerak
        "due_1week":      [],   # 1–7 kun ichida
        "due_2weeks":     [],   # 8–14 kun ichida
        "due_later":      [],   # 14 kundan keyin
    }

    for app in applications:
        contract_total = flt(app.custom_grand_total_with_interest)
        total_paid     = paid_map.get(app.name, 0.0)
        remaining_debt = contract_total - total_paid

        # To'liq to'langan shartnomalarni o'tkazib yuborish
        if remaining_debt <= 0.01:
            continue

        schedule = schedules_map.get(app.name)
        if not schedule:
            continue

        # ── FIFO Waterfall: birinchi to'liq to'lanmagan installmentni top ────────
        active = _find_active_installment(schedule, total_paid)
        if not active:
            continue

        due_date     = getdate(active["due_date"])
        days_diff    = (due_date - today).days
        overdue_days = abs(days_diff) if days_diff < 0 else None

        note = notes_map.get(app.name, {})

        row = {
            "group_header":          "",
            "contract_link":         app.name,
            "customer_link":         app.customer,
            "current_month_payment": active["schedule_amount"],
            "due_amount":            active["due_amount"],
            "remaining_debt":        remaining_debt,
            "overdue_days":          overdue_days,
            "note_text":             note.get("note_text", "")     if note else "",
            "note_category":         note.get("note_category", "") if note else "",
            "note_date":             note.get("note_date", "")     if note else "",
            "indent":                1,
            "bold":                  0,
        }

        # ── Guruh tanlash mantiq ──────────────────────────────────────────────────
        # Qoida: chala to'langan bo'lsa ham due_date o'tgan bo'lsa — overdue guruh.
        # To'liq to'lana solmay FIFO bo'yicha keyingi oyga o'tilmaydi.
        if days_diff < 0:
            if days_diff <= -15:
                groups["overdue_more"].append(row)
            elif days_diff <= -8:
                groups["overdue_2weeks"].append(row)
            else:
                groups["overdue_1week"].append(row)
        elif days_diff == 0:
            groups["today"].append(row)
        elif days_diff <= 7:
            groups["due_1week"].append(row)
        elif days_diff <= 14:
            groups["due_2weeks"].append(row)
        else:
            groups["due_later"].append(row)

    return _build_output(groups)


def _find_active_installment(schedule, total_paid):
    """
    FIFO Waterfall algoritmi.

    To'langan summani birinchi oydan boshlab ketma-ket yutib boradi.
    Birinchi to'liq to'lanmagan installmentni qaytaradi.

    Qaytaradigan dict:
        due_date        — installmentning to'lov sanasi
        schedule_amount — ushbu oyning to'liq summasi
        due_amount      — hali to'lanishi kerak bo'lgan qoldiq
    """
    temp_paid = flt(total_paid)

    for item in schedule:
        amount = flt(item.payment_amount)

        if temp_paid >= amount - 0.01:
            # Bu installment to'liq to'langan — keyingiga o't
            temp_paid -= amount
            temp_paid  = max(temp_paid, 0.0)
            continue

        # Bu installment to'liq to'lanmagan — aktiv installment shu
        return {
            "due_date":        item.due_date,
            "schedule_amount": amount,
            "due_amount":      round(amount - temp_paid, 2),
        }

    # Barcha schedule qatorlari consumed lekin remaining_debt > 0 —
    # bu holat normal emas, oxirgi qatorni qaytaramiz
    last = schedule[-1]
    return {
        "due_date":        last.due_date,
        "schedule_amount": flt(last.payment_amount),
        "due_amount":      0.0,
    }


def _build_output(groups):
    """
    Guruh sarlavhalari, qatorlar va jami summalar bilan
    to'liq output qurish.
    """
    group_configs = [
        ("overdue_more",   "1. TO'LOV 2 HAFTADAN KO'P O'TIB KETGANLAR (15+ kun)"),
        ("overdue_2weeks", "2. TO'LOV 2 HAFTA O'TIB KETGANLAR (8–14 kun)"),
        ("overdue_1week",  "3. TO'LOV 1 HAFTA O'TIB KETGANLAR (1–7 kun)"),
        ("today",          "4. BUGUN TO'LASHI KERAK BO'LGANLAR"),
        ("due_1week",      "5. 1 HAFTA ICHIDA TO'LASHI KERAK BO'LGANLAR"),
        ("due_2weeks",     "6. 2 HAFTA ICHIDA TO'LASHI KERAK BO'LGANLAR"),
        ("due_later",      "7. KEYINROQ TO'LASHI KERAK BO'LGANLAR (14+ kun)"),
    ]

    data = []

    for group_key, group_title in group_configs:
        items = groups.get(group_key, [])
        if not items:
            continue

        # Guruh sarlavhasi
        data.append({
            "group_header":          group_title,
            "contract_link":         "",
            "customer_link":         "",
            "current_month_payment": None,
            "due_amount":            None,
            "remaining_debt":        None,
            "overdue_days":          None,
            "note_text":             "",
            "note_category":         "",
            "note_date":             "",
            "indent": 0,
            "bold":   1,
        })

        for row in items:
            data.append(row)

        # Guruh jami
        data.append({
            "group_header":          "",
            "contract_link":         "",
            "customer_link":         _("JAMI:"),
            "current_month_payment": sum(flt(r.get("current_month_payment", 0)) for r in items),
            "due_amount":            sum(flt(r.get("due_amount",            0)) for r in items),
            "remaining_debt":        sum(flt(r.get("remaining_debt",        0)) for r in items),
            "overdue_days":          None,
            "note_text":             "",
            "note_category":         "",
            "note_date":             "",
            "indent": 1,
            "bold":   1,
        })

    return data


# ─────────────────────────────────────────────────────────────────────────────
#  Izoh saqlash / o'qish endpointlari
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def save_note(contract_reference, note_text, note_category="Eslatma"):
    """Yangi shartnoma izohi saqlash"""
    if not contract_reference:
        return {"success": False, "message": "Shartnoma ko'rsatilmagan"}

    if not note_text or not note_text.strip():
        return {"success": False, "message": "Izoh matni bo'sh"}

    if not frappe.db.exists("Installment Application", contract_reference):
        return {"success": False, "message": f"Shartnoma topilmadi: {contract_reference}"}

    try:
        doc = frappe.new_doc("Contract Notes")
        doc.contract_reference = contract_reference
        doc.note_text          = note_text.strip()
        doc.note_category      = note_category or "Eslatma"
        doc.note_date          = nowdate()
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "message": "Izoh saqlandi",
            "note_id": doc.name
        }

    except Exception as e:
        frappe.log_error(f"Note save error: {str(e)}", "Save Note Error")
        return {"success": False, "message": f"Xatolik: {str(e)}"}


@frappe.whitelist()
def get_contract_notes(contract_reference):
    """Shartnomaning barcha izohlarini olish"""
    try:
        notes = frappe.get_all(
            "Contract Notes",
            filters={"contract_reference": contract_reference},
            fields=["name", "note_text", "note_category", "note_date", "created_by_user"],
            order_by="creation desc"
        )
        return {"success": True, "notes": notes}

    except Exception as e:
        frappe.log_error(f"Get notes error: {str(e)}")
        return {"success": False, "message": str(e), "notes": []}
