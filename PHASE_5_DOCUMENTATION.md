# 📄 PHASE 5 - PRINT FORMATS & VALIDATIONS - DOCUMENTATION

**Created:** October 13, 2025  
**Status:** ✅ COMPLETED

---

## 📋 YARATILGAN FAYLLAR

### 1️⃣ **SHARTNOMA (Sales Order Print Format)**

**Path:** `cash_flow_management/print_format/shartnoma/`

**Files:**
- `__init__.py`
- `shartnoma.json` (Print Format definition)
- `shartnoma.html` (Jinja template)

**Features:**
- ✅ O'zbek tilida
- ✅ Letter Head integratsiyasi
- ✅ Mijoz ma'lumotlari
- ✅ Mahsulotlar jadvali (IMEI bilan)
- ✅ To'lov jadvali (Payment Schedule)
- ✅ Foiz hisoblash ko'rsatiladi
- ✅ Boshlang'ich to'lov (downpayment)
- ✅ Oylik to'lov miqdori
- ✅ Shartnoma shartlari (5 ta punktlar)
- ✅ Imzo joylari (Sotuvchi va Xaridor)
- ✅ A4 print-ready
- ✅ Responsive design

**Usage:**
```
Sales Order → Print → Select "Shartnoma" format
```

---

### 2️⃣ **KASSA KVITANSIYA (Payment Entry Print Format)**

**Path:** `cash_flow_management/print_format/kassa_kvitansiya/`

**Files:**
- `__init__.py`
- `kassa_kvitansiya.json` (Print Format definition)
- `kassa_kvitansiya.html` (Jinja template)

**Features:**
- ✅ O'zbek tilida
- ✅ Letter Head integratsiyasi
- ✅ Kirim/Chiqim rangli ajratish (Green/Red)
- ✅ Katta summa ko'rsatish (48px font)
- ✅ Summa so'zlar bilan
- ✅ To'lov turi (Naqd/Click/Terminal)
- ✅ Kategoriya ko'rsatish
- ✅ Shartnoma bog'lanishi
- ✅ Filial ma'lumoti
- ✅ Bog'langan hujjatlar jadvali
- ✅ Hisob ma'lumotlari (Debet/Kredit)
- ✅ Imzo joylari
- ✅ A5 portrait print-ready
- ✅ Responsive design

**Dynamic Features:**
- Auto-detects Kirim vs Chiqim
- Color changes based on payment type
- Shows reference documents if linked
- Displays amount in words (USD)

**Usage:**
```
Payment Entry → Print → Select "Kassa Kvitansiya" format
```

---

### 3️⃣ **NEGATIVE BALANCE VALIDATION**

**Path:** `cash_flow_management/custom/payment_validations.py`

**Functions:**

#### `validate_negative_balance(doc, method)`
**Purpose:** Prevents cash account from going negative

**Logic:**
```python
if payment_type == "Pay":
    current_balance = get_account_balance()
    if current_balance < payment_amount:
        throw error with detailed message
```

**Error Message Shows:**
- Current balance
- Payment amount
- Shortage amount (RED)
- Helpful instruction

**Triggers:** Payment Entry → validate event (only for Pay type)

---

#### `get_account_balance(account, date, company)`
**Purpose:** Get account balance as of specific date

**Uses:** ERPNext native function `get_balance_on()`

**Returns:** Float (USD balance)

---

#### `validate_payment_schedule_paid_amount(doc, method)`
**Purpose:** Ensure paid amount doesn't exceed payment amount in schedule

**Logic:**
```python
for each schedule row:
    if paid_amount > payment_amount:
        throw error
```

**Triggers:** Sales Order → validate event

---

#### `warn_on_overdue_payments(doc, method)`
**Purpose:** Warn when receiving payment from customer with overdue installments

**Features:**
- ✅ Shows table of overdue payments
- ✅ Displays days overdue (RED)
- ✅ Shows total overdue amount
- ✅ Warning (not error - allows continuation)
- ✅ Limited to top 5 overdue payments

**Triggers:** Payment Entry → validate event (only for Receive from Customer)

**UI Display:**
- Orange indicator
- Table format
- Total summary

---

## 🔧 HOOKS REGISTRATION

