# 🧪 QUICK TEST GUIDE - REPORTS

## Tezkor Test Qilish Uchun

### 1️⃣ Migration
```bash
cd ~/frappe-bench
bench --site site1.localhost clear-cache
bench --site site1.localhost migrate
bench restart
```

### 2️⃣ Access Reports
ERPNext UI → Reports → Cash Flow Management module ichida:
- Daily Cash Flow
- Outstanding Installments  
- Monthly Payment Schedule
- Category-wise Summary

### 3️⃣ Quick Console Test (agar UI'da xato bo'lsa)

```python
# bench console orqali
bench --site site1.localhost console

# Python console ichida:
import frappe
from cash_flow_app.cash_flow_management.report.daily_cash_flow.daily_cash_flow import execute

# Test filters
filters = {
    "from_date": "2025-10-01",
    "to_date": "2025-10-31"
}

# Execute
columns, data, message, chart, summary = execute(filters)

# Check results
print(f"Columns: {len(columns)}")
print(f"Data rows: {len(data)}")
print(f"Summary: {summary}")
```

### 4️⃣ Common Issues & Fixes

**Xato:** "custom_counterparty_category not found"
**Fix:** Custom field hali yaratilmagan, Phase 5'da qilamiz

**Xato:** "No module named ..."
**Fix:** 
```bash
bench --site site1.localhost migrate
bench restart
```

**Xato:** Report list'da ko'rinmayapti
**Fix:**
```bash
bench --site site1.localhost clear-cache
bench build --app cash_flow_app
```

### 5️⃣ Quick Check

Reports yaratilganini tekshirish:
```bash
cd ~/frappe-bench/apps/cash_flow_app
ls -la cash_flow_app/cash_flow_management/report/
```

Ko'rinishi kerak:
- daily_cash_flow/
- outstanding_installments/
- monthly_payment_schedule/
- category_wise_summary/

---

## 📊 UI'da Test Qilish Ketma-ketligi:

1. **Login** → site1.localhost
2. **Go to:** Reports list
3. **Module:** Cash Flow Management
4. **Select:** Daily Cash Flow
5. **Set filters:** From/To date
6. **Run:** Generate report
7. **Check:**
   - Chart displays
   - Summary cards show
   - Data table loads
   - Export works

---

## ⚠️ ESLATMA

Agar Payment Entry'da **custom_counterparty_category** field bo'lmasa:
- Reports ishlamaydi
- Keyingi phase'da custom field yaratamiz
- Hozircha faqat kod strukturasini test qiling
