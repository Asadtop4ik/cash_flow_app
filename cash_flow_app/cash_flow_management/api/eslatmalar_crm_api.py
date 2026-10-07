# Copyright (c) 2026, AsadStack and contributors
# For license information, please see license.txt
"""
═══════════════════════════════════════════════════════════════════════════════
 ESLATMALAR CRM — Collections Worklist API
═══════════════════════════════════════════════════════════════════════════════

"Eslatmalar" reporti statik ro'yxat edi: operator har kuni bir xil 337 qatorni
ko'rardi va kimga qo'ng'iroq qilishni o'zi hal qilardi. Bu modul uni haqiqiy
collections CRM navbatiga aylantiradi.

Asosiy g'oya — PRIORITET BALL. Toza "eng kech qolgan birinchi" tartib ishlamaydi,
chunki 820 kun kechikkan umidsiz qarzlar navbatning boshini doimiy egallab oladi.
Shuning uchun ball quyidagilarni birlashtiradi:

    kechikish kuni (cheklangan) + qarz hajmi + mijoz toifasi (A/B/C)
    + buzilgan va'da + bugunga rejalashtirilgan harakat
    − yaqinda aloqa qilingani uchun jarima

Natijada bugun qo'ng'iroq qilingan mijoz navbatdan tushadi, va'dasini buzgan
mijoz esa tepaga chiqadi.

Barcha so'rovlar bulk — N+1 yo'q. 337 shartnoma uchun 7 ta query.
═══════════════════════════════════════════════════════════════════════════════
"""

import math

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, now_datetime, nowdate

from cash_flow_app.cash_flow_management.doctype.collection_activity.collection_activity import (
    CONTACTED_DISPOSITIONS,
)

# ─────────────────────────────────────────────────────────────────────────────
#  Prioritet ball koeffitsiyentlari
# ─────────────────────────────────────────────────────────────────────────────

# Kechikish va qarz hajmi LOGARIFMIK shkalada ballga aylantiriladi.
#
# Nega chiziqli emas: chiziqli shkalada 820 kunlik qarz 8 kunlikdan 100 barobar
# muhim bo'lib chiqadi va navbatni umidsiz eski qarzlar butunlay egallab oladi.
# Nega qattiq "cap" ham emas: cap qo'yilganda yuzlab qator bir xil maksimal
# ballga tiqilib qoladi va tartiblash amalda ishlamay qoladi (birinchi sinovda
# 329 qatorning hammasi 185 ball olgan edi).
#
# Logarifm ikkala muammoni ham hal qiladi: ball doim o'sadi, lekin o'sish
# tezligi pasayib boradi — har bir qator o'zining aniq o'rnini oladi.
#
#   kechikish:  7 kun → 7.5    30 kun → 18    180 kun → 36    657 kun → 50
#   qarz:     $100   → 9.5    $600   → 22    $3200   → 36
OVERDUE_LOG_WEIGHT = 25.0      # 25 * log10(1 + kun / 7)
OVERDUE_LOG_DIVISOR = 7.0
AMOUNT_LOG_WEIGHT  = 20.0      # 20 * log10(1 + summa / 50)
AMOUNT_LOG_DIVISOR = 50.0

# Mijoz toifasi (customer_classification — payment_entry.py avtomatik qo'yadi)
TIER_BONUS         = {"A": 0.0, "B": 10.0, "C": 20.0}

BROKEN_PROMISE_BONUS   = 40.0   # va'dasini buzgan — eng ishonchsiz, darhol aloqa
PROMISE_DUE_BONUS      = 25.0   # va'da sanasi bugun/o'tdi — eslatish kerak
NEXT_ACTION_DUE_BONUS  = 30.0   # operator o'zi "shu kuni qo'ng'iroq qil" degan
NEVER_CONTACTED_BONUS  = 15.0   # hali bir marta ham urinilmagan

# Yaqinda aloqa qilinganlik jarimasi (kun → ayiriladigan ball)
RECENCY_PENALTY = {0: 70.0, 1: 35.0, 2: 15.0, 3: 5.0}

# Navbatga tushish uchun kechikkan shartnomaga qayta urinishgacha kutiladigan kun
RETRY_COOLDOWN_DAYS = 3

# Kechikmagan, lekin yaqinlashayotgan to'lov necha kun oldin navbatga tushadi
UPCOMING_WINDOW_DAYS = 7


