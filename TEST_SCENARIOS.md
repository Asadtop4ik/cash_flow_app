# 🧪 INSTALLMENT APPLICATION - CANCEL/AMEND TEST SCENARIOS

Bu yerda barcha test scenariolarini browser orqali qo'lda test qilish uchun qo'llanma.

---

## ⚙️ PRE-REQUISITES (Oldindan tayyorgarlik)

### 1. Accounts Settings ni tekshirish
- **URL**: http://asadstack.com:8000/app/accounts-settings
- **Setting**: "Unlink advance payment on cancellation of order"
- **Qiymati**: ✅ **CHECKED bo'lishi kerak** (default ERPNext behavior)
- **Sabab**: Bu setting o'chirilsa, boshqa tizimlarda muammo bo'lishi mumkin

### 2. Supplier Debt Tracking ishlayotganini tekshirish
```sql
SELECT custom_total_debt, custom_paid_amount, custom_remaining_debt 
FROM `tabSupplier` 
WHERE name = 'MacBookMarket';
```

---

## 📋 TEST CASE 1: Draft PE Delete on SO Cancel

### Maqsad
Sales Order cancel qilinganda:
- ✅ Submitted PE lar **CANCEL** bo'lishi kerak
- ✅ Draft PE lar **DELETE** bo'lishi kerak (cancel emas!)

### Test Qadamlari

#### 1. Yangi Installment Application yaratish
- **DocType**: Installment Application
- **Customer**: Asadbek (yoki istalgan)
- **Item**: iPhone 13 (1 dona, $1000)
- **Supplier**: MacBookMarket
- **Downpayment**: $500
- **Monthly Payment**: $100
- **Months**: 6
- **Action**: Submit ✅

#### 2. Sales Order yaratilganini tekshirish
- List: Sales Order
- Filter: Status = "To Deliver and Bill"
- **Expected**: Yangi SO yaratilgan (CON-2025-XXXXX)

#### 3. Payment Entry (Submitted) yaratish
- **DocType**: Payment Entry
- **Type**: Receive
- **Party**: Customer (Asadbek)
- **Amount**: $500
- **Custom Contract Reference**: CON-2025-XXXXX (yuqoridagi SO)
- **Custom Counterparty Category**: Klient
- **Custom Payment Schedule Row**: "Boshlang'ich to'lov"
- **Action**: Submit ✅

#### 4. Payment Entry (Draft) yaratish
- **DocType**: Payment Entry
- **Type**: Receive
- **Party**: Customer (Asadbek)
- **Amount**: $100
- **Custom Contract Reference**: CON-2025-XXXXX
- **Custom Counterparty Category**: Klient
- **Custom Payment Schedule Row**: "1-to'lov"
- **Action**: Save (draft sifatida qoldirish) 💾

#### 5. BEFORE Cancel - PE larni tekshirish
```sql
SELECT name, paid_amount, docstatus, custom_contract_reference
FROM `tabPayment Entry`
WHERE custom_contract_reference = 'CON-2025-XXXXX'
ORDER BY creation;
```
**Expected**:
- 2 ta PE
- 1 ta docstatus=1 (Submitted) - $500
- 1 ta docstatus=0 (Draft) - $100

#### 6. Installment Application ni CANCEL qilish
- **Action**: Cancel ❌
- **Expected Messages**:
  - ✅ "Sales Order CON-2025-XXXXX cancelled"
  - ✅ "✅ 1 ta to'lov bekor qilindi"
  - ✅ "🗑️ 1 ta draft to'lov o'chirildi"

#### 7. AFTER Cancel - PE larni tekshirish
```sql
SELECT name, paid_amount, docstatus, custom_contract_reference
FROM `tabPayment Entry`
WHERE custom_contract_reference = 'CON-2025-XXXXX'
ORDER BY creation;
```
**Expected**:
- 1 ta PE (submitted)
- docstatus=2 (Cancelled)
- Draft PE **yo'q** (o'chirilgan)

#### 8. Supplier Debt ni tekshirish
```sql
SELECT custom_total_debt, custom_paid_amount, custom_remaining_debt 
FROM `tabSupplier` 
WHERE name = 'MacBookMarket';
```
**Expected**: Debt $1000 ga kamaygan bo'lishi kerak

