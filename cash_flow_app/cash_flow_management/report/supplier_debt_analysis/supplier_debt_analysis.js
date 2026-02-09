// Copyright (c) 2025, Cash Flow App and contributors
// For license information, please see license.txt

frappe.query_reports["Supplier Debt Analysis"] = {
	"filters": [
		{
			"fieldname": "supplier",
			"label": __("Yetkazib beruvchi"),
			"fieldtype": "Link",
			"options": "Supplier",
			"reqd": 1,
			"width": 180
		},
		{
			"fieldname": "from_date",
			"label": __("Boshlanish sanasi"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -6),
			"width": 130
		},
		{
			"fieldname": "to_date",
			"label": __("Tugash sanasi"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"width": 130
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// JAMI qatori
		if (data && data.is_total_row) {
			if (column.fieldname == "item_name") {
				return `<span style="font-weight: 700; font-size: 15px; color: #1e3a8a;">JAMI</span>`;
			}
			if (['kredit', 'debit', 'outstanding'].includes(column.fieldname)) {
				let amount = flt(data[column.fieldname]);
				let formatted = format_currency_with_symbol(amount);
				return `<span style="font-weight: 700; color: #1e3a8a; font-size: 15px;">${formatted}</span>`;
			}
			return '';
		}

		// Boshlang'ich qoldiq qatori
		if (data && data.is_initial_row) {
			if (column.fieldname == "item_name") {
				return `<span style="font-weight: 600; font-size: 13px; color: #2563eb; font-style: italic;">${value}</span>`;
			}
			if (['kredit', 'debit', 'outstanding'].includes(column.fieldname)) {
				let amount = flt(data[column.fieldname]);
				let formatted = format_currency_with_symbol(amount);
				return `<span style="font-weight: 600; color: #2563eb; font-size: 13px;">${formatted}</span>`;
			}
			return '';
		}

		// Kredit - qizil
		if (column.fieldname == "kredit" && flt(data.kredit) > 0) {
			let formatted = format_currency_with_symbol(flt(data.kredit));
			value = `<span style="color: #dc2626; font-weight: 600; font-size: 13px;">${formatted}</span>`;
		}

		// Debit - yashil
		if (column.fieldname == "debit" && flt(data.debit) > 0) {
			let formatted = format_currency_with_symbol(flt(data.debit));
			value = `<span style="color: #16a34a; font-weight: 600; font-size: 13px;">${formatted}</span>`;
		}

		// Qoldiq
		if (column.fieldname == "outstanding") {
			let amount = flt(data.outstanding);
			let formatted = format_currency_with_symbol(Math.abs(amount));
			if (amount > 0) {
				value = `<span style="color: #dc2626; font-weight: 700; font-size: 13px;">${formatted}</span>`;
			} else if (amount < 0) {
				value = `<span style="color: #16a34a; font-weight: 700; font-size: 13px;">-${formatted}</span>`;
			} else {
				value = `<span style="color: #6b7280; font-weight: 600; font-size: 13px;">${formatted}</span>`;
			}
		}

		// Hujjat linki
		if (column.fieldname == "document" && data.document && data.document_type) {
			// Initial Balance uchun link qilmaslik
			if (data.document === 'Initial Balance') {
				value = `<span style="color: #2563eb; font-weight: 600; font-size: 13px; font-style: italic;">${data.document}</span>`;
			} else {
				let route = data.document_type.toLowerCase().replace(/ /g, '-');
				value = `<a href="/app/${route}/${data.document}" target="_blank" style="color: #2563eb; font-weight: 600; font-size: 13px;">${data.document}</a>`;
			}
		}

		// Note category badge
		if (column.fieldname == "note_category" && value) {
			let text = value.replace(/<[^>]*>/g, '').trim();
			if (text) {
				let badge_color = get_category_badge_color(text);
				value = `<span class="badge" style="background-color: ${badge_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">${text}</span>`;
			}
		}

		// Note text - limited display
		if (column.fieldname == "note_text" && value) {
			let text = value.replace(/<[^>]*>/g, '').trim();
			if (text && text.length > 50) {
				text = text.substring(0, 50) + '...';
			}
			if (text) {
				value = `<span style="font-size: 12px; color: #374151;" title="${value.replace(/<[^>]*>/g, '').trim()}">${text}</span>`;
			}
		}

		// Note date formatting
		if (column.fieldname == "note_date" && value) {
			let text = value.replace(/<[^>]*>/g, '').trim();
			if (text) {
				value = `<span style="font-size: 11px; color: #6b7280;">${text}</span>`;
			}
		}

		if (column.fieldname == "custom_cashier" && value && value.trim()) {
			value = `<span style="background:#bbf7d0; color:#065f46; padding:2px 6px; border-radius:3px; font-size:11px; font-weight:600;">${value}</span>`;
		}


		return value;
	},

	"onload": function(report) {
		// Izohlar menu
		report.page.add_inner_button(__('Yangi Izoh'), function() {
			show_add_note_dialog(report);
		}, __('Izohlar'));

		report.page.add_inner_button(__('Barcha Izohlar'), function() {
			let supplier = frappe.query_report.get_filter_value('supplier');
			if (supplier) {
				frappe.set_route('List', 'Supplier Nots', { supplier: supplier });
			} else {
				frappe.set_route('List', 'Supplier Nots');
			}
		}, __('Izohlar'));

		// Boshqa tugmalar
		report.page.add_inner_button(__("Barcha to'lovlar"), () => {
			frappe.set_route("List", "Payment Entry", { "party_type": "Supplier", "docstatus": 1 });
		});
		report.page.add_inner_button(__("Excel ga eksport"), () => report.export_report("xlsx"));
		report.page.add_inner_button(__("Yangi to'lov"), () => {
			frappe.new_doc("Payment Entry", { "party_type": "Supplier", "payment_type": "Pay" });
		});

		// Ogohlantirish
		if (!frappe.query_report.get_filter_value('supplier')) {
			frappe.show_alert({ message: __('Iltimos, yetkazib beruvchini tanlang'), indicator: 'orange' }, 5);
		}

		// CSS - Jadval va Dashboard optimallashtirish
		add_custom_css();

		// Dashboard summary kartalarini $ bilan formatlash
		format_summary_cards();
	},

	"after_datatable_render": function(datatable) {
		// Summary kartalarini har safar yangilash
		format_summary_cards();

		// Payment Entry qatorlarida "Izoh" tugmasini qo'shish
		try {
			if (datatable && datatable.datamanager && datatable.datamanager.data) {
				add_note_buttons(datatable);
			}
		} catch(e) {
			console.error("Supplier Debt Analysis: Error in after_datatable_render:", e);
		}
	}
};


function get_category_badge_color(category) {
	const colors = {
		'Eslatma': '#3b82f6',
		'Ogohlantirish': '#f59e0b',
		'Qo\'ng\'iroq Qilindi': '#10b981',
		'To\'lov qilish kerak': '#ef4444',
		'Boshqa': '#6b7280'
	};
	return colors[category] || '#6b7280';
}


function add_note_buttons(datatable) {
	try {
		if (!datatable || !datatable.datamanager || !datatable.datamanager.data) {
			return;
		}

		// Qo'llab-quvvatlanadigan hujjat turlari
		const supported_types = ['Payment Entry', 'Installment Application'];

		datatable.datamanager.data.forEach((row, row_index) => {
			try {
				// Faqat qo'llab-quvvatlanadigan hujjat turlari uchun
				if (!row.document || !row.document_type || !supported_types.includes(row.document_type)) {
					return;
				}

				const document_col_index = datatable.datamanager.columns.findIndex(
					col => col.fieldname === 'document'
				);

				if (document_col_index === -1) return;

				const cell = datatable.getCell(row_index, document_col_index);
				if (!cell) return;

				// Agar tugma allaqachon qo'shilgan bo'lsa, o'tkazib yuborish
				if (cell.querySelector('.note-btn')) return;

				// Tugma yaratish
				const btn = document.createElement('button');
				btn.className = 'btn btn-xs btn-default note-btn';
				btn.innerHTML = '<i class="fa fa-pencil"></i>';
				btn.style.marginLeft = '5px';
				btn.title = 'Izoh qo\'shish yoki ko\'rish';

				btn.onclick = function(e) {
					e.preventDefault();
					e.stopPropagation();
					show_note_dialog(row.document_type, row.document, row);
				};

				const cell_content = cell.querySelector('.dt-cell__content');
				if (cell_content) {
					cell_content.appendChild(btn);
				}
			} catch (row_error) {
				console.error("Error processing row", row_index, row_error);
			}
		});
	} catch (error) {
		console.error("Error in add_note_buttons:", error);
	}
}


function show_note_dialog(reference_type, reference_name, row_data) {
	// Avval mavjud izohlarni olish
	frappe.call({
		method: 'cash_flow_app.cash_flow_management.report.supplier_debt_analysis.supplier_debt_analysis.get_supplier_notes',
		args: {
			reference_type: reference_type,
			reference_name: reference_name
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				show_note_dialog_with_history(reference_type, reference_name, row_data, r.message.notes);
			} else {
				show_note_dialog_with_history(reference_type, reference_name, row_data, []);
			}
		}
	});
}


function show_note_dialog_with_history(reference_type, reference_name, row_data, existing_notes) {
	const supplier = frappe.query_report.get_filter_value('supplier');
	
	// Hujjat turini o'zbek tilida ko'rsatish
	const type_label = reference_type === 'Payment Entry' ? 'To\'lov' : 'Shartnoma';
	
	const d = new frappe.ui.Dialog({
		title: __('{0}: {1}', [type_label, reference_name]),
		size: 'large',
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'doc_info',
				options: `<div class="alert alert-info">
					<strong>Hujjat turi:</strong> ${reference_type}<br>
					<strong>Yetkazib beruvchi:</strong> ${supplier || 'N/A'}<br>
					<strong>Summa:</strong> ${format_currency_with_symbol(row_data.debit || row_data.kredit || 0)}
				</div>`
			},
			{
				fieldtype: 'Section Break',
				label: __('Yangi Izoh Qo\'shish')
			},
			{
				fieldtype: 'Select',
				fieldname: 'note_category',
				label: __('Kategoriya'),
				options: [
					'Eslatma',
					'Ogohlantirish',
					'Qo\'ng\'iroq Qilindi',
					'To\'lov qilish kerak',
					'Boshqa'
				],
				default: 'Eslatma',
				reqd: 1
			},
			{
				fieldtype: 'Small Text',
				fieldname: 'note_text',
				label: __('Izoh'),
				reqd: 1
			},
			{
				fieldtype: 'Section Break',
				label: __('Avvalgi Izohlar')
			},
			{
				fieldtype: 'HTML',
				fieldname: 'notes_history',
				options: render_notes_history(existing_notes)
			}
		],
		primary_action_label: __('Saqlash'),
		primary_action: function(values) {
			frappe.call({
				method: 'cash_flow_app.cash_flow_management.report.supplier_debt_analysis.supplier_debt_analysis.save_supplier_note',
				args: {
					reference_type: reference_type,
					reference_name: reference_name,
					note_text: values.note_text,
					note_category: values.note_category,
					supplier: supplier
				},
				freeze: true,
				freeze_message: __('Saqlanmoqda...'),
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __('✅ Izoh saqlandi'),
							indicator: 'green'
						}, 3);

						d.hide();

						// Report ni yangilash
						setTimeout(function() {
							frappe.query_report.refresh();
						}, 500);
					} else {
						frappe.msgprint({
							title: __('Xatolik'),
							message: r.message ? r.message.message : __('Noma\'lum xatolik'),
							indicator: 'red'
						});
					}
				},
				error: function(err) {
					console.error("Save error:", err);
					frappe.msgprint({
						title: __('Xatolik'),
						message: __('Izohni saqlashda xatolik yuz berdi'),
						indicator: 'red'
					});
				}
			});
		}
	});

	d.show();
}


