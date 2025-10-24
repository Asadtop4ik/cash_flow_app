# Testing Installation (For Developers)

Bu qo'llanma app ni test qilish uchun - yangi site yaratib, appni o'rnatib ko'rish.

## Test Qilish

### 1. Yangi Test Site Yaratish

```bash
cd /home/asadbek/frappe-bench

# Yangi test site
bench new-site test.localhost
```

### 2. ERPNext va Cash Flow App O'rnatish

```bash
# ERPNext ni o'rnatish
bench --site test.localhost install-app erpnext

# Cash Flow App ni o'rnatish
bench --site test.localhost install-app cash_flow_app

# Migrate (fixtures import)
bench --site test.localhost migrate
```

### 3. Tekshirish

```bash
# Site ni set qilish
bench use test.localhost

# Bench ishga tushirish
bench start
```

Browser da: http://test.localhost:8000

**Administrator** bilan login qiling va tekshiring:

#### Item DocType:
- `item_type_custom` field bor
- `item_category` field bor
- `item_code_manual` field bor
- Ba'zi fieldlar hidden (masalan, `barcode`, `has_variants`)

#### Payment Entry DocType:
- `custom_izoh` field bor
- `custom_counterparty_category` field bor
- `custom_supplier_contract` field bor
- `custom_installment_application` field bor

#### Supplier DocType:
- Ba'zi fieldlar hidden:
  - `is_transporter`
  - `default_bank_account`
  - `naming_series`
  - `image`
  - `tax_id`

#### Customer DocType:
- Custom fieldlar qo'shilgan
- Ba'zi fieldlar hidden

### 4. Test Site O'chirish

Agar test muvaffaqiyatli bo'lsa:

```bash
bench drop-site test.localhost
```

## Natija

Agar barcha customizationlar to'g'ri import bo'lsa, sheriklar ham clone qilganda aynan shu natijani olishadi! ✅

---

## Troubleshooting

### Custom Fieldlar Import Bo'lmasa

```bash
# Fixtures ni manual import
bench --site test.localhost migrate --skip-failing

# Yoki bench console dan
bench --site test.localhost console

# Console da:
from frappe.core.doctype.doctype.test_doctype import clear_custom_fields
clear_custom_fields("Item")

# Qayta migrate
bench --site test.localhost migrate
```

### Property Setter Import Bo'lmasa

```bash
# Property Setter ni to'liq reload
bench --site test.localhost console

# Console da:
frappe.db.sql("DELETE FROM `tabProperty Setter` WHERE module IS NULL")
frappe.db.commit()
exit()

bench --site test.localhost migrate
```
