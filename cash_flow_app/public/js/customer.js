// Customer Form - Contract & Payment History
// Shows customer's contracts and payment history

frappe.ui.form.on('Customer', {
    refresh: function(frm) {
        if (frm.doc.__islocal) {
            return; // Skip for new records
        }
        
        // Add custom section for history
        show_customer_history(frm);
    }
});

function show_customer_history(frm) {
    // Remove existing section if any
    $('.customer-history-section').remove();
    
    // Create wrapper after form layout
    let wrapper = $('<div class="customer-history-section" style="margin: 20px 0;"></div>');
    
    // Insert after form layout (before comments/activity)
    if (frm.$wrapper.find('.form-layout').length) {
        frm.$wrapper.find('.form-layout').after(wrapper);
    } else {
        // Fallback: insert at end of form container
        frm.$wrapper.find('.form-container').append(wrapper);
    }
    
    // Load contract history
    load_contract_history(frm, wrapper);
    
    // Load payment history
    load_payment_history(frm, wrapper);
}

function load_contract_history(frm, wrapper) {
    frappe.call({
        method: 'cash_flow_app.cash_flow_management.api.customer_history.get_customer_contracts',
        args: {
            customer: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let html = `
                    <div class="form-section card-section visible-section" style="margin-bottom: 20px;">
                        <div class="section-head">
                            <span class="indicator blue">📋</span>
                            <span class="section-title">1-qism (tepada): Shartnoma umumiy ma'lumotlari</span>
                        </div>
                        <div class="section-body" style="padding: 15px;">
                            <table class="table table-bordered" style="margin-bottom: 0;">
                                <tbody>
                `;
                
                let contract = r.message[0]; // Latest contract
                
                html += `
                    <tr>
                        <td style="width: 40%; font-weight: 500;">Mijoz ismi</td>
                        <td>${contract.customer_name || '-'}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 500;">Shartnoma raqami</td>
                        <td><a href="/app/sales-order/${contract.name}">${contract.name}</a></td>
                    </tr>
                    <tr>
                        <td style="font-weight: 500;">Sana</td>
                        <td>${frappe.datetime.str_to_user(contract.transaction_date)}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 500;">Umumiy summa</td>
                        <td><strong>${format_currency(contract.total_amount, 'USD')}</strong></td>
                    </tr>
                    <tr>
                        <td style="font-weight: 500;">Nechi oyga</td>
                        <td>${contract.installment_months || 0} oy</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 500;">Har oy to'lov</td>
                        <td>${format_currency(contract.monthly_payment, 'USD')}</td>
                    </tr>
                    <tr>
                        <td style="font-weight: 500;">To'lagan jami</td>
                        <td><strong style="color: green;">${format_currency(contract.paid_amount, 'USD')}</strong></td>
                    </tr>
                    <tr>
                        <td style="font-weight: 500;">Qolgan qarz</td>
                        <td><strong style="color: ${contract.outstanding_amount > 0 ? 'red' : 'green'};">${format_currency(contract.outstanding_amount, 'USD')}</strong></td>
                    </tr>
                    <tr>
                        <td style="font-weight: 500;">To'lov jarayoni</td>
                        <td>
                            <div class="progress" style="height: 25px; margin-bottom: 5px;">
                                <div class="progress-bar bg-${contract.status_color}" 
                                     style="width: ${contract.payment_percentage || 0}%;">
                                    ${contract.payment_percentage || 0}%
                                </div>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td style="font-weight: 500;">Holat</td>
                        <td>
                            <span style="font-size: 16px;">${contract.status_icon || '📋'}</span>
                            <span class="indicator-pill ${contract.status_color}">${contract.custom_status || contract.status}</span>
                        </td>
                    </tr>
                `;
                
                html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                
                wrapper.append(html);
            }
        }
    });
}

