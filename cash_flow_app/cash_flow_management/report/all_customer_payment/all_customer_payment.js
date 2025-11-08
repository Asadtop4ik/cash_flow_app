// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["All Customer Payment"] = {
    "filters": [
       {
          "fieldname": "from_date",
          "label": __("From Date"),
          "fieldtype": "Date",
          "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
          "reqd": 1
       },
       {
          "fieldname": "to_date",
          "label": __("To Date"),
          "fieldtype": "Date",
          "default": frappe.datetime.get_today(),
          "reqd": 1
       },
       {
          "fieldname": "classification",
          "label": __("Customer Classification"),
          "fieldtype": "Select",
          "options": ["", "A", "B", "C"],
          "default": ""
       },
       {
          "fieldname": "customer",
          "label": __("Customer"),
          "fieldtype": "Link",
          "options": "Customer"
       },
       {
          "fieldname": "report_type",
          "label": __("Report Type"),
          "fieldtype": "Select",
          "options": ["Monthly", "Daily"],
          "default": "Monthly",
          "reqd": 1
       }
    ],

    // ✅ Styling funksiyalari ham shu ichida
    onload: function(report) {
       // Reportga CSS qo'shish
       frappe.after_ajax(() => {
          this.add_total_row_styling();
       });
    },

    refresh: function(report) {
       // Har refresh bo'lganda styling qo'llash
       this.add_total_row_styling();
    },

    add_total_row_styling: function() {
       setTimeout(() => {
          // Barcha rowlarni topish
          const rows = document.querySelectorAll('.dt-row');

          if (rows.length > 0) {
             // Oxirgi row (Jami row)
             const lastRow = rows[rows.length - 1];

             // Barcha celllarni bold qilish
             const cells = lastRow.querySelectorAll('.dt-cell__content');
             cells.forEach(cell => {
                cell.style.fontWeight = 'bold';
                cell.style.backgroundColor = '#f0f0f0'; // Opsional: background color
             });
          }
       }, 100);
    }
};