# ═════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def get_queue(view="today", only_mine=0, search="", stage=None, limit=400):
    """
    Operator navbati + KPI qatori.

    view:
        today     — bugun qilinishi kerak bo'lgan ishlar (asosiy ko'rinish)
        overdue   — barcha kechikkanlar
        promises  — ochiq va'dalar
        broken    — buzilgan va'dalar
        upcoming  — yaqin 7 kun ichida to'lovi bor
        unassigned— operatorga biriktirilmaganlar
        all       — barcha to'lanmagan shartnomalar
    """
    only_mine = cint(only_mine)
    limit     = cint(limit) or 400
    search    = (search or "").strip().lower()

    states = _build_contract_states()
    today  = getdate(nowdate())

    rows = []
    for st in states:
        if only_mine and st["collection_operator"] != frappe.session.user:
            continue
        if stage and st["collection_stage"] != stage:
            continue
        if search and not _matches(st, search):
            continue
        if not _in_view(st, view, today):
            continue
        rows.append(st)

    rows.sort(key=lambda r: (-r["priority_score"], -r["overdue_days"]))

    return {
        "view":    view,
        "rows":    rows[:limit],
        "total":   len(rows),
        "kpi":     _compute_kpi(states, today, only_mine),
        "counts":  _view_counts(states, today, only_mine),
        "stages":  _stage_counts(states),
        "as_of":   str(now_datetime()),
    }


@frappe.whitelist()
def get_contract_360(contract_reference):
    """O'ng paneldagi mijoz 360° ko'rinishi uchun to'liq ma'lumot"""
    if not frappe.db.exists("Installment Application", contract_reference):
        frappe.throw(_("Shartnoma topilmadi: {0}").format(contract_reference))

    app = frappe.db.get_value(
        "Installment Application", contract_reference,
        ["name", "customer", "customer_name", "sales_order", "transaction_date",
         "custom_grand_total_with_interest", "total_amount", "downpayment_amount",
         "monthly_payment", "installment_months", "custom_start_date", "notes",
         "collection_operator", "collection_stage", "last_contact_date",
         "next_action_date"],
        as_dict=True
    )

    customer = _customer_info([app.customer]).get(app.customer, {})

    schedule = frappe.db.sql("""
        SELECT due_date, payment_amount
        FROM `tabPayment Schedule`
        WHERE parent = %(c)s AND parenttype = 'Installment Application'
        ORDER BY due_date ASC
    """, {"c": contract_reference}, as_dict=1)

    payments = []
    if app.sales_order:
        payments = frappe.db.sql("""
            SELECT name, posting_date, paid_amount, mode_of_payment
            FROM `tabPayment Entry`
            WHERE custom_contract_reference = %(so)s
              AND docstatus = 1 AND payment_type = 'Receive'
            ORDER BY posting_date ASC, creation ASC
        """, {"so": app.sales_order}, as_dict=1)

    total_paid = flt(sum(flt(p.paid_amount) for p in payments))

    # FIFO: har bir installmentning holati
    schedule_rows = _fifo_schedule_status(schedule, total_paid)

    activities = frappe.get_all(
        "Collection Activity",
        filters={"contract_reference": contract_reference},
        fields=["name", "activity_datetime", "channel", "disposition", "outcome_note",
                "next_action_date", "next_action_time", "operator", "promise",
                "phone_called", "is_important"],
        order_by="activity_datetime desc",
        limit=50,
    )

    promises = frappe.get_all(
        "Promise To Pay",
        filters={"contract_reference": contract_reference},
        fields=["name", "promised_date", "promised_amount", "status", "paid_amount",
                "grace_days", "operator", "broken_on", "settled_on", "notes"],
        order_by="promised_date desc",
        limit=30,
    )

    # Eski "Contract Notes" yozuvlari — CRM'dan oldingi izohlar yo'qolmasligi uchun
    legacy_notes = frappe.get_all(
        "Contract Notes",
        filters={"contract_reference": contract_reference},
        fields=["name", "note_date", "note_category", "note_text", "created_by_user"],
        order_by="creation desc",
        limit=30,
    )

    contract_total  = flt(app.custom_grand_total_with_interest)
    remaining_debt  = contract_total - total_paid
    active          = _find_active_installment(schedule, total_paid)
    overdue_days    = 0
    if active:
        diff = (getdate(active["due_date"]) - getdate(nowdate())).days
        overdue_days = -diff if diff < 0 else 0

    return {
        "contract":        app,
        "customer":        customer,
        "phones":          customer.get("phones", []),
        "contract_total":  contract_total,
        "total_paid":      total_paid,
        "remaining_debt":  remaining_debt,
        "paid_percent":    round(total_paid / contract_total * 100, 1) if contract_total else 0,
        "overdue_days":    overdue_days,
        "active":          active,
        "schedule":        schedule_rows,
        "payments":        payments,
        "activities":      activities,
        "promises":        promises,
        "legacy_notes":    legacy_notes,
        "dispositions":    _disposition_options(),
    }


