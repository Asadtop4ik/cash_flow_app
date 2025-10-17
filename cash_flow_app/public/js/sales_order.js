frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        // Collapse Activity/Timeline section by default
        $('.form-sidebar .sidebar-section.form-timeline').addClass('collapsed');
        
        // Hide default totals section fields (confusing for operator)
        frm.set_df_property('total', 'hidden', 1);
        frm.set_df_property('net_total', 'hidden', 1);
        frm.set_df_property('total_net_weight', 'hidden', 1);
        
        // Rename and emphasize custom totals
        frm.set_df_property('custom_downpayment_amount', 'label', 'Boshlang\'ich To\'lov');
        frm.set_df_property('custom_total_interest', 'label', 'Foyda (Internal)');
        frm.set_df_property('custom_grand_total_with_interest', 'label', '💰 JAMI TO\'LOV');
        
        // Add payment progress indicator
        if (frm.doc.docstatus === 1 && frm.doc.custom_grand_total_with_interest) {
            let grand_total = flt(frm.doc.custom_grand_total_with_interest);
            let paid = flt(frm.doc.advance_paid) || 0;
            let outstanding = grand_total - paid;
            let percent = grand_total > 0 ? (paid / grand_total * 100) : 0;
            
            // Add indicator
            frm.dashboard.add_indicator(__('✅ To\'landi: {0} USD ({1}%)', 
                [format_currency(paid, 'USD'), percent.toFixed(0)]), 
                percent >= 100 ? 'green' : 'orange'
            );
            
            frm.dashboard.add_indicator(__('⏳ Qolgan: {0} USD', 
                [format_currency(outstanding, 'USD')]), 
                outstanding > 0 ? 'red' : 'green'
            );
        }
        
        // Rename "Advance Paid" label to "To'langan Summa"
        frm.set_df_property('advance_paid', 'label', "💵 To'langan Summa");
        
        // Make it bold and prominent
        frm.set_df_property('advance_paid', 'bold', 1);
    }
});
