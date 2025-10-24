# O'rnatish Bo'yicha Ko'rsatma (O'zbekcha)

## Sheriklar Uchun - Git Clone va O'rnatish

Agar siz jamoada ishlayotgan bo'lsangiz va bu appni clone qilayotgan bo'lsangiz, quyidagi qadamlarni bajaring:

### 1. Frappe Bench O'rnatish

Agar Frappe Bench o'rnatilmagan bo'lsa:

```bash
# Python va pip o'rnatilganligini tekshiring
python3 --version

# Frappe Bench o'rnatish
pip3 install frappe-bench

# Bench yaratish
bench init frappe-bench --frappe-branch version-15
cd frappe-bench
```

### 2. ERPNext O'rnatish

```bash
# ERPNext appni olish
bench get-app erpnext --branch version-15

# Site yaratish
bench new-site YOUR_SITE_NAME

# ERPNext ni site ga o'rnatish
bench --site YOUR_SITE_NAME install-app erpnext
```

### 3. Cash Flow App O'rnatish

```bash
# Cash Flow App ni GitHub dan clone qilish
bench get-app https://github.com/Asadtop4ik/cash_flow_app.git --branch main

# App ni site ga o'rnatish
bench --site YOUR_SITE_NAME install-app cash_flow_app

# Migrate qilish (JUDA MUHIM!)
bench --site YOUR_SITE_NAME migrate
```

### 4. Natija

`migrate` buyrug'i bajarilgandan so'ng, quyidagilar avtomatik qo'llanadi:

✅ **Custom Fields** - ERPNext doctipalariga qo'shilgan barcha custom fieldlar:
   - Item, Customer, Supplier
   - Payment Entry, Sales Order
   - Installment Application va boshqalar

✅ **Property Setters** - Yashirilgan va o'zgartirilgan fieldlar:
   - 30+ ta doctype da customizationlar
   - Hidden fieldlar, required fieldlar va boshqalar

✅ **Counterparty Categories** - Kontragent kategoriyalari

✅ **Mode of Payment** - To'lov usullari (Naqd, Terminal/Click)

### 5. Tekshirish

Hammasi to'g'ri o'rnatilganligini tekshirish uchun:

```bash
# Bench ishga tushirish
bench start

# Browserda ochish
# http://YOUR_SITE_NAME:8000
```

ERPNext ga kirib, quyidagi doctiplarni ochib ko'ring:
- **Item** - custom fieldlar (item_type_custom, item_category va boshqalar) ko'rinishi kerak
- **Payment Entry** - custom fieldlar (custom_izoh, custom_counterparty_category va boshqalar)
- **Customer**, **Supplier** - ba'zi fieldlar hidden bo'lishi kerak

### Muammolar

#### Agar custom fieldlar ko'rinmasa:

```bash
# Fixtures ni qayta import qilish
bench --site YOUR_SITE_NAME migrate --skip-failing

# Yoki to'liq reload
bench --site YOUR_SITE_NAME reinstall
```

#### Agar "Module not found" xatosi chiqsa:

```bash
# App o'rnatilganligini tekshiring
bench --site YOUR_SITE_NAME list-apps

# Agar yo'q bo'lsa, qayta o'rnating
bench --site YOUR_SITE_NAME install-app cash_flow_app
```

### Developer uchun qo'shimcha

Agar siz ERPNext doctipalarida o'zgarishlar qilsangiz:

```bash
# Fixtures ni export qilish
bench --site YOUR_SITE_NAME export-fixtures

# Git ga commit va push
cd apps/cash_flow_app
git add .
git commit -m "Updated fixtures"
git push origin main
```

## Savollar

Agar muammo bo'lsa, quyidagilarni tekshiring:

1. `bench --site YOUR_SITE_NAME migrate` bajarilganmi?
2. `bench --site YOUR_SITE_NAME list-apps` da `cash_flow_app` bormi?
3. Browser cache ni tozalang (Ctrl+Shift+R)
4. Frappe va ERPNext versiyalari to'g'rimi? (version-15 bo'lishi kerak)

---

**Eslatma:** Bu app faqat **ERPNext version 15** bilan ishlaydi. Boshqa versiyalar uchun muammolar bo'lishi mumkin.