@frappe.whitelist()
def log_activity(contract_reference, disposition, outcome_note=None, channel="Telefon",
                 next_action_date=None, next_action_time=None, phone_called=None,
                 promised_date=None, promised_amount=None, grace_days=3,
                 is_important=0, overdue_days=None, outstanding=None):
    """
    Qo'ng'iroq natijasini qayd etish. Kerak bo'lsa bir vaqtda va'da yaratadi.

    Bitta tranzaksiyada: Collection Activity + (ixtiyoriy) Promise To Pay,
    so'ng shartnomadagi denormalizatsiya maydonlari yangilanadi.
    """
    if not frappe.has_permission("Collection Activity", "create"):
        frappe.throw(_("Ruxsat yo'q"))

    activity = frappe.new_doc("Collection Activity")
    activity.contract_reference       = contract_reference
    activity.disposition              = disposition
    activity.outcome_note             = outcome_note
    activity.channel                  = channel or "Telefon"
    activity.next_action_date         = next_action_date or None
    activity.next_action_time         = next_action_time or None
    activity.phone_called             = phone_called
    activity.is_important             = cint(is_important)
    activity.overdue_days_at_contact  = cint(overdue_days) if overdue_days else 0
    activity.outstanding_at_contact   = flt(outstanding)
    activity.insert(ignore_permissions=True)

    promise_name = None
    if promised_date and flt(promised_amount) > 0:
        promise = frappe.new_doc("Promise To Pay")
        promise.contract_reference    = contract_reference
        promise.promised_date         = promised_date
        promise.promised_amount       = flt(promised_amount)
        promise.grace_days            = cint(grace_days) or 3
        promise.status                = "Open"
        promise.created_from_activity = activity.name
        promise.notes                 = outcome_note
        promise.insert(ignore_permissions=True)
        promise_name = promise.name

        activity.db_set("promise", promise_name, update_modified=False)

        # Va'da sanasi keyingi harakat sanasi sifatida ham xizmat qiladi —
        # operator o'sha kuni to'lov kelganini tekshirishi kerak.
        if not next_action_date:
            frappe.db.set_value(
                "Installment Application", contract_reference,
                "next_action_date", promised_date, update_modified=False
            )

    frappe.db.commit()

    return {
        "success":  True,
        "message":  _("Natija qayd etildi"),
        "activity": activity.name,
        "promise":  promise_name,
    }


@frappe.whitelist()
def assign_operator(contract_reference, operator=None):
    """Shartnomani operatorga biriktirish (bo'sh qoldirilsa — biriktirish olinadi)"""
    if not frappe.has_permission("Installment Application", "write"):
        frappe.throw(_("Ruxsat yo'q"))

    if operator:
        _validate_operator(operator)

    frappe.db.set_value(
        "Installment Application", contract_reference,
        "collection_operator", operator or None, update_modified=False
    )
    frappe.db.commit()
    return {"success": True, "operator": operator}


@frappe.whitelist()
def bulk_assign(contracts, operator):
    """Bir nechta shartnomani bitta operatorga biriktirish"""
    if isinstance(contracts, str):
        contracts = frappe.parse_json(contracts)

    if not frappe.has_permission("Installment Application", "write"):
        frappe.throw(_("Ruxsat yo'q"))

    if operator:
        _validate_operator(operator)

    for c in contracts:
        frappe.db.set_value(
            "Installment Application", c,
            "collection_operator", operator or None, update_modified=False
        )
    frappe.db.commit()
    return {"success": True, "count": len(contracts)}


def _validate_operator(operator):
    """Biriktirilayotgan foydalanuvchi haqiqatan operator ekanini tekshirish"""
    if not frappe.db.exists("User", operator):
        frappe.throw(_("Foydalanuvchi topilmadi: {0}").format(operator))

    if not frappe.db.exists("Has Role", {"parent": operator, "role": OPERATOR_ROLE}):
        frappe.throw(_(
            "{0} foydalanuvchisida '{1}' roli yo'q — shartnomani unga "
            "biriktirish mumkin emas"
        ).format(operator, OPERATOR_ROLE))


@frappe.whitelist()
def set_stage(contract_reference, stage):
    """Collection bosqichini qo'lda o'zgartirish (eskalatsiya uchun)"""
    frappe.db.set_value(
        "Installment Application", contract_reference,
        "collection_stage", stage, update_modified=False
    )
    frappe.db.commit()
    return {"success": True, "stage": stage}


