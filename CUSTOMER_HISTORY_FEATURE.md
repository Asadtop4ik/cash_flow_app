# 📊 CUSTOMER HISTORY FEATURE - DOCUMENTATION

**Created:** October 18, 2025  
**Feature:** Customer Contract & Payment History Display  
**Status:** ✅ IMPLEMENTED

---

## 🎯 OVERVIEW

Customer DocType formida mijozning shartnoma va to'lov tarixini ko'rsatish uchun real-time dynamic section qo'shildi.

---

## 📁 FILES CREATED

### 1. **Client Script**
**Path:** `cash_flow_app/public/js/customer.js`

**Features:**
- ✅ Customer formda 2ta custom section yaratadi
- ✅ Real-time data API dan olinadi
- ✅ Auto-refresh on form load
- ✅ Responsive table design
- ✅ Status indicators (On Time, Late, Upcoming, Overdue)

### 2. **Backend API**
**Path:** `cash_flow_app/cash_flow_management/api/customer_history.py`

**Functions:**

#### `get_customer_contracts(customer)` 
- Returns latest contract summary
- Joins Sales Order + Installment Application
- Calculates outstanding amount
- Determines status color

#### `get_payment_schedule_with_history(customer)`
- Returns payment schedule with actual payments
- Maps Payment Entry to schedule rows
- Calculates days late/remaining
- Status determination logic

---

## 🎨 UI STRUCTURE

### **Section 1: Shartnoma Umumiy Ma'lumotlari**

Shows:
- Mijoz ismi
- Shartnoma raqami (clickable link)
- Sana
- Umumiy summa
- Nechi oyga
- Har oy to'lov
- To'lagan jami (green)
- Qolgan qarz (red if outstanding)
- Holat (status pill)

### **Section 2: Oylik To'lovlar Jadvali**

Table columns:
1. **Oy raqami** - Payment number
2. **To'lov kuni** - Due date
3. **To'lash kerak summa** - Payment amount
4. **To'lashga qolgan / O'tgan kun** - Status badge
5. **To'lagan summa** - Paid amount
6. **To'lagan sana** - Payment date
7. **Holat** - Status pill

---

## 🔧 STATUS LOGIC

### Payment Schedule Status:

1. **On Time** (Green ✅)
   - Paid amount >= payment amount
   - Paid on or before due date
   - Shows: "0 kun erta"

2. **Late** (Red ❌)
   - Paid amount >= payment amount
   - Paid after due date
   - Shows: "X kun kechikdi"

3. **Upcoming** (Orange ⏳)
   - Not paid yet
   - Due date in future
   - Shows: "X kun qoldi"

4. **Overdue** (Red ❌)
   - Not paid yet
   - Due date passed
   - Shows: "X kun kechikdi"

---

## 📊 DATA FLOW

```
Customer Form Load
    ↓
refresh() trigger
    ↓
show_customer_history()
    ↓
    ├── load_contract_history()
    │   └── API: get_customer_contracts()
    │       └── Query: Sales Order + Installment App
    │       └── Display: Section 1
    │
    └── load_payment_history()
        └── API: get_payment_schedule_with_history()
            └── Query: Payment Schedule + Payment Entry
            └── Logic: Map payments to schedule
            └── Display: Section 2 (Table)
```

---

## 🔌 INTEGRATION

### Hooks Configuration:
```python
# hooks.py
doctype_js = {
    "Customer": "public/js/customer.js"
}
```

### API Whitelisted:
```python
@frappe.whitelist()
def get_customer_contracts(customer):
    ...

@frappe.whitelist()
def get_payment_schedule_with_history(customer):
    ...
```

---

## 💡 USAGE

1. Open any Customer record
2. Form automatically loads history sections
3. Click contract number to open Sales Order
4. Data updates when:
   - New Payment Entry submitted
   - Sales Order updated
   - Form refreshed

---

## 🎨 STYLING

- **Card sections** with visible borders
- **Indicator pills** for status
- **Color coding:**
  - Green: Positive (paid, on time)
  - Red: Negative (overdue, late)
  - Orange: Warning (upcoming)
  - Blue: Info (section headers)
- **Responsive table** with horizontal scroll
- **Hover effects** on table rows

---

## 🧪 TESTING

### Test Case 1: Customer with Contract
```
1. Go to Customer: "Asadbek"
2. Check Section 1: Shows contract CON-2025-00008
3. Check Section 2: Shows 7 payment rows
4. Verify: 1st payment "On Time", rest "Upcoming"
```

### Test Case 2: Customer without Contract
```
1. Go to new Customer
2. See: "❌ Hali shartnoma mavjud emas"
```

### Test Case 3: Overdue Payment
```
1. Customer with past due date
2. Payment not made
3. See: "❌ X kun kechikdi" in red
4. Status: "Overdue"
```

---

## 🚀 FUTURE ENHANCEMENTS

1. ⏳ Multiple contracts support (tabs/accordion)
2. ⏳ Payment history graph
3. ⏳ Export to PDF/Excel
4. ⏳ SMS/Email reminders for overdue
5. ⏳ Quick payment button
6. ⏳ Payment prediction (ML)

---

## 📝 NOTES

- Only latest contract shown (LIMIT 1)
- Real-time data (no caching)
- Requires submitted Sales Order
- Payment Entry must be linked to Sales Order
- Status auto-updates on refresh

---

## ✅ COMPLETED FEATURES

- [x] Contract summary display
- [x] Payment schedule table
- [x] Status indicators
- [x] Date calculations
- [x] Responsive design
- [x] API integration
- [x] Error handling
- [x] Empty state handling

---

**Status:** ✅ **PRODUCTION READY**
