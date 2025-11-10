// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Kassa Hisoboti"] = {
    "filters": [
       {
          "fieldname": "from_date",
          "label": __("From Date"),
          "fieldtype": "Date",
          "default": frappe.datetime.month_start(),
          "reqd": 1
       },
       {
          "fieldname": "to_date",
          "label": __("To Date"),
          "fieldtype": "Date",
          "default": frappe.datetime.month_end(),
          "reqd": 1
       },
       {
          "fieldname": "payment_type",
          "label": __("Payment Type"),
          "fieldtype": "Select",
          "options": "\nReceive\nPay",
          "default": ""
       },
       {
          "fieldname": "mode_of_payment",
          "label": __("Mode of Payment"),
          "fieldtype": "Link",
          "options": "Mode of Payment"
       },
       {
          "fieldname": "counterparty_category",
          "label": __("Category"),
          "fieldtype": "Link",
          "options": "Counterparty Category"
       },
       {
          "fieldname": "cash_account",
          "label": __("Cash"),
          "fieldtype": "Link",
          "options": "Account",
          "get_query": function() {
             return {
                "filters": {
                   "account_type": "Cash",
                   "is_group": 0
                }
             };
          }
       }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
       value = default_formatter(value, row, column, data);

       if (column.fieldname == "payment_type") {
          if (data && data.payment_type == "Receive") {
             value = '<span class="badge badge-success">Kirim</span>';
          } else if (data && data.payment_type == "Pay") {
             value = '<span class="badge badge-danger">Chiqim</span>';
          }
       }

       if (column.fieldname == "balance") {
          if (data && data.balance < 0) {
             value = '<span style="color: red; font-weight: bold;">' + value + '</span>';
          } else if (data && data.balance > 0) {
             value = '<span style="color: green; font-weight: bold;">' + value + '</span>';
          }
       }

       return value;
    },

    onload: function(report) {
       report.page.add_inner_button(__('Export to Excel'), function() {
          report.export_report('xlsx');
       });
    }
};
