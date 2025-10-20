// Payment Entry Client Script
// Shows Installment Application link when Customer is selected

frappe.ui.form.on('Payment Entry', {
    setup: function(frm) {
        // Filter Mode of Payment - faqat Naqd va Terminal/Click
        frm.set_query('mode_of_payment', function() {
            return {
                filters: {
                    'name': ['in', ['Naqd', 'Terminal/Click']],
                    'enabled': 1
                }
            };
        });
    },
    
    onload: function(frm) {
        // Auto-fill contract reference when form loads (for Draft payments created by Installment Application)
        if (frm.doc.party && !frm.doc.custom_contract_reference) {
            auto_fill_contract_reference(frm);
        }
        
        // Setup category filter
        setup_category_filter(frm);
    },
    
    refresh: function(frm) {
        // Hide timezone display
        setTimeout(() => {
            const timeDisplay = document.querySelector('.text-muted.small');
            if (timeDisplay && timeDisplay.textContent.includes('Asia/Samarkand')) {
                timeDisplay.style.display = 'none';
            }
        }, 500);
        
        // Lock fields for payments created by Installment Application (Draft only)
        lock_auto_created_payment_fields(frm);
        
        // Show Installment Applications link for Customer
        show_installment_applications_link(frm);
        
        // Rename fields for clarity
        rename_payment_entry_fields(frm);
        
        // Auto-fill contract if not set (for existing drafts)
        if (frm.doc.party && !frm.doc.custom_contract_reference && frm.doc.payment_type === 'Receive') {
            auto_fill_contract_reference(frm);
        }
        
        // Setup category filter
        setup_category_filter(frm);
    },
    
    payment_type: function(frm) {
        // When payment type changes, reset category and update filter
        frm.set_value('custom_counterparty_category', '');
        setup_category_filter(frm);
    },
    
    party: function(frm) {
        // When customer changes, update installment applications link and auto-fill contract
        show_installment_applications_link(frm);
        auto_fill_contract_reference(frm);
    },
    
    party_type: function(frm) {
        // When party type changes, update visibility
        show_installment_applications_link(frm);
    },
    
    custom_contract_reference: function(frm) {
        // When contract is selected, update payment schedule options
        update_payment_schedule_options(frm);
    }
});

function show_installment_applications_link(frm) {
    // Remove existing link if any
    frm.dashboard.clear_headline();
    
    if (frm.doc.party_type === 'Customer' && frm.doc.party) {
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Installment Application',
                filters: {
                    customer: frm.doc.party,
                    docstatus: 1  // Submitted only
                },
                fields: ['name', 'transaction_date', 'custom_grand_total_with_interest', 'sales_order', 'status'],
                order_by: 'creation desc',
                limit: 5
            },
            callback: function(r) {
                if (r.message && r.message.length > 0) {
                    let apps = r.message;
                    
                    // Create headline with links
                    let html = `<div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">`;
                    html += `<h6 style="margin: 0 0 10px 0; color: #333;">📋 ${frm.doc.party} - Installment Applications (${apps.length})</h6>`;
                    
                    apps.forEach((app, idx) => {
                        let status_color = app.status === 'Completed' ? 'green' : 
                                         app.status === 'Active' ? 'orange' : 'gray';
                        
                        html += `<div style="margin-bottom: 5px;">`;
                        html += `<a href="/app/installment-application/${app.name}" target="_blank" style="font-weight: 500;">${app.name}</a> `;
                        html += `<span style="color: ${status_color}; font-size: 11px;">● ${app.status}</span> `;
                        html += `<span style="color: #666; font-size: 12px;">| $${app.custom_grand_total_with_interest}</span> `;
                        
                        if (app.sales_order) {
                            html += `<span style="color: #888; font-size: 11px;">→</span> `;
                            html += `<a href="/app/sales-order/${app.sales_order}" target="_blank" style="font-size: 11px;">${app.sales_order}</a>`;
                        }
                        
                        html += `</div>`;
                    });
                    
                    html += `</div>`;
                    
                    frm.dashboard.set_headline(html);
                } else {
                    // No installment applications found
                    frm.dashboard.set_headline(`
                        <div style="padding: 8px; background: #fff3cd; border-radius: 5px; color: #856404;">
                            ℹ️ <strong>${frm.doc.party}</strong> uchun Installment Application topilmadi
                        </div>
                    `);
                }
            }
        });
    }
}

function rename_payment_entry_fields(frm) {
    // Rename fields with Uzbek/emoji for clarity
    if (frm.fields_dict.paid_amount) {
        frm.set_df_property('paid_amount', 'label', '💵 To\'lov Summasi (USD)');
    }
    
    if (frm.fields_dict.received_amount) {
        frm.set_df_property('received_amount', 'label', '✅ Qabul Qilingan (USD)');
    }
    
    if (frm.fields_dict.mode_of_payment) {
        frm.set_df_property('mode_of_payment', 'label', '💳 To\'lov Turi');
    }
    
    if (frm.fields_dict.custom_counterparty_category) {
        frm.set_df_property('custom_counterparty_category', 'label', '📂 Kategoriya');
    }
    
    if (frm.fields_dict.custom_contract_reference) {
        frm.set_df_property('custom_contract_reference', 'label', '📄 Shartnoma Raqami');
    }
}