@frappe.whitelist()
def cancel_promise(promise, reason=None):
    """Va'dani bekor qilish (noto'g'ri kiritilgan bo'lsa)"""
    doc = frappe.get_doc("Promise To Pay", promise)
    doc.status = "Cancelled"
    if reason:
        doc.notes = f"{doc.notes or ''}\n[Bekor qilindi] {reason}".strip()
    doc.flags.ignore_permissions = True
    doc.save()
    frappe.db.commit()
    return {"success": True}


# Qarz yig'ish navbati faqat shu roldagi foydalanuvchilarga taqsimlanadi.
# Ataylab "System Manager" va "Accounts Manager" kiritilmagan — ular tizim
# ma'murlari, qo'ng'iroq qiluvchi operatorlar emas. Kimni operator qilish
# kerak bo'lsa, unga User'da "Operator" roli beriladi.
OPERATOR_ROLE = "Operator"


@frappe.whitelist()
def get_operators():
    """
    Operator rolidagi faol foydalanuvchilar + hozirgi yuklamasi.

    `assigned` — shu operatorga biriktirilgan to'lanmagan shartnomalar soni.
    Rahbar navbatni taqsimlayotganda kimning yuklamasi kamligini ko'rishi uchun.
    """
    operators = frappe.db.sql("""
        SELECT DISTINCT u.name, u.full_name
        FROM `tabUser` u
        INNER JOIN `tabHas Role` r ON r.parent = u.name
        WHERE u.enabled = 1
          AND r.role = %(role)s
          AND u.name NOT IN ('Guest', 'Administrator')
        ORDER BY u.full_name
    """, {"role": OPERATOR_ROLE}, as_dict=1)

    if not operators:
        return []

    loads = {
        r.collection_operator: cint(r.n)
        for r in frappe.db.sql("""
            SELECT collection_operator, COUNT(*) AS n
            FROM `tabInstallment Application`
            WHERE docstatus = 1 AND collection_operator IS NOT NULL
            GROUP BY collection_operator
        """, as_dict=1)
    }

    for o in operators:
        o["assigned"] = loads.get(o.name, 0)

    return operators


# ═════════════════════════════════════════════════════════════════════════════
#  SCHEDULER
# ═════════════════════════════════════════════════════════════════════════════

def evaluate_promises():
    """
    Kunlik: ochiq va'dalarni baholash.

    Kutish muddati o'tgan va to'lov kelmagan va'dalar Broken deb belgilanadi
    va shartnoma "Buzilgan va'da" bosqichiga o'tadi — ertasiga operator
    navbatining tepasida turadi.
    """
    open_promises = frappe.get_all(
        "Promise To Pay",
        filters={"status": "Open"},
        fields=["name"],
    )

    changed = 0
    for p in open_promises:
        try:
            doc = frappe.get_doc("Promise To Pay", p.name)
            before = doc.status
            after  = doc.evaluate(save=True)
            if before != after:
                changed += 1
        except Exception:
            frappe.log_error(
                f"Promise evaluate failed: {p.name}",
                "Promise To Pay Evaluation Error"
            )

    frappe.db.commit()
    frappe.logger().info(
        f"evaluate_promises: {len(open_promises)} tekshirildi, {changed} o'zgardi"
    )
    return {"checked": len(open_promises), "changed": changed}


def on_payment_submit_evaluate(doc, method=None):
    """
    Payment Entry submit bo'lganda shu shartnomaning ochiq va'dalarini
    darhol baholash — operator kunlik scheduler'ni kutmasligi uchun
    va'da "Kept" holatiga o'sha zahoti o'tadi.
    """
    sales_order = getattr(doc, "custom_contract_reference", None)
    if not sales_order or doc.payment_type != "Receive":
        return

    contracts = frappe.get_all(
        "Installment Application",
        filters={"sales_order": sales_order, "docstatus": 1},
        pluck="name",
    )
    if not contracts:
        return

    promises = frappe.get_all(
        "Promise To Pay",
        filters={"contract_reference": ["in", contracts], "status": "Open"},
        pluck="name",
    )

    for name in promises:
        try:
            frappe.get_doc("Promise To Pay", name).evaluate(save=True)
        except Exception:
            frappe.log_error(
                f"Promise evaluate on payment failed: {name}",
                "Promise To Pay Evaluation Error"
            )


# ═════════════════════════════════════════════════════════════════════════════
#  CORE — shartnoma holatlarini bulk qurish
# ═════════════════════════════════════════════════════════════════════════════

