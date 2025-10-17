# 📘 SALES ORDER vs INSTALLMENT APPLICATION - Farqi

**Savolingizga javob: Har ikkisi ham shartnoma edi, nima farqi bor?**

---

## 1️⃣ **SALES ORDER** (Standart ERPNext)

### Qachon ishlatiladi:
- ✅ **Oddiy buyurtmalar** (bir martalik to'lov)
- ✅ **Manual** to'lov jadvali kerak bo'lganda
- ✅ **Foizsiz** shartnomalar
- ✅ Standart savdo jarayoni

### Xususiyatlari:
- ✅ ERPNext'ning **native** (o'rnatilgan) DocType'i
- ❌ Foiz hisoblash **YO'Q**
- ❌ Payment Schedule **qo'lda** yozish kerak
- ❌ Avtomatik hisob-kitob **YO'Q**

### Ishlatish:
```
Selling → Sales Order → New
→ Customer tanlang
→ Items qo'shing
→ Payment Schedule qo'lda yozing:
  - Due Date
  - Payment Amount
  - Paid Amount (to'langanda)
→ Save → Submit → Print (Shartnoma)
```

### Misol:
```
Item: iPhone 14 Pro
Price: $1,200
Downpayment: $360 (30%)
Balance: $840

Payment Schedule (QO'LDA YOZASIZ):
Row 1: Bugun       - $360 (Boshlang'ich)
Row 2: 1-noyabr    - $70
Row 3: 1-dekabr    - $70
...
Row 13: 1-oktyabr  - $70
```

---

## 2️⃣ **INSTALLMENT APPLICATION** (Custom - Bizniki!)

### Qachon ishlatiladi:
- ✅ **Bo'lib to'lash** (nasiya, kredit)
- ✅ **Foizli** shartnomalar (15%, 20%, va h.k.)
- ✅ **Avtomatik** to'lov jadvali kerak
- ✅ Tez va xatosiz hisob-kitob

### Xususiyatlari:
- ✅ **Custom** DocType (biz yozdik!)
- ✅ Foiz hisoblash **BOR** (interest rate)
- ✅ Payment Schedule **avtomatik** yaratadi
- ✅ "Calculate Schedule" tugmasi bor
- ✅ Submit qilganda **Sales Order avtomatik yaratadi**

### Ishlatish:
```
Cash Flow Management → Installment Application → New
→ Customer tanlang
→ Items qo'shing
→ To'lov shartlarini kiriting:
  - Downpayment %: 30
  - Installment Months: 12
  - Interest Rate %: 15
  - Start Date: bugun
→ "Calculate Schedule" tugmasini bosing ✨
→ Save → Submit
→ Sales Order avtomatik yaratiladi!
```

### Misol (avtomatik):
```
Item: iPhone 14 Pro
Price: $1,200
Downpayment: 30% = $360
Finance Amount: $840

Interest Calculation:
- Monthly Rate: 15% ÷ 12 = 1.25%
- Total Interest: $840 × 1.25% × 12 = $126
- Grand Total: $840 + $126 = $966
- Monthly Payment: $966 ÷ 12 = $80.50

Payment Schedule (AVTOMATIK YARATILADI):
Row 1: Bugun       - $360.00 (Downpayment)
Row 2: 1-noyabr    - $80.50
Row 3: 1-dekabr    - $80.50
...
Row 13: 1-oktyabr  - $80.50
```

---

## 3️⃣ **FARQI - Qisqacha Jadval**

| Xususiyat | Sales Order | Installment Application |
|-----------|-------------|------------------------|
| **DocType** | Native ERPNext | Custom (bizniki) |
| **Foiz hisoblash** | ❌ YO'Q | ✅ BOR (%) |
| **Payment Schedule** | 🖊️ Qo'lda | 🤖 Avtomatik |
| **Xato xavfi** | 🟡 Bor (manual) | 🟢 Yo'q (auto) |
| **Tezlik** | 🐢 Sekin | 🚀 Tez |
| **Interest Rate** | ❌ YO'Q | ✅ BOR |
| **Calculate tugmasi** | ❌ YO'Q | ✅ BOR |
| **Ishlatish** | Oddiy savdo | Bo'lib to'lash |

---

## 4️⃣ **OQIM (Workflow)**

