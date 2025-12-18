// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt

frappe.query_reports["Eslatmalar"] = {
	"filters": [],

	"onload": function(report) {
		console.log("Eslatmalar report loaded");

		// Yangi izoh qo'shish tugmasi
		report.page.add_inner_button(__('Yangi Izoh'), function() {
			show_add_note_dialog(report);
		}, __('Izohlar'));

		// Barcha izohlarni ko'rish
		report.page.add_inner_button(__('Barcha Izohlar'), function() {
			frappe.set_route('List', 'Contract Notes');
		}, __('Izohlar'));
	},

	"after_datatable_render": function(datatable) {
		// Har bir qatorda "Izoh" tugmasini qo'shish
		try {
			if (datatable && datatable.datamanager && datatable.datamanager.data) {
				add_note_buttons(datatable);
			} else {
				console.warn("Eslatmalar: datatable structure not ready");
			}
		} catch(e) {
			console.error("Eslatmalar: Error in after_datatable_render:", e);
		}
	}
};


function add_note_buttons(datatable) {
	// Har bir qatorga tugma qo'shish
	try {
		if (!datatable || !datatable.datamanager || !datatable.datamanager.data) {
			console.warn("Eslatmalar: Invalid datatable structure");
			return;
		}

		datatable.datamanager.data.forEach((row, row_index) => {
			try {
				// Faqat shartnoma qatorlari uchun
				if (!row.contract_link || typeof row.contract_link !== 'string') {
					return;
				}

				const contract = row.contract_link;

				// Shartnoma ustunini topish
				const contract_col_index = datatable.datamanager.columns.findIndex(
					col => col.fieldname === 'contract_link'
				);

				if (contract_col_index === -1) return;

				const cell = datatable.getCell(row_index, contract_col_index);
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
					show_note_dialog(contract, row);
				};

				// Cell ichiga tugma qo'shish
				const cell_content = cell.querySelector('.dt-cell__content');
				if (cell_content) {
					cell_content.appendChild(btn);
				}
			} catch (row_error) {
				console.error("Eslatmalar: Error processing row", row_index, row_error);
			}
		});
	} catch (error) {
		console.error("Eslatmalar: Error in add_note_buttons:", error);
	}
}


function show_note_dialog(contract, row_data) {
	console.log("Opening note dialog for:", contract);

	// Avval mavjud izohlarni olish
	frappe.call({
		method: 'cash_flow_app.cash_flow_management.report.eslatmalar.eslatmalar.get_contract_notes',
		args: {
			contract_reference: contract
		},
		callback: function(r) {
			if (r.message && r.message.success) {
				show_note_dialog_with_history(contract, row_data, r.message.notes);
			} else {
				show_note_dialog_with_history(contract, row_data, []);
			}
		}
	});
}


function show_note_dialog_with_history(contract, row_data, existing_notes) {
	// Dialog yaratish
	const d = new frappe.ui.Dialog({
		title: __('Shartnoma: {0}', [contract]),
		size: 'large',
		fields: [
			{
				fieldtype: 'HTML',
				fieldname: 'customer_info',
				options: `<div class="alert alert-info">
					<strong>Klient:</strong> ${row_data.customer_link || 'N/A'}<br>
					<strong>Qolgan qarz:</strong> ${frappe.format(row_data.remaining_debt || 0, {fieldtype: 'Currency'})}
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
					'To\'lov Kutilmoqda',
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
			console.log("Saving note:", values);

			frappe.call({
				method: 'cash_flow_app.cash_flow_management.report.eslatmalar.eslatmalar.save_note',
				args: {
					contract_reference: contract,
					note_text: values.note_text,
					note_category: values.note_category
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
							cur_report.refresh();
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

	let html = '<div class="notes-history">';

	notes.forEach(note => {
		const date = note.note_date ? frappe.datetime.str_to_user(note.note_date) : 'N/A';
		const category_badge = get_category_badge(note.note_category);

		html += `
			<div class="note-item" style="border-left: 3px solid #2490ef; padding: 10px; margin-bottom: 10px; background: #f9f9f9;">
				<div style="margin-bottom: 5px;">
					${category_badge}
					<small class="text-muted">${date}</small>
				</div>
				<div>${note.note_text}</div>
				${note.created_by_user ? `<small class="text-muted">Yaratgan: ${note.created_by_user}</small>` : ''}
			</div>
		`;
	});

	html += '</div>';

	return html;
}


function get_category_badge(category) {
	const badges = {
		'Eslatma': 'info',
		'Ogohlantirish': 'warning',
		'Qo\'ng\'iroq Qilindi': 'success',
		'To\'lov Kutilmoqda': 'orange',
		'Boshqa': 'secondary'
	};

	const color = badges[category] || 'secondary';
	return `<span class="badge badge-${color}">${category}</span>`;
}


function show_add_note_dialog(report) {
	// Barcha shartnomalar ro'yxatini olish
	const d = new frappe.ui.Dialog({
		title: __('Yangi Izoh Qo\'shish'),
		fields: [
			{
				fieldtype: 'Link',
				fieldname: 'contract',
				label: __('Shartnoma'),
				options: 'Installment Application',
				reqd: 1,
				get_query: function() {
					return {
						filters: {
							docstatus: 1
						}
					};
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
					'To\'lov Kutilmoqda',
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
				method: 'cash_flow_app.cash_flow_management.report.eslatmalar.eslatmalar.save_note',
				args: {
					contract_reference: values.contract,
					note_text: values.note,
					note_category: values.category
				},
				freeze: true,
				callback: function(r) {
					if (r.message && r.message.success) {
						frappe.show_alert({
							message: __('✅ Izoh saqlandi'),
							indicator: 'green'
						}, 3);
						d.hide();
						report.refresh();
					}
				}
			});
		}
	});

	d.show();
}