function load_payment_history(frm, wrapper) {
    console.log('🔍 Loading payment history for:', frm.doc.name);
    
    frappe.call({
        method: 'cash_flow_app.cash_flow_management.api.customer_history.get_payment_schedule_with_history',
        args: {
            customer: frm.doc.name
        },
        callback: function(r) {
            console.log('📊 Payment schedule result:', r.message);
            
            if (r.message && r.message.length > 0) {
                let html = `
                    <div class="form-section card-section visible-section">
                        <div class="section-head">
                            <span class="indicator orange">📅</span>
                            <span class="section-title">2-qism (pastda): Oylik to'lovlar jadvali - REAL-TIME</span>
                        </div>
                        <div class="section-body" style="padding: 15px; overflow-x: auto;">
                            <table class="table table-bordered table-hover">
                                <thead>
                                    <tr style="background-color: #f5f5f5;">
                                        <th style="width: 8%;">Oy</th>
                                        <th style="width: 12%;">Muddat</th>
                                        <th style="width: 12%;">Summa</th>
                                        <th style="width: 12%;">To'landi</th>
                                        <th style="width: 12%;">Qoldi</th>
                                        <th style="width: 12%;">To'lov sanasi</th>
                                        <th style="width: 32%;">Status (Real-Time)</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                r.message.forEach((row) => {
                    let paid = parseFloat(row.paid_amount) || 0;
                    let payment_amount = parseFloat(row.payment_amount) || 0;
                    let outstanding = parseFloat(row.outstanding) || 0;
                    
                    // Month description
                    let month_desc = row.description || `${row.payment_number}-oy`;
                    
                    // Payment date
                    let payment_date = row.payment_date 
                        ? frappe.datetime.str_to_user(row.payment_date) 
                        : '-';
                    
                    // Status with color
                    let status_html = `<span style="color: ${row.status_color}; font-weight: 500;">${row.status}</span>`;
                    
                    // Payment entry link
                    if (row.payment_name) {
                        payment_date = `<a href="/app/payment-entry/${row.payment_name}" target="_blank">${payment_date}</a>`;
                    }
                    
                    html += `
                        <tr>
                            <td style="text-align: center;"><strong>${month_desc}</strong></td>
                            <td>${frappe.datetime.str_to_user(row.due_date)}</td>
                            <td><strong>${format_currency(payment_amount, 'USD')}</strong></td>
                            <td style="color: ${paid > 0 ? 'green' : 'gray'};">${format_currency(paid, 'USD')}</td>
                            <td style="color: ${outstanding > 0 ? 'red' : 'green'};">${format_currency(outstanding, 'USD')}</td>
                            <td>${payment_date}</td>
                            <td>${status_html}</td>
                        </tr>
                    `;
                });
                
                html += `
                                </tbody>
                            </table>
                            <div style="margin-top: 15px; padding: 10px; background-color: #f0f9ff; border-left: 3px solid #2563eb;">
                                <strong>🔄 Real-Time Tracking:</strong> Bu jadval har safar Payment Entry submit qilinganda avtomatik yangilanadi!
                                <br>
                                <small style="color: #666;">
                                    ✅ = To'langan | 🟡 = Qisman to'langan | ⏳ = Kutilmoqda | ❌ = Muddati o'tgan
                                </small>
                            </div>
                        </div>
                    </div>
                `;
                
                wrapper.append(html);
            } else {
                // No payment schedule
                let html = `
                    <div class="form-section card-section visible-section">
                        <div class="section-head">
                            <span class="indicator gray">📅</span>
                            <span class="section-title">2-qism: Oylik to'lovlar jadvali</span>
                        </div>
                        <div class="section-body" style="padding: 15px;">
                            <p style="color: #999; text-align: center;">
                                Bu mijozda hozircha shartnoma yo'q
                            </p>
                        </div>
                    </div>
                `;
                wrapper.append(html);
            }
        },
        error: function(r) {
            console.error('Payment schedule load error:', r);
            frappe.msgprint({
                title: 'Error',
                message: 'To\'lov jadvali yuklashda xatolik: ' + (r.message || 'Unknown error'),
                indicator: 'red'
            });
        }
    });
}

function format_currency(value, currency) {
    return frappe.format(value, {fieldtype: 'Currency', options: currency});
}