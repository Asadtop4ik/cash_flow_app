// Customer Form - Professional Dashboard
// Frappe Standard: Dashboard renders BELOW form fields, not above

frappe.ui.form.on('Customer', {
    refresh: function(frm) {
        if (frm.doc.__islocal) return;
        
        // Clear previous dashboards
        frm.dashboard.clear_headline();
        
        // Load customer contracts and payment schedules
        load_customer_dashboard(frm);
        
        // Add action buttons
        add_customer_action_buttons(frm);
        
        // Real-time event listeners
        setup_realtime_listener(frm);
        setup_custom_event_listener(frm);
    }
});

function setup_custom_event_listener(frm) {
    // 🚀 CUSTOM EVENT LISTENER - works even if socket.io is down
    console.log('🟡 Setting up CUSTOM event listener for customer:', frm.doc.name);
    
    // Use global event bus via $(document)
    $(document).off('customer_payment_submitted').on('customer_payment_submitted', function(e, data) {
        console.log('\n🟠 RECEIVED CUSTOM EVENT:');
        console.log('   Event: customer_payment_submitted');
        console.log('   Data:', data);
        console.log('   Current customer:', frm.doc.name);
        console.log('   Event customer:', data.customer);
        
        if (data.customer === frm.doc.name) {
            console.log('✅ CUSTOM event match! Refreshing dashboard...');
            
            frappe.show_alert({
                message: __('Payment Entry {0} submitted! Refreshing dashboard...', [data.payment_entry]),
                indicator: 'green'
            }, 5);
            
            // Refresh dashboard
            refresh_customer_dashboard(frm);
        }
    });
    
    console.log('✅ Custom event listener setup complete!\n');
}

function setup_realtime_listener(frm) {
    // 🔍 DEBUG: Log listener setup
    console.log('🟢 Setting up realtime listener for customer:', frm.doc.name);
    console.log('   User:', frappe.session.user);
    console.log('   Session:', frappe.session);
    
    // ✅ IMPORTANT: Remove old listener first to prevent duplicates
    frappe.realtime.off('payment_entry_submitted');
    
    // Listen for payment_entry_submitted event (socket.io)
    frappe.realtime.on('payment_entry_submitted', function(data) {
        // 🔍 DEBUG: Log event reception
        console.log('\n🟣 RECEIVED REALTIME EVENT:');
        console.log('   Event: payment_entry_submitted');
        console.log('   Data:', data);
        console.log('   Current customer:', frm.doc.name);
        console.log('   Event customer:', data.customer);
        console.log('   Match:', data.customer === frm.doc.name);
        
        // Only refresh if this customer is affected
        if (data.customer === frm.doc.name) {
            console.log('✅ Customer match! Refreshing dashboard...');
            
            // Show notification
            frappe.show_alert({
                message: __('Payment Entry {0} submitted! Refreshing dashboard...', [data.payment_entry]),
                indicator: 'green'
            }, 5);
            
            // Refresh dashboard
            refresh_customer_dashboard(frm);
        } else {
            console.log('❌ Customer does NOT match. Skipping refresh.');
        }
    });
    
    console.log('✅ Realtime listener setup complete!\n');
}

function refresh_customer_dashboard(frm) {
    console.log('🔄 FORCE REFRESH - clearing cache and reloading...');
    
    // Clear existing dashboard sections
    $('.customer-contracts-section').remove();
    $('.customer-payment-schedule-section').remove();
    
    // ✅ FORCE RELOAD - Use Promise.all to fetch BOTH API calls in parallel
    Promise.all([
        frappe.call({
            method: 'cash_flow_app.cash_flow_management.api.customer_history.get_customer_contracts',
            args: { customer: frm.doc.name },
            freeze: true,
            freeze_message: __('Yangilanmoqda...'),
            no_cache: true,  // ✅ Bypass cache
            async: false  // ✅ Force synchronous to ensure fresh data
        }),
        frappe.call({
            method: 'cash_flow_app.cash_flow_management.api.customer_history.get_payment_schedule_with_history',
            args: { customer: frm.doc.name },
            no_cache: true,  // ✅ Bypass cache
            async: false  // ✅ Force synchronous to ensure fresh data
        })
    ]).then(([contracts_response, schedules_response]) => {
        console.log('📥 Received fresh data from both APIs:');
        console.log('   Contracts:', contracts_response.message?.length || 0);
        console.log('   Schedules:', schedules_response.message?.length || 0);
        
        const contracts = contracts_response.message || [];
        const schedules = schedules_response.message || [];
        
        if (contracts.length > 0) {
            render_contracts_with_inline_schedules(frm, contracts, schedules);
            console.log('✅ Dashboard refreshed with latest data!');
        } else {
            render_empty_state(frm);
        }
    }).catch(error => {
        console.error('❌ Error refreshing dashboard:', error);
        frappe.msgprint(__('Ma\'lumotlarni yangilashda xatolik'));
    });
}

