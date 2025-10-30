# 🧪 Installment Application Amend & Clone - Test Guide

## ✅ **Qo'shilgan Funksiyalar:**

### 1️⃣ **Sales Order Cancel → Payment Entry Cancel/Delete**
- SO cancel bo'lganda, unga bog'langan:
  - ✅ Submitted PE'lar **CANCEL** qilinadi
  - ✅ Draft PE'lar **DELETE** qilinadi
  - ✅ User'ga xabar beriladi

### 2️⃣ **Installment Application Amend → Payment Entry Clone**
- InstApp amend qilinganda:
  - ✅ Eski cancelled PE'lar topiladi
  - ✅ O'zgarishlar tahlil qilinadi (financial fields)
  - ✅ Clone strategiyasi aniqlanadi
  - ✅ PE'lar clone yoki draft yaratiladi

### 3️⃣ **Supplier Debt Reverse**
- InstApp cancel bo'lganda:
  - ✅ Supplier qarzdorlik **kamaytriladi**
  - ✅ Status yangilanadi (To'landi/Qisman/Qarzda)

---

## 🧪 **Test Scenario'lar:**

### **Test 1: IMEI O'zgarishi (Financial bir xil)**
```
1. InstApp yarating:
   - Customer: Test Customer
   - Item: ITEM-001, IMEI: 123456, Price: $1000
   - Downpayment: $100
   - Monthly: $50 × 12 oy

2. Submit qiling → SO-001 yaratiladi

3. PE-001 (draft, $100) yaratiladi → Submit qiling ✅

4. PE-002 (draft, $50) 1-oy uchun yarating → Submit qiling ✅

5. Admin: "IMEI xato! 654321 bo'lishi kerak"

6. InstApp ni CANCEL qiling ❌
   → Natija:
   ✅ SO-001 cancelled
   ✅ PE-001, PE-002 cancelled
   ✅ Supplier debt kamaytrildi

7. InstApp ni AMEND qiling → InstApp-1 yaratiladi

8. IMEI'ni 654321 ga o'zgartiring (boshqa hech narsa o'zgartirmang!)

9. SUBMIT qiling ✅
   → Kutilayotgan natija:
   ✅ SO-002 yaratiladi
   ✅ PE-003 (submitted, $100) clone qilinadi
   ✅ PE-004 (submitted, $50) clone qilinadi
   ✅ Message: "Moliyaviy ma'lumotlar o'zgarmadi. Barcha to'lovlar qayta tiklanadi."
```

---

### **Test 2: Boshlang'ich To'lov O'zgarishi**
```
1. InstApp yarating:
   - Downpayment: $100
   - Monthly: $50 × 12 oy

2. Submit → SO-001

3. PE-001 (draft, $100) → Submit ✅

4. Admin: "Boshlang'ich $200 bo'lishi kerak!"

5. CANCEL InstApp ❌
   → PE-001 cancelled

6. AMEND → InstApp-1

7. Downpayment'ni $200 ga o'zgartiring

8. SUBMIT ✅
   → Kutilayotgan natija:
   ✅ SO-002 yaratiladi
   ✅ PE-002 (DRAFT, $200) yaratiladi
   ⚠️ Message: "Boshlang'ich to'lov o'zgardi. Yangi summa bilan DRAFT yaratildi. Tekshiring va submit qiling!"
```

---

### **Test 3: Oylik To'lov O'zgarishi**
```
1. InstApp yarating:
   - Downpayment: $100
   - Monthly: $50 × 12 oy

2. Submit → SO-001

3. PE-001 (downpayment, $100) → Submit ✅

4. PE-002 (1-oy, $50) → Submit ✅

5. PE-003 (2-oy, $50) → Submit ✅

6. Admin: "Oylik $60 bo'lishi kerak!"

7. CANCEL InstApp ❌

8. AMEND → InstApp-1

9. Monthly payment'ni $60 ga o'zgartiring

10. SUBMIT ✅
    → Kutilayotgan natija:
    ✅ PE-004 (downpayment, $100) clone
    ✅ PE-005 (1-oy, $50) clone (eski summa)
    ✅ PE-006 (2-oy, $50) clone (eski summa)
    ⚠️ Message: "Oylik to'lov o'zgardi. Eski to'lovlar clone qilinadi, yangi summa keyingi oylar uchun."
```

---

### **Test 4: Supplier O'zgarishi**
```
1. InstApp yarating:
   - Item: MacBook, Supplier: MacBookMarket, Price: $1000
   - Downpayment: $100

2. Submit → SO-001
   → Supplier MacBookMarket: +$1000 debt

3. CANCEL InstApp ❌
   → Kutilayotgan natija:
   ✅ Supplier MacBookMarket: -$1000 debt (reversed)
   ✅ Message: "Qarz kamaytrildi"

4. AMEND → InstApp-1

5. Supplier'ni AppleStore ga o'zgartiring

6. SUBMIT ✅
   → Kutilayotgan natija:
   ✅ Supplier AppleStore: +$1000 debt (yangi)
```

---

### **Test 5: Multiple PE'lar (Draft + Submitted)**
```
1. InstApp yarating, submit qiling

2. PE-001 (downpayment) → Submit ✅

3. PE-002 (1-oy) → Submit ✅

4. PE-003 (2-oy) → DRAFT qoldiring 📝

5. CANCEL InstApp ❌
   → Kutilayotgan natija:
   ✅ PE-001, PE-002 cancelled
   ✅ PE-003 deleted (draft bo'lgani uchun)

6. AMEND → InstApp-1

7. SUBMIT ✅
   → Kutilayotgan natija:
   ✅ PE-001, PE-002 clone (faqat submitted'lar)
   ❌ PE-003 clone QILINMAYDI (draft edi)
```

---

## 🔍 **Tekshirish Buyruqlari:**

### 1. Payment Entry'larni ko'rish:
```sql
SELECT name, paid_amount, custom_contract_reference, docstatus, posting_date 
FROM `tabPayment Entry` 
WHERE custom_contract_reference IN ('CON-2025-XXXXX', 'CON-2025-YYYYY')
ORDER BY posting_date;
```

### 2. Supplier qarzdorlik ko'rish:
```sql
SELECT name, custom_total_debt, custom_paid_amount, custom_remaining_debt, custom_payment_status 
FROM `tabSupplier` 
WHERE name = 'MacBookMarket';
```

### 3. Sales Order status:
```sql
SELECT name, docstatus, grand_total, advance_paid 
FROM `tabSales Order` 
WHERE name IN ('CON-2025-XXXXX', 'CON-2025-YYYYY');
```

### 4. Log'larni ko'rish:
```bash
cd /home/asadbek/frappe-bench
bench logs
```

---

## ⚠️ **Ma'lum Limitlar:**

1. **Muddat o'zgarishi:** Agar allaqachon PE'lar submit qilingan bo'lsa, muddat (installment_months) o'zgartirilmaydi (real hayotda bunday holat bo'lmaydi deb faraz qilindi).

2. **Item price o'zgarishi:** Agar item price o'zgarsa va boshlang'ich to'lov o'zgartirilmasa, eski summa saqlanadi.

3. **Draft PE clone:** Faqat **submitted** PE'lar clone qilinadi. Draft'lar delete qilinadi va yangi yaratilmaydi (agar downpayment draft kerak bo'lsa, avtomatik yaratiladi).

---

## 🐛 **Agar Xatolik Bo'lsa:**

1. **Check Logs:**
   ```bash
   tail -f logs/frappe.log.1
   ```

2. **Check Error Log:**
   Frappe UI'da: `Error Log` doctype'ni oching

3. **Restart Bench:**
   ```bash
   bench restart
   ```

4. **Clear Cache:**
   ```bash
   bench clear-cache
   bench restart
   ```

---

## 📊 **Expected Flow:**

```
InstApp (original)
    ↓ submit
SO-001 (submitted)
    ↓ create
PE-001 (draft) → Submit ✅
PE-002 (draft) → Submit ✅
    ↓
Admin: "Xato bor!"
    ↓ cancel
InstApp (cancelled) ❌
SO-001 (cancelled) ❌
PE-001 (cancelled) ❌
PE-002 (cancelled) ❌
    ↓ amend
InstApp-1 (new)
    ↓ fix & submit
SO-002 (submitted) ✅
    ↓ clone
PE-003 (submitted) ✅ [clone of PE-001]
PE-004 (submitted) ✅ [clone of PE-002]
```

---

**Test qilishni boshlang va natijalarni menga xabar bering!** 🚀
