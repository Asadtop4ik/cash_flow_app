# Sheriklar Uchun - Tezkor Boshlash

## Minimal Qadamlar

Agar siz Frappe/ERPNext bilan ishlagan bo'lsangiz va faqat bu appni o'rnatmoqchi bo'lsangiz:

```bash
# 1. App ni clone qilish
cd /path/to/your/frappe-bench
bench get-app https://github.com/Asadtop4ik/cash_flow_app.git --branch main

# 2. Site ga o'rnatish
bench --site YOUR_SITE install-app cash_flow_app

# 3. Migrate qilish (JUDA MUHIM!)
bench --site YOUR_SITE migrate

# 4. Ishga tushirish
bench start
```

## ⚠️ Muhim!

`bench migrate` buyrug'i **albatta** bajarilishi kerak! Aks holda:
- ❌ Custom fieldlar ko'rinmaydi
- ❌ ERPNext doctiplari standart holatda qoladi
- ❌ Hidden fieldlar ko'rinadi
- ❌ Counterparty Categories bo'lmaydi

## Nima Import Bo'ladi?

✅ **Custom Fields** - 11 ta doctype uchun (Item, Customer, Supplier, Payment Entry, etc.)  
✅ **Property Setters** - 30+ doctype da hidden va customization  
✅ **Counterparty Categories** - Kontragent kategoriyalari  
✅ **Mode of Payment** - To'lov usullari (Naqd, Terminal/Click)

## Tekshirish

Login qiling va tekshiring:

1. **Item** - yangi fieldlar bor (item_type_custom, item_category)
2. **Payment Entry** - custom_izoh, custom_counterparty_category
3. **Supplier** - ba'zi fieldlar hidden

Agar barchasi ko'rinsa - ✅ Hammasi tayyor!

## Muammo Bo'lsa?

To'liq ko'rsatma: [INSTALL_GUIDE_UZ.md](./INSTALL_GUIDE_UZ.md)

---

**Support:** asadbek.backend@gmail.com
