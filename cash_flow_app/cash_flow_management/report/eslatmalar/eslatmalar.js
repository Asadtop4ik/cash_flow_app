// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Eslatmalar"] = {
	"filters": [

	],
	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Make group headers and subtotals bold
		if (data && data.bold) {
			value = value.bold();
			// Add background color for group headers
			if (data.indent === 0) {
				var $value = $(value).css({
					"background-color": "#f0f4f7",
					"font-weight": "bold",
					"font-size": "13px"
				});
				value = $value.wrap('<p>').parent().html();
			} else if (data.customer_link === "JAMI:") {
				// Subtotal rows - yellow background
				var $value = $(value).css({
					"background-color": "#fff9e6",
					"font-weight": "bold"
				});
				value = $value.wrap('<p>').parent().html();
			}
		}

		return value;
	},
	"onload": function(report) {
		// Auto-refresh report when payment entry is submitted
		frappe.realtime.on("refresh_report", function(data) {
			console.log("Payment Entry submitted - refreshing Eslatmalar report");
			if (report && report.refresh) {
				report.refresh();
			}
		});
	}
};
