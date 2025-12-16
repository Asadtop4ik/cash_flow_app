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
	},
	"get_datatable_options": function(options) {
		return Object.assign(options, {
			events: {
				onCheckRow: function() {},
				onRemoveColumn: function() {},
				onDestroy: function() {},
				onCellChanged: function(colIndex, rowIndex, oldValue, newValue, cellContent) {
					// Get the column and row data
					let column = options.columns[colIndex];
					let row = options.data[rowIndex];

					// Only handle note column changes
					if (column && column.id === 'note' && row && row.contract_link) {
						let contract_id = row.contract_link;

						console.log('Saving note:', {
							contract_id: contract_id,
							oldValue: oldValue,
							newValue: newValue,
							colIndex: colIndex,
							rowIndex: rowIndex
						});

						// Save to database using custom API that works with submitted docs
						frappe.call({
							method: 'cash_flow_app.cash_flow_management.api.eslatmalar_api.save_contract_note',
							args: {
								contract_id: contract_id,
								note_value: newValue
							},
							callback: function(r) {
								console.log('Save response:', r);
								if (r.message && r.message.success) {
									console.log('Saved value from DB:', r.message.saved_value);
									frappe.show_alert({
										message: r.message.message + ' (DB: ' + (r.message.saved_value || 'null') + ')',
										indicator: 'green'
									}, 5);
								} else {
									frappe.show_alert({
										message: r.message ? r.message.message : __('Izohni saqlashda xatolik'),
										indicator: 'red'
									}, 5);
								}
							},
							error: function(r) {
								console.error('Save error:', r);
								frappe.show_alert({
									message: __('Izohni saqlashda xatolik'),
									indicator: 'red'
								}, 5);
							}
						});
					}
				}
			}
		});
	}
};