// Auto-fill contract reference when customer is selected
function auto_fill_contract_reference(frm) {
    // Only for Receive type and Customer party type
    if (frm.doc.payment_type !== 'Receive' || frm.doc.party_type !== 'Customer' || !frm.doc.party) {
        return;
    }
    
    // Don't override if already set
    if (frm.doc.custom_contract_reference) {
        return;
    }
    
    // Prevent infinite loop - check if we're already processing
    if (frm._filling_contract_reference) {
        return;
    }
    
    frm._filling_contract_reference = true;
    
    // Get latest active Sales Order for this customer
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Sales Order',
            filters: {
                customer: frm.doc.party,
                docstatus: 1,  // Submitted
                status: ['not in', ['Completed', 'Cancelled', 'Closed']]
            },
            fields: ['name', 'transaction_date', 'custom_grand_total_with_interest', 'advance_paid'],
            order_by: 'transaction_date desc',
            limit: 1
        },
        callback: function(r) {
            frm._filling_contract_reference = false;
            
            if (r.message && r.message.length > 0) {
                let contract = r.message[0];
                
                // Just set the value, DON'T auto-save (user will save manually)
                frm.set_value('custom_contract_reference', contract.name);
                
                // Update payment schedule options
                update_payment_schedule_options(frm);
                
                // Show message
                frappe.show_alert({
                    message: `📄 Shartnoma avtomatik tanlandi: ${contract.name}`,
                    indicator: 'green'
                }, 5);
            }
        }
    });
}

// Update payment schedule dropdown when contract is selected
function update_payment_schedule_options(frm) {
    if (!frm.doc.custom_contract_reference) {
        return;
    }
    
    // Get unpaid payment schedules for this contract
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Payment Schedule',
            filters: {
                parent: frm.doc.custom_contract_reference,
                parenttype: 'Sales Order'
            },
            fields: ['name', 'idx', 'due_date', 'payment_amount', 'paid_amount', 'description'],
            order_by: 'idx asc'
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let unpaid_schedules = r.message.filter(schedule => {
                    let paid = parseFloat(schedule.paid_amount) || 0;
                    let amount = parseFloat(schedule.payment_amount) || 0;
                    return paid < amount;  // Not fully paid
                });
                
                if (unpaid_schedules.length > 0) {
                    // Show info about next unpaid schedule
                    let next = unpaid_schedules[0];
                    let outstanding = parseFloat(next.payment_amount) - (parseFloat(next.paid_amount) || 0);
                    
                    frappe.show_alert({
                        message: `📅 Keyingi to'lov: ${next.description || next.idx + '-oy'} - $${outstanding.toFixed(2)}`,
                        indicator: 'blue'
                    }, 7);
                    
                    // Auto-select first unpaid schedule
                    frm.set_value('custom_payment_schedule_row', next.name);
                    frm.set_value('custom_payment_month', next.description || (next.idx + '-oy'));
                }
            }
        }
    });
}

// Setup Counterparty Category filter based on Payment Type
function setup_category_filter(frm) {
    if (!frm.fields_dict.custom_counterparty_category) {
        return;
    }
    
    // Determine category type based on payment type
    let category_type = null;
    if (frm.doc.payment_type === 'Receive') {
        category_type = 'Income';  // Kirim uchun - Income categories
    } else if (frm.doc.payment_type === 'Pay') {
        category_type = 'Expense';  // Chiqim uchun - Expense categories
    }
    
    if (category_type) {
        frm.set_query('custom_counterparty_category', function() {
            return {
                filters: {
                    'category_type': category_type,
                    'is_active': 1
                }
            };
        });
        
        // Show helpful message
        let label_emoji = category_type === 'Income' ? '📥' : '📤';
        frm.set_df_property('custom_counterparty_category', 'label', `${label_emoji} Kategoriya (${category_type})`);
    } else {
        // No filter if payment type not set
        frm.set_query('custom_counterparty_category', function() {
            return {
                filters: {
                    'is_active': 1
                }
            };
        });
        frm.set_df_property('custom_counterparty_category', 'label', '📂 Kategoriya');
    }
}

// Lock fields for auto-created payments (from Installment Application)
function lock_auto_created_payment_fields(frm) {
    // Only lock if:
    // 1. Payment is Draft (docstatus = 0)
    // 2. Created from Installment Application (has custom_contract_reference)
    // 3. Has remarks containing "Boshlang'ich to'lov"
    
    if (frm.doc.docstatus === 0 && 
        frm.doc.custom_contract_reference && 
        frm.doc.remarks && 
        frm.doc.remarks.includes("Boshlang'ich to'lov")) {
        
        // Lock all fields EXCEPT mode_of_payment
        const editable_fields = ['mode_of_payment'];
        
        // Get all fields
        frm.fields.forEach(field => {
            if (!editable_fields.includes(field.df.fieldname)) {
                frm.set_df_property(field.df.fieldname, 'read_only', 1);
            }
        });
        
        // Show message
        frm.dashboard.add_comment(`
            <div style="background: #FFF3CD; padding: 10px; border-radius: 5px; border-left: 4px solid #FFC107;">
                <strong>ℹ️ Installment Application dan yaratilgan to'lov</strong><br>
                Faqat <strong>Mode of Payment</strong> ni o'zgartira olasiz.<br>
                To'lov tasdiqlanishi uchun <strong>Submit</strong> tugmasini bosing.
            </div>
        `, 0);
    }
}
