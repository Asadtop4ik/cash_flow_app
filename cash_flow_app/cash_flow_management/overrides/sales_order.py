from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

class CustomSalesOrder(SalesOrder):
    def set_payment_schedule(self):
        """
        Override to always use transaction_date as base for payment schedule
        instead of delivery_date
        """
        # --- Fix: force base_date to transaction_date ---
        base_date = self.transaction_date

        # Asl funksiyani chaqirishdan oldin, self.delivery_date ni ham moslashtiramiz
        self.base_date_for_schedule = base_date

        super().set_payment_schedule()
