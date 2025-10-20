// Supplier Client Script
// Shows debt history and payment tracking

frappe.ui.form.on('Supplier', {
    refresh: function(frm) {
        // Add custom buttons and sections
        if (!frm.is_new()) {
            // Show debt summary
            show_debt_summary(frm);
            
            // Add "📦 Qarzlar Tahlili" button - NEW REPORT
            frm.add_custom_button(__('📦 Qarzlar Tahlili'), function() {
                frappe.set_route("query-report", "Supplier Debt Analysis", {
                    "supplier": frm.doc.name
                });
            }, __('Reports'));
            
            // Add button to view payment history
            frm.add_custom_button(__('To\'lov Tarixi'), function() {
                show_payment_history(frm);
            }, __('View'));
            
            // Add button to view installment applications
            frm.add_custom_button(__('Shartnomalar (Contracts)'), function() {
                show_supplier_contracts(frm);
            }, __('View'));
        }
        
        // Update debt fields styling
        style_debt_fields(frm);
    }
});

function show_debt_summary(frm) {
    // Remove existing dashboard
    $('.supplier-debt-dashboard').remove();
    
    const total_debt = frm.doc.custom_total_debt || 0;
    const paid_amount = frm.doc.custom_paid_amount || 0;
    const remaining_debt = frm.doc.custom_remaining_debt || 0;
    const status = frm.doc.custom_payment_status || "Qarzda";
    
    // Status icon
    let status_icon = '⚠️';
    let status_color = '#FF9800';
    
    if (status === 'To\'landi') {
        status_icon = '✅';
        status_color = '#4CAF50';
    } else if (status === 'Qisman to\'langan') {
        status_icon = '🔵';
        status_color = '#2196F3';
    }
    
    // Calculate payment percentage
    const payment_percentage = total_debt > 0 ? (paid_amount / total_debt * 100) : 0;
    
    // Create summary HTML
    const summary_html = `
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid ${status_color};">
            <h4 style="margin-top: 0; color: ${status_color};">
                ${status_icon} ${status}
            </h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin-top: 10px;">
                <div>
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Jami Qarz</div>
                    <div style="font-size: 20px; font-weight: bold; color: #d32f2f;">
                        $ ${total_debt.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                    </div>
                </div>
                <div>
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">To'langan</div>
                    <div style="font-size: 20px; font-weight: bold; color: #388e3c;">
                        $ ${paid_amount.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                    </div>
                </div>
                <div>
                    <div style="font-size: 12px; color: #666; margin-bottom: 5px;">Qolgan Qarz</div>
                    <div style="font-size: 20px; font-weight: bold; color: ${remaining_debt > 0 ? '#d32f2f' : '#388e3c'};">
                        $ ${remaining_debt.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                    </div>
                </div>
            </div>
            
            <!-- Progress Bar -->
            <div style="margin-top: 15px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="font-size: 12px; color: #666;">To'lov progress</span>
                    <span style="font-size: 12px; font-weight: bold; color: ${status_color};">
                        ${payment_percentage.toFixed(1)}%
                    </span>
                </div>
                <div style="background: #e0e0e0; height: 20px; border-radius: 10px; overflow: hidden;">
                    <div style="
                        background: linear-gradient(90deg, ${status_color}, ${status_color}dd);
                        width: ${payment_percentage}%;
                        height: 100%;
                        transition: width 0.3s ease;
                    "></div>
                </div>
            </div>
        </div>
    `;
    
    // Create permanent wrapper div
    let wrapper = $(`<div class="supplier-debt-dashboard" style="margin: 15px 0;"></div>`);
    wrapper.html(summary_html);
    
    // Insert after form toolbar (before tabs)
    if (frm.dashboard.wrapper) {
        $(frm.dashboard.wrapper).after(wrapper);
    } else if (frm.$wrapper.find('.form-dashboard').length) {
        frm.$wrapper.find('.form-dashboard').after(wrapper);
    } else {
        // Fallback: insert after page title
        frm.$wrapper.find('.page-head').after(wrapper);
    }
}

function show_payment_history(frm) {
    // Show Payment Entry list for this supplier
    frappe.route_options = {
        "party_type": "Supplier",
        "party": frm.doc.name,
        "payment_type": "Pay",
        "docstatus": 1
    };
    frappe.set_route("List", "Payment Entry");
}

function show_supplier_contracts(frm) {
    // Show Installment Applications that have items from this supplier
    frappe.call({
        method: 'cash_flow_app.cash_flow_management.api.supplier_history.get_supplier_contracts',
        args: {
            supplier: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                const contracts_html = `
                    <div style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-bordered" style="margin-top: 10px;">
                            <thead>
                                <tr>
                                    <th>Shartnoma</th>
                                    <th>Mijoz</th>
                                    <th>Mahsulotlar</th>
                                    <th>Summa (USD)</th>
                                    <th>Sana</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${r.message.map(contract => `
                                    <tr>
                                        <td>
                                            <a href="/app/installment-application/${contract.name}">
                                                ${contract.name}
                                            </a>
                                        </td>
                                        <td>${contract.customer_name || contract.customer}</td>
                                        <td>${contract.items_count} ta mahsulot</td>
                                        <td style="font-weight: bold;">
                                            $ ${contract.supplier_amount.toLocaleString('en-US', {minimumFractionDigits: 2})}
                                        </td>
                                        <td>${frappe.datetime.str_to_user(contract.transaction_date)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                `;
                
                frappe.msgprint({
                    title: __('Shartnomalar - ') + frm.doc.supplier_name,
                    message: contracts_html,
                    wide: true
                });
            } else {
                frappe.msgprint(__('Hozircha shartnoma yo\'q'));
            }
        }
    });
}

function style_debt_fields(frm) {
    // Add color coding to debt fields
    if (frm.fields_dict.custom_remaining_debt) {
        const remaining = frm.doc.custom_remaining_debt || 0;
        if (remaining > 0) {
            frm.fields_dict.custom_remaining_debt.$wrapper.find('.control-value').css('color', '#d32f2f');
        } else {
            frm.fields_dict.custom_remaining_debt.$wrapper.find('.control-value').css('color', '#388e3c');
        }
    }
}