function render_notes_history(notes) {
	if (!notes || notes.length === 0) {
		return '<p class="text-muted">Hali izohlar yo\'q</p>';
	}

	let html = '<div class="notes-history" style="max-height: 300px; overflow-y: auto;">';

	notes.forEach(note => {
		const date = note.note_date ? frappe.datetime.str_to_user(note.note_date) : 'N/A';
		const category = note.note_category || 'Eslatma';
		const badge_color = get_category_badge_color(category);

		html += `
			<div class="note-item" style="border-left: 3px solid #2490ef; padding: 10px; margin-bottom: 10px; background: #f9f9f9; border-radius: 4px;">
				<div style="margin-bottom: 5px;">
					<span class="badge" style="background-color: ${badge_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px;">${category}</span>
					<small class="text-muted" style="margin-left: 8px;">${date}</small>
				</div>
				<div style="margin-top: 5px;">${note.note_text || ''}</div>
				${note.created_by_user ? `<small class="text-muted">Yaratgan: ${note.created_by_user}</small>` : ''}
			</div>
		`;
	});

	html += '</div>';

	return html;
}


function format_currency(value) {
	// Russian style formatting: space separator, no decimals
	if (!value) return '0';
	return Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}


function format_currency_with_symbol(value) {
	// Russian style formatting with $ symbol: $ 1 234
	if (!value && value !== 0) return '$ 0';
	let formatted = Math.round(Math.abs(value)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
	return '$ ' + formatted;
}


function format_summary_cards() {
	// Dashboard summary kartalaridagi qiymatlarni $ bilan formatlash
	setTimeout(function() {
		$('.summary-card .value, .report-summary .value, .number-card-value').each(function() {
			let $el = $(this);
			let text = $el.text().trim();
			
			// Agar allaqachon $ bo'lsa, o'tkazib yuborish
			if (text.includes('$')) return;
			
			// Raqamni olish (vergul, nuqta, probel olib tashlash)
			let num = parseFloat(text.replace(/[,\s]/g, '').replace(/[^0-9.-]/g, ''));
			
			if (!isNaN(num)) {
				let formatted = format_currency_with_symbol(num);
				$el.text(formatted);
			}
		});
	}, 100);
}


function show_add_note_dialog(report) {
	const supplier = frappe.query_report.get_filter_value('supplier');
	
	const d = new frappe.ui.Dialog({
		title: __('Yangi Izoh Qo\'shish'),
		fields: [
			{
				fieldtype: 'Select',
				fieldname: 'reference_type',
				label: __('Hujjat Turi'),
				options: [
					'Payment Entry',
					'Installment Application'
				],
				default: 'Payment Entry',
				reqd: 1,
				onchange: function() {
					// Hujjat turi o'zgarganda reference_name ni tozalash
					d.set_value('reference_name', '');
				}
			},
			{
				fieldtype: 'Dynamic Link',
				fieldname: 'reference_name',
				label: __('Hujjat'),
				options: 'reference_type',
				reqd: 1,
				get_query: function() {
					let ref_type = d.get_value('reference_type');
					
					if (ref_type === 'Payment Entry') {
						let filters = { docstatus: 1, party_type: 'Supplier' };
						if (supplier) {
							filters.party = supplier;
						}
						return { filters: filters };
					} else if (ref_type === 'Installment Application') {
						// Installment Application uchun custom query
						return {
							query: 'cash_flow_app.cash_flow_management.report.supplier_debt_analysis.supplier_debt_analysis.get_installment_applications_query',
							filters: { supplier: supplier }
						};
					}
					return { filters: { docstatus: 1 } };
				}
			},
			{
				fieldtype: 'Select',
				fieldname: 'category',
				label: __('Kategoriya'),
				options: [
					'Eslatma',
					'Ogohlantirish',
					'Qo\'ng\'iroq Qilindi',
					'To\'lov qilish kerak',
					'Boshqa'
				],
				default: 'Eslatma',
				reqd: 1
			},
			{
				fieldtype: 'Small Text',
				fieldname: 'note',
				label: __('Izoh'),
				reqd: 1
			}
		],
		primary_action_label: __('Saqlash'),
		primary_action: function(values) {
			frappe.call({
				method: 'cash_flow_app.cash_flow_management.report.supplier_debt_analysis.supplier_debt_analysis.save_supplier_note',
				args: {
					reference_type: values.reference_type,
					reference_name: values.reference_name,
					note_text: values.note,
					note_category: values.category,
					supplier: supplier
				},
				freeze: true,
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __('✅ Izoh saqlandi'),
							indicator: 'green'
						}, 3);
						d.hide();
						frappe.query_report.refresh();
					} else {
						frappe.msgprint({
							title: __('Xatolik'),
							message: r.message ? r.message.message : __('Noma\'lum xatolik'),
							indicator: 'red'
						});
					}
				}
			});
		}
	});

	d.show();
}


