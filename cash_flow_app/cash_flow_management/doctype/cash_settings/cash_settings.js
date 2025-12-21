// Cash Settings Client Script
// Telegram admin chat ID validation va help text

frappe.ui.form.on('Cash Settings', {
	refresh: function(frm) {
		// Help message ko'rsatish
		if (!frm.doc.telegram_admin_chat_id) {
			frm.set_df_property('telegram_admin_chat_id', 'description',
				'<b>Telegram ID ni olish:</b><br>' +
				'1. Telegram\'da <code>@userinfobot</code> ni oching<br>' +
				'2. <code>/start</code> bosing<br>' +
				'3. ID ni bu yerga kiriting<br>' +
				'<b>Bir nechta admin:</b> 123456789, 987654321 (vergul bilan ajrating)'
			);
		}

		// Test notification button
		if (frm.doc.telegram_notification_bot_token && frm.doc.telegram_admin_chat_id) {
			frm.add_custom_button(__('Test Admin Notification'), function() {
				frappe.call({
					method: 'cash_flow_app.cash_flow_management.api.telegram_bot_api.send_test_admin_notification',
					freeze: true,
					freeze_message: __('Sending test notification...'),
					callback: function(r) {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __('Test notification sent successfully!'),
								indicator: 'green'
							}, 5);
						} else {
							frappe.show_alert({
								message: __('Failed to send test notification. Check Error Log.'),
								indicator: 'red'
							}, 5);
						}
					}
				});
			}, __('Actions'));
		}
	},

	telegram_admin_chat_id: function(frm) {
		// Real-time validation
		if (frm.doc.telegram_admin_chat_id) {
			let chat_ids = frm.doc.telegram_admin_chat_id.split(',').map(id => id.trim());
			let invalid_ids = chat_ids.filter(id => !/^\d+$/.test(id));

			if (invalid_ids.length > 0) {
				frappe.show_alert({
					message: __('Invalid Telegram ID format. Only numbers allowed.'),
					indicator: 'orange'
				}, 5);
			} else {
				frappe.show_alert({
					message: __(`Valid! ${chat_ids.length} admin(s) configured.`),
					indicator: 'green'
				}, 3);
			}
		}
	}
});
