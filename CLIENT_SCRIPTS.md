# Cash Flow App Client Scripts

## Payment Entry Auto-expand Accounts Section

This client script automatically expands the Accounts section when Payment Type is "Pay" (Kassa Chiqim).

### Location
Setup → Customize Form → Payment Entry → Client Script

### Script Name
`auto_expand_accounts_for_pay`

### Script Type
Form

### Code:

```javascript
frappe.ui.form.on('Payment Entry', {
    refresh: function(frm) {
        // Auto-expand Accounts section for better UX
        if (frm.doc.payment_type === 'Pay') {
            frm.set_df_property('accounts', 'collapsible', 0);
        }
    },
    
    payment_type: function(frm) {
        // When payment type changes to Pay, expand accounts
        if (frm.doc.payment_type === 'Pay') {
            frm.set_df_property('accounts', 'collapsible', 0);
            
            // Set default mode of payment if not set
            if (!frm.doc.mode_of_payment) {
                frm.set_value('mode_of_payment', 'Naqd');
            }
        }
    }
});
```

### How to Add:

1. Go to: **Setup → Customize Form**
2. Select **Payment Entry**
3. Scroll to **Client Script** section
4. Click **Add Row**
5. Fill:
   - **Script Name:** `auto_expand_accounts_for_pay`
   - **Enabled:** ✅
   - **Script:** (paste the JavaScript code above)
6. **Save**

---

## Alternative: Quick Entry Form

For faster data entry, you can also create a custom button that opens a simplified dialog.

### Code:

```javascript
frappe.ui.form.on('Payment Entry', {
    onload: function(frm) {
        // Add custom quick entry button for Kassa Chiqim
        if (frm.is_new() && frm.doc.payment_type === 'Pay') {
            frm.add_custom_button(__('Tezkor Kiritish'), function() {
                let d = new frappe.ui.Dialog({
                    title: 'Kassa Chiqim - Tezkor Kiritish',
                    fields: [
                        {
                            label: 'Summa',
                            fieldname: 'amount',
                            fieldtype: 'Currency',
                            reqd: 1
                        },
                        {
                            label: 'Kategoriya',
                            fieldname: 'category',
                            fieldtype: 'Link',
                            options: 'Counterparty Category',
                            reqd: 1,
                            get_query: function() {
                                return {
                                    filters: {
                                        'category_type': 'Expense'
                                    }
                                };
                            }
                        },
                        {
                            label: 'Izoh',
                            fieldname: 'remarks',
                            fieldtype: 'Small Text'
                        }
                    ],
                    primary_action_label: 'Yaratish',
                    primary_action(values) {
                        frm.set_value('paid_amount', values.amount);
                        frm.set_value('received_amount', values.amount);
                        frm.set_value('custom_counterparty_category', values.category);
                        frm.set_value('remarks', values.remarks);
                        d.hide();
                    }
                });
                d.show();
            });
        }
    }
});
```

---

## Notes

- These scripts are optional enhancements
- The basic functionality works without them
- They improve user experience for faster data entry
- Can be added via Customize Form or Custom Script DocType
