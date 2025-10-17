# 🎯 UI TEST GUIDE - Cash Flow App

**Status:** Phase 5 tugallandi, endi UI test qilish vaqti!

---

## ✅ TAYYOR KOMPONENTLAR

### 📊 Reports (4 ta)
- ✅ Daily Cash Flow Report
- ✅ Outstanding Installments Report
- ✅ Monthly Payment Schedule
- ✅ Category-wise Summary

### 🖨️ Print Formats (2 ta)
- ✅ Shartnoma (Sales Order print)
- ✅ Kassa Kvitansiya (Payment Entry print)

### ⚠️ Validations (3 ta)
- ✅ Negative balance prevention
- ✅ Payment schedule validation
- ✅ Overdue payment warnings

---

## 📝 TEST QILISH TARTIBI

### **1. Counterparty Category yaratish**

#### Yo'l:
```
Accounting → Setup → Counterparty Category → New
```

#### Yaratish kerak bo'lgan kategoriyalar:

**KIRIM (Income):**
- Klient - Mijozlardan tushgan to'lovlar
- Boshqa to'lov - Boshqa manbalardан kirgan pul
- Uslugadan foyda - Xizmat ko'rsatishdan olingan foyda
- Boshqa foyda - Qo'shimcha daromadlar
- Investor - Investor qo'ygan mablag'

**CHIQIM (Expense):**
- Hodim - Xodimlarga to'lovlar (maosh)
- Postavshik - Yetkazib beruvchilarga to'lovlar
- Xarajat - Umumiy xarajatlar
- Investor chiqimi - Investorga qaytarish
- Komunal - Kommunal to'lovlar
- Bank - Bank xizmatlari

---

### **2. Test Customer yaratish**

#### Yo'l:
```
Selling → Customer → New
```

#### Test mijoz:
- **Customer Name:** Ahmadov Aziz
- **Customer Group:** Individual
- **Territory:** All Territories
- **Mobile No:** +998901234567

---

### **3. Test Item yaratish**

#### Yo'l:
```
Stock → Item → New
```

#### Test mahsulot:
- **Item Code:** PHONE-IP14
- **Item Name:** iPhone 14 Pro 256GB
- **Item Group:** Products
- **Standard Rate:** 1200.00
- ✅ **Is Stock Item** - belgilang

---

### **4. 🔥 TEST 1: PAYMENT ENTRY (Kassa Kirim)**

#### Yo'l:
```
Accounts → Payment Entry → New
```

#### Sozlamalar:
- **Payment Type:** Receive
- **Party Type:** Customer
- **Party:** Ahmadov Aziz
- **Paid From:** Debtors (Receivable account)
- **Paid To:** Cash (Cash account)
- **Paid Amount:** 500.00
- **Mode of Payment:** Naqd
- **Custom Counterparty Category:** Klient
- **Remarks:** Test kirim to'lovi

#### ✅ TEST:
1. **Save** tugmasini bosing
2. **Submit** tugmasini bosing
3. **Print** → **Kassa Kvitansiya** tanlang
4. **PDF** tugmasi ishlashi kerak
5. PDF ochilishi kerak
6. **Rang: GREEN** (yashil) bo'lishi kerak
7. **Summa: 500.00** katta harflar bilan ko'rinishi kerak

#### 📸 Tekshirish:
- ✅ Kvitansiya yashil rangda
- ✅ "KASSA KIRIM" yozuvi
- ✅ Summa katta (48px)
- ✅ Sana va vaqt ko'rsatilgan
- ✅ Customer nomi ko'rsatilgan
- ✅ Qabul qildi/Topshirdi imzo joylari

---

### **5. 🔥 TEST 2: PAYMENT ENTRY (Kassa Chiqim)**

#### Yo'l:
```
Accounts → Payment Entry → New
```

#### ⚠️ **QADAMMA-QADAM (MUHIM!):**

**QADAM 1:** Yuqorida to'ldiring
- **Series:** ACC-PAY-.YYYY.-
- **Payment Type:** Pay
- **Posting Date:** bugun
- **Mode of Payment:** Naqd
- **Counterparty Category:** Xarajat - Umumiy xarajatlar
- **Additional Notes:** Test ofis xarajatlari

