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
                        <td style="font-weight: 500;">Holat</td>
                        <td>
                            <span class="indicator-pill ${contract.status_color}">${contract.status}</span>
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
    frappe.call({
        method: 'cash_flow_app.cash_flow_management.api.customer_history.get_payment_schedule_with_history',
        args: {
            customer: frm.doc.name
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let html = `
                    <div class="form-section card-section visible-section">
                        <div class="section-head">
                            <span class="indicator orange">📅</span>
                            <span class="section-title">2-qism (pastda): Oylik to'lovlar jadvali</span>
                        </div>
                        <div class="section-body" style="padding: 15px; overflow-x: auto;">
                            <table class="table table-bordered table-hover">
                                <thead>
                                    <tr style="background-color: #f5f5f5;">
                                        <th>Oy raqami</th>
                                        <th>To'lov kuni</th>
                                        <th>To'lash kerak summa</th>
                                        <th>To'lashga qolgan / O'tgan kun</th>
                                        <th>To'lagan summa</th>
                                        <th>To'lagan sana</th>
                                        <th>Holat</th>
                                    </tr>
                                </thead>
                                <tbody>
                `;
                
                r.message.forEach((row, index) => {
                    let status_badge = '';
                    let status_color = '';
                    
                    if (row.status === 'On Time') {
                        status_badge = '✅ 0 kun erta';
                        status_color = 'green';
                    } else if (row.status === 'Late') {
                        status_badge = `❌ ${row.days_late} kun kechikdi`;
                        status_color = 'red';
                    } else if (row.status === 'Upcoming') {
                        status_badge = `⏳ ${row.days_remaining} kun qoldi`;
                        status_color = 'orange';
                    } else {
                        status_badge = '-';
                        status_color = 'gray';
                    }
                    
                    html += `
                        <tr>
                            <td>${row.payment_number}-oy</td>
                            <td>${frappe.datetime.str_to_user(row.due_date)}</td>
                            <td><strong>${format_currency(row.payment_amount, 'USD')}</strong></td>
                            <td style="color: ${status_color};">${status_badge}</td>
                            <td>${row.paid_amount > 0 ? format_currency(row.paid_amount, 'USD') : '0'}</td>
                            <td>${row.payment_date ? frappe.datetime.str_to_user(row.payment_date) : '-'}</td>
                            <td>
                                <span class="indicator-pill ${row.status === 'On Time' ? 'green' : row.status === 'Late' ? 'red' : row.status === 'Upcoming' ? 'orange' : 'gray'}">
                                    ${row.status}
                                </span>
                            </td>
                        </tr>
                    `;
                });
                
                html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                `;
                
                wrapper.append(html);
            } else {
                wrapper.append(`
                    <div class="form-section card-section visible-section">
                        <div class="section-body" style="padding: 15px; text-align: center; color: #888;">
                            <p>❌ Hali shartnoma mavjud emas</p>
                        </div>
                    </div>
                `);
            }
        }
    });
}