function load_customer_dashboard(frm) {
    // 🚀 Fetch BOTH contracts AND payment schedules TOGETHER
    Promise.all([
        frappe.call({
            method: 'cash_flow_app.cash_flow_management.api.customer_history.get_customer_contracts',
            args: { customer: frm.doc.name }
        }),
        frappe.call({
            method: 'cash_flow_app.cash_flow_management.api.customer_history.get_payment_schedule_with_history',
            args: { customer: frm.doc.name }
        })
    ]).then(([contracts_response, schedules_response]) => {
        const contracts = contracts_response.message || [];
        const all_schedules = schedules_response.message || [];
        
        if (contracts.length > 0) {
            // ✅ Render contracts WITH inline payment schedules
            render_contracts_with_inline_schedules(frm, contracts, all_schedules);
        } else {
            render_empty_state(frm);
        }
    });
}

// ❌ OLD FUNCTIONS REMOVED - using render_contracts_with_inline_schedules instead
// Contracts and payment schedules are now rendered TOGETHER in one combined view

// ✅ NEW FUNCTION: Render contracts WITH inline payment schedules
function render_contracts_with_inline_schedules(frm, contracts, all_schedules) {
    // 🔍 DEBUG: Log received data from API
    console.log('\n📊 RENDERING DASHBOARD:');
    console.log('   Contracts:', contracts.length);
    console.log('   All schedules:', all_schedules.length);
    console.log('   Schedule data sample:', all_schedules.slice(0, 3));
    
    // Remove any existing dashboard
    $('.customer-contracts-section').remove();
    $('.customer-payment-schedule-section').remove();
    
    // Group schedules by contract
    const schedules_by_contract = {};
    all_schedules.forEach(row => {
        const contract = row.contract || 'Unknown';
        if (!schedules_by_contract[contract]) {
            schedules_by_contract[contract] = [];
        }
        schedules_by_contract[contract].push(row);
    });
    
    // Render each contract WITH its payment schedule inline
    contracts.forEach((contract, index) => {
        const contract_schedules = schedules_by_contract[contract.name] || [];
        
        // Build contract card
        const total = contract.grand_total_with_interest || 0;
        const paid = contract.paid_amount || 0;
        const outstanding = contract.outstanding_amount || 0;
        const progress = contract.payment_percentage || 0;
        const status = contract.custom_status || 'Pending';
        const is_active = status !== 'Completed' && status !== 'Cancelled';
        
        // Status-based gradient colors
        let gradient_start = '#667eea', gradient_end = '#764ba2';
        if (status === 'Completed') {
            gradient_start = '#56ab2f'; gradient_end = '#a8e063';
        } else if (is_active) {
            gradient_start = '#667eea'; gradient_end = '#764ba2';
        } else {
            gradient_start = '#c33764'; gradient_end = '#f8c291';
        }
        
        // Build payment schedule table HTML with carry-over logic
        let schedule_rows_html = '';
        let carry_over = 0;
        
        // 🔍 DEBUG: Log schedule data before rendering
        console.log(`\n📅 Rendering schedule for contract ${contract.name}:`);
        console.log('   Schedule rows:', contract_schedules.length);
        contract_schedules.forEach((row, idx) => {
            console.log(`   Row ${idx + 1}:`, {
                month: row.description || `${row.payment_number}-oy`,
                paid_amount: row.paid_amount,
                payment_amount: row.payment_amount,
                outstanding: row.outstanding
            });
        });
        
        contract_schedules.forEach((row, idx) => {
            let paid_amt = parseFloat(row.paid_amount) || 0;
            let amount = parseFloat(row.payment_amount) || 0;
            let outstanding_amt = parseFloat(row.outstanding) || 0;
            const month = row.description || `${row.payment_number}-oy`;

            // Apply carry-over from previous overpayment
            if (carry_over > 0) {
                paid_amt += carry_over;
                carry_over = 0;
            }

            // Calculate new outstanding and carry-over for next month
            let display_paid = paid_amt;
            let display_outstanding = 0;
            let display_status = row.status;
            let display_status_color = row.status_color;

            if (paid_amt >= amount) {
                // Overpaid or fully paid
                display_paid = amount;
                carry_over = paid_amt - amount;
                display_outstanding = 0;
                if (carry_over > 0) {
                    display_status = `✅ To'landi`;
                    display_status_color = 'green';
                } else {
                    display_status = row.status;
                    display_status_color = row.status_color;
                }
            } else if (paid_amt > 0 && paid_amt < amount) {
                // Partial payment
                display_outstanding = amount - paid_amt;
                display_status = `🟡 Qisman to'landi ($${paid_amt.toFixed(2)}/$${amount.toFixed(2)})`;
                display_status_color = 'orange';
            } else {
                // Not paid
                display_outstanding = amount;
                display_status = row.status;
                display_status_color = row.status_color;
            }

            let payment_date_html = '-';
            if (row.payment_date && row.payment_name) {
                payment_date_html = `<a href="/app/payment-entry/${row.payment_name}" target="_blank" style="color: #2563eb; font-weight: 500;">
                    ${frappe.datetime.str_to_user(row.payment_date)}
                </a>`;
            } else if (row.payment_date) {
                payment_date_html = frappe.datetime.str_to_user(row.payment_date);
            }

            let row_bg = '';
            if (display_status_color === 'green') row_bg = 'background: #f0fdf4;';
            else if (display_status_color === 'red') row_bg = 'background: #fef2f2;';
            else if (display_status_color === 'orange') row_bg = 'background: #fff7ed;';
            else if (display_status_color === 'blue') row_bg = 'background: #eff6ff;';

            let status_color = '#9ca3af';
            if (display_status_color === 'green') status_color = '#16a34a';
            else if (display_status_color === 'red') status_color = '#dc2626';
            else if (display_status_color === 'orange') status_color = '#ea580c';
            else if (display_status_color === 'blue') status_color = '#2563eb';

            schedule_rows_html += `
                <tr style="${row_bg}">
                    <td style="text-align: center; font-weight: bold;">${month}</td>
                    <td>${frappe.datetime.str_to_user(row.due_date)}</td>
                    <td style="text-align: right; font-weight: 600;">$${amount.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                    <td style="text-align: right; color: ${display_paid > 0 ? '#16a34a' : '#9ca3af'}; font-weight: 600;">
                        $${display_paid.toLocaleString('en-US', {minimumFractionDigits: 2})}
                    </td>
                    <td style="text-align: right; color: ${display_outstanding > 0 ? '#dc2626' : '#16a34a'}; font-weight: 600;">
                        $${display_outstanding.toLocaleString('en-US', {minimumFractionDigits: 2})}
                    </td>
                    <td>${payment_date_html}</td>
                    <td><span style="color: ${status_color}; font-weight: 500;">${display_status}</span></td>
                </tr>
            `;
        });
        
        const combined_html = `
            <div class="customer-contracts-section" style="margin-top: 20px; background: white; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); overflow: hidden;">
                <!-- Contract Card -->
                <div style="
                    background: linear-gradient(135deg, ${gradient_start} 0%, ${gradient_end} 100%);
                    padding: 20px;
                    color: white;
                    ${is_active ? 'border: 3px solid #FFD700;' : ''}
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 style="margin: 0; color: white; font-size: 18px;">
                            ${is_active ? '⚡' : '✅'} ${status}
                            ${is_active ? '<span style="background: #FFD700; color: #000; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin-left: 10px;">ACTIVE</span>' : ''}
                        </h3>
                        <a href="/app/sales-order/${contract.name}" target="_blank" 
                           style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px; color: white; text-decoration: none; font-weight: bold;">
                            📄 ${contract.name}
                        </a>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 15px 0;">
                        <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; opacity: 0.9; margin-bottom: 5px;">💰 Jami</div>
                            <div style="font-size: 20px; font-weight: bold;">$${total.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; opacity: 0.9; margin-bottom: 5px;">✅ To'langan</div>
                            <div style="font-size: 20px; font-weight: bold; color: #90EE90;">$${paid.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                        </div>
                        <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px; text-align: center;">
                            <div style="font-size: 11px; opacity: 0.9; margin-bottom: 5px;">⚠️ Qolgan</div>
                            <div style="font-size: 20px; font-weight: bold; color: ${outstanding > 0 ? '#FFB6C1' : '#90EE90'};">$${outstanding.toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                        </div>
                    </div>
                    
                    <div style="background: rgba(255,255,255,0.15); padding: 15px; border-radius: 8px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span style="font-size: 12px;">📊 Progress</span>
                            <span style="font-size: 13px; font-weight: bold;">${progress.toFixed(1)}%</span>
                        </div>
                        <div style="background: rgba(0,0,0,0.2); height: 20px; border-radius: 10px; overflow: hidden;">
                            <div style="
                                background: linear-gradient(90deg, #4ade80, #22c55e);
                                width: ${progress}%;
                                height: 100%;
                                transition: width 0.5s ease;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-size: 10px;
                                font-weight: bold;
                            ">${progress > 8 ? progress.toFixed(0) + '%' : ''}</div>
                        </div>
                    </div>
                    
                    <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.2);">
                        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; font-size: 11px;">
                            <div>
                                <div style="opacity: 0.8;">📅 Sana</div>
                                <div style="font-weight: 500; margin-top: 3px;">${frappe.datetime.str_to_user(contract.transaction_date)}</div>
                            </div>
                            <div>
                                <div style="opacity: 0.8;">📆 Muddati</div>
                                <div style="font-weight: 500; margin-top: 3px;">${contract.installment_months || 0} oy</div>
                            </div>
                            <div>
                                <div style="opacity: 0.8;">💵 Oylik</div>
                                <div style="font-weight: 500; margin-top: 3px;">$${(contract.monthly_payment || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                            </div>
                            <div>
                                <div style="opacity: 0.8;">🎯 Boshlang'ich</div>
                                <div style="font-weight: 500; margin-top: 3px;">$${(contract.downpayment || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Payment Schedule Table INLINE -->
                ${contract_schedules.length > 0 ? `
                    <div style="padding: 20px; background: #f9fafb;">
                        <h4 style="margin: 0 0 15px 0; color: #1f2937; display: flex; justify-content: space-between; align-items: center;">
                            <span>📅 Oylik To'lovlar Jadvali</span>
                            <span style="background: #eff6ff; color: #1e40af; padding: 4px 12px; border-radius: 4px; font-size: 12px;">
                                ${contract_schedules.length} oy
                            </span>
                        </h4>
                        
                        <div style="overflow-x: auto;">
                            <table class="table table-bordered table-hover" style="margin: 0; background: white;">
                                <thead style="background: #f9fafb;">
                                    <tr>
                                        <th style="width: 10%;">Oy</th>
                                        <th style="width: 12%;">Muddat</th>
                                        <th style="width: 12%; text-align: right;">Summa</th>
                                        <th style="width: 12%; text-align: right;">To'landi</th>
                                        <th style="width: 12%; text-align: right;">Qoldi</th>
                                        <th style="width: 14%;">To'lov sanasi</th>
                                        <th style="width: 28%;">Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${schedule_rows_html}
                                </tbody>
                            </table>
                        </div>
                        
                        <div style="margin-top: 15px; padding: 12px; background: #eff6ff; border-left: 4px solid #2563eb; border-radius: 4px;">
                            <div style="color: #1e40af; font-weight: 600; margin-bottom: 5px;">
                                🔄 Real-Time Tracking
                            </div>
                            <div style="color: #1e3a8a; font-size: 13px;">
                                Payment Entry submit qilinganda avtomatik yangilanadi!
                                <span style="display: block; margin-top: 5px;">
                                    ✅ To'langan | 🟡 Qisman | ⏳ Kutilmoqda | ❌ Muddati o'tgan
                                </span>
                            </div>
                        </div>
                    </div>
                ` : '<div style="padding: 20px; text-align: center; color: #9ca3af;">To\'lovlar jadvali hali mavjud emas</div>'}
            </div>
        `;
        
        // Add to dashboard
        frm.dashboard.add_section(combined_html);
    });
}

