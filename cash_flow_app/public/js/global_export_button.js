/**
 * OPERATOR PANEL GOOGLE SHEETS EXPORT BUTTON
 * Faqat Operator Panelda ko'rinadi
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

// Global function for export dialog
window.show_global_export_dialog = function() {
    console.log('📊 Opening export dialog...');
    
    const d = new frappe.ui.Dialog({
        title: __('Google Sheet'),
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                options: `
                    <div style="padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                color: white; border-radius: 12px; margin-bottom: 20px; text-align: center;">
                        <h2 style="margin: 0 0 10px 0;">🚀 Universal Export</h2>
                        <p style="margin: 0; opacity: 0.95;">Export any DocType or Report instantly</p>
                    </div>
                `
            },
            {
                fieldtype: 'Section Break',
                label: __('Select Export Type')
            },
            {
                fieldtype: 'Select',
                fieldname: 'export_type',
                label: __('Export Type'),
                options: ['DocType', 'Report'],
                default: 'DocType',
                reqd: 1,
                onchange: function() {
                    const type = d.get_value('export_type');
                    d.set_df_property('doctype_name', 'hidden', type !== 'DocType');
                    d.set_df_property('report_name', 'hidden', type !== 'Report');
                    d.refresh();
                }
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Link',
                fieldname: 'doctype_name',
                label: __('DocType'),
                options: 'DocType',
                description: __('Select DocType (e.g., Customer, Item)'),
                onchange: function() {
                    const doctype = d.get_value('doctype_name');
                    if (doctype) {
                        d.set_value('sheet_name', doctype.replace(/ /g, '_'));
                    }
                }
            },
            {
                fieldtype: 'Data',
                fieldname: 'report_name',
                label: __('Report Name'),
                hidden: 1,
                description: __('Enter report name'),
                onchange: function() {
                    const report = d.get_value('report_name');
                    if (report) {
                        d.set_value('sheet_name', report.replace(/ /g, '_'));
                    }
                }
            },
            {
                fieldtype: 'Section Break',
                label: __('Google Sheets Settings')
            },
            {
                fieldtype: 'Data',
                fieldname: 'sheet_name',
                label: __('Sheet Name'),
                reqd: 1,
                description: __('Name for the sheet tab')
            },
            {
                fieldtype: 'Column Break'
            },
            {
                fieldtype: 'Data',
                fieldname: 'spreadsheet_id',
                label: __('Spreadsheet ID (Optional)'),
                description: __('Leave empty to create new spreadsheet')
            },
            {
                fieldtype: 'Section Break'
            },
            {
                fieldtype: 'HTML',
                options: `
                    <div class="alert alert-info">
                        <strong>💡 Tip:</strong> Leave Spreadsheet ID empty to create a new Google Sheet. 
                        Or paste an existing spreadsheet ID to add data to it.
                    </div>
                `
            }
        ],
        primary_action_label: __('Export Now'),
        primary_action: function(values) {
            console.log('📤 Exporting with values:', values);
            
            if (values.export_type === 'DocType') {
                if (!values.doctype_name) {
                    frappe.msgprint(__('Please select a DocType'));
                    return;
                }
                export_doctype_to_sheets(values);
            } else {
                if (!values.report_name) {
                    frappe.msgprint(__('Please enter a Report name'));
                    return;
                }
                export_report_to_sheets(values);
            }
            
            d.hide();
        }
    });
    
    d.show();
};

function export_doctype_to_sheets(values) {
    frappe.show_alert({
        message: __('⏳ Exporting {0} to Google Sheets...', [values.doctype_name]),
        indicator: 'blue'
    }, 3);
    
    frappe.call({
        method: 'cash_flow_app.google_sheets_integration.export_to_google_sheets',
        args: {
            doctype: values.doctype_name,
            filters: {},
            spreadsheet_id: values.spreadsheet_id || null,
            sheet_name: values.sheet_name
        },
        freeze: true,
        freeze_message: __('⏳ Exporting to Google Sheets...'),
        callback: function(r) {
            console.log('✅ Export response:', r);
            
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('✅ Successfully exported to Google Sheets!'),
                    indicator: 'green'
                }, 5);
                
                // Open in new tab
                if (r.message.url) {
                    window.open(r.message.url, '_blank');
                }
                
                // Show success dialog with link
                frappe.msgprint({
                    title: __('Export Successful'),
                    indicator: 'green',
                    message: `
                        <div style="text-align: center; padding: 20px;">
                            <div style="font-size: 48px; margin-bottom: 15px;">✅</div>
                            <h3 style="color: #2ecc71; margin-bottom: 15px;">Export Successful!</h3>
                            <p><strong>${values.doctype_name}</strong> has been exported to Google Sheets</p>
                            ${r.message.rows_exported ? `<p>Total rows: <strong>${r.message.rows_exported}</strong></p>` : ''}
                            <a href="${r.message.url}" target="_blank" class="btn btn-primary btn-sm" 
                               style="margin-top: 15px;">
                                🔗 Open Google Sheet
                            </a>
                        </div>
                    `
                });
            } else {
                frappe.msgprint({
                    title: __('Export Failed'),
                    indicator: 'red',
                    message: __('Error: ') + (r.message?.message || r.exc || 'Unknown error')
                });
            }
        },
        error: function(err) {
            console.error('❌ Export error:', err);
            frappe.msgprint({
                title: __('Export Failed'),
                indicator: 'red',
                message: __('Failed to export. Check console for details.')
            });
        }
    });
}

function export_report_to_sheets(values) {
    frappe.show_alert({
        message: __('⏳ Exporting {0} report...', [values.report_name]),
        indicator: 'blue'
    }, 3);
    
    frappe.call({
        method: 'cash_flow_app.google_sheets_integration.export_report_to_google_sheets',
        args: {
            report_name: values.report_name,
            filters: {},
            spreadsheet_id: values.spreadsheet_id || null,
            sheet_name: values.sheet_name
        },
        freeze: true,
        freeze_message: __('⏳ Exporting report...'),
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.show_alert({
                    message: __('✅ Report exported successfully!'),
                    indicator: 'green'
                }, 5);
                
                if (r.message.url) {
                    window.open(r.message.url, '_blank');
                }
            } else {
                frappe.msgprint(__('Export failed: ') + (r.message?.message || ''));
            }
        }
    });
}

console.log('✅ Global Export Button Script Loaded');
