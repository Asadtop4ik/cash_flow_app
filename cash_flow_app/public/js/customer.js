// Customer Form - Contract & Payment History
// Shows customer's contracts and payment history with beautiful UI

frappe.ui.form.on('Customer', {
    refresh: function(frm) {
        if (frm.doc.__islocal) {
            return; // Skip for new records
        }
        
        // Load latest contract data
        load_customer_contract_summary(frm);
        
        // Add action buttons
        add_customer_action_buttons(frm);
    }
});

function load_customer_contract_summary(frm) {
    frappe.call({
        method: 'cash_flow_app.cash_flow_management.api.customer_history.get_customer_contracts',
        args: {
            customer: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                // Show ALL contracts, not just the latest
                show_all_contracts_dashboard(frm, r.message);
                
                // Show payment schedule for the ACTIVE contract only
                const active_contract = r.message.find(c => 
                    c.custom_status !== 'Completed' && c.custom_status !== 'Cancelled'
                ) || r.message[0];
                
                show_payment_schedule(frm, active_contract);
            } else {
                show_no_contract_message(frm);
            }
        }
    });
}

function show_all_contracts_dashboard(frm, contracts) {
    // Remove existing dashboard
    $('.customer-contract-dashboard').remove();
    
    // Create contracts list HTML
    let contracts_html = '';
    
    contracts.forEach((contract, index) => {
        const total_with_interest = contract.grand_total_with_interest || 0;
        const paid_amount = contract.paid_amount || 0;
        const outstanding_amount = contract.outstanding_amount || 0;
        const payment_percentage = contract.payment_percentage || 0;
        const status = contract.custom_status || 'Pending';
        const status_color = contract.status_color || 'orange';
        const status_icon = contract.status_icon || '⏳';
        const is_active = status !== 'Completed' && status !== 'Cancelled';
        
        // Color mapping
        let status_color_hex = '#FF9800';
        let gradient_start = '#667eea';
        let gradient_end = '#764ba2';
        
        if (status_color === 'green') {
            status_color_hex = '#4CAF50';
            gradient_start = '#56ab2f';
            gradient_end = '#a8e063';
        } else if (status_color === 'blue') {
            status_color_hex = '#2196F3';
            gradient_start = '#2196F3';
            gradient_end = '#64b5f6';
        } else if (status_color === 'red') {
            status_color_hex = '#d32f2f';
            gradient_start = '#c33764';
            gradient_end = '#f8c291';
        } else if (is_active) {
            gradient_start = '#667eea';
            gradient_end = '#764ba2';
        }
        
        contracts_html += `
            <div style="
                background: linear-gradient(135deg, ${gradient_start} 0%, ${gradient_end} 100%);
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 15px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                color: white;
                ${is_active ? 'border: 3px solid #FFD700;' : ''}
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="margin: 0; color: white; font-size: 18px;">
                        ${status_icon} ${status}
                        ${is_active ? '<span style="background: #FFD700; color: #000; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin-left: 10px;">ACTIVE</span>' : ''}
                    </h3>
                    <a href="/app/sales-order/${contract.name}" target="_blank" 
                       style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px; color: white; text-decoration: none; font-size: 14px;">
                        <strong>📄 ${contract.name}</strong>
                    </a>
                </div>
                
                <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0;">
                    <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 11px; opacity: 0.9; margin-bottom: 8px;">💰 Jami Summa</div>
                        <div style="font-size: 20px; font-weight: bold;">
                            $ ${total_with_interest.toLocaleString('en-US', {minimumFractionDigits: 2})}
                        </div>
                    </div>
                    <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 11px; opacity: 0.9; margin-bottom: 8px;">✅ To'langan</div>
                        <div style="font-size: 20px; font-weight: bold; color: #90EE90;">
                            $ ${paid_amount.toLocaleString('en-US', {minimumFractionDigits: 2})}
                        </div>
                    </div>
                    <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 11px; opacity: 0.9; margin-bottom: 8px;">⚠️ Qolgan</div>
                        <div style="font-size: 20px; font-weight: bold; color: ${outstanding_amount > 0 ? '#FFB6C1' : '#90EE90'};">
                            $ ${outstanding_amount.toLocaleString('en-US', {minimumFractionDigits: 2})}
                        </div>
                    </div>
                </div>
                
                <!-- Progress Bar -->
                <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <span style="font-size: 12px; font-weight: 500;">📊 To'lov progress</span>
                        <span style="font-size: 13px; font-weight: bold;">
                            ${payment_percentage.toFixed(1)}%
                        </span>
                    </div>
                    <div style="background: rgba(0,0,0,0.2); height: 20px; border-radius: 10px; overflow: hidden;">
                        <div style="
                            background: linear-gradient(90deg, #4ade80, #22c55e);
                            width: ${payment_percentage}%;
                            height: 100%;
                            transition: width 0.5s ease;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 10px;
                            font-weight: bold;
                            color: white;
                        ">${payment_percentage > 8 ? payment_percentage.toFixed(0) + '%' : ''}</div>
                    </div>
                </div>
                
                <!-- Contract Details -->
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2);">
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 11px;">
                        <div>
                            <div style="opacity: 0.8;">📅 Sana</div>
                            <div style="font-weight: 500; margin-top: 3px;">${frappe.datetime.str_to_user(contract.transaction_date)}</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8;">📆 Nechi oy</div>
                            <div style="font-weight: 500; margin-top: 3px;">${contract.installment_months || 0} oy</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8;">💵 Oylik</div>
                            <div style="font-weight: 500; margin-top: 3px;">$ ${(contract.monthly_payment || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                        </div>
                        <div>
                            <div style="opacity: 0.8;">🎯 Boshlang'ich</div>
                            <div style="font-weight: 500; margin-top: 3px;">$ ${(contract.downpayment || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    // Wrap all contracts
    const dashboard_html = `
        <div style="margin: 15px 0;">
            <h2 style="color: #667eea; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
                <span>📋</span>
                <span>Shartnomalar (${contracts.length})</span>
            </h2>
            ${contracts_html}
        </div>
    `;
    
    // Create permanent wrapper div
    let wrapper = $(`<div class="customer-contract-dashboard"></div>`);
    wrapper.html(dashboard_html);
    
    // Insert after form toolbar
    if (frm.dashboard.wrapper) {
        $(frm.dashboard.wrapper).after(wrapper);
    } else if (frm.$wrapper.find('.form-dashboard').length) {
        frm.$wrapper.find('.form-dashboard').after(wrapper);
    } else {
        frm.$wrapper.find('.page-head').after(wrapper);
    }
}

function show_customer_dashboard(frm, contract) {
    // Remove existing dashboard
    $('.customer-contract-dashboard').remove();
    
    const total_with_interest = contract.grand_total_with_interest || 0;
    const paid_amount = contract.paid_amount || 0;
    const outstanding_amount = contract.outstanding_amount || 0;
    const payment_percentage = contract.payment_percentage || 0;
    const status = contract.custom_status || 'Pending';
    const status_color = contract.status_color || 'orange';
    const status_icon = contract.status_icon || '⏳';
    
    // Color mapping for status
    let status_color_hex = '#FF9800';
    if (status_color === 'green') status_color_hex = '#4CAF50';
    else if (status_color === 'blue') status_color_hex = '#2196F3';
    else if (status_color === 'red') status_color_hex = '#d32f2f';
    
    // Create dashboard HTML
    const dashboard_html = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 12px; margin: 15px 0; box-shadow: 0 4px 6px rgba(0,0,0,0.1); color: white;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <h3 style="margin: 0; color: white; font-size: 20px;">
                    ${status_icon} ${status}
                </h3>
                <div style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px;">
                    <strong style="font-size: 14px;">Shartnoma: ${contract.name}</strong>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0;">
                <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9; margin-bottom: 8px;">💰 Jami Summa</div>
                    <div style="font-size: 24px; font-weight: bold;">
                        $ ${total_with_interest.toLocaleString('en-US', {minimumFractionDigits: 2})}
                    </div>
                </div>
                <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9; margin-bottom: 8px;">✅ To'langan</div>
                    <div style="font-size: 24px; font-weight: bold; color: #90EE90;">
                        $ ${paid_amount.toLocaleString('en-US', {minimumFractionDigits: 2})}
                    </div>
                </div>
                <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; text-align: center;">
                    <div style="font-size: 12px; opacity: 0.9; margin-bottom: 8px;">⚠️ Qolgan</div>
                    <div style="font-size: 24px; font-weight: bold; color: ${outstanding_amount > 0 ? '#FFB6C1' : '#90EE90'};">
                        $ ${outstanding_amount.toLocaleString('en-US', {minimumFractionDigits: 2})}
                    </div>
                </div>
            </div>
            
            <!-- Progress Bar -->
            <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-size: 13px; font-weight: 500;">📊 To'lov progress</span>
                    <span style="font-size: 14px; font-weight: bold;">
                        ${payment_percentage.toFixed(1)}%
                    </span>
                </div>
                <div style="background: rgba(0,0,0,0.2); height: 24px; border-radius: 12px; overflow: hidden;">
                    <div style="
                        background: linear-gradient(90deg, #4ade80, #22c55e);
                        width: ${payment_percentage}%;
                        height: 100%;
                        transition: width 0.5s ease;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 11px;
                        font-weight: bold;
                        color: white;
                    ">${payment_percentage > 5 ? payment_percentage.toFixed(0) + '%' : ''}</div>
                </div>
            </div>
            
            <!-- Contract Details -->
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2);">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 12px;">
                    <div>
                        <div style="opacity: 0.8;">📅 Sana</div>
                        <div style="font-weight: 500; margin-top: 3px;">${frappe.datetime.str_to_user(contract.transaction_date)}</div>
                    </div>
                    <div>
                        <div style="opacity: 0.8;">📆 Nechi oy</div>
                        <div style="font-weight: 500; margin-top: 3px;">${contract.installment_months || 0} oy</div>
                    </div>
                    <div>
                        <div style="opacity: 0.8;">💵 Oylik</div>
                        <div style="font-weight: 500; margin-top: 3px;">$ ${(contract.monthly_payment || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                    </div>
                    <div>
                        <div style="opacity: 0.8;">🎯 Boshlang'ich to'lov</div>
                        <div style="font-weight: 500; margin-top: 3px;">$ ${(contract.downpayment || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Create permanent wrapper div
    let wrapper = $(`<div class="customer-contract-dashboard" style="margin: 15px 0;"></div>`);
    wrapper.html(dashboard_html);
    
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

function show_payment_schedule(frm, contract) {
    // Remove existing schedule table
    $('.customer-payment-schedule').remove();
    
    frappe.call({
        method: 'cash_flow_app.cash_flow_management.api.customer_history.get_payment_schedule_with_history',
        args: {
            customer: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                const schedule_html = `
                    <div style="background: white; padding: 20px; border-radius: 8px; margin: 15px 0; border: 1px solid #e5e7eb;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <h4 style="margin: 0; color: #1f2937;">
                                📅 Oylik To'lovlar Jadvali - <span style="color: #2563eb;">REAL-TIME</span>
                            </h4>
                            <button class="btn btn-sm btn-primary" onclick="frappe.set_route('List', 'Payment Entry', {party: '${frm.doc.name}'})">
                                📜 Barcha To'lovlar
                            </button>
                        </div>
                        
                        <div style="overflow-x: auto;">
                            <table class="table table-bordered table-hover" style="margin: 0;">
                                <thead style="background: #f9fafb;">
                                    <tr>
                                        <th style="width: 8%; text-align: center;">Oy</th>
                                        <th style="width: 12%;">Muddat</th>
                                        <th style="width: 12%; text-align: right;">Summa</th>
                                        <th style="width: 12%; text-align: right;">To'landi</th>
                                        <th style="width: 12%; text-align: right;">Qoldi</th>
                                        <th style="width: 12%;">To'lov sanasi</th>
                                        <th style="width: 32%;">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                let rows_html = '';
                r.message.forEach((row) => {
                    const paid = parseFloat(row.paid_amount) || 0;
                    const payment_amount = parseFloat(row.payment_amount) || 0;
                    const outstanding = parseFloat(row.outstanding) || 0;
                    const month_desc = row.description || `${row.payment_number}-oy`;
                    
                    let payment_date_html = '-';
                    if (row.payment_date && row.payment_name) {
                        payment_date_html = `<a href="/app/payment-entry/${row.payment_name}" target="_blank" style="color: #2563eb; font-weight: 500;">
                            ${frappe.datetime.str_to_user(row.payment_date)}
                        </a>`;
                    } else if (row.payment_date) {
                        payment_date_html = frappe.datetime.str_to_user(row.payment_date);
                    }
                    
                    // Row background based on status
                    let row_bg = '';
                    if (row.status_color === 'green') row_bg = 'background: #f0fdf4;';
                    else if (row.status_color === 'red') row_bg = 'background: #fef2f2;';
                    else if (row.status_color === 'orange') row_bg = 'background: #fff7ed;';
                    else if (row.status_color === 'blue') row_bg = 'background: #eff6ff;';
                    
                    rows_html += `
                        <tr style="${row_bg}">
                            <td style="text-align: center; font-weight: bold; font-size: 14px;">${month_desc}</td>
                            <td style="font-weight: 500;">${frappe.datetime.str_to_user(row.due_date)}</td>
                            <td style="text-align: right; font-weight: 600;">$${payment_amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                            <td style="text-align: right; color: ${paid > 0 ? '#16a34a' : '#9ca3af'}; font-weight: 600;">
                                $${paid.toLocaleString('en-US', {minimumFractionDigits: 2})}
                            </td>
                            <td style="text-align: right; color: ${outstanding > 0 ? '#dc2626' : '#16a34a'}; font-weight: 600;">
                                $${outstanding.toLocaleString('en-US', {minimumFractionDigits: 2})}
                            </td>
                            <td>${payment_date_html}</td>
                            <td>
                                <span style="color: ${row.status_color === 'green' ? '#16a34a' : row.status_color === 'red' ? '#dc2626' : row.status_color === 'orange' ? '#ea580c' : '#2563eb'}; font-weight: 500;">
                                    ${row.status}
                                </span>
                            </td>
                        </tr>
                    `;
                });
                
                const final_html = schedule_html + rows_html + `
                                </tbody>
                            </table>
                        </div>
                        
                        <div style="margin-top: 15px; padding: 12px; background: #eff6ff; border-left: 4px solid #2563eb; border-radius: 4px;">
                            <div style="color: #1e40af; font-weight: 600; margin-bottom: 5px;">
                                🔄 Real-Time Tracking
                            </div>
                            <div style="color: #1e3a8a; font-size: 13px;">
                                Bu jadval har safar Payment Entry submit qilinganda avtomatik yangilanadi!
                                <br>
                                <span style="margin-top: 5px; display: inline-block;">
                                    ✅ To'langan | 🟡 Qisman | ⏳ Kutilmoqda | ❌ Muddati o'tgan
                                </span>
                            </div>
                        </div>
                    </div>
                `;
                
                // Create permanent wrapper
                let wrapper = $(`<div class="customer-payment-schedule" style="margin: 15px 0;"></div>`);
                wrapper.html(final_html);
                
                // Insert after dashboard or form content
                if ($('.customer-contract-dashboard').length) {
                    $('.customer-contract-dashboard').after(wrapper);
                } else if (frm.dashboard.wrapper) {
                    $(frm.dashboard.wrapper).after(wrapper);
                } else {
                    frm.$wrapper.find('.form-layout').before(wrapper);
                }
            }
        }
    });
}

