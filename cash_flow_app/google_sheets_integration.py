# -*- coding: utf-8 -*-
"""
Google Sheets Integration for ERPNext
Professional implementation with comprehensive error handling
"""

import frappe
from frappe import _
import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleSheetsExporter:
    """
    Professional Google Sheets Export Handler
    Handles authentication, data formatting, and export to Google Sheets
    """
    
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    # Fields to exclude from export (non-data/virtual fields)
    EXCLUDED_FIELDTYPES = [
        'Table', 'Table MultiSelect', 'HTML', 'Image', 'Attach Image',
        'Signature', 'Barcode', 'Geolocation', 'Button', 'Heading',
        'Column Break', 'Section Break', 'Tab Break'
    ]
    
    def __init__(self):
        """Initialize with service account credentials"""
        self.service = None
        self.credentials = None
        self._init_google_service()
    
    def _init_google_service(self):
        """Initialize Google Sheets API service"""
        try:
            # Get credentials file path
            site_path = frappe.utils.get_site_path()
            creds_file = os.path.join(site_path, 'private', 'files', 'google_credentials.json')
            
            if not os.path.exists(creds_file):
                error_msg = f"Credentials file not found: {creds_file}"
                frappe.log_error(error_msg, "Google Sheets Init")
                frappe.throw(_(error_msg))
            
            # Load credentials
            self.credentials = service_account.Credentials.from_service_account_file(
                creds_file,
                scopes=self.SCOPES
            )
            
            # Build service
            self.service = build('sheets', 'v4', credentials=self.credentials)
            
            frappe.logger().info("Google Sheets service initialized")
            
        except Exception as e:
            error_msg = f"Failed to initialize Google Sheets: {str(e)}"
            frappe.log_error(error_msg, "Google Sheets Init Error")
            frappe.throw(_(error_msg))
    
    def export_doctype(self, doctype_name, filters=None, fields=None,
                      spreadsheet_id=None, sheet_name=None):
        """
        Export DocType data to Google Sheets
        
        Args:
            doctype_name (str): DocType to export
            filters (dict): Filters to apply
            fields (list): Fields to export (None = all)
            spreadsheet_id (str): Existing spreadsheet ID or None
            sheet_name (str): Sheet tab name
            
        Returns:
            dict: Export result with success status and details
        """
        try:
            frappe.logger().info(f"Starting export: {doctype_name}")
            
            # Validate inputs
            if not doctype_name:
                return {'success': False, 'message': 'DocType name is required'}
            
            if not frappe.db.exists('DocType', doctype_name):
                return {'success': False, 'message': f'DocType {doctype_name} does not exist'}
            
            # Get data
            data = self._fetch_doctype_data(doctype_name, filters, fields)
            
            if not data:
                return {
                    'success': False,
                    'message': 'No data found to export'
                }
            
            # Prepare for sheets
            headers = list(data[0].keys())
            rows = [[self._format_cell_value(row.get(h)) for h in headers] for row in data]
            sheet_data = [headers] + rows
            
            # Export to Google Sheets
            result = self._write_to_google_sheets(
                sheet_data,
                spreadsheet_id,
                sheet_name or doctype_name
            )
            
            frappe.logger().info(f"Export completed: {len(data)} rows")
            
            return {
                'success': True,
                'spreadsheet_id': result['spreadsheet_id'],
                'url': result['spreadsheet_url'],  # Add url key for frontend
                'spreadsheet_url': result['spreadsheet_url'],
                'sheet_name': result['sheet_name'],
                'rows_exported': len(data),
                'records_exported': len(data),  # Add for compatibility
                'message': f'Successfully exported {len(data)} records'
            }
            
        except Exception as e:
            error_msg = f"Export failed: {str(e)}"
            frappe.log_error(error_msg, "Google Sheets Export")
            frappe.logger().error(error_msg)
            return {
                'success': False,
                'message': error_msg
            }
    
    def _fetch_doctype_data(self, doctype_name, filters=None, fields=None):
        """Fetch DocType data with proper field validation"""
        try:
            # Get DocType metadata
            meta = frappe.get_meta(doctype_name)

            # Get valid database columns
            db_columns = set(frappe.db.get_table_columns(doctype_name))

            # Determine fields to fetch (parent fields)
            if not fields:
                fields = []

                # Add standard fields
                for std_field in ['name', 'owner', 'creation', 'modified', 'modified_by', 'docstatus']:
                    if std_field in db_columns:
                        fields.append(std_field)

                # Add DocType fields
                for field in meta.fields:
                    if (field.fieldtype not in self.EXCLUDED_FIELDTYPES and
                        field.fieldname in db_columns and
                        field.fieldname not in fields):
                        fields.append(field.fieldname)

            # Validate all fields exist in database
            parent_fields = [f for f in fields if f in db_columns]

            if not parent_fields:
                frappe.throw(_("No valid parent fields found for export"))

            frappe.logger().info(f"Fetching {len(parent_fields)} parent fields for {doctype_name}")

            # Fetch parent data
            parents = frappe.get_all(
                doctype_name,
                filters=filters or {},
                fields=parent_fields,
                limit_page_length=0,  # No limit
                order_by='modified desc'
            )

            frappe.logger().info(f"Fetched {len(parents)} parent records")

            # Check if doc has any child tables
            child_tables = []
            for f in meta.fields:
                if f.fieldtype == 'Table':
                    child_tables.append({'fieldname': f.fieldname, 'doctype': f.options})

            rows = []

            # If there are child tables, include them as JSON in parent row
            if child_tables:
                frappe.logger().info(f"Found {len(child_tables)} child tables for {doctype_name}: {[ct['fieldname'] for ct in child_tables]}")

                for p in parents:
                    parent_name = p.get('name')
                    parent_row = {**p}  # Copy parent data
                    
                    # Fetch each child table and add as JSON column
                    for ct in child_tables:
                        child_fieldname = ct['fieldname']
                        child_doctype = ct['doctype']
                        
                        try:
                            # Prepare child fields to fetch
                            child_meta = frappe.get_meta(child_doctype)
                            child_db_cols = set(frappe.db.get_table_columns(child_doctype))
                            child_fields = [cf.fieldname for cf in child_meta.fields if cf.fieldname in child_db_cols]
                            
                            # Fetch child rows
                            children = frappe.get_all(
                                child_doctype,
                                filters={'parent': parent_name},
                                fields=child_fields,
                                order_by='idx asc'
                            )
                            
                            # For 'items' table, add supplier info to each item
                            if child_fieldname == 'items' and children:
                                for child_row in children:
                                    item_code = child_row.get('item_code') or child_row.get('item') or ''
                                    supplier = child_row.get('supplier') or child_row.get('supplier_name') or ''
                                    
                                    # If no supplier in child row, lookup from Item Supplier
                                    if not supplier and item_code:
                                        try:
                                            sup = frappe.get_all('Item Supplier', 
                                                filters={'parent': item_code}, 
                                                fields=['supplier','supplier_name'], 
                                                limit_page_length=1)
                                            if sup:
                                                supplier = sup[0].get('supplier') or sup[0].get('supplier_name') or ''
                                        except Exception:
                                            supplier = ''
                                    
                                    child_row['supplier'] = supplier or ''
                            
                            # Add child table as JSON string
                            import json
                            parent_row[f'{child_fieldname}_json'] = json.dumps(children, default=str, ensure_ascii=False) if children else '[]'
                                
                        except Exception as e:
                            frappe.logger().error(f"Failed to fetch {child_fieldname} for {parent_name}: {str(e)}")
                            parent_row[f'{child_fieldname}_json'] = '[]'
                    
                    rows.append(parent_row)

                return rows

            # No child table expansion: return parent list of dicts
            return parents

        except Exception as e:
            error_msg = f"Data fetch failed: {str(e)}"
            frappe.logger().error(error_msg)
            frappe.throw(_(error_msg))
    
    def _format_cell_value(self, value):
        """Format cell value for Google Sheets"""
        if value is None:
            return ''
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)
    
    def _write_to_google_sheets(self, data, spreadsheet_id=None, sheet_name='Sheet1'):
        """Write data to Google Sheets with formatting"""
        try:
            # Create or use existing spreadsheet
            if not spreadsheet_id:
                spreadsheet = self.service.spreadsheets().create(body={
                    'properties': {
                        'title': f'ERPNext Export - {sheet_name}'
                    },
                    'sheets': [{
                        'properties': {
                            'title': sheet_name
                        }
                    }]
                }).execute()
                
                spreadsheet_id = spreadsheet['spreadsheetId']
                frappe.logger().info(f"Created spreadsheet: {spreadsheet_id}")
            else:
                # Ensure sheet exists
                self._ensure_sheet_exists(spreadsheet_id, sheet_name)
            
            # Clear existing data
            try:
                self.service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{sheet_name}'!A:ZZ"
                ).execute()
            except HttpError:
                pass  # Sheet might not exist yet
            
            # Write data
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"'{sheet_name}'!A1",
                valueInputOption='RAW',
                body={'values': data}
            ).execute()
            
            # Format header row
            self._format_header(spreadsheet_id, sheet_name)
            
            # Auto-resize columns
            self._auto_resize_columns(spreadsheet_id, sheet_name)
            
            spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            
            return {
                'spreadsheet_id': spreadsheet_id,
                'spreadsheet_url': spreadsheet_url,
                'sheet_name': sheet_name
            }
            
        except HttpError as e:
            error_msg = f"Google API error: {str(e)}"
            frappe.logger().error(error_msg)
            frappe.throw(_(error_msg))
        except Exception as e:
            error_msg = f"Write failed: {str(e)}"
            frappe.logger().error(error_msg)
            frappe.throw(_(error_msg))
    
    def _ensure_sheet_exists(self, spreadsheet_id, sheet_name):
        """Ensure sheet tab exists in spreadsheet"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheet_exists = any(
                sheet['properties']['title'] == sheet_name
                for sheet in spreadsheet.get('sheets', [])
            )
            
            if not sheet_exists:
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        'requests': [{
                            'addSheet': {
                                'properties': {
                                    'title': sheet_name
                                }
                            }
                        }]
                    }
                ).execute()
                frappe.logger().info(f"Created sheet: {sheet_name}")
                
        except Exception as e:
            frappe.logger().warning(f"Sheet check failed: {str(e)}")
    
    def _format_header(self, spreadsheet_id, sheet_name):
        """Format header row (bold, colored background)"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheet_id = None
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    'requests': [{
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 0,
                                'endRowIndex': 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {
                                        'red': 0.2,
                                        'green': 0.6,
                                        'blue': 0.86
                                    },
                                    'textFormat': {
                                        'bold': True,
                                        'foregroundColor': {
                                            'red': 1,
                                            'green': 1,
                                            'blue': 1
                                        }
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                        }
                    }]
                }
            ).execute()
            
        except Exception as e:
            frappe.logger().warning(f"Header formatting failed: {str(e)}")
    
    def _auto_resize_columns(self, spreadsheet_id, sheet_name):
        """Auto-resize columns to fit content"""
        try:
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheet_id = None
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                return
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    'requests': [{
                        'autoResizeDimensions': {
                            'dimensions': {
                                'sheetId': sheet_id,
                                'dimension': 'COLUMNS',
                                'startIndex': 0,
                                'endIndex': 26  # A-Z columns
                            }
                        }
                    }]
                }
            ).execute()
            
        except Exception as e:
            frappe.logger().warning(f"Column resize failed: {str(e)}")