function add_custom_css() {
	let css = `
		/* Jadval - to'liq ko'rinishi uchun */
		.report-wrapper .dt-scroll-body {
			max-height: 60vh !important;
			overflow-y: auto !important;
		}
		.dt-responsive table.dataTable {
			width: 100% !important;
			min-width: auto !important;
			table-layout: auto !important;
		}
		.dataTable th, .dataTable td {
			min-width: 110px !important;
			max-width: 250px !important;
			padding: 8px 10px !important;
			font-size: 13px !important;
			white-space: nowrap !important;
			overflow: hidden !important;
			text-overflow: ellipsis !important;
		}
		.dataTable th {
			background: #f8fafc !important;
			font-weight: 600 !important;
			position: sticky !important;
			top: 0 !important;
			z-index: 10 !important;
		}

		/* Dashboard kartalari - bir qatorda, pastga tushmaydi */
		.dashboard-summary {
			display: flex !important;
			flex-wrap: nowrap !important;
			overflow-x: auto !important;
			gap: 12px !important;
			padding: 8px 0 !important;
			margin-bottom: 8px !important;
			scrollbar-width: thin;
		}
		.dashboard-summary::-webkit-scrollbar {
			height: 6px;
		}
		.dashboard-summary::-webkit-scrollbar-thumb {
			background: #cbd5e1;
			border-radius: 3px;
		}
		.dashboard-summary .summary-card {
			flex: 0 0 auto !important;
			min-width: 135px !important;
			max-width: 160px !important;
			padding: 10px 8px !important;
			border-radius: 6px !important;
			box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
			background: white !important;
			text-align: center !important;
			font-size: 13px !important;
			margin: 0 !important;
		}
		.dashboard-summary .summary-card .label {
			font-size: 11.5px !important;
			color: #4b5563 !important;
			margin-bottom: 4px !important;
			white-space: nowrap !important;
			overflow: hidden !important;
			text-overflow: ellipsis !important;
		}
		.dashboard-summary .summary-card .value {
			font-size: 16px !important;
			font-weight: 700 !important;
			color: #1f2937 !important;
		}

		/* Note button styling */
		.note-btn {
			padding: 2px 6px !important;
			font-size: 10px !important;
		}
		.note-btn:hover {
			background-color: #e5e7eb !important;
		}

		/* Umumiy oq fonni optimallashtirish */
		.report-wrapper {
			padding: 8px !important;
		}
		.page-container {
			background: #f1f5f9 !important;
		}
	`;

	// CSS ni qo'shish
	if (!$('style#supplier-debt-custom-css').length) {
		$('head').append(`<style id="supplier-debt-custom-css">${css}</style>`);
	}
}
