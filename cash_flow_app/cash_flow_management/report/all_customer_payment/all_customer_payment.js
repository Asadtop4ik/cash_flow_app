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

   "formatter": function(value, row, column, data, default_formatter) {
      value = default_formatter(value, row, column, data);

      // classification fieldida 'Jami' borligini aniqlash (HTML taglarni olib tashlash)
      let isJamiRow = false;
      if (data) {
         if (
            (data.classification && data.classification.replace(/<[^>]*>?/gm, '') === 'Jami') ||
            (data.customer === 'Jami') ||
            (data.customer_name === 'Jami')
         ) {
            isJamiRow = true;
         }
      }

      if (isJamiRow && value) {
         value = `<span style="font-weight: bold;">${value}</span>`;
      }
      return value;
   }
};
