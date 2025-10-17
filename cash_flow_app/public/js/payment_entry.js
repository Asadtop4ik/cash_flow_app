// Payment Entry Client Script
// Shows Installment Application link when Customer is selected

frappe.ui.form.on('Payment Entry', {
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
    },
    
    party: function(frm) {
        // When customer changes, update installment applications link
        show_installment_applications_link(frm);
    },
    
    party_type: function(frm) {
        // When party type changes, update visibility
        show_installment_applications_link(frm);
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
