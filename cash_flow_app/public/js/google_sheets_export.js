/**
 * Google Sheets Export - Universal Integration
 * Adds Google Sheets to Export Dialog (Excel, CSV, Google Sheets)
 */

(function() {
    'use strict';
    
    console.log('🚀 Google Sheets Export Loading...');

    frappe.provide('frappe.views');
    
    frappe.ready(function() {
        if (frappe.views.ListView) {
            override_listview_export();
        }
        override_report_export();
    });
    
    function override_listview_export() {
        frappe.views.ListView.prototype.get_export_dialog = function() {
            const me = this;
            
            const dialog = new frappe.ui.Dialog({
                title: __('Export Data'),
                fields: [
                    {
                        fieldtype: 'Select',
                        fieldname: 'file_format',
                        label: __('File Format'),
                        options: ['Excel', 'CSV', 'Google Sheets'],
                        default: 'Excel',
                        onchange: function() {
                            dialog.refresh();
                        }
                    },
                    {
                        fieldtype: 'Section Break',
                        depends_on: 'eval:doc.file_format === "Google Sheets"'
                    },
                    {
                        fieldtype: 'Data',
                        fieldname: 'spreadsheet_id',
                        label: __('Spreadsheet ID (Optional)'),
                        depends_on: 'eval:doc.file_format === "Google Sheets"'
                    },
                    {
                        fieldtype: 'Data',
                        fieldname: 'sheet_name',
                        label: __('Sheet Name'),
                        default: me.doctype.replace(/ /g, '_'),
                        depends_on: 'eval:doc.file_format === "Google Sheets"',
                        mandatory_depends_on: 'eval:doc.file_format === "Google Sheets"'
                    },
                    {
                        fieldtype: 'HTML',
                        depends_on: 'eval:doc.file_format === "Google Sheets"',
                        options: '<div class="alert alert-info">📊 All records will be exported to Google Sheets</div>'
                    }
                ],
                primary_action_label: __('Export'),
                primary_action: function(values) {
                    if (values.file_format === 'Google Sheets') {
                        export_to_sheets(me, values);
                    } else {
                        me.export_records(values.file_format, 'All', 0);
                    }
                    dialog.hide();
                }
            });
            
            dialog.show();
            return dialog;
        };
    }
    
    function export_to_sheets(listview, values) {
        frappe.call({
            method: 'cash_flow_app.google_sheets_integration.export_to_google_sheets',
            args: {
                doctype: listview.doctype,
                filters: listview.get_filters_for_args() || {},
                spreadsheet_id: values.spreadsheet_id,
                sheet_name: values.sheet_name
            },
            freeze: true,
            freeze_message: __('Exporting...'),
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert({message: '✅ Exported!', indicator: 'green'}, 3);
                    window.open(r.message.url, '_blank');
                } else {
                    frappe.msgprint(__('Export failed: ') + (r.message?.message || ''));
                }
            }
        });
    }
    
    function override_report_export() {
        frappe.after_ajax(function() {
            if (frappe.get_route()[0] === 'query-report') {
                setTimeout(function() {
                    if (window.cur_page && cur_page.report_name) {
                        add_report_export();
                    }
                }, 1000);
            }
        });
    }
    
    function add_report_export() {
        if (!cur_page || !cur_page.report_name || cur_page._gs_added) return;
        
        frappe.query_report.get_export_dialog = function() {
            const report_name = cur_page.report_name;
            const filters = cur_page.get_values ? cur_page.get_values() : {};
            
            const dialog = new frappe.ui.Dialog({
                title: __('Export Report'),
                fields: [
                    {
                        fieldtype: 'Select',
                        fieldname: 'file_format',
                        label: __('File Format'),
                        options: ['Excel', 'CSV', 'Google Sheets'],
                        default: 'Excel',
                        onchange: function() { dialog.refresh(); }
                    },
                    {
                        fieldtype: 'Section Break',
                        depends_on: 'eval:doc.file_format === "Google Sheets"'
                    },
                    {
                        fieldtype: 'Data',
                        fieldname: 'spreadsheet_id',
                        label: __('Spreadsheet ID (Optional)'),
                        depends_on: 'eval:doc.file_format === "Google Sheets"'
                    },
                    {
                        fieldtype: 'Data',
                        fieldname: 'sheet_name',
                        label: __('Sheet Name'),
                        default: report_name.replace(/ /g, '_'),
                        depends_on: 'eval:doc.file_format === "Google Sheets"',
                        mandatory_depends_on: 'eval:doc.file_format === "Google Sheets"'
                    }
                ],
                primary_action_label: __('Export'),
                primary_action: function(values) {
                    if (values.file_format === 'Google Sheets') {
                        export_report_to_sheets(report_name, filters, values);
                    } else {
                        frappe.query_report.export_report(values.file_format);
                    }
                    dialog.hide();
                }
            });
            
            dialog.show();
            return dialog;
        };
        
        cur_page._gs_added = true;
    }
    
    function export_report_to_sheets(report_name, filters, values) {
        frappe.call({
            method: 'cash_flow_app.google_sheets_integration.export_report_to_google_sheets',
            args: {
                report_name: report_name,
                filters: filters || {},
                spreadsheet_id: values.spreadsheet_id,
                sheet_name: values.sheet_name
            },
            freeze: true,
            freeze_message: __('Exporting report...'),
            callback: function(r) {
                if (r.message && r.message.success) {
                    frappe.show_alert({message: '✅ Report exported!', indicator: 'green'}, 3);
                    window.open(r.message.url, '_blank');
                } else {
                    frappe.msgprint(__('Export failed: ') + (r.message?.message || ''));
                }
            }
        });
    }
    
    console.log('✅ Google Sheets Export Loaded');
})();