def _build_contract_states():
    """
    Barcha to'lanmagan shartnomalar uchun to'liq collection holati.

    Reportdagi FIFO waterfall mantiqi saqlanadi, ustiga CRM qatlami qo'shiladi:
    aloqa tarixi, va'dalar, operator biriktirmasi va prioritet ball.
    """
    today = getdate(nowdate())

    applications = frappe.get_all(
        "Installment Application",
        filters={"docstatus": 1},
        fields=["name", "customer", "customer_name", "sales_order",
                "custom_grand_total_with_interest", "collection_operator",
                "collection_stage", "last_contact_date", "next_action_date"],
    )
    if not applications:
        return []

    app_names    = [a.name for a in applications]
    sales_orders = [a.sales_order for a in applications if a.sales_order]
    if not sales_orders:
        return []

    so_to_app = {a.sales_order: a.name for a in applications if a.sales_order}

    # ── Payment Schedule ────────────────────────────────────────────────────
    schedules_map = {}
    for row in frappe.db.sql("""
        SELECT parent, due_date, payment_amount
        FROM `tabPayment Schedule`
        WHERE parent IN %(apps)s AND parenttype = 'Installment Application'
        ORDER BY parent, due_date ASC
    """, {"apps": app_names}, as_dict=1):
        schedules_map.setdefault(row.parent, []).append(row)

    # ── Jami to'lovlar ──────────────────────────────────────────────────────
    paid_map = {}
    for r in frappe.db.sql("""
        SELECT custom_contract_reference AS so, SUM(paid_amount) AS total_paid
        FROM `tabPayment Entry`
        WHERE custom_contract_reference IN %(sos)s
          AND docstatus = 1 AND payment_type = 'Receive'
        GROUP BY custom_contract_reference
    """, {"sos": sales_orders}, as_dict=1):
        app_name = so_to_app.get(r.so)
        if app_name:
            paid_map[app_name] = flt(r.total_paid)

    # ── Aloqa tarixi aggregate ──────────────────────────────────────────────
    activity_map = {}
    for r in frappe.db.sql("""
        SELECT contract_reference,
               COUNT(*)                  AS attempts,
               MAX(activity_datetime)    AS last_attempt
        FROM `tabCollection Activity`
        WHERE contract_reference IN %(apps)s
        GROUP BY contract_reference
    """, {"apps": app_names}, as_dict=1):
        activity_map[r.contract_reference] = r

    # Oxirgi natija kodi va izohi (har shartnoma uchun bitta)
    last_activity_map = {}
    for r in frappe.db.sql("""
        SELECT ca.contract_reference, ca.disposition, ca.outcome_note,
               ca.activity_datetime, ca.operator
        FROM `tabCollection Activity` ca
        INNER JOIN (
            SELECT contract_reference, MAX(activity_datetime) AS mx
            FROM `tabCollection Activity`
            WHERE contract_reference IN %(apps)s
            GROUP BY contract_reference
        ) t ON t.contract_reference = ca.contract_reference
           AND t.mx = ca.activity_datetime
        GROUP BY ca.contract_reference
    """, {"apps": app_names}, as_dict=1):
        last_activity_map[r.contract_reference] = r

    # ── Va'dalar ────────────────────────────────────────────────────────────
    open_promise_map   = {}
    broken_promise_map = {}
    for r in frappe.db.sql("""
        SELECT contract_reference, name, promised_date, promised_amount,
               status, paid_amount, grace_days
        FROM `tabPromise To Pay`
        WHERE contract_reference IN %(apps)s
          AND status IN ('Open', 'Broken')
        ORDER BY promised_date DESC
    """, {"apps": app_names}, as_dict=1):
        if r.status == "Open":
            open_promise_map.setdefault(r.contract_reference, r)
        else:
            bucket = broken_promise_map.setdefault(r.contract_reference, {"count": 0, "last": None})
            bucket["count"] += 1
            if bucket["last"] is None:
                bucket["last"] = r

    # ── Mijoz ma'lumotlari ──────────────────────────────────────────────────
    customers_info = _customer_info(list({a.customer for a in applications if a.customer}))

    # ── Qurish ──────────────────────────────────────────────────────────────
    states = []
    for app in applications:
        contract_total = flt(app.custom_grand_total_with_interest)
        total_paid     = paid_map.get(app.name, 0.0)
        remaining_debt = contract_total - total_paid

        if remaining_debt <= 0.01:
            continue

        schedule = schedules_map.get(app.name)
        if not schedule:
            continue

        active = _find_active_installment(schedule, total_paid)
        if not active:
            continue

        due_date  = getdate(active["due_date"])
        days_diff = (due_date - today).days

        cust = customers_info.get(app.customer, {})

        act  = activity_map.get(app.name)
        last = last_activity_map.get(app.name)

        last_attempt_date = getdate(act.last_attempt) if act and act.last_attempt else None
        days_since_contact = (today - last_attempt_date).days if last_attempt_date else None

        open_promise = open_promise_map.get(app.name)
        broken       = broken_promise_map.get(app.name)

        st = {
            "contract":            app.name,
            "customer":            app.customer,
            "customer_name":       app.customer_name or cust.get("customer_name") or app.customer,
            "classification":      cust.get("classification") or "A",
            "phones":              cust.get("phones", []),
            "telegram_id":         cust.get("telegram_id"),
            "image":               cust.get("image"),

            "contract_total":      contract_total,
            "total_paid":          total_paid,
            "remaining_debt":      remaining_debt,
            "due_date":            str(due_date),
            "due_amount":          active["due_amount"],
            "installment_amount":  active["schedule_amount"],
            "days_diff":           days_diff,
            "overdue_days":        -days_diff if days_diff < 0 else 0,
            "bucket":              _bucket(days_diff),

            "collection_operator": app.collection_operator,
            "collection_stage":    app.collection_stage or "Yangi",
            "next_action_date":    str(app.next_action_date) if app.next_action_date else None,

            "attempts":            cint(act.attempts) if act else 0,
            "last_contact":        str(last_attempt_date) if last_attempt_date else None,
            "days_since_contact":  days_since_contact,
            "last_disposition":    last.disposition if last else None,
            "last_note":           last.outcome_note if last else None,

            "open_promise":        _promise_brief(open_promise),
            "broken_promises":     broken["count"] if broken else 0,
        }

        st["priority_score"] = _priority_score(st, today)
        st["reasons"]        = _queue_reasons(st, today)
        states.append(st)

    return states


