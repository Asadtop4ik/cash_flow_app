// Copyright (c) 2025, AsadStack and contributors
// For license information, please see license.txt
//
// ═══════════════════════════════════════════════════════════════════
// FIX: Frappe datatable da _style background har doim qo'llanilmaydi.
// Shuning uchun matn rangi oq (#ffffff) emas, to'q (#1a1a1a) bo'lishi
// kerak — aks holda oq matn + oq fon = ko'rinmas qator.
// ═══════════════════════════════════════════════════════════════════

frappe.query_reports["Custom Profit and Loss"] = {

    "formatter": function(value, row, column, data, default_formatter) {
        if (value === undefined || value === null || value === "") return "";

        // ── Raqamli ustunlar ────────────────────────────────────────
        if (column.fieldname !== "account" && data) {

            // Shartnomalar soni — son, $ yo'q
            if (data.account === "Shartnomalar soni") {
                let numValue = parseInt(String(value).replace(/[^0-9.-]/g, ''), 10);
                if (isNaN(numValue)) return default_formatter(value, row, column, data);
                return String(numValue);
            }

            // Foiz qatorlari
            const isPercentage = data.account?.includes("Rentabillik");
            let numValue = parseFloat(String(value).replace(/[^0-9.-]/g, ''));

            if (isNaN(numValue)) {
                return default_formatter(value, row, column, data);
            }

            if (isPercentage) {
                return `<span style="font-style: italic; color: #555555;">${numValue.toFixed(1)}%</span>`;
            }

            // Pul qiymati
            let roundedValue = Math.round(numValue);
            let formattedNumber = new Intl.NumberFormat('ru-RU')
                .format(Math.abs(roundedValue))
                .replace(/\u00a0/g, '\u00a0');

            let displayValue = (roundedValue < 0)
                ? `- $ ${formattedNumber}`
                : `$ ${formattedNumber}`;

            let styles = ["font-weight: 700"];

            const keyAccounts = [
                "Savdo", "Tannarx", "Yalpi foyda",
                "Jami harajatlar", "Sof foyda", "Operatsion foyda"
            ];

            if (keyAccounts.includes(data.account)) {
                // MUHIM: oq emas, to'q matn — background qo'llanilmasa ham ko'rinadi
                if (roundedValue < 0) {
                    styles.push("color: #CC0000");
                } else {
                    styles.push("color: #1a1a1a");
                }
            } else {
                // Oddiy qatorlar
                if (roundedValue < 0) styles.push("color: #FF0000");
                else styles = []; // bold kerak emas
            }

            if (styles.length > 0) {
                return `<span style="${styles.join('; ')}">${displayValue}</span>`;
            }
            return displayValue;
        }

        // ── Account ustuni ──────────────────────────────────────────
        value = default_formatter(value, row, column, data);
        if (!data) return value;

        // Savdo — bold + link
        if (data.account === "Savdo" && column.fieldname === "account") {
            const from_date = frappe.query_report.get_filter_value('from_date');
            const to_date   = frappe.query_report.get_filter_value('to_date');
            return `<a href="#" onclick="
                frappe.set_route('query-report', 'Savdo va Foyda', {
                    'from_date': '${from_date}',
                    'to_date':   '${to_date}'
                });
                return false;
            " style="font-weight: 700; color: #2490ef; text-decoration: underline; cursor: pointer;">
                ${data.account}
            </a>`;
        }

        // Asosiy ko'rsatkichlar — bold, to'q matn (fon ko'rinmasa ham xavfsiz)
        const keyAccounts = ["Savdo", "Tannarx", "Yalpi foyda", "Sof foyda", "Operatsion foyda"];
        if (keyAccounts.includes(data.account) && column.fieldname === "account") {
            return `<span style="font-weight: 700; color: #1a1a1a;">${data.account}</span>`;
        }

        // Jami harajatlar — bold
        if (data.account === "Jami harajatlar" && column.fieldname === "account") {
            return `<span style="font-weight: 700; color: #1a1a1a;">${data.account}</span>`;
        }

        // Kichik sektsiya sarlavhalari — bold
        const subsectionAccounts = ["Administrativ", "Tijorat", "Boshqa daromad"];
        if (subsectionAccounts.includes(data.account) && column.fieldname === "account") {
            return `<span style="font-weight: 700; color: #1a1a1a;">${data.account}</span>`;
        }

        // Rentabillik — kursiv
        if (["Rentabillik", "Sof Rentabillik"].includes(data.account) && column.fieldname === "account") {
            return `<span style="font-style: italic; color: #666666;">${data.account}</span>`;
        }

        // Check qatori — bold
        if (data.account?.includes("Check") && column.fieldname === "account") {
            return `<span style="font-weight: 700; color: #ffffff;">${data.account}</span>`;
        }

        // Xarajat kategoriyalari — Payment Entry ga link
        if (column.fieldname === "account" && data.category_id && data.indent === 1) {
            return `<a href="#" onclick="
                frappe.set_route('List', 'Payment Entry', {
                    'custom_counterparty_category': '${data.category_id}'
                });
                return false;
            " style="color: #2490ef; text-decoration: underline; cursor: pointer;">
                ${value}
            </a>`;
        }

        return value;
    },

    "filters": [
        {
            "fieldname": "from_date",
            "label":     __("From Date"),
            "fieldtype": "Date",
            "default":   frappe.datetime.year_start(),
            "reqd":      1
        },
        {
            "fieldname": "to_date",
            "label":     __("To Date"),
            "fieldtype": "Date",
            "default":   frappe.datetime.get_today(),
            "reqd":      1
        },
        {
            "fieldname": "periodicity",
            "label":     __("Davr turi"),
            "fieldtype": "Select",
            "options":   "Monthly\nYearly",
            "default":   "Monthly",
            "reqd":      1
        }
    ],

    onload: function(report) {

        report.page.add_inner_button(__("Chop etish"), function() {
            var filters = report.get_values();
            if (!filters) return;

            frappe.show_alert({ message: __("Chop etish tayyorlanmoqda..."), indicator: "blue" }, 3);

            frappe.call({
                method: "cash_flow_app.cash_flow_management.report.custom_profit_and_loss.custom_profit_and_loss.get_print_html",
                args: { filters: filters },
                callback: function(r) {
                    if (!r.message) {
                        frappe.msgprint(__("HTML render xatosi. Konsolni tekshiring."));
                        return;
                    }
                    var w = window.open("", "_blank");
                    if (!w) {
                        frappe.msgprint(__("Pop-up bloklandi. Brauzer sozlamalarida ruxsat bering."));
                        return;
                    }
                    w.document.write(r.message);
                    w.document.close();
                    setTimeout(function() { w.print(); }, 800);
                }
            });
        });

        report.page.add_inner_button(__("Yangilash"), function() {
            report.refresh();
        });

        report.page.add_inner_button(__("Excel'ga eksport"), function() {
            frappe.utils.to_excel(report.data, report.report_name);
        });

        frappe.show_alert({
            message:   __('Hisobot muvaffaqiyatli yuklandi'),
            indicator: 'green'
        }, 3);
    },

    get_datatable_options: function(options) {
        return Object.assign(options, {
            checkboxColumn: false,
            layout: 'fluid'
        });
    }
};