@frappe.whitelist()
def export_to_google_sheets(doctype, filters=None, fields=None,
                            spreadsheet_id=None, sheet_name=None):
    """
    Public API endpoint for Google Sheets export
    
    Args:
        doctype: DocType to export (can be string name)
        filters: Filters as JSON string or dict
        fields: Fields to export as JSON string or list
        spreadsheet_id: Optional existing spreadsheet ID
        sheet_name: Optional sheet name
        
    Returns:
        dict: Export result
    """
    try:
        # Handle both 'doctype' and 'doctype_name' parameter names
        doctype_name = doctype
        
        # Parse JSON strings if needed
        if isinstance(filters, str):
            filters = json.loads(filters) if filters else {}
        
        if isinstance(fields, str):
            fields = json.loads(fields) if fields else None
        
        # Validate DocType exists
        if not frappe.db.exists('DocType', doctype_name):
            return {
                'success': False,
                'message': f'DocType "{doctype_name}" does not exist'
            }
        
        # Create exporter and run export
        exporter = GoogleSheetsExporter()
        result = exporter.export_doctype(
            doctype_name=doctype_name,
            filters=filters,
            fields=fields,
            spreadsheet_id=spreadsheet_id,
            sheet_name=sheet_name
        )
        
        return result
        
    except Exception as e:
        error_msg = f"API call failed: {str(e)}"
        frappe.log_error(error_msg, "Google Sheets API")
        return {
            'success': False,
            'message': error_msg
        }