def _priority_score(st, today):
    """
    Navbat prioriteti.

    Modul boshidagi izohga qarang — maqsad: eng ko'p pul qaytarish ehtimoli
    bor qo'ng'iroqni tepaga chiqarish, umidsiz eski qarzlarni navbatni band
    qilishiga yo'l qo'ymaslik.
    """
    score = 0.0

    if st["overdue_days"] > 0:
        score += OVERDUE_LOG_WEIGHT * math.log10(
            1 + st["overdue_days"] / OVERDUE_LOG_DIVISOR
        )

    due = flt(st["due_amount"])
    if due > 0:
        score += AMOUNT_LOG_WEIGHT * math.log10(1 + due / AMOUNT_LOG_DIVISOR)

    score += TIER_BONUS.get(st["classification"], 0.0)

    if st["broken_promises"]:
        score += BROKEN_PROMISE_BONUS

    promise = st["open_promise"]
    if promise and getdate(promise["promised_date"]) <= today:
        score += PROMISE_DUE_BONUS

    if st["next_action_date"] and getdate(st["next_action_date"]) <= today:
        score += NEXT_ACTION_DUE_BONUS

    if st["attempts"] == 0 and st["overdue_days"] > 0:
        score += NEVER_CONTACTED_BONUS

    dsc = st["days_since_contact"]
    if dsc is not None:
        score -= RECENCY_PENALTY.get(dsc, 0.0)

    return round(score, 1)


def _queue_reasons(st, today):
    """Qator nega navbatda turganini operatorga ko'rsatish uchun yorliqlar"""
    reasons = []

    if st["broken_promises"]:
        reasons.append("Va'da buzilgan")

    promise = st["open_promise"]
    if promise:
        pd = getdate(promise["promised_date"])
        if pd < today:
            reasons.append("Va'da muddati o'tdi")
        elif pd == today:
            reasons.append("Va'da bugun")

    if st["next_action_date"]:
        nad = getdate(st["next_action_date"])
        if nad < today:
            reasons.append("Rejalashtirilgan harakat o'tdi")
        elif nad == today:
            reasons.append("Bugun qo'ng'iroq rejalashtirilgan")

    if st["overdue_days"] > 0 and st["attempts"] == 0:
        reasons.append("Hali urinilmagan")

    if st["days_diff"] == 0:
        reasons.append("To'lov bugun")

    return reasons