**Updated:** `hooks.py`

```python
doc_events = {
    "Payment Entry": {
        "autoname": "...payment_entry_naming.autoname",
        "validate": [
            "...payment_entry_hooks.validate",
            "...payment_validations.validate_negative_balance",
            "...payment_validations.warn_on_overdue_payments"
        ],
        "on_submit": "...payment_entry_hooks.on_submit",
        "on_cancel": "...payment_entry_hooks.on_cancel"
    },
    "Sales Order": {
        "validate": "...payment_validations.validate_payment_schedule_paid_amount"
    }
}
```

**Multiple validators on Payment Entry:**
- Category validation
- Negative balance check
- Overdue payment warning

---

## 📊 PRINT FORMAT DETAILS

### **Shartnoma Template Sections:**

1. **Header**
   - Letter Head (if configured)
   - Title: "MUDDATLI TO'LOV SHARTNOMASI"
   - Contract number and date

2. **Contract Info**
   - Contract date
   - Customer name
   - Phone (if available)
   - Branch/Filial

3. **Items Table**
   - # (row number)
   - Product name
   - IMEI (if exists)
   - Quantity
   - Price (USD)
   - Amount (USD)
   - Total row

4. **Payment Schedule Table**
   - # (payment number)
   - Due date
   - Amount (USD)
   - Status (Paid ✓ / Pending)

5. **Payment Summary**
   - Product value
   - Downpayment (% and amount)
   - Interest amount (RED if > 0)
   - Total with interest (RED, BOLD)
   - Finance amount
   - Term (months)
   - Monthly payment (GREEN, BOLD)

6. **Terms & Conditions**
   - 5 contractual points in O'zbek

7. **Signatures**
   - Seller signature line
   - Buyer signature line with name

8. **Footer**
   - System reference number
   - Print date/time
   - "Electronically verified" text

---

### **Kassa Kvitansiya Template Sections:**

1. **Header**
   - Letter Head
   - Title: "KASSA KIRIM" (GREEN) or "KASSA CHIQIM" (RED)
   - Receipt number

2. **Receipt Info**
   - Date
   - Time
   - Party name (From/To based on type)
   - Category
   - Payment mode (badge)
   - Contract reference (if linked)
   - Branch/Filial

3. **Amount Display**
   - Large centered amount (48px)
   - Color matches payment type
   - USD currency label

4. **Amount in Words**
   - Full amount spelled out
   - Uses Frappe's `money_in_words()` function

5. **Remarks**
   - Shows if any remarks added

6. **Reference Documents**
   - Table of linked documents
   - Shows allocated amounts

7. **Account Info**
   - Debit account (From)
   - Credit account (To)

8. **Signatures**
   - Recipient/Payer signature
   - Cashier signature

9. **Footer**
   - System reference
   - Print timestamp
   - Electronic verification notice

---

## 🎨 DESIGN FEATURES

### **Shartnoma:**
- Professional contract layout
- Clear section headings
- Bordered tables
- Highlighted totals
- Color coding (RED for costs, GREEN for payments)
- Print-optimized for A4
- Minimal page breaks

### **Kassa Kvitansiya:**
- Receipt-style compact layout
- Eye-catching amount display
- Color psychology (Green=good, Red=outgoing)
- Quick scan friendly
- Thermal printer compatible
- A5 portrait optimized

---

## 💡 BUSINESS LOGIC

### **Negative Balance Prevention:**
**Why?** Prevents overspending and maintains accurate cash records

**When?** Before saving Payment Entry (Pay type only)

**How?**
1. Get current balance from GL Entry
2. Compare with payment amount
3. Block if insufficient
4. Show clear error with numbers

**Benefits:**
- Prevents accounting errors
- Maintains data integrity
- Clear user guidance

---

### **Payment Schedule Validation:**
**Why?** Prevents data corruption in payment tracking

**When?** Before saving Sales Order

**How?**
1. Loop through payment schedule rows
2. Check paid_amount <= payment_amount
3. Throw error if violated

**Benefits:**
- Data consistency
- Accurate outstanding calculations
- Prevents negative balances

---

### **Overdue Payment Warning:**
**Why?** Helps track customer payment discipline

**When?** When creating payment entry for customer

