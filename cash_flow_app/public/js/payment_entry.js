// Payment Entry Client Script
// Shows Installment Application link when Customer is selected

frappe.ui.form.on('Payment Entry', {
    onload: function(frm) {
        // Auto-fill contract reference when form loads (for Draft payments created by Installment Application)
        if (frm.doc.party && !frm.doc.custom_contract_reference) {
            auto_fill_contract_reference(frm);
        }
    },
    
    refresh: function(frm) {
        // Hide timezone display
        setTimeout(() => {
            const timeDisplay = document.querySelector('.text-muted.small');
            if (timeDisplay && timeDisplay.textContent.includes('Asia/Samarkand')) {
                timeDisplay.style.display = 'none';
            }
        }, 500);
        
        // Show Installment Applications link for Customer
        show_installment_applications_link(frm);
        
        // Rename fields for clarity
        rename_payment_entry_fields(frm);
        
        // Auto-fill contract if not set (for existing drafts)
        if (frm.doc.party && !frm.doc.custom_contract_reference && frm.doc.payment_type === 'Receive') {
            auto_fill_contract_reference(frm);
        }
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
            if (r.message && r.message.length > 0) {
                let contract = r.message[0];
                
                // Auto-fill contract reference and save
                frm.set_value('custom_contract_reference', contract.name).then(() => {
                    // After setting contract, update payment schedule
                    update_payment_schedule_options(frm);
                    
                    // Auto-save if draft
                    if (!frm.doc.__islocal && frm.doc.docstatus === 0) {
                        frm.save().then(() => {
                            frappe.show_alert({
                                message: `✅ Shartnoma avtomatik tanlandi va saqlandi: ${contract.name}`,
                                indicator: 'green'
                            }, 5);
                        });
                    } else {
                        // Show message without saving
                        frappe.show_alert({
                            message: `📄 Shartnoma avtomatik tanlandi: ${contract.name}`,
                            indicator: 'green'
                        }, 5);
                    }
                });
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