### ✅ SUCCESS CRITERIA
- [x] Submitted PE cancelled
- [x] Draft PE deleted (DB dan butunlay yo'q)
- [x] SO cancelled
- [x] InstApp cancelled
- [x] Supplier debt reversed

---

## 📋 TEST CASE 2: FULL CLONE - Non-Financial Change (IMEI)

### Maqsad
Faqat IMEI o'zgarganda (moliyaviy o'zgarish yo'q):
- ✅ Barcha PE lar **CLONE** qilinadi (draft sifatida)
- ✅ Clone PE daeski amount saqlanadi
- ✅ Supplier debt to'g'ri qayta tiklanadi

### Test Qadamlari

#### 1. Yangi InstApp yaratish va submit qilish
- Item: iPhone 13, $1000
- IMEI: **123456789**
- Downpayment: $500, Monthly: $100, Months: 6
- Submit ✅

#### 2. Payment Entry yaratish
- Amount: $500 (downpayment)
- Submit ✅

#### 3. CANCEL va AMEND
- InstApp ni cancel ❌
- Amend tugmasini bosing 🔄
- **IMEI ni o'zgartiring**: 987654321
- **Amount larni o'zgartirMANG**
- Submit ✅

#### 4. Natijani tekshirish
```sql
SELECT ia.name, ia.amended_from, ia.imei_number, 
       so.name as sales_order, so.docstatus
FROM `tabInstallment Application` ia
LEFT JOIN `tabSales Order` so ON so.name = ia.sales_order
WHERE ia.name LIKE 'INST-APP-2025-00052-1%'
ORDER BY ia.creation DESC;
```

#### 5. Payment Entry larni tekshirish
**DIQQAT**: Clone qilingan PE **DRAFT** bo'ladi, shuning uchun Payment Entry List da filter qo'yish kerak!

**Browser da**:
- Payment Entry List ga boring
- **Filter**: Custom Contract Reference = CON-2025-XXXXX (yangi SO)
- **Filter**: Status = "Draft" yoki "All"
- **Expected**: 1 ta Draft PE ko'rinishi kerak (clone)

**SQL orqali**:
```sql
SELECT pe.name, pe.paid_amount, pe.docstatus, 
       pe.custom_contract_reference
FROM `tabPayment Entry` pe
WHERE pe.custom_contract_reference LIKE 'CON-2025-XXXXX%'
ORDER BY pe.creation;
```

**Expected**:
- Eski PE: docstatus=2 (cancelled)
- **Yangi PE (CLONE)**: docstatus=0 (draft), amount=$500
- **MUHIM**: Clone PE ni ko'rish uchun "Draft" filterini qo'ying!

#### 6. Supplier Debt
```sql
SELECT custom_total_debt FROM `tabSupplier` WHERE name = 'MacBookMarket';
```
**Expected**: Debt o'zgarmagan (cancel -$1000, submit +$1000)

### ✅ SUCCESS CRITERIA
- [x] Eski PE cancelled
- [x] Yangi PE created (draft) ← **DRAFT bo'ladi, filter qo'ying!**
- [x] Yangi PE amount = Eski PE amount
- [x] Supplier debt restored correctly
- [x] Green success message ko'rsatildi

### 💡 MUHIM ESLATMA
Clone qilingan Payment Entry lar **DRAFT** sifatida yaratiladi. Ularni ko'rish uchun:
1. Payment Entry List → Filter → Status = "Draft"
2. Yoki SQL orqali: `WHERE docstatus = 0`
3. Clone PE ni o'zingiz submit qilishingiz kerak!

---

## 📋 TEST CASE 3: PARTIAL CLONE - Downpayment Change

### Maqsad
Downpayment amount o'zgarganda:
- ✅ Eski PE cancel
- ✅ **YANGI** draft PE yaratiladi (yangi amount bilan)
- ⚠️ Warning message ko'rsatiladi

### Test Qadamlari

#### 1. InstApp yaratish
- Downpayment: **$500**
- Monthly: $100
- Submit ✅

#### 2. Downpayment PE yaratish
- Amount: $500
- Submit ✅

#### 3. CANCEL va AMEND
- Cancel ❌
- Amend 🔄
- **Downpayment ni o'zgartiring**: **$300**
- Submit ✅

#### 4. Expected Messages
- ⚠️ "OGOHLANTIRISH: Boshlang'ich to'lov $500 → $300 o'zgardi"
- ⚠️ "Yangi draft to'lov yaratildi. Eski summani tekshiring!"

#### 5. PE larni tekshirish
```sql
SELECT name, paid_amount, docstatus, custom_is_cloned_payment
FROM `tabPayment Entry`
WHERE custom_contract_reference LIKE 'CON-2025-XXXXX%'
ORDER BY creation;
```

**Expected**:
- Eski PE: $500, docstatus=2 (cancelled)
- Yangi PE: $300, docstatus=0 (draft), custom_is_cloned_payment=0 (YANGI!)

### ✅ SUCCESS CRITERIA
- [x] Eski PE cancelled
- [x] Yangi PE created with NEW amount ($300)
- [x] custom_is_cloned_payment = 0 (not a clone, new payment!)
- [x] Warning message (orange) shown

---

## 📋 TEST CASE 4: PARTIAL CLONE - Monthly Payment Change

### Maqsad
Monthly payment o'zgarganda:
- ✅ Eski PE lar clone qilinadi (eski amount bilan)
- ⚠️ Foydalanuvchiga yangi oylik to'lov haqida ogohlantirish

### Test Qadamlari

#### 1. InstApp yaratish
- Downpayment: $500
- Monthly: **$100**
- Months: 6
- Submit ✅

#### 2. 2 ta Monthly PE yaratish
- PE1: $100 (1-to'lov) - Submit ✅
- PE2: $100 (2-to'lov) - Submit ✅

#### 3. CANCEL va AMEND
- Cancel ❌
- Amend 🔄
- **Monthly Payment ni o'zgartiring**: **$150**
- Submit ✅

#### 4. Expected Messages
- ⚠️ "OGOHLANTIRISH: Oylik to'lov $100 → $150 o'zgardi"
- ⚠️ "Eski to'lovlar clone qilindi. Yangi oylar uchun $150 to'lash kerak!"

#### 5. PE larni tekshirish
**Expected**:
- 2 ta eski PE: cancelled
- 2 ta yangi PE: draft, amount=$100 (eski amount!), cloned=1

### ✅ SUCCESS CRITERIA
- [x] Barcha eski PE lar cancelled
- [x] Yangi PE lar eski amount bilan clone qilindi
- [x] Warning message shown
- [x] Supplier debt restored

---

## 📋 TEST CASE 5: NO CLONE - All Fields Changed

### Maqsad
Agar **BARCHA** moliyaviy fieldlar o'zgartrilsa:
- ⚠️ Hech qanday clone **BO'LMAYDI**
- ⚠️ Blue message: "Foydalanuvchi yangi to'lovlarni qo'lda kiritishi kerak"

### Test Qadamlari

#### 1. InstApp yaratish
- Downpayment: $500, Monthly: $100, Months: 6
- Submit ✅

#### 2. PE yaratish
- $500 downpayment - Submit ✅

#### 3. CANCEL va AMEND
- Cancel ❌
- Amend 🔄
- **Downpayment**: $300 (o'zgardi)
- **Monthly**: $150 (o'zgardi)
- **Months**: 12 (o'zgardi)
- **Total**: $2000 (o'zgardi)
- Submit ✅

#### 4. Expected Messages
- 🔵 "MA'LUMOT: Barcha moliyaviy fieldlar o'zgardi"
- 🔵 "Clone qilinmaydi. Yangi to'lovlarni qo'lda kiriting."

#### 5. PE larni tekshirish
**Expected**:
- Faqat eski PE (cancelled)
- Yangi PE lar **YO'Q**

### ✅ SUCCESS CRITERIA
- [x] Eski PE cancelled
- [x] Yangi PE lar yaratilmagan
- [x] Blue info message shown
- [x] NO clone operation performed

---

## 📋 TEST CASE 6: Multiple Suppliers

### Maqsad
2 ta item (har xil supplier) bo'lganda debt tracking to'g'ri ishlashini tekshirish.

### Test Qadamlari

#### 1. InstApp yaratish
- Item 1: iPhone 13, $1000, **Supplier: MacBookMarket**
- Item 2: MacBook Pro, $2000, **Supplier: AppleStore**
- Downpayment: $1500
- Submit ✅

#### 2. Debt ni tekshirish
```sql
SELECT name, custom_total_debt FROM `tabSupplier` 
WHERE name IN ('MacBookMarket', 'AppleStore');
```
**Expected**:
- MacBookMarket: +$1000
- AppleStore: +$2000

#### 3. CANCEL
- InstApp ni cancel ❌

#### 4. Debt ni qayta tekshirish
**Expected**:
- MacBookMarket: -$1000 (reversed)
- AppleStore: -$2000 (reversed)

### ✅ SUCCESS CRITERIA
- [x] Har ikkala supplier debt to'g'ri qo'shildi
- [x] Cancel qilinganda har ikkala debt reversed
- [x] No errors during cancel

---

## 🔧 DEBUG COMMANDS

### Payment Entry larni tekshirish
```sql
SELECT pe.name, pe.paid_amount, pe.docstatus,
       pe.custom_contract_reference,
       pe.custom_is_cloned_payment,
       pe.custom_original_payment_entry
FROM `tabPayment Entry` pe
WHERE pe.creation > '2025-01-28'
ORDER BY pe.creation DESC
LIMIT 20;
```

### Supplier Debt History
```sql
SELECT name, custom_total_debt, custom_paid_amount, custom_remaining_debt,
       modified
FROM `tabSupplier`
WHERE name IN ('MacBookMarket', 'AppleStore')
ORDER BY modified DESC;
```

### InstApp va SO relationship
```sql
SELECT ia.name as InstApp, 
       ia.amended_from,
       ia.docstatus as IA_Status,
       so.name as SO,
       so.docstatus as SO_Status,
       COUNT(pe.name) as PE_Count
FROM `tabInstallment Application` ia
LEFT JOIN `tabSales Order` so ON so.name = ia.sales_order
LEFT JOIN `tabPayment Entry` pe ON pe.custom_contract_reference = so.name
WHERE ia.creation > '2025-01-28'
GROUP BY ia.name, so.name
ORDER BY ia.creation DESC;
```

### Log Messages tekshirish
```sql
SELECT creation, error FROM `tabError Log`
WHERE error LIKE '%payment%' OR error LIKE '%clone%'
ORDER BY creation DESC
LIMIT 10;
```

---

## 📊 EXPECTED BEHAVIOR SUMMARY

| Scenario | Downpayment | Monthly | Months | Total | Clone Strategy | New PE Amount |
|----------|-------------|---------|--------|-------|----------------|---------------|
| IMEI change only | Same | Same | Same | Same | **FULL_CLONE** | Old amount |
| Downpayment changed | Changed | Same | Same | Any | **PARTIAL_CLONE** | NEW amount |
| Monthly changed | Same | Changed | Same | Any | **PARTIAL_CLONE** | Old amount |
| All changed | Changed | Changed | Changed | Changed | **NO_CLONE** | None (manual) |

---

## 🚨 TROUBLESHOOTING

### Agar PE cancel bo'lmasa:
1. Terminal da log larni ko'ring: `tail -f logs/frappe.log`
2. PE da boshqa linklar bormi tekshiring
3. ERPNext Accounts Settings tekshiring

### Agar Draft PE delete bo'lmasa:
1. Redis server ishlayotganini tekshiring: `bench start`
2. Force delete qilib ko'ring: `bench --site asadstack.com console`
   ```python
   frappe.delete_doc("Payment Entry", "PE-NAME", force=1)
   ```

### Agar Supplier Debt reverse bo'lmasa:
1. `supplier_debt_tracking.py` da `on_cancel` hook borligini tekshiring
2. Console da qo'lda test qiling:
   ```python
   from cash_flow_app.cash_flow_management.custom.supplier_debt_tracking import update_supplier_debt_on_cancel_installment
   app = frappe.get_doc("Installment Application", "INST-APP-NAME")
   update_supplier_debt_on_cancel_installment(app)
   ```

---

## ✅ FINAL CHECKLIST

Barcha testlar o'tganidan keyin:
- [ ] TEST 1: Draft PE Delete - PASSED
- [ ] TEST 2: FULL CLONE (IMEI) - PASSED
- [ ] TEST 3: PARTIAL CLONE (Downpayment) - PASSED
- [ ] TEST 4: PARTIAL CLONE (Monthly) - PASSED
- [ ] TEST 5: NO CLONE (All changed) - PASSED
- [ ] TEST 6: Multiple Suppliers - PASSED
- [ ] No errors in logs
- [ ] Supplier debt tracking correct
- [ ] Browser messages ko'rsatiladi

**Muvaffaqiyat!** 🎉