**How?**
1. Query overdue payment schedules
2. Calculate days overdue
3. Show warning with details
4. Allow user to proceed

**Benefits:**
- Payment discipline awareness
- Collection reminder
- Better cash flow management

**Note:** It's a warning, not an error - user can continue

---

## 🧪 TESTING GUIDE

### **Shartnoma Print Format:**

1. Create Sales Order
2. Add items with prices
3. Add Payment Schedule (manual or via Installment Application)
4. Submit
5. Click Print → Select "Shartnoma"
6. Check:
   - ✅ All sections display
   - ✅ Calculations correct
   - ✅ Payment schedule shows
   - ✅ Print preview looks good
   - ✅ PDF generation works

---

### **Kassa Kvitansiya:**

**For Kirim (Receive):**
1. Create Payment Entry (Receive)
2. Set mode of payment
3. Add category
4. Set amount
5. Submit
6. Print → "Kassa Kvitansiya"
7. Check:
   - ✅ GREEN title/colors
   - ✅ "KASSA KIRIM" shows
   - ✅ Amount correct
   - ✅ Party shows

**For Chiqim (Pay):**
1. Create Payment Entry (Pay)
2. Similar steps
3. Check:
   - ✅ RED title/colors
   - ✅ "KASSA CHIQIM" shows

---

### **Negative Balance Validation:**

1. Check cash account balance (e.g., 100 USD)
2. Try to create Payment Entry (Pay) for 200 USD
3. Try to save
4. Expected:
   - ❌ Error blocks save
   - ✅ Shows current balance: 100 USD
   - ✅ Shows payment: 200 USD
   - ✅ Shows shortage: 100 USD (RED)
   - ✅ Helpful message

---

### **Overdue Warning:**

1. Create Sales Order with payment schedule
2. Set due date in past
3. Don't make payment
4. Create new Payment Entry for same customer
5. Try to save
6. Expected:
   - ⚠️ Orange warning appears
   - ✅ Shows overdue table
   - ✅ Shows days overdue
   - ✅ Shows outstanding amounts
   - ✅ Can still save (warning only)

---

## 📁 FILE STRUCTURE

```
cash_flow_app/
└── cash_flow_app/
    └── cash_flow_management/
        ├── custom/
        │   ├── payment_entry_hooks.py (existing)
        │   ├── payment_entry_naming.py (existing)
        │   └── payment_validations.py (NEW ✨)
        └── print_format/
            ├── shartnoma/ (NEW ✨)
            │   ├── __init__.py
            │   ├── shartnoma.json
            │   └── shartnoma.html
            └── kassa_kvitansiya/ (NEW ✨)
                ├── __init__.py
                ├── kassa_kvitansiya.json
                └── kassa_kvitansiya.html
```

---

## ✅ PHASE 5 CHECKLIST

- [x] Shartnoma Print Format created
- [x] Kassa Kvitansiya Print Format created
- [x] Negative balance validation implemented
- [x] Payment schedule validation implemented
- [x] Overdue payment warning implemented
- [x] Hooks registered
- [x] O'zbek language used
- [x] Letter Head integration
- [x] Responsive design
- [x] Print-optimized layouts
- [x] Error messages clear and helpful
- [x] Documentation complete

---

## 🚀 NEXT STEPS (Migration & Testing)

```bash
# 1. Clear cache
bench --site asadstack.com clear-cache

# 2. Migrate
bench --site asadstack.com migrate

# 3. Restart
bench restart

# 4. Test in UI
- Create Sales Order → Print Shartnoma
- Create Payment Entry → Print Kvitansiya
- Test negative balance
- Test overdue warning
```

---

## 📊 PHASE 5 SUMMARY

| Component | Status | Files | Lines of Code |
|-----------|--------|-------|---------------|
| Shartnoma Print | ✅ | 3 | ~300 |
| Kvitansiya Print | ✅ | 3 | ~250 |
| Validations | ✅ | 1 | ~150 |
| Hooks Update | ✅ | 1 | ~10 |
| **TOTAL** | **✅** | **8** | **~710** |

---

**Phase 5 MUVAFFAQIYATLI YAKUNLANDI!** 🎉

Next: Phase 6 - Permissions & Custom Fields
