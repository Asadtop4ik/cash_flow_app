// Fayl joyi: apps/cash_flow_app/cash_flow_app/public/js/sales_order.js
frappe.ui.form.on('Sales Order', {
refresh: function(frm) {
// HAR DOIM PDF tugmasi ko'rinsin (Draft, Submitted, har qanday holatda)
frm.add_custom_button('Shartnoma PDF', function() {
generate_contract_pdf(frm);
        }, 'Yaratish');
    }
});
function generate_contract_pdf(frm) {
frappe.call({
method: 'cash_flow_app.custom_scripts.sales_order_pdf.generate_contract_pdf',
args: {
sales_order_name: frm.doc.name
        },
freeze: true,
freeze_message: 'PDF yaratilmoqda, iltimos kuting...',
callback: function(r) {
if (r.message && r.message.success) {
frappe.msgprint({
title: 'Muvaffaqiyatli',
indicator: 'green',
message: r.message.message
                });
// PDF ni yangi tabda ochish
if (r.message.file_url) {
window.open(r.message.file_url, '_blank');
                }
// Refresh qilish (attachments ko'rinsin)
frm.reload_doc();
            } else {
frappe.msgprint({
title: 'Xatolik',
indicator: 'red',
message: r.message ? r.message.message : 'PDF yaratishda xatolik yuz berdi'
                });
            }
        },
error: function(r) {
frappe.msgprint({
title: 'Xatolik',
indicator: 'red',
message: 'Server bilan aloqada xatolik. Iltimos, qaytadan urinib ko\'ring.'
            });
        }
    });
}