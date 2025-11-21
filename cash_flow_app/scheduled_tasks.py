# -*- coding: utf-8 -*-
"""
Scheduled Tasks for Cash Flow App
Har kuni soat 00:00 da avtomatik export
"""

import frappe
from frappe import _


def daily_export_to_google_sheets():
    """
    Har kuni soat 00:00 da avtomatik ravishda 5 ta doctypeni
    Google Sheets ga export qiladi

    Bu funksiya hooks.py da scheduler_events orqali har kuni ishga tushadi
    """
    try:
        frappe.logger().info("🕐 Starting scheduled daily export to Google Sheets...")

        # Bu yerda sizning Google Sheet ID ni qo'yish kerak
        # Button dan export qilganda ishlatilgan ID ni ishlatamiz
        SHEET_ID = '13brBTN3zmN0eWVJ0G7t0d53jI_eSmUBwb8BnMkgAoMc'

        # Export all doctypes function ni chaqiramiz
        from cash_flow_app.google_sheets_integration import export_all_doctypes_to_sheet

        result = export_all_doctypes_to_sheet(spreadsheet_id=SHEET_ID)

        if result.get('success'):
            frappe.logger().info(
                f"✅ Scheduled export successful: {result.get('successful_exports')}/{result.get('total_exports')} doctypes exported"
            )

            # Success log
            frappe.log_error(
                title="✅ Daily Export Success",
                message=f"""
                Successful export at {frappe.utils.now()}

                Spreadsheet URL: {result.get('spreadsheet_url')}
                Total exports: {result.get('total_exports')}
                Successful: {result.get('successful_exports')}
                Failed: {result.get('failed_exports')}

                Results:
                {frappe.as_json(result.get('results'), indent=2)}
                """
            )
        else:
            error_msg = result.get('message', 'Unknown error')
            frappe.logger().error(f"❌ Scheduled export failed: {error_msg}")

            # Error log
            frappe.log_error(
                title="❌ Daily Export Failed",
                message=f"""
                Failed export at {frappe.utils.now()}

                Error: {error_msg}
                """
            )

    except Exception as e:
        error_msg = f"Scheduled export error: {str(e)}"
        frappe.logger().error(f"❌ {error_msg}")

        frappe.log_error(
            title="❌ Daily Export Exception",
            message=f"""
            Exception during scheduled export at {frappe.utils.now()}

            Error: {str(e)}
            """
        )


def test_scheduled_export():
    """
    Test funksiyasi - bu funksiyani qo'lda chaqirib test qilish mumkin

    Usage:
        bench --site your-site console
        >>> from cash_flow_app.scheduled_tasks import test_scheduled_export
        >>> test_scheduled_export()
    """
    frappe.logger().info("🧪 Testing scheduled export...")
    daily_export_to_google_sheets()
    frappe.logger().info("✅ Test completed. Check Error Log for results.")