def _in_view(st, view, today):
    """Qator tanlangan ko'rinishga tushadimi"""
    if view == "all":
        return True

    if view == "overdue":
        return st["overdue_days"] > 0

    if view == "promises":
        return bool(st["open_promise"])

    if view == "broken":
        return st["broken_promises"] > 0

    if view == "upcoming":
        return 0 < st["days_diff"] <= UPCOMING_WINDOW_DAYS

    if view == "unassigned":
        return not st["collection_operator"]

    # ── view == "today": bugun haqiqatan ish qilinishi kerak bo'lganlar ────
    if st["broken_promises"]:
        return True

    if st["next_action_date"] and getdate(st["next_action_date"]) <= today:
        return True

    promise = st["open_promise"]
    if promise and getdate(promise["promised_date"]) <= today:
        return True

    if st["days_diff"] == 0:
        return True

    if st["overdue_days"] > 0:
        # Ochiq va'dasi bor va muddati kelmagan bo'lsa — bezovta qilmaymiz
        if promise and getdate(promise["promised_date"]) > today:
            return False
        dsc = st["days_since_contact"]
        return dsc is None or dsc >= RETRY_COOLDOWN_DAYS

    return False


def _view_counts(states, today, only_mine):
    """Filtr tugmalaridagi sonlar"""
    views = ["today", "overdue", "promises", "broken", "upcoming", "unassigned", "all"]
    counts = {}
    for v in views:
        n = 0
        for st in states:
            if only_mine and st["collection_operator"] != frappe.session.user:
                continue
            if _in_view(st, v, today):
                n += 1
        counts[v] = n
    return counts


def _stage_counts(states):
    counts = {}
    for st in states:
        counts[st["collection_stage"]] = counts.get(st["collection_stage"], 0) + 1
    return counts


def _compute_kpi(states, today, only_mine=0):
    """
    Collections bo'limining asosiy ko'rsatkichlari.

    ptp_kept_rate — jahon amaliyotida collections bo'limining №1 KPI'si:
    berilgan va'dalarning qanchasi haqiqatan bajarilgan. Oxirgi 30 kun.
    """
    overdue = [s for s in states if s["overdue_days"] > 0]

    # Bugungi urinishlar va aloqa foizi
    attempts_today = frappe.db.sql("""
        SELECT disposition, COUNT(*) AS n
        FROM `tabCollection Activity`
        WHERE DATE(activity_datetime) = %(today)s
        GROUP BY disposition
    """, {"today": today}, as_dict=1)

    total_attempts = sum(cint(r.n) for r in attempts_today)
    contacted = sum(cint(r.n) for r in attempts_today if r.disposition in CONTACTED_DISPOSITIONS)

    my_attempts = frappe.db.count("Collection Activity", {
        "operator": frappe.session.user,
        "activity_datetime": [">=", f"{today} 00:00:00"],
    })

    # Va'dalar
    open_promises = frappe.db.sql("""
        SELECT COUNT(*) AS n, IFNULL(SUM(promised_amount), 0) AS amt
        FROM `tabPromise To Pay` WHERE status = 'Open'
    """, as_dict=1)[0]

    promise_outcomes = frappe.db.sql("""
        SELECT status, COUNT(*) AS n
        FROM `tabPromise To Pay`
        WHERE promised_date >= %(from_date)s
          AND status IN ('Kept', 'Partially Kept', 'Broken')
        GROUP BY status
    """, {"from_date": add_days(today, -30)}, as_dict=1)

    outcome = {r.status: cint(r.n) for r in promise_outcomes}
    settled = sum(outcome.values())
    kept    = outcome.get("Kept", 0)

    collected_today = frappe.db.sql("""
        SELECT IFNULL(SUM(paid_amount), 0) AS amt
        FROM `tabPayment Entry`
        WHERE docstatus = 1 AND payment_type = 'Receive' AND posting_date = %(today)s
    """, {"today": today}, as_dict=1)[0]

    # "Bugungi navbat" soni ko'rinish filtriga bo'ysunadi — operator
    # "Mening navbatim" yoqilganda o'zining ishini ko'rishi kerak.
    queue_states = states
    if only_mine:
        queue_states = [s for s in states
                        if s["collection_operator"] == frappe.session.user]

    return {
        "queue_today":       sum(1 for s in queue_states if _in_view(s, "today", today)),
        "my_attempts_today": cint(my_attempts),
        "attempts_today":    total_attempts,
        "contacted_today":   contacted,
        "contact_rate":      round(contacted / total_attempts * 100, 1) if total_attempts else 0,
        "open_promises":     cint(open_promises.n),
        "open_promise_amt":  flt(open_promises.amt),
        "broken_promises":   outcome.get("Broken", 0),
        "ptp_kept_rate":     round(kept / settled * 100, 1) if settled else None,
        "overdue_count":     len(overdue),
        "overdue_amount":    flt(sum(s["due_amount"] for s in overdue)),
        "total_debt":        flt(sum(s["remaining_debt"] for s in states)),
        "collected_today":   flt(collected_today.amt),
    }