@frappe.whitelist()
def export_report_to_google_sheets(report_name, filters=None,
                                   spreadsheet_id=None, sheet_name=None):
    """
    Export Report to Google Sheets
    
    Args:
        report_name: Report name
        filters: Report filters
        spreadsheet_id: Optional spreadsheet ID
        sheet_name: Optional sheet name
    """
    try:
        # Parse filters
        if isinstance(filters, str):
            filters = json.loads(filters) if filters else {}
        
        # Get report data
        from frappe.desk.query_report import run
        result = run(report_name, filters=filters)
        
        if not result or not result.get('result'):
            return {
                'success': False,
                'message': 'No data in report'
            }
        
        # Prepare data
        columns = result.get('columns', [])
        data = result.get('result', [])
        
        headers = [col.get('label') or col.get('fieldname') for col in columns]
        fieldnames = [col.get('fieldname') for col in columns]
        
        rows = []
        for row in data:
            if isinstance(row, dict):
                rows.append([str(row.get(f, '')) for f in fieldnames])
            elif isinstance(row, list):
                rows.append([str(v) for v in row])
        
        sheet_data = [headers] + rows
        
        # Export
        exporter = GoogleSheetsExporter()
        result = exporter._write_to_google_sheets(
            sheet_data,
            spreadsheet_id,
            sheet_name or report_name
        )
        
        return {
            'success': True,
            'spreadsheet_id': result['spreadsheet_id'],
            'url': result['spreadsheet_url'],  # Add url key for frontend
            'spreadsheet_url': result['spreadsheet_url'],
            'sheet_name': result['sheet_name'],
            'rows_exported': len(rows),
            'records_exported': len(rows),  # Add for compatibility
            'message': f'Successfully exported {len(rows)} rows'
        }
        
    except Exception as e:
        error_msg = f"Report export failed: {str(e)}"
        frappe.log_error(error_msg, "Report Export")
        return {
            'success': False,
            'message': error_msg
        }


