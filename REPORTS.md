# 📊 CASH FLOW APP - REPORTS DOCUMENTATION

## Phase 4: Reports Implementation - COMPLETED ✅

**Created Date:** October 13, 2025  
**Total Reports:** 4

---

## 📋 REPORT LIST

### 1️⃣ **Daily Cash Flow Report**
**Path:** `cash_flow_management/report/daily_cash_flow`  
**Type:** Script Report  
**Reference DocType:** Payment Entry  

**Purpose:**  
Monitor daily cash movements with running balance calculation.

**Features:**
- ✅ Running balance calculation
- ✅ Color-coded Income (Green) vs Expense (Red)
- ✅ Chart visualization (Bar chart)
- ✅ Summary cards (Total Kirim, Total Chiqim, Net Balance)
- ✅ Export to Excel

**Filters:**
- From Date (default: month start)
- To Date (default: month end)
- Payment Type (Receive/Pay)
- Mode of Payment (Naqd/Click/Terminal)
- Category (Counterparty Category)
- Cost Center
- Branch

**Columns:**
- Posting Date
- Document (Payment Entry link)
- Type (Kirim/Chiqim with badges)
- Mode of Payment
- Category
- Party
- Debit (Chiqim in USD)
- Credit (Kirim in USD)
- Balance (Running balance)
- Cost Center
- Branch
- Remarks

**Access Roles:**
- Operator
- Accounts User
- Accounts Manager
- System Manager

---

### 2️⃣ **Outstanding Installments Report**
**Path:** `cash_flow_management/report/outstanding_installments`  
**Type:** Script Report  
**Reference DocType:** Sales Order  

**Purpose:**  
Track outstanding installment amounts and overdue contracts.

**Features:**
- ✅ Outstanding amount calculation
- ✅ Next payment date tracking
- ✅ Overdue detection (days calculation)
- ✅ Status indicators (Active/Overdue/Completed)
- ✅ Pie chart (Active vs Overdue)
- ✅ Summary cards (Active Contracts, Total Outstanding, Overdue Contracts, Overdue Amount)

**Filters:**
- Customer
- From Date (default: year start)
- To Date (default: year end)
- Status (Active/Overdue/Completed)
- Cost Center

**Columns:**
- Customer (link)
- Customer Name
- Contract (Sales Order link)
- Contract Date
- Total Amount (USD)
- Paid Amount (USD)
- Outstanding Amount (USD) - highlighted in red if overdue
- Next Payment Date
- Next Payment Amount (USD)
- Days Overdue - red if > 0
- Status (badge: Active/Overdue/Completed)
- Cost Center

**Business Logic:**
- Queries Payment Schedule for next pending payment
- Calculates days overdue from due_date vs today
- Status determination:
  - `Overdue`: days_overdue > 0
  - `Active`: outstanding > 0 and not overdue
  - `Completed`: outstanding = 0

**Access Roles:**
- Operator
- Accounts User
- Accounts Manager
- System Manager

---

### 3️⃣ **Monthly Payment Schedule**
**Path:** `cash_flow_management/report/monthly_payment_schedule`  
**Type:** Script Report  
**Reference DocType:** Payment Schedule  

**Purpose:**  
View monthly payment schedule and send reminders.

**Features:**
- ✅ Monthly view (current + optional next month)
- ✅ Status tracking (Pending/Overdue/Due Today/Due This Week/Paid)
- ✅ Days to due calculation
- ✅ Phone number for reminders
- ✅ Pie chart by status
- ✅ Summary cards (Expected, Collected, Pending, Overdue)
- ✅ "Send Reminders" button (placeholder for future SMS)

**Filters:**
- Month (default: current month start)
- Include Next Month (checkbox)
- Customer
- Status (Pending/Overdue/Due Today/Due This Week/Paid)
- Cost Center

**Columns:**
- Due Date
- Customer (link)
- Customer Name
- Contract (Sales Order link)
- Payment Amount (USD)
- Paid Amount (USD)
- Outstanding (USD) - red if overdue
- Status (color-coded badges)
- Days to Due - negative if overdue, "Today" if due today
- Phone (for SMS reminders)
- Cost Center

**Status Logic:**
- `Paid`: outstanding = 0
- `Overdue`: due_date < today
- `Due Today`: due_date = today
- `Due This Week`: 0 < days_to_due <= 7
- `Pending`: days_to_due > 7

**Access Roles:**
- Operator
- Accounts User
- Accounts Manager
- System Manager

---

### 4️⃣ **Category-wise Summary**
**Path:** `cash_flow_management/report/category_wise_summary`  
**Type:** Script Report  
**Reference DocType:** Payment Entry  

**Purpose:**  
Analyze income and expense by category with percentage breakdown.