// ❌ OLD FUNCTION REMOVED - using render_contracts_with_inline_schedules instead
// Payment schedules are now rendered INLINE with each contract card

function render_empty_state(frm) {
    const html = `
        <div class="customer-contracts-section" style="background: #f9fafb; padding: 40px; border-radius: 8px; margin-top: 20px; text-align: center; border: 2px dashed #d1d5db;">
            <div style="font-size: 48px; margin-bottom: 15px;">📋</div>
            <h4 style="color: #6b7280; margin-bottom: 10px;">Hozircha shartnoma yo'q</h4>
            <p style="color: #9ca3af; font-size: 14px;">Yangi Installment Application yarating</p>
        </div>
    `;
    
    frm.dashboard.add_section(html);
}

function add_customer_action_buttons(frm) {
    // To'liq Hisobot
    frm.add_custom_button(__('📊 To\'liq Hisobot'), function() {
        frappe.set_route("query-report", "Customer Payment History", {
            "customer": frm.doc.name
        });
    }, __('Reports'));
    
    // To'lov Tarixi
    frm.add_custom_button(__('To\'lov Tarixi'), function() {
        frappe.route_options = {
            "party_type": "Customer",
            "party": frm.doc.name,
            "payment_type": "Receive",
            "docstatus": 1
        };
        frappe.set_route("List", "Payment Entry");
    }, __('View'));
    
    // Shartnomalar
    frm.add_custom_button(__('Shartnomalar'), function() {
        frappe.route_options = {
            "customer": frm.doc.name,
            "docstatus": 1
        };
        frappe.set_route("List", "Sales Order");
    }, __('View'));
}