@frappe.whitelist()
def export_installment_application(spreadsheet_id=None, sheet_name='Shartnoma', filters=None):
    """
    Export Installment Application with child items in readable format
    Each item creates a separate row with parent info
    """
    try:
        exporter = GoogleSheetsExporter()

        # Parse filters
        if isinstance(filters, str):
            filters = json.loads(filters) if filters else {}

        # Get all Installment Applications (including cancelled ones)
        # By default frappe.get_all excludes cancelled documents (docstatus=2)
        # We use or_filters to include all docstatus values
        base_filters = filters or {}

        applications = frappe.get_all(
            'Installment Application',
            filters=base_filters,
            fields=[
                'name', 'customer', 'customer_name', 'transaction_date',
                'total_amount', 'downpayment_amount', 'finance_amount',
                'monthly_payment', 'installment_months', 'custom_start_date',
                'custom_total_interest', 'custom_profit_percentage',
                'custom_finance_profit_percentage', 'custom_grand_total_with_interest',
                'status', 'docstatus'
            ],
            order_by='transaction_date desc',
            ignore_permissions=False,
            # Include all documents regardless of docstatus (including cancelled)
            or_filters=[
                {'docstatus': 0},  # Draft
                {'docstatus': 1},  # Submitted
                {'docstatus': 2}   # Cancelled
            ]
        )

        if not applications:
            return {
                'success': False,
                'message': 'Shartnoma topilmadi'
            }

        report_data = []

        for app in applications:
            app_name = app.get('name')

            # Get child items
            items = frappe.get_all(
                'Installment Application Item',
                filters={'parent': app_name},
                fields=['item_code', 'item_name', 'imei', 'qty', 'rate', 'amount', 'custom_supplier'],
                order_by='idx asc'
            )

            # If no items, still show parent with empty item info
            if not items:
                items = [{}]

            # Create one row for each item
            for item in items:
                # Get supplier name if supplier exists
                supplier_name = ''
                if item.get('custom_supplier'):
                    supplier_name = frappe.db.get_value('Supplier', item.get('custom_supplier'), 'supplier_name') or item.get('custom_supplier')

                row = {
                    'shartnoma_raqami': app.get('name'),
                    'mijoz': app.get('customer_name') or app.get('customer'),
                    'sana': str(app.get('transaction_date') or ''),
                    'status': app.get('status'),

                    # Item info
                    'mahsulot_kodi': item.get('item_code') or '',
                    'mahsulot_nomi': item.get('item_name') or '',
                    'imei': item.get('imei') or '',
                    'soni': item.get('qty') or 0,
                    'tan_narxi_usd': item.get('rate') or 0,
                    'item_jami_usd': item.get('amount') or 0,
                    'pastavshik': supplier_name,

                    # Payment info
                    'jami_summa_usd': app.get('total_amount') or 0,
                    'boshlangich_tolov_usd': app.get('downpayment_amount') or 0,
                    'qolgan_summa_usd': app.get('finance_amount') or 0,
                    'oylik_tolov_usd': app.get('monthly_payment') or 0,
                    'oylar_soni': app.get('installment_months') or 0,
                    'birinchi_tolov_sanasi': str(app.get('custom_start_date') or ''),

                    # Profit info
                    'foyda_summasi_usd': app.get('custom_total_interest') or 0,
                    'marja_foiz': app.get('custom_profit_percentage') or 0,
                    'ustama_foiz': app.get('custom_finance_profit_percentage') or 0,
                    'jami_tolov_usd': app.get('custom_grand_total_with_interest') or 0,
                }

                report_data.append(row)

        # Prepare for sheets
        if not report_data:
            return {
                'success': False,
                'message': 'Ma\'lumot topilmadi'
            }

        headers = list(report_data[0].keys())
        rows = [[str(row.get(h, '')) for h in headers] for row in report_data]
        sheet_data = [headers] + rows

        # Write to sheet
        result = exporter._write_to_google_sheets(
            sheet_data,
            spreadsheet_id,
            sheet_name
        )

        return {
            'success': True,
            'spreadsheet_id': result['spreadsheet_id'],
            'spreadsheet_url': result['spreadsheet_url'],
            'sheet_name': result['sheet_name'],
            'rows_exported': len(report_data),
            'records_exported': len(report_data),
            'message': f'Shartnoma: {len(applications)} ta shartnoma, {len(report_data)} ta qator'
        }

    except Exception as e:
        error_msg = f"Shartnoma eksport xatosi: {str(e)}"
        frappe.log_error(error_msg, "Installment Application Export")
        return {
            'success': False,
            'message': error_msg
        }