### Sales Order (Manual):
```
1. Sales Order yaratish
2. Items qo'shish
3. Payment Schedule qo'lda yozish (har qator)
   - Due Date kiritish
   - Payment Amount hisoblab yozish
4. Save → Submit
5. Print (Shartnoma)
```

### Installment Application (Auto):
```
1. Installment Application yaratish
2. Items qo'shish
3. Faqat 4 ta narsa kiritish:
   - Downpayment %
   - Months
   - Interest Rate %
   - Start Date
4. "Calculate Schedule" bosish ✨
5. Save → Submit
   → Sales Order AVTOMATIK yaratiladi!
   → Payment Schedule AVTOMATIK to'ldiriladi!
6. Yaratilgan Sales Order'ga o'tish
7. Print (Shartnoma)
```

---

## 5️⃣ **SALES INVOICE bilan qilsa bo'ladimi?**

**Ha, bo'ladi!** Lekin:

### Sales Order (Buyurtma):
- ✅ **Oldindan** - Mijoz buyurtma beradi
- ✅ To'lov jadvali **boshidan** ma'lum
- ✅ Mahsulot tayyor bo'lmasa ham shartnoma tuzish mumkin

### Sales Invoice (Hisob-faktura):
- ✅ **Keyinroq** - Mahsulot topshirilgandan keyin
- ✅ To'lov jadvali ham qo'shish mumkin
- ❌ Lekin mahsulot tayyor bo'lishi kerak

### Tavsiya:
```
1. INSTALLMENT APPLICATION → 
2. SALES ORDER (shartnoma) →
3. Downpayment PAYMENT ENTRY →
4. Mahsulot tayyor →
5. DELIVERY NOTE →
6. SALES INVOICE →
7. Oylik PAYMENT ENTRY'lar
```

---

## 6️⃣ **QAYSI BIRINI ISHLATASIZ?**

### INSTALLMENT APPLICATION ishlatiniz agar:
- ✅ **Foizli** shartnoma
- ✅ **Bo'lib to'lash** (12 oy, 24 oy)
- ✅ Tez hisob-kitob kerak
- ✅ Xato qilishni istamasangiz

### SALES ORDER ishlatiniz agar:
- ✅ **Foizsiz** shartnoma
- ✅ **Oddiy** buyurtma
- ✅ Bir martalik to'lov
- ✅ O'zingiz schedule yozmoqchisiz

---

## 7️⃣ **REAL MISOL**

### Mijoz: Ahmadov Aziz
### Mahsulot: iPhone 14 Pro - $1,200
### Shart: 30% oldindan, 12 oyga, 15% foiz

### ❌ NOTO'G'RI (Sales Order - Manual):
```
1. Sales Order ochish
2. Item qo'shish
3. Excel'da hisoblab:
   - Downpayment: 1200 × 30% = 360
   - Finance: 1200 - 360 = 840
   - Interest: 840 × 15% = 126
   - Total: 840 + 126 = 966
   - Monthly: 966 ÷ 12 = 80.50
4. Payment Schedule'ga qo'lda 13 ta qator yozish
   - 1: Bugun - 360
   - 2: 1-noyabr - 80.50
   - 3: 1-dekabr - 80.50
   - ...
5. Save → Submit
```
**⏱️ Vaqt: 10-15 daqiqa**
**❌ Xato xavfi: YUQORI**

### ✅ TO'G'RI (Installment Application - Auto):
```
1. Installment Application ochish
2. Item qo'shish
3. Shartlarni kiritish:
   - Downpayment %: 30
   - Months: 12
   - Interest Rate: 15
   - Start Date: bugun
4. "Calculate Schedule" bosish
5. Save → Submit
```
**⏱️ Vaqt: 2-3 daqiqa**
**✅ Xato xavfi: YO'Q**

---

## 8️⃣ **XULOSA**

### Sizning holatda:
1. ✅ **Installment Application ishlatiniz** - chunki:
   - Foizli shartnomalar
   - Bo'lib to'lash
   - Avtomatik hisob-kitob
   - Tez va xatosiz

2. ✅ **Sales Order'ga ehtiyoj YO'Q** - chunki:
   - Installment Application avtomatik yaratadi
   - Payment Schedule avtomatik to'ladi

3. ✅ **Sales Invoice keyinroq** - mahsulot topshirilgandan keyin

---

**ESLATMA:** Sales Order'ni test qilish faqat print formatni ko'rish uchun. Real ishda **Installment Application** ishlatiladi! 🚀
