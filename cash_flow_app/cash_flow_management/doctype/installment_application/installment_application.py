# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, add_months, getdate
from frappe import _

class InstallmentApplication(Document):
    def validate(self):
        """Validate before save"""
        self.calculate_totals()
        self.validate_payment_terms()
        
        # Clear cancelled Sales Order link for amended documents
        if self.sales_order:
            frappe.logger().info(f"Checking SO link: {self.sales_order}")
            # Check if linked SO is cancelled using db query (faster and safer)
            so_status = frappe.db.get_value("Sales Order", self.sales_order, "docstatus")
            frappe.logger().info(f"SO Status: {so_status}")
            
            if so_status == 2:  # Cancelled
                frappe.logger().info(f"Clearing cancelled SO link: {self.sales_order}")
                self.sales_order = None
            else:
                frappe.logger().info(f"SO is not cancelled, keeping link")

    def calculate_totals(self):
        """Calculate total amount and payment breakdown with interest"""
        # Calculate total from items
        total = 0
        for item in self.items:
            item.amount = flt(item.qty) * flt(item.rate)
            total += item.amount

        self.total_amount = total

        # Calculate finance amount (qolgan summa)
        # Finance Amount = Total - Downpayment
        self.finance_amount = flt(self.total_amount) - flt(self.downpayment_amount)

        # Calculate interest based on user input
        # Interest = (Monthly Payment × Months) - Finance Amount
        monthly_payment = flt(self.monthly_payment)
        months = flt(self.installment_months)

        total_installments = monthly_payment * months
        total_interest = total_installments - flt(self.finance_amount)

        self.custom_total_interest = total_interest

        # Grand total = Downpayment + Total Installments
        grand_total = flt(self.downpayment_amount) + total_installments
        self.custom_grand_total_with_interest = grand_total

        # Marja Foiz (%) = (Foyda / Oylik To'lovlar) × 100%
        # Bu ko'rsatadi: oylik to'lovlarning qancha qismi foyda
        if total_installments > 0:
            profit_percentage = (total_interest / total_installments) * 100
            self.custom_profit_percentage = round(profit_percentage, 2)  # 2 raqam verguldan keyin
        else:
            self.custom_profit_percentage = 0

        # Ustama Foiz (%) = (Foyda / Qolgan Summa) × 100%
        # Bu ko'rsatadi: qolgan summadan qancha foiz foyda
        if flt(self.finance_amount) > 0:
            finance_profit_percentage = (total_interest / flt(self.finance_amount)) * 100
            self.custom_finance_profit_percentage = round(finance_profit_percentage, 2)  # 2 raqam verguldan keyin
        else:
            self.custom_finance_profit_percentage = 0

        # Debug log
        frappe.logger().info(f"Installment Calc: Total={self.total_amount}, Downpayment={self.downpayment_amount}, Finance={self.finance_amount}, Monthly={self.monthly_payment}, Interest={self.custom_total_interest}, Marja%={self.custom_profit_percentage}, Finance%={self.custom_finance_profit_percentage}")

    def validate_payment_terms(self):
        """Validate payment terms"""
        # Boshlang'ich to'lov 0 yoki ijobiy bo'lishi mumkin (ixtiyoriy)
        if flt(self.downpayment_amount) < 0:
            frappe.throw(_("Boshlang'ich to'lov 0 dan kam bo'lishi mumkin emas"))

        # Agar boshlang'ich to'lov kiritilgan bo'lsa, umumiy narxdan kam bo'lishi kerak
        if flt(self.downpayment_amount) > 0 and flt(self.downpayment_amount) >= flt(self.total_amount):
            frappe.throw(_("Boshlang'ich to'lov umumiy narxdan kam bo'lishi kerak"))

        if flt(self.installment_months) < 1:
            frappe.throw(_("Oylar soni kamida 1 bo'lishi kerak"))

        if flt(self.total_amount) <= 0:
            frappe.throw(_("Umumiy narx 0 dan katta bo'lishi kerak"))

        if flt(self.monthly_payment) <= 0:
            frappe.throw(_("Oylik to'lov 0 dan katta bo'lishi kerak"))

    def on_submit(self):
        """Create Sales Order after submission"""
        self.status = "Approved"
        
        # If this is an amended document, cancel old Sales Order and create new one
        if self.amended_from:
            old_doc = frappe.get_doc("Installment Application", self.amended_from)
            if old_doc.sales_order:
                old_so = frappe.get_doc("Sales Order", old_doc.sales_order)
                if old_so.docstatus == 1:
                    old_so.cancel()
                    frappe.msgprint(_("Eski Sales Order {0} bekor qilindi").format(old_so.name), alert=True)
            
            # Always create new SO for amended docs
            self.create_sales_order()
        elif not self.sales_order:
            # For new docs, create SO if doesn't exist
            self.create_sales_order()

    def create_sales_order(self):
        """Create Sales Order with Payment Schedule"""
                # Create Sales Order
        company = frappe.defaults.get_user_default("Company")

        so = frappe.get_doc({
            "doctype": "Sales Order",
            "naming_series": "CON-.YYYY.-.#####",
            "customer": self.customer,
            "transaction_date": self.transaction_date,
            "delivery_date": add_months(self.transaction_date, self.installment_months),
            "company": company,
            "currency": "USD",
            "conversion_rate": 1.0,  # USD to USD = 1
            "plc_conversion_rate": 1.0,  # Price List Currency to USD = 1
            "ignore_pricing_rule": 1,
            "items": []
        })

        # Add items from Installment Application
        # IMPORTANT: Add interest as a separate line item
        for item in self.items:
            so_item = {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "uom": item.get("uom") or "Nos",
                "conversion_factor": 1.0,
                "custom_imei": item.get("imei")  # Copy IMEI if exists
            }
            
            # Copy custom_notes if exists (for Sales Order)
            if item.get("custom_notes"):
                so_item["description"] = item.get("custom_notes")
            
            so.append("items", so_item)
        
        # Add interest as separate item if exists
        if flt(self.custom_total_interest) > 0:
            # Check if "Interest Charge" item exists, if not create a generic description item
            so.append("items", {
                "item_code": frappe.db.get_value("Item", {"item_name": "Interest Charge"}, "name") or self.items[0].item_code,
                "item_name": "Foiz (Interest)",
                "description": f"Muddatli to'lov foizi - {self.installment_months} oy",
                "qty": 1,
                "uom": "Nos",
                "conversion_factor": 1.0,
                "rate": flt(self.custom_total_interest),
                "amount": flt(self.custom_total_interest)
            })

        # Calculate totals first
        so.run_method("calculate_taxes_and_totals")

        # Get start date - use custom_start_date if available, otherwise transaction_date
        start_date = getdate(self.get("custom_start_date") or self.transaction_date)

        # Now Sales Order grand_total should match our custom_grand_total_with_interest
        so_grand_total = flt(so.grand_total)

        # Add downpayment schedule only if downpayment > 0
        if flt(self.downpayment_amount) > 0:
            downpayment_portion = (flt(self.downpayment_amount) / so_grand_total) * 100
            so.append("payment_schedule", {
                "due_date": start_date,
                "invoice_portion": downpayment_portion,
                "payment_amount": flt(self.downpayment_amount)
            })

        # Monthly payment schedules with custom payment day
        monthly_portion = (flt(self.monthly_payment) / so_grand_total) * 100
        payment_day = int(self.custom_monthly_payment_day) if self.custom_monthly_payment_day else getdate(start_date).day

        # Get start date components
        start_date_obj = getdate(start_date)
        current_year = start_date_obj.year
        current_month = start_date_obj.month

        for i in range(1, int(self.installment_months) + 1):
            # Calculate next month
            target_month = current_month + i
            target_year = current_year

            # Handle year overflow
            while target_month > 12:
                target_month -= 12
                target_year += 1

            # Create date with specific payment_day
            from datetime import date
            from calendar import monthrange

            try:
                # Try to create date with payment_day
                due_date = date(target_year, target_month, payment_day)
            except ValueError:
                # If day doesn't exist in month (e.g., Feb 30), use last day
                last_day = monthrange(target_year, target_month)[1]
                due_date = date(target_year, target_month, last_day)

            so.append("payment_schedule", {
                "due_date": due_date,
                "invoice_portion": monthly_portion,
                "payment_amount": flt(self.monthly_payment)
            })

        # Store custom fields in Sales Order BEFORE calculate
        so.custom_contract_type = "Nasiya"
        so.custom_downpayment_amount = flt(self.downpayment_amount)
        so.custom_total_interest = flt(self.custom_total_interest)
        so.custom_grand_total_with_interest = flt(self.custom_grand_total_with_interest)

        # Recalculate to ensure totals match
        so.run_method("calculate_taxes_and_totals")

        # Save and submit Sales Order
        so.insert(ignore_permissions=True)
        so.submit()

        # Update Installment Application
        self.db_set("sales_order", so.name)
        self.db_set("status", "Sales Order Created")

        # Create Downpayment Payment Entry (Draft)
        # ⚠️ IMPORTANT: Only create PE for NEW documents, not for AMENDED ones!
        # Amended docs will be handled by on_submit_installment_application hook
        pe_name = None
        if flt(self.downpayment_amount) > 0 and not self.amended_from:
            pe_name = self.create_downpayment_payment_entry(so.name)

        # Success message
        message = _("Sales Order {0} created successfully").format(
            f'<a href="/app/sales-order/{so.name}">{so.name}</a>'
        )

        if pe_name:
            message += "<br>" + _("Boshlang'ich to'lov Payment Entry {0} yaratildi (Draft)").format(
                f'<a href="/app/payment-entry/{pe_name}">{pe_name}</a>'
            )

        frappe.msgprint(message)

    def create_downpayment_payment_entry(self, sales_order_name):
        """
        Create draft Payment Entry for downpayment
        Operator will verify and submit manually
        """
        try:
            # Get default cash account
            cash_settings = frappe.get_single("Cash Settings")
            default_cash_account = cash_settings.get("default_cash_account")

            if not default_cash_account:
                frappe.msgprint(_("⚠️ Cash Settings'da default_cash_account topilmadi!"), alert=True)
                return None

            # Get company
            company = frappe.defaults.get_user_default("Company")
            
            # ✅ IMPORTANT: Use custom_start_date for posting_date (for historical entries)
            # This allows entering old contracts with correct payment dates
            posting_date = getdate(self.get("custom_start_date") or self.transaction_date)

            # Create Payment Entry
            pe = frappe.get_doc({
                "doctype": "Payment Entry",
                "naming_series": "CIN-.YYYY.-.#####",
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": self.customer,
                "company": company,
                "posting_date": posting_date,  # ✅ Use custom_start_date
                "paid_amount": flt(self.downpayment_amount),
                "received_amount": flt(self.downpayment_amount),
                "paid_to": default_cash_account,
                "paid_to_account_currency": "USD",
                "paid_from_account_currency": "USD",
                "source_exchange_rate": 1.0,
                "target_exchange_rate": 1.0,
                "reference_no": sales_order_name,
                "reference_date": posting_date,  # ✅ Use same date
                "custom_counterparty_category": "Klient",
                "custom_contract_reference": sales_order_name,
                "mode_of_payment": "Naqd",
                "remarks": f"Boshlang'ich to'lov - Shartnoma {sales_order_name}\nInstallment Application: {self.name}"
            })

            # Add reference to Sales Order (IMPORTANT for linking!)
            pe.append("references", {
                "reference_doctype": "Sales Order",
                "reference_name": sales_order_name,
                "total_amount": flt(self.custom_grand_total_with_interest),
                "outstanding_amount": flt(self.custom_grand_total_with_interest),
                "allocated_amount": flt(self.downpayment_amount)
            })

            # Insert as Draft (operator will submit)
            pe.insert(ignore_permissions=True)

            frappe.logger().info(f"Created downpayment PE {pe.name} for SO {sales_order_name}")

            return pe.name

        except Exception as e:
            frappe.log_error(f"Error creating downpayment PE: {e}")
            frappe.msgprint(_("⚠️ Boshlang'ich to'lov Payment Entry yaratilmadi: {0}").format(str(e)), alert=True)
            return None

    def on_cancel(self):
        """Cancel related Sales Order"""
        print(f"\n🔴 on_cancel() CALLED for InstApp: {self.name}")
        frappe.logger().info(f"🔴 Cancelling Installment Application: {self.name}")
        
        if self.sales_order:
            try:
                print(f"   📋 Linked Sales Order: {self.sales_order}")
                frappe.logger().info(f"Getting SO: {self.sales_order}")
                
                so = frappe.get_doc("Sales Order", self.sales_order, ignore_permissions=True)
                
                print(f"   📊 SO Status: {so.docstatus} ({['Draft', 'Submitted', 'Cancelled'][so.docstatus]})")
                frappe.logger().info(f"SO {so.name} status: {so.docstatus}")
                
                if so.docstatus == 1:  # Submitted
                    print(f"   ⚠️  Cancelling Sales Order...")
                    frappe.logger().info(f"Cancelling SO {so.name}")
                    
                    # Cancel SO - this will trigger on_cancel_sales_order hook
                    # which will cancel all linked Payment Entries
                    so.cancel()
                    
                    print(f"   ✅ Sales Order cancelled: {so.name}")
                    frappe.logger().info(f"✅ SO {so.name} cancelled successfully")
                    
                    frappe.msgprint(
                        _("✅ Sales Order {0} va bog'langan to'lovlar bekor qilindi").format(so.name),
                        alert=True
                    )
                elif so.docstatus == 2:  # Already cancelled
                    print(f"   ℹ️  Sales Order already cancelled")
                    frappe.logger().info(f"SO {so.name} already cancelled")
                else:
                    print(f"   ℹ️  Sales Order is draft, skipping cancel")
                    
            except Exception as e:
                print(f"   ❌ Error cancelling SO: {e}")
                frappe.logger().error(f"Error cancelling SO {self.sales_order}: {e}")
                import traceback
                traceback.print_exc()
                
                # Don't throw - allow InstApp to be cancelled even if SO cancel fails
                frappe.msgprint(
                    _("⚠️ Xatolik: Sales Order bekor qilinmadi. Qo'lda bekor qiling: {0}").format(self.sales_order),
                    alert=True,
                    indicator="orange"
                )
        else:
            print(f"   ℹ️  No Sales Order linked")
            frappe.logger().info(f"No SO linked to InstApp {self.name}")

        self.status = "Cancelled"
        print(f"   ✅ InstApp status updated to Cancelled")