@frappe.whitelist()
def export_all_doctypes_to_sheet(spreadsheet_id=None):
    """
    Export all main doctypes to Google Sheet automatically

    Args:
        spreadsheet_id: Optional spreadsheet ID (if None, creates new)

    Returns:
        dict: Export results for all doctypes
    """
    try:
        # Define doctypes to export with their display names
        doctypes_to_export = [
            {'doctype': 'Customer', 'sheet_name': 'Mijozlar'},
            {'doctype': 'Supplier', 'sheet_name': 'Pastavshiklar'},
            {'doctype': 'Payment Entry', 'sheet_name': 'Kassa Kirim-chiqim'},
            {'doctype': 'Item', 'sheet_name': 'Mahsulotlar'},
        ]

        results = []
        exporter = GoogleSheetsExporter()

        # Use single spreadsheet for all exports
        current_spreadsheet_id = spreadsheet_id

        # First, export Installment Application using specialized function
        try:
            frappe.logger().info("Exporting Shartnoma (Installment Application)")
            installment_result = export_installment_application(
                spreadsheet_id=current_spreadsheet_id,
                sheet_name='Shartnoma'
            )

            if installment_result.get('success'):
                # Use the same spreadsheet for subsequent exports
                if not current_spreadsheet_id:
                    current_spreadsheet_id = installment_result.get('spreadsheet_id')

                results.append({
                    'doctype': 'Installment Application',
                    'sheet_name': 'Shartnoma',
                    'success': True,
                    'records': installment_result.get('records_exported', 0),
                    'message': installment_result.get('message', '')
                })
            else:
                results.append({
                    'doctype': 'Installment Application',
                    'sheet_name': 'Shartnoma',
                    'success': False,
                    'message': installment_result.get('message', 'Export failed')
                })
        except Exception as e:
            frappe.log_error(f"Failed to export Installment Application: {str(e)}", "Installment Export Error")
            results.append({
                'doctype': 'Installment Application',
                'sheet_name': 'Shartnoma',
                'success': False,
                'message': str(e)
            })

        for doc_config in doctypes_to_export:
            try:
                doctype = doc_config['doctype']
                sheet_name = doc_config['sheet_name']
                
                frappe.logger().info(f"Exporting {doctype} to {sheet_name}")
                
                # Export doctype (allow passing filters from config)
                result = exporter.export_doctype(
                    doctype_name=doctype,
                    filters=doc_config.get('filters'),
                    fields=doc_config.get('fields'),  # Pass fields from config
                    spreadsheet_id=current_spreadsheet_id,
                    sheet_name=sheet_name
                )
                
                if result.get('success'):
                    # Use the same spreadsheet for subsequent exports
                    if not current_spreadsheet_id:
                        current_spreadsheet_id = result.get('spreadsheet_id')
                    
                    results.append({
                        'doctype': doctype,
                        'sheet_name': sheet_name,
                        'success': True,
                        'records': result.get('records_exported', 0),
                        'message': f"{sheet_name}: {result.get('records_exported', 0)} records"
                    })
                else:
                    results.append({
                        'doctype': doctype,
                        'sheet_name': sheet_name,
                        'success': False,
                        'message': result.get('message', 'Export failed')
                    })
                    
            except Exception as e:
                frappe.log_error(f"Failed to export {doctype}: {str(e)}", "Doctype Export Error")
                results.append({
                    'doctype': doctype,
                    'sheet_name': sheet_name,
                    'success': False,
                    'message': str(e)
                })
        
        # Count successful exports
        successful = sum(1 for r in results if r['success'])
        total = len(doctypes_to_export)
        
        # Get spreadsheet URL
        spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{current_spreadsheet_id}"
        
        return {
            'success': successful > 0,
            'spreadsheet_id': current_spreadsheet_id,
            'spreadsheet_url': spreadsheet_url,
            'total_exports': total,
            'successful_exports': successful,
            'failed_exports': total - successful,
            'results': results,
            'message': f"Exported {successful}/{total} doctypes successfully"
        }
        
    except Exception as e:
        error_msg = f"Bulk export failed: {str(e)}"
        frappe.log_error(error_msg, "Bulk Export Error")
        return {
            'success': False,
            'message': error_msg
        }
