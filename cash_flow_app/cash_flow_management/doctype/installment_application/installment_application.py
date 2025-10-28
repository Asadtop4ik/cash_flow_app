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
        if flt(self.downpayment_amount) < 0:
            frappe.throw(_("Boshlang'ich to'lov 0 dan kam bo'lishi mumkin emas"))

        if flt(self.downpayment_amount) >= flt(self.total_amount):
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

        # Check if Sales Order already exists
        if not self.sales_order:
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
            so.append("items", {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "uom": item.get("uom") or "Nos",
                "conversion_factor": 1.0,
                "custom_imei": item.get("imei")  # Copy IMEI if exists
            })

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

        # Downpayment schedule
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
        pe_name = None
        if flt(self.downpayment_amount) > 0:
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

            # Create Payment Entry
            pe = frappe.get_doc({
                "doctype": "Payment Entry",
                "naming_series": "CIN-.YYYY.-.#####",
                "payment_type": "Receive",
                "party_type": "Customer",
                "party": self.customer,
                "company": company,
                "posting_date": self.transaction_date,
                "paid_amount": flt(self.downpayment_amount),
                "received_amount": flt(self.downpayment_amount),
                "paid_to": default_cash_account,
                "paid_to_account_currency": "USD",
                "paid_from_account_currency": "USD",
                "source_exchange_rate": 1.0,
                "target_exchange_rate": 1.0,
                "reference_no": sales_order_name,
                "reference_date": self.transaction_date,
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
        if self.sales_order:
            so = frappe.get_doc("Sales Order", self.sales_order)
            if so.docstatus == 1:
                so.cancel()
                frappe.msgprint(_("Sales Order {0} cancelled").format(so.name))

        self.status = "Cancelled"
