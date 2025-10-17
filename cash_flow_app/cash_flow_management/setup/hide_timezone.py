"""
Hide timezone display in Installment Application
"""

import frappe

def hide_timezone_in_forms():
    """Hide time_zone field display"""
    
    # This is controlled by system settings, not field-level
    # We'll hide it via client script instead
    
    print("⚠️ Timezone field is system-level. Will hide via JS.")
    print("✅ Check installment_application.js for hide logic")

if __name__ == "__main__":
    hide_timezone_in_forms()
