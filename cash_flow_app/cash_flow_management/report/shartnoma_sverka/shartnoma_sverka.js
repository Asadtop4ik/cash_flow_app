frappe.query_reports["Overpayment Detection Report"] = {

    filters: [],

    formatter: function (value, row, column, data, default_formatter) {
        let formatted_value = default_formatter(value, row, column, data);

        if (column.fieldname === "sales_order" && data && data.sales_order) {
            const encoded = encodeURIComponent(data.sales_order);
            formatted_value = `

                    href="#"
                    style="color: var(--text-on-light-green); font-weight: 500;"
                    onclick="event.preventDefault();
                             window._overpayment_open_payment_list('${encoded}');"
                >
                    ${frappe.utils.escape_html(data.sales_order)}
                </a>
            `;
        }

        return formatted_value;
    },

    _open_payment_list: function (encoded_so_name) {
        const so_name = decodeURIComponent(encoded_so_name);
        frappe.route_options = {
            "custom_contract_reference": so_name,
            "docstatus": 1
        };
        frappe.set_route("List", "Payment Entry", "List");
    },

    onload: function () {
        window._overpayment_open_payment_list =
            frappe.query_reports["Overpayment Detection Report"]._open_payment_list;
    }
};
