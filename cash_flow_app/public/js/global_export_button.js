/**
 * OPERATOR PANEL GOOGLE SHEETS EXPORT BUTTON
 * Faqat Operator Panelda ko'rinadi
 * Sheet tugmasini bosganingizda avtomatik export qilinadi
 */

frappe.provide('frappe.ui.toolbar');

$(document).ready(function() {
    console.log('🚀 Operator Panel Export Button Loading...');
    
    // Wait for navbar to be ready
    setTimeout(function() {
        add_export_to_navbar();
    }, 2000);
    
    // Re-check on route change
    frappe.router.on('change', function() {
        setTimeout(function() {
            add_export_to_navbar();
        }, 500);
    });
});

function add_export_to_navbar() {
    // Check if we are on Operator Panel page
    const currentPath = window.location.pathname + window.location.hash;
    const isOperatorPanel = currentPath.includes('/app/operator-paneli') || 
                           currentPath.includes('/app/operator-panel') ||
                           currentPath.includes('Operator%20Paneli') ||
                           frappe.get_route()[0] === 'operator-paneli' ||
                           frappe.get_route()[0] === 'Operator Paneli';
    
    // Check if button already exists
    const buttonExists = $('#global-sheets-export-btn').length > 0;
    
    if (!isOperatorPanel && buttonExists) {
        // Remove button if not on Operator Panel
        $('#global-sheets-export-btn').remove();
        console.log('❌ Export button removed (not on Operator Panel)');
        return;
    }
    
    if (!isOperatorPanel) {
        // Don't add button if not on Operator Panel
        return;
    }
    
    if (buttonExists) {
        console.log('⚠️ Button already exists');
        return;
    }
    
    console.log('✅ Adding Export button to navbar (Operator Panel only)');
    
    // Add button to navbar - Oq fon, qora matn, bold emas
    const exportBtn = $(`
        <li class="nav-item dropdown dropdown-help dropdown-mobile-header" id="global-sheets-export-btn">
            <a class="nav-link" onclick="show_global_export_dialog()" 
               style="cursor: pointer; 
                      background: #FFFFFF; 
                      color: #000000 !important; 
                      font-weight: normal;
                      font-size: 14px;
                      padding: 8px 16px;
                      border-radius: 6px;
                      margin: 8px 8px 8px 0;
                      transition: all 0.2s ease;
                      border: 1px solid #d1d8dd;
                      box-shadow: 0 1px 2px rgba(0,0,0,0.05);"
               onmouseover="this.style.background='#f5f7fa'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)';"
               onmouseout="this.style.background='#FFFFFF'; this.style.boxShadow='0 1px 2px rgba(0,0,0,0.05)';">
                Sheet
            </a>
        </li>
    `);
    
    // Insert before Help icon
    const helpDropdown = $('.dropdown-help').first();
    if (helpDropdown.length > 0) {
        exportBtn.insertBefore(helpDropdown);
    } else {
        // Or append to navbar
        $('.navbar-right').append(exportBtn);
    }
    
    console.log('✅ Export button added to navbar');
}

// Global function - Sheet tugmasini bosganda chaqiriladi
window.show_global_export_dialog = function() {
    console.log('📊 Starting auto export...');
    
    // =====================================================
    // BU YERGA O'ZINGIZNING GOOGLE SHEET ID NI QO'YING
    // =====================================================
    const SHEET_ID = '1-CMS3s4vb97OeA-ikFchAOG2up2tVfGgGEazsmQrIoA';
    // Masalan: const SHEET_ID = '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms';
    
    frappe.show_alert({
        message: __('⏳ Exporting all data to Google Sheets...'),
        indicator: 'blue'
    }, 5);
    
    frappe.call({
        method: 'cash_flow_app.google_sheets_integration.export_all_doctypes_to_sheet',
        args: {
            spreadsheet_id: SHEET_ID
        },
        freeze: true,
        freeze_message: __('⏳ Exporting: Mijozlar, Pastavshiklar, Shartnoma, Kassa, Mahsulotlar...'),
        callback: function(r) {
            console.log('✅ Export response:', r);
            
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('✅ Export Muvaffaqiyatli!'),
                    indicator: 'green'
                }, 5);
                
                // Open Google Sheet in new tab
                if (r.message.spreadsheet_url) {
                    window.open(r.message.spreadsheet_url, '_blank');
                }
                
                // Show simple success message
                frappe.msgprint({
                    title: __('✅ Export Muvaffaqiyatli'),
                    indicator: 'green',
                    message: `
                        <div style="text-align: center; padding: 30px;">
                            <div style="font-size: 60px; margin-bottom: 20px;">✅</div>
                            <h3 style="color: #2ecc71; margin-bottom: 15px;">Export Muvaffaqiyatli!</h3>
                            <p style="font-size: 16px; margin-bottom: 10px;">
                                <strong>${r.message.successful_exports}</strong> ta doctype export bo'ldi
                            </p>
                            <p style="color: #6c757d;">
                                Mijozlar, Pastavshiklar, Shartnoma, Kassa Kirim-chiqim, Mahsulotlar
                            </p>
                            <a href="${r.message.spreadsheet_url}" target="_blank" 
                               class="btn btn-primary btn-lg" 
                               style="margin-top: 20px; font-size: 16px; padding: 12px 30px;">
                                🔗 Google Sheet ni ochish
                            </a>
                        </div>
                    `
                });
            } else {
                frappe.msgprint({
                    title: __('❌ Export Muvaffaqiyatsiz'),
                    indicator: 'red',
                    message: `
                        <div style="text-align: center; padding: 30px;">
                            <div style="font-size: 60px; margin-bottom: 20px;">❌</div>
                            <h3 style="color: #e74c3c; margin-bottom: 15px;">Export Muvaffaqiyatsiz</h3>
                            <p>${r.message?.message || 'Xatolik yuz berdi'}</p>
                        </div>
                    `
                });
            }
        },
        error: function(err) {
            console.error('❌ Export error:', err);
            frappe.msgprint({
                title: __('❌ Export Muvaffaqiyatsiz'),
                indicator: 'red',
                message: `
                    <div style="text-align: center; padding: 30px;">
                        <div style="font-size: 60px; margin-bottom: 20px;">❌</div>
                        <h3 style="color: #e74c3c; margin-bottom: 15px;">Export Muvaffaqiyatsiz</h3>
                        <p>Xatolik yuz berdi. Console ni tekshiring.</p>
                    </div>
                `
            });
        }
    });
};

console.log('✅ Global Export Button Script Loaded');