# ═════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _customer_info(customer_names):
    """Telefon raqamlari, toifa, telegram — bitta query bilan"""
    if not customer_names:
        return {}

    rows = frappe.db.sql("""
        SELECT name, customer_name, customer_classification,
               custom_phone_1, custom_phone_2, custom_phone,
               mobile_no, custom_telegram_id, custom_telegram_username, image
        FROM `tabCustomer`
        WHERE name IN %(names)s
    """, {"names": customer_names}, as_dict=1)

    info = {}
    for r in rows:
        phones = []
        for label, value in (
            ("Asosiy",    r.custom_phone_1),
            ("Qo'shimcha", r.custom_phone_2),
            ("Boshqa",    r.custom_phone),
            ("Mobil",     r.mobile_no),
        ):
            v = (value or "").strip()
            if v and v not in [p["number"] for p in phones]:
                phones.append({"label": label, "number": v})

        info[r.name] = {
            "customer_name":      r.customer_name,
            "classification":     r.customer_classification or "A",
            "phones":             phones,
            "telegram_id":        r.custom_telegram_id,
            "telegram_username":  r.custom_telegram_username,
            "image":              r.image,
        }
    return info


def _find_active_installment(schedule, total_paid):
    """
    FIFO waterfall — reportdagi mantiqning aynan o'zi.

    To'langan summa birinchi oydan ketma-ket "yutiladi"; birinchi to'liq
    to'lanmagan installment aktiv hisoblanadi.
    """
    temp_paid = flt(total_paid)

    for item in schedule:
        amount = flt(item.payment_amount)
        if temp_paid >= amount - 0.01:
            temp_paid = max(temp_paid - amount, 0.0)
            continue
        return {
            "due_date":        str(item.due_date),
            "schedule_amount": amount,
            "due_amount":      round(amount - temp_paid, 2),
        }

    last = schedule[-1]
    return {
        "due_date":        str(last.due_date),
        "schedule_amount": flt(last.payment_amount),
        "due_amount":      0.0,
    }


def _fifo_schedule_status(schedule, total_paid):
    """360° panelda to'lov jadvalini holat bilan ko'rsatish"""
    temp_paid = flt(total_paid)
    today     = getdate(nowdate())
    rows      = []

    for item in schedule:
        amount = flt(item.payment_amount)
        if temp_paid >= amount - 0.01:
            temp_paid = max(temp_paid - amount, 0.0)
            paid, status = amount, "paid"
        elif temp_paid > 0.01:
            paid, temp_paid = temp_paid, 0.0
            status = "partial"
        else:
            paid, status = 0.0, "unpaid"

        due = getdate(item.due_date)
        rows.append({
            "due_date":     str(due),
            "amount":       amount,
            "paid":         round(paid, 2),
            "outstanding":  round(amount - paid, 2),
            "status":       status,
            "is_overdue":   status != "paid" and due < today,
            "overdue_days": (today - due).days if status != "paid" and due < today else 0,
        })
    return rows


def _promise_brief(promise):
    if not promise:
        return None
    return {
        "name":            promise.name,
        "promised_date":   str(promise.promised_date),
        "promised_amount": flt(promise.promised_amount),
        "paid_amount":     flt(promise.paid_amount),
        "grace_days":      cint(promise.grace_days),
    }


def _bucket(days_diff):
    """Reportdagi 7 ta guruhga mos keluvchi yorliq"""
    if days_diff < 0:
        if days_diff <= -15:
            return "overdue_more"
        if days_diff <= -8:
            return "overdue_2weeks"
        return "overdue_1week"
    if days_diff == 0:
        return "today"
    if days_diff <= 7:
        return "due_1week"
    if days_diff <= 14:
        return "due_2weeks"
    return "due_later"


def _matches(st, needle):
    haystack = " ".join(filter(None, [
        st["contract"], st["customer"], st["customer_name"],
        " ".join(p["number"] for p in st["phones"]),
    ])).lower()
    return needle in haystack


def _disposition_options():
    """Natija kodlari — doctype Select maydonidan o'qiladi, qotib qolmasligi uchun"""
    meta = frappe.get_meta("Collection Activity")
    field = meta.get_field("disposition")
    options = [o for o in (field.options or "").split("\n") if o]
    return [
        {"value": o, "contacted": o in CONTACTED_DISPOSITIONS}
        for o in options
    ]