**Features:**
- ✅ Group by Counterparty Category
- ✅ Transaction count and average calculation
- ✅ Percentage of total
- ✅ Chart visualization (Pie for single type, Bar for both)
- ✅ Summary cards (Total Income, Total Expense, Net Profit/Loss, Total Transactions)
- ✅ Export details button (placeholder)

**Filters:**
- From Date (default: month start)
- To Date (default: month end)
- Category Type (Both/Income/Expense)
- Specific Category
- Cost Center
- Branch

**Columns:**
- Category (Counterparty Category link)
- Type (Income/Expense badge)
- Transaction Count
- Total Amount (USD) - green for income, red for expense
- Percentage (of total)
- Avg per Transaction (USD)
- Cost Center

**Business Logic:**
- Groups all Payment Entries by custom_counterparty_category
- Calculates percentage based on total amount
- Joins with Counterparty Category to get type
- Chart changes based on filter:
  - Single type → Pie chart (top 10 categories)
  - Both types → Bar chart (Income vs Expense side by side)

**Access Roles:**
- Operator
- Accounts User
- Accounts Manager
- System Manager

---

## 🔧 TECHNICAL DETAILS

### Database Indexes Recommended:
```sql
-- For better performance, add these indexes:
ALTER TABLE `tabPayment Entry` ADD INDEX idx_cash_flow 
  (posting_date, docstatus, mode_of_payment, custom_counterparty_category, cost_center);

ALTER TABLE `tabSales Order` ADD INDEX idx_installments 
  (docstatus, status, customer, transaction_date);

ALTER TABLE `tabPayment Schedule` ADD INDEX idx_schedule 
  (parenttype, parent, due_date, docstatus);
```

### Custom Fields Required:
These reports depend on the following custom fields:
- `Payment Entry.custom_counterparty_category` (Link: Counterparty Category)
- `Payment Entry.custom_branch` (Data or Link)
- `Payment Entry.custom_contract_reference` (Link: Sales Order)

### SQL Optimization:
- All queries use proper WHERE clauses with indexed columns
- LEFT JOIN used for optional relationships
- Result sets limited by date ranges
- Running calculations done in Python (not in SQL) for better maintainability

---

## 🎯 TESTING CHECKLIST

### Before Testing:
1. ✅ Ensure Custom Fields exist on Payment Entry
2. ✅ Create sample Counterparty Categories
3. ✅ Configure Cash Settings
4. ✅ Create sample Payment Entries
5. ✅ Create sample Sales Orders with Payment Schedules
6. ✅ Run bench migrate

### Test Scenarios:

**Daily Cash Flow:**
- [ ] Filter by date range
- [ ] Filter by Mode of Payment
- [ ] Filter by Category
- [ ] Check running balance calculation
- [ ] Verify chart displays correctly
- [ ] Export to Excel

**Outstanding Installments:**
- [ ] Check outstanding calculation accuracy
- [ ] Verify overdue detection
- [ ] Test status badges
- [ ] Filter by customer
- [ ] Check next payment retrieval

**Monthly Payment Schedule:**
- [ ] Select current month
- [ ] Include next month
- [ ] Check status determination
- [ ] Verify days to due calculation
- [ ] Test phone number retrieval
- [ ] Click "Send Reminders" button

**Category-wise Summary:**
- [ ] Filter by Income only
- [ ] Filter by Expense only
- [ ] View Both types
- [ ] Check percentage calculation
- [ ] Verify average calculation
- [ ] Test chart switching

---

## 🐛 KNOWN LIMITATIONS

1. **Phone Numbers:**
   - Pulls from Customer.mobile_no first
   - Falls back to primary Contact if not found
   - May be empty if not configured

2. **Payment Schedule:**
   - Assumes Payment Schedule is properly configured on Sales Orders
   - Does not handle manual payment schedule modifications

3. **SMS Reminders:**
   - Button exists but functionality not implemented (future phase)

4. **Performance:**
   - Large datasets (>10,000 records) may need pagination
   - Consider using Prepared Reports for production

---

## 📝 MIGRATION COMMANDS

```bash
# After creating reports, run:
cd ~/frappe-bench
bench --site site1.localhost migrate

# Clear cache
bench --site site1.localhost clear-cache

# Restart
bench restart
```

---

## 🚀 NEXT STEPS (Phase 5)

After testing these reports:
1. Print Formats (Shartnoma, Kvitansiya)
2. Validation improvements
3. Permissions finalization
4. Sample data creation
5. Production deployment

---

**Status:** ✅ **READY FOR TESTING**

All 4 reports created with:
- ✅ Zero syntax errors
- ✅ Proper ERPNext conventions
- ✅ Clean, documented code
- ✅ Comprehensive filters
- ✅ Chart visualizations
- ✅ Summary sections
- ✅ Color-coded UI
- ✅ Export capabilities