**QADAM 2:** "Payment From / To" bo'limiga o'ting
- **Party Type:** (bo'sh qoldiring)

**QADAM 3:** "Accounts" bo'limini oching (agar yopiq bo'lsa ▶ bosing)
- **Account Paid From:** Cash - A

**QADAM 4:** 📜 **SCROLL DOWN QILING!** (Pastga suring!)
- **Account Currency (From):** USD (avtomatik)
- **Account Balance (From):** $500.00 (ko'rinadi)

**QADAM 5:** Yana pastga scroll qiling - **bu yerda asosiy maydonlar:**
- **Paid Amount (USD):** **150.00** ← **MAJBURIY!**
- **Source Exchange Rate:** 1.00 (avtomatik)

**QADAM 6:** Yana pastroq - "Paid To" section:
- **Account Paid To:** **Biror Expense account tanlang**
  - Masalan: "Expenses - A" yoki "Office Expenses - A"
- **Account Currency (To):** USD (avtomatik)
- **Received Amount (USD):** 150.00 (avtomatik to'ladi)

**QADAM 7:** Oxirida:
- **Target Exchange Rate:** 1.00 (avtomatik)

**💡 MASLAHAT:** 
- ❌ **XATO:** "Account Paid To" ni to'ldirmay Save bosish
- ✅ **TO'G'RI:** Avval **barcha 3 ta maydonni** to'ldiring:
  1. Account Paid From
  2. Paid Amount
  3. Account Paid To

#### ✅ TEST:
1. **Save** tugmasini bosing
2. **Submit** tugmasini bosing
3. **Print** → **Kassa Kvitansiya** tanlang
4. **PDF** tugmasi ishlashi kerak
5. PDF ochilishi kerak
6. **Rang: RED** (qizil) bo'lishi kerak
7. **Summa: 150.00** katta harflar bilan ko'rinishi kerak

#### 📸 Tekshirish:
- ✅ Kvitansiya qizil rangda
- ✅ "KASSA CHIQIM" yozuvi
- ✅ Summa katta (48px)
- ✅ Sana va vaqt ko'rsatilgan
- ✅ Remarks ko'rsatilgan

---

### **6. 🔥 TEST 3: SALES ORDER (Shartnoma)**

#### Yo'l:
```
Selling → Sales Order → New
```

#### Sozlamalar:
- **Naming Series:** CON-.YYYY.-.#####
- **Customer:** Ahmadov Aziz
- **Transaction Date:** bugun
- **Delivery Date:** 30 kun keyingi sana

#### Items jadvali:
- **Item Code:** PHONE-IP14
- **Qty:** 1
- **Rate:** 1200.00

#### Payment Schedule (qo'lda qo'shish):

**💡 DIQQAT:** Sales Order'da Payment Schedule **avtomatik yaratilmaydi**!

**Variant 1: INSTALLMENT APPLICATION ishlatiniz** (Oson!)
```
Keyingi testda (TEST 4) Installment Application'ni sinab ko'ring.
U Payment Schedule'ni AVTOMATIK yaratadi!
```

**Variant 2: Qo'lda qo'shish** (Qiyin - faqat test uchun)

Items jadvali ostida **Payment Schedule** jadvalini toping va qo'lda to'ldiring:

1. **Add Row** bosing - 1-qator (Downpayment):
   - **Due Date:** bugun
   - **Payment Amount:** 360.00
   - **Paid Amount:** 360.00 ✅

2. **Add Row** bosing - 2-qator:
   - **Due Date:** 1 oy keyin
   - **Payment Amount:** 70.00
   - **Paid Amount:** 0.00

3. **Add Row** bosing - 3-qator:
   - **Due Date:** 2 oy keyin
   - **Payment Amount:** 70.00
   - **Paid Amount:** 0.00

...va hokazo 12 oyga

**⚠️ MUHIM:** Bu juda uzoq! Shuning uchun **Installment Application** yozilgan! 😊

#### ✅ TEST:
1. **Save** tugmasini bosing
2. **Submit** tugmasini bosing
3. **Print** → **Shartnoma** tanlang
4. **PDF** tugmasi ishlashi kerak
5. PDF ochilishi kerak

#### 📸 Tekshirish:
- ✅ Header: "SHARTNOMA" va raqam
- ✅ Customer ma'lumotlari
- ✅ Items jadvali (IMEI ustuni bilan)
- ✅ To'lov jadvali (12 oylik)
- ✅ Foiz hisoblari (% ko'rsatilgan)
- ✅ Imzo bloklari (Sotuvchi/Xaridor)
- ✅ Shartlar va qoidalar bo'limi

---

### **7. 🔥 TEST 4: INSTALLMENT APPLICATION**

#### Yo'l:
```
Cash Flow Management → Installment Application → New
```

#### Sozlamalar:
- **Customer:** Ahmadov Aziz
- **Delivery Date:** 30 kun keyingi sana

#### Items jadvali:
- **Item:** PHONE-IP14
- **Qty:** 1
- **Rate:** 1200.00

#### To'lov shartlari (avtomatik hisoblash):
- **Downpayment %:** 30.000
- **Installment Months:** 6 (yoki 12)
- **Yillik Foiz (%):** 15.000
- **Boshlang'ich Sana:** bugun

**📊 AVTOMATIK HISOBLANADI:**
- **Downpayment Amount:** (avtomatik)
- **Finance Amount:** (avtomatik)
- **Jami Foiz (USD):** (avtomatik)
- **Foiz bilan Jami (USD):** (avtomatik)
- **Monthly Payment:** (avtomatik)

#### ✅ TEST:
1. **Calculate Payment Schedule** tugmasini bosing
   - **Yashil xabar:** "Payment schedule calculated!"
   - **Barcha summalar** avtomatik to'ladi
2. **Save** tugmasini bosing
3. **Submit** tugmasini bosing
   - **Sales Order avtomatik yaratilishi kerak**
4. Yaratilgan Sales Order'ga o'ting
5. **Print** → **Shartnoma** tanlang
6. PDF ko'ring

#### 📸 Tekshirish:
- ✅ Payment schedule to'g'ri hisoblandi
- ✅ Sales Order yaratildi
- ✅ Shartnoma PDF to'g'ri ko'rinadi

---

### **8. 🔥 TEST 5: VALIDATIONS**

#### Test 5.1: Negative Balance
1. Payment Entry (Pay) yarating
2. **Paid Amount:** 999999.00 (juda katta summa)
3. **Save** bosing
4. **❌ Xato chiqishi kerak:** "Kassada yetarli mablag' yo'q!"

#### Test 5.2: Payment Schedule Validation
1. Sales Order ochig
2. Payment Schedule'da **Paid Amount > Payment Amount** qiling
3. **Save** bosing
4. **❌ Xato chiqishi kerak:** "To'langan summa umumiy summadan oshib ketgan"

#### Test 5.3: Overdue Warning
1. Sales Order yarating (eski sana bilan)
2. Payment Schedule'da **Due Date** ni o'tmishga qo'ying
3. **Save** bosing
4. **⚠️ Ogohlantirish chiqishi kerak:** Overdue payments jadvali

---

### **9. 🔥 TEST 6: REPORTS**

#### Test 6.1: Daily Cash Flow
```
Reports → Cash Flow Management → Daily Cash Flow
```
- Date Range tanlang
- **Run** bosing
- **Chart** ko'rinishi kerak
- **Summary** ko'rinishi kerak
- Running balance hisoblandi
- Export Excel/PDF ishlaydi

#### Test 6.2: Outstanding Installments
```
Reports → Cash Flow Management → Outstanding Installments
```
- Date Range tanlang
- **Run** bosing
- To'lanmagan to'lovlar ko'rinadi
- Overdue kun hisobi to'g'ri
- Next payment date ko'rsatiladi

#### Test 6.3: Monthly Payment Schedule
```
Reports → Cash Flow Management → Monthly Payment Schedule
```
- Month tanlang
- **Run** bosing
- Oylik to'lov kalendari
- Status (Paid/Unpaid/Partial) ko'rinadi

#### Test 6.4: Category-wise Summary
```
Reports → Cash Flow Management → Category-wise Summary
```
- Date Range tanlang
- **Run** bosing
- Income/Expense breakdown
- Percentage calculations
- Total summary

---

## 🐛 MUAMMOLAR VA YECHIMLAR

### ❌ Muammo 1: "Invalid wkhtmltopdf version"
**Yechim:** ✅ HAL QILINDI - wkhtmltopdf 0.12.6.1 o'rnatildi

### ❌ Muammo 2: "str object has no attribute strftime" (Print Error line 27)
**Yechim:** ✅ HAL QILINDI - `frappe.utils.formatdate()` ishlatildi

### ❌ Muammo 3: Payment Entry Pay - Paid Amount/Paid To ko'rinmaydi
**Yechim:** 
1. **Accounts** section'ni expand qiling (▶ belgisini bosing)
2. **Account Paid From** ni avval tanlang (Cash - A)
3. Keyin **Paid Amount** maydoni ochiladi
4. **Account Paid To** ni tanlang (Expense account)

**Boshqa variant:** Browser'ni refresh qiling (F5) va qaytadan urinib ko'ring

### ❌ Muammo 4: "Counterparty Category not found"
**Yechim:** Avval Counterparty Category yarating (Qadam 1)

### ❌ Muammo 5: "Custom field not found"
**Yechim:** Phase 6'da custom fields yaratamiz (keyingi qadam)

### ❌ Muammo 6: Print formatda ma'lumotlar ko'rinmaydi
**Yechim:** 
- Letter Head yarating (Settings → Letter Head)
- Custom fields yaratilganligini tekshiring

---

## 📊 TEST NATIJALAR JADVALI

| Test | Holat | Izoh |
|------|-------|------|
| Counterparty Category | ✅ | Yaratildi |
| Test Customer | ✅ | Yaratildi |
| Test Item | ✅ | Yaratildi |
| Payment Entry Kirim (GREEN) | ✅ | Ishladi! PDF yashil |
| Payment Entry Chiqim (RED) | ⏳ | Test qilish kerak |
| Sales Order - Shartnoma Print | ⏳ | Test qiling |
| Installment Application | ⏳ | Test qiling |
| Negative Balance Validation | ⏳ | Test qiling |
| Payment Schedule Validation | ⏳ | Test qiling |
| Overdue Warning | ⏳ | Test qiling |
| Daily Cash Flow Report | ⏳ | Test qiling |
| Outstanding Installments | ⏳ | Test qiling |
| Monthly Payment Schedule | ⏳ | Test qiling |
| Category-wise Summary | ⏳ | Test qiling |

**Legend:**
- ⏳ = Test qilish kerak
- ✅ = Muvaffaqiyatli
- ❌ = Xato topildi
- 🔧 = Tuzatish kerak

---

## 🎥 SCREENSHOT OLING

Screenshot olishda quyidagilarni ko'rsating:

1. **Payment Entry Kirim:**
   - Form to'ldirilgan
   - Kassa Kvitansiya PDF (yashil)

2. **Payment Entry Chiqim:**
   - Form to'ldirilgan
   - Kassa Kvitansiya PDF (qizil)

3. **Sales Order:**
   - Form + Payment Schedule
   - Shartnoma PDF

4. **Installment Application:**
   - Form to'ldirilgan
   - Yaratilgan Sales Order

5. **Validations:**
   - Xato xabarlari (negative balance)
   - Ogohlantirish xabarlari (overdue)

6. **Reports:**
   - Har bir report'ning natijasi
   - Chart va Summary

---

## ⏭️ KEYINGI QADAM: PHASE 6

Test qilishdan keyin Phase 6'ga o'tamiz:
- ✅ Custom Fields yaratish
- ✅ Permissions sozlash
- ✅ Final testing
- ✅ Production'ga deploy

---

**TEST QILING VA NATIJALARNI YUBORING! 🚀**
