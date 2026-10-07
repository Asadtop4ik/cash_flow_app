# Copyright (c) 2026, AsadStack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime


# Mijoz bilan haqiqiy gaplashildi deb hisoblanadigan natijalar.
# "Aloqa foizi" (contact rate) KPI'si shu ro'yxat asosida hisoblanadi.
CONTACTED_DISPOSITIONS = (
    "Va'da berdi",
    "To'ladi",
    "Rad etdi",
    "Nizo / Pretenziya",
    "Keyinroq qo'ng'iroq so'radi",
)

# Natija → shartnomaning collection bosqichi
DISPOSITION_STAGE = {
    "Va'da berdi":                "Va'da berdi",
    "To'ladi":                    "Aloqada",
    "Rad etdi":                   "Eskalatsiya",
    "Nizo / Pretenziya":          "Eskalatsiya",
    "Javob bermadi":              "Aloqada",
    "Band":                       "Aloqada",
    "Telefon o'chiq":             "Aloqada",
    "Noto'g'ri raqam":            "Eskalatsiya",
    "Qarindoshi javob berdi":     "Aloqada",
    "Keyinroq qo'ng'iroq so'radi": "Aloqada",
    "Boshqa":                     "Aloqada",
}


class CollectionActivity(Document):
    """
    Qarz yig'ish bo'yicha bitta aloqa urinishi.

    Har bir qo'ng'iroq — javob berilgan yoki berilmagan — shu yerda
    natija kodi (disposition) bilan qayd etiladi. Operator navbati
    aynan shu yozuvlarga tayanadi: oxirgi urinish sanasi, keyingi
    harakat sanasi va urinishlar soni.
    """

    def validate(self):
        if not self.operator:
            self.operator = frappe.session.user

        if not self.activity_datetime:
            self.activity_datetime = now_datetime()

        if not self.customer and self.contract_reference:
            self.customer = frappe.db.get_value(
                "Installment Application", self.contract_reference, "customer"
            )

    def after_insert(self):
        """
        Shartnomadagi collection maydonlarini yangilash.

        Bu maydonlar navbat so'rovini tezlashtirish uchun denormalizatsiya
        qilingan — har safar Collection Activity jadvalini aggregate
        qilmaslik uchun.
        """
        if not self.contract_reference:
            return

        updates = {
            "last_contact_date": frappe.utils.getdate(self.activity_datetime),
            "next_action_date":  self.next_action_date or None,
        }

        stage = DISPOSITION_STAGE.get(self.disposition)
        if stage:
            # "Va'da berdi" bosqichini Promise To Pay o'zi qo'yadi — bu yerda
            # faqat va'da yaratilmagan holatda qo'yiladi.
            if stage != "Va'da berdi" or not self.promise:
                updates["collection_stage"] = stage

        try:
            frappe.db.set_value(
                "Installment Application", self.contract_reference,
                updates, update_modified=False
            )
        except Exception:
            frappe.log_error(
                f"Contract collection fields update failed: {self.contract_reference}",
                "Collection Activity Error"
            )

    @property
    def is_contacted(self):
        return self.disposition in CONTACTED_DISPOSITIONS