function add_customer_action_buttons(frm) {
    // Add "📊 To'liq Hisobot" button - NEW REPORT
    frm.add_custom_button(__('📊 To\'liq Hisobot'), function() {
        frappe.set_route("query-report", "Customer Payment History", {
            "customer": frm.doc.name
        });
    }, __('Reports'));
    
    // Add "To'lov Tarixi" button
    frm.add_custom_button(__('To\'lov Tarixi'), function() {
        frappe.route_options = {
            "party_type": "Customer",
            "party": frm.doc.name,
            "payment_type": "Receive",
            "docstatus": 1
        };
        frappe.set_route("List", "Payment Entry");
    }, __('View'));
    
    // Add "Sales Orders" button
    frm.add_custom_button(__('Shartnomalar'), function() {
        frappe.route_options = {
            "customer": frm.doc.name,
            "docstatus": 1
        };
        frappe.set_route("List", "Sales Order");
    }, __('View'));
}

function show_no_contract_message(frm) {
    // Remove existing message
    $('.customer-no-contract-message').remove();
    
    const message_html = `
        <div style="background: #f9fafb; padding: 40px; border-radius: 8px; margin: 15px 0; text-align: center; border: 2px dashed #d1d5db;">
            <div style="font-size: 48px; margin-bottom: 15px;">📋</div>
            <h4 style="color: #6b7280; margin-bottom: 10px;">Hozircha shartnoma yo'q</h4>
            <p style="color: #9ca3af; font-size: 14px;">Mijoz uchun yangi Installment Application yarating</p>
        </div>
    `;
    
    // Create permanent wrapper
    let wrapper = $(`<div class="customer-no-contract-message"></div>`);
    wrapper.html(message_html);
    
    // Insert after form toolbar
    if (frm.dashboard.wrapper) {
        $(frm.dashboard.wrapper).after(wrapper);
    } else {
        frm.$wrapper.find('.page-head').after(wrapper);
    }
}