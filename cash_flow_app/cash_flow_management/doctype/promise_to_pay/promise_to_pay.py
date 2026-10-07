# Copyright (c) 2026, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, nowdate


class PromiseToPay(Document):
    """
    To'lov va'dasi (Promise to Pay, PTP).

    Operator mijoz bilan gaplashib "falon sanada falon summa to'layman" degan
    va'dani qayd etadi. Keyin tizim o'zi kuzatadi: va'da sanasidan keyin
    kutish muddati (grace_days) o'tganda to'lov kelmasa — va'da buzilgan
    (Broken) deb belgilanadi. Buzilgan va'dalar operator navbatida eng
    yuqori prioritetga chiqadi.
    """

    def validate(self):
        if not self.operator:
            self.operator = frappe.session.user

        if flt(self.promised_amount) <= 0:
            frappe.throw(_("Va'da summasi noldan katta bo'lishi kerak"))

        if self.grace_days is None:
            self.grace_days = 3

        if not self.customer and self.contract_reference:
            self.customer = frappe.db.get_value(
                "Installment Application", self.contract_reference, "customer"
            )

    def after_insert(self):
        """Shartnomaning collection bosqichini yangilash"""
        _set_contract_stage(self.contract_reference, "Va'da berdi")

    # ──────────────────────────────────────────────────────────────────────
    #  Va'da holatini baholash
    # ──────────────────────────────────────────────────────────────────────

    def evaluate(self, save=True):
        """
        Va'dadan keyin tushgan to'lovlarni hisoblab holatni aniqlaydi.

        Qoida:
          to'liq to'landi                      → Kept
          muddat o'tdi, qisman to'landi        → Partially Kept
          muddat o'tdi, to'lov yo'q            → Broken
          muddat o'tmagan                      → Open
        """
        if self.status in ("Kept", "Partially Kept", "Broken", "Cancelled"):
            return self.status

        payments = _payments_since(self.contract_reference, getdate(self.creation))
        paid = flt(sum(flt(p.paid_amount) for p in payments))

        self.paid_amount = paid

        deadline = add_days(getdate(self.promised_date), int(self.grace_days or 0))
        today = getdate(nowdate())

        new_status = "Open"

        if paid >= flt(self.promised_amount) - 0.01:
            new_status = "Kept"
            self.settled_on = max(getdate(p.posting_date) for p in payments)
        elif today > deadline:
            if paid > 0.01:
                new_status = "Partially Kept"
                self.settled_on = max(getdate(p.posting_date) for p in payments)
            else:
                new_status = "Broken"
                self.broken_on = today

        self.status = new_status

        if save:
            self.flags.ignore_permissions = True
            self.save()

            if new_status == "Broken":
                _set_contract_stage(self.contract_reference, "Buzilgan va'da")
            elif new_status in ("Kept", "Partially Kept"):
                _set_contract_stage(self.contract_reference, "Aloqada")

        return new_status


def _payments_since(contract_reference, from_date):
    """
    Shartnoma bo'yicha berilgan sanadan keyin tushgan to'lovlar.

    Payment Entry'lar shartnomaga sales_order orqali bog'lanadi
    (custom_contract_reference maydoni) — Installment Application nomiga
    emas. Shuning uchun avval sales_order olinadi.
    """
    sales_order = frappe.db.get_value(
        "Installment Application", contract_reference, "sales_order"
    )
    if not sales_order:
        return []

    return frappe.db.sql("""
        SELECT paid_amount, posting_date
        FROM `tabPayment Entry`
        WHERE custom_contract_reference = %(so)s
          AND docstatus = 1
          AND payment_type = 'Receive'
          AND posting_date >= %(from_date)s
    """, {"so": sales_order, "from_date": from_date}, as_dict=1)


def _set_contract_stage(contract_reference, stage):
    """Submitted shartnomada ham ishlashi uchun db.set_value"""
    if not contract_reference:
        return
    try:
        frappe.db.set_value(
            "Installment Application", contract_reference,
            "collection_stage", stage, update_modified=False
        )
    except Exception:
        frappe.log_error(
            f"Stage update failed: {contract_reference} → {stage}",
            "Collection Stage Error"
        )
