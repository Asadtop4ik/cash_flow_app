# 🔧 QUICK FIX GUIDE - Customer History Not Showing

## ✅ FIXED ISSUES:

### Issue 1: JavaScript not loading
**Problem:** `customer.js` wasn't built into assets  
**Fix:** `bench build --app cash_flow_app`

### Issue 2: Wrong DOM selector
**Problem:** `frm.fields_dict['customer_name']` not working  
**Fix:** Changed to `frm.$wrapper.find('.form-layout').after(wrapper)`

### Issue 3: Payment Entry not linked to Sales Order  
**Problem:** `custom_contract_reference` was NULL  
**Fix:** Already added `references` table in code, will work for NEW payments

### Issue 4: Payment Schedule not updating
**Problem:** Hook wasn't triggered because `custom_contract_reference` NULL  
**Fix:** Manually set for existing payment, will auto-work for new ones

---

## 🧪 TESTING STEPS:

### 1. Check if customer.js is loaded:
Open browser console (F12) and type:
```javascript
frappe.ui.form.on('Customer')
```
Should show object with `refresh` function.

### 2. Open Customer form:
```
http://your-site/app/customer/Asadbekkkk
```

### 3. Check browser console for errors:
Look for JavaScript errors related to:
- `customer_history`
- `get_customer_contracts`
- `get_payment_schedule_with_history`

### 4. Check API response:
In console, run:
```javascript
frappe.call({
    method: 'cash_flow_app.cash_flow_management.api.customer_history.get_customer_contracts',
    args: { customer: 'Asadbekkkk' },
    callback: (r) => console.log(r.message)
});
```

---

## 📱 FOR OPERATOR:

**If sections still not showing:**

1. **Hard refresh browser:**
   - Chrome/Firefox: `Ctrl + Shift + R`
   - Or clear browser cache

2. **Check network tab:**
   - F12 → Network
   - Look for `customer.js` file
   - Should return 200 OK

3. **Try different browser:**
   - Test in Chrome/Firefox/Edge

---

## 🔄 WORKFLOW FOR NEW CONTRACTS:

**This will work automatically now:**

1. Create Installment Application
2. Submit → Sales Order created
3. Payment Entry created WITH `custom_contract_reference` ✅
4. Operator submits Payment Entry
5. Hook triggers → Payment Schedule updates ✅
6. Refresh Customer → Sections appear ✅

**Current customer (Asadbekkkk):**
- ✅ Contract: CON-2025-00011
- ✅ Payment: $1000 paid
- ✅ Schedule: Row 1 marked as paid
- ✅ API working
- ⏳ Need browser hard refresh to see sections

---

## 💻 BROWSER STEPS:

1. Go to: http://asadstack.com/app/customer/Asadbekkkk
2. Hard refresh: `Ctrl + Shift + R`
3. Scroll down after customer fields
4. Should see:
   - 📋 Section 1: Shartnoma umumiy ma'lumotlari
   - 📅 Section 2: Oylik to'lovlar jadvali

If still not showing, open F12 console and share screenshot of errors.
