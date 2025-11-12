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
            
            # Determine fields to fetch
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
            fields = [f for f in fields if f in db_columns]
            
            if not fields:
                frappe.throw(_("No valid fields found for export"))
            
            frappe.logger().info(f"Fetching {len(fields)} fields")
            
            # Fetch data
            data = frappe.get_all(
                doctype_name,
                filters=filters or {},
                fields=fields,
                limit_page_length=0,  # No limit
                order_by='modified desc'
            )
            
            frappe.logger().info(f"Fetched {len(data)} records")
            
            return data
            
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
