// Copyright (c) 2026, FSC and contributors
// Client Script for Sales Invoice - Pass-Through Item Functionality

frappe.ui.form.on('Sales Invoice Item', {
    is_passthrough_item: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.is_passthrough_item) {
            // Set default buying price list if not set
            if (!row.buying_price_list) {
                frappe.model.set_value(cdt, cdn, 'buying_price_list', 'Standard Buying');
            }

            // Warn if update_stock is enabled
            if (row.update_stock == 1) {
                frappe.msgprint({
                    title: __('Stock Update'),
                    message: __('Pass-through items should not update stock. Please uncheck "Update Stock" for this item.'),
                    indicator: 'orange'
                });
            }
        } else {
            // Clear pass-through fields
            frappe.model.set_value(cdt, cdn, 'supplier', '');
            frappe.model.set_value(cdt, cdn, 'supplier_rate', 0);
            frappe.model.set_value(cdt, cdn, 'supplier_amount', 0);
            frappe.model.set_value(cdt, cdn, 'margin_amount', 0);
            frappe.model.set_value(cdt, cdn, 'margin_percentage', 0);
        }
    },

    supplier: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.is_passthrough_item && row.supplier && row.item_code && row.buying_price_list) {
            // Fetch supplier rate from buying price list
            fetch_supplier_rate(frm, cdt, cdn);
        }
    },

    buying_price_list: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.is_passthrough_item && row.supplier && row.item_code && row.buying_price_list) {
            // Fetch supplier rate from buying price list
            fetch_supplier_rate(frm, cdt, cdn);
        }
    },

    supplier_rate: function (frm, cdt, cdn) {
        calculate_passthrough_margin(frm, cdt, cdn);
    },

    qty: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.is_passthrough_item) {
            calculate_passthrough_margin(frm, cdt, cdn);
        }
    },

    rate: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.is_passthrough_item) {
            calculate_passthrough_margin(frm, cdt, cdn);
        }
    },

    amount: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.is_passthrough_item) {
            calculate_passthrough_margin(frm, cdt, cdn);
        }
    }
});

frappe.ui.form.on('Sales Invoice', {
    refresh: function (frm) {
        // Add pass-through summary to dashboard
        if (frm.doc.docstatus === 0 && frm.doc.items && frm.doc.items.length > 0) {
            show_passthrough_summary(frm);
        }

        // Add custom button to view linked Purchase Invoices
        if (frm.doc.docstatus === 1) {
            let has_passthrough = frm.doc.items.some(item => item.is_passthrough_item);

            if (has_passthrough) {
                frm.add_custom_button(__('View Purchase Invoices'), function () {
                    view_linked_purchase_invoices(frm);
                }, __('Pass-Through'));

                frm.add_custom_button(__('Passthrough Summary'), function () {
                    show_passthrough_detail_dialog(frm);
                }, __('Pass-Through'));
            }
        }
    },

    before_submit: function (frm) {
        // Validate pass-through items before submission
        return validate_passthrough_items(frm);
    }
});

function fetch_supplier_rate(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    frappe.call({
        method: 'erpnext.stock.get_item_details.get_price_list_rate',
        args: {
            args: {
                item_code: row.item_code,
                price_list: row.buying_price_list,
                supplier: row.supplier,
                company: frm.doc.company,
                qty: row.qty || 1,
                transaction_date: frm.doc.posting_date,
                doctype: 'Purchase Invoice'
            }
        },
        callback: function (r) {
            if (r.message && r.message.price_list_rate) {
                frappe.model.set_value(cdt, cdn, 'supplier_rate', r.message.price_list_rate);
                frappe.show_alert({
                    message: __('Supplier rate fetched: {0}', [format_currency(r.message.price_list_rate, frm.doc.currency)]),
                    indicator: 'green'
                });
            } else {
                frappe.msgprint({
                    title: __('Price Not Found'),
                    message: __('No price found for item {0} in price list {1} for supplier {2}',
                        [row.item_code, row.buying_price_list, row.supplier]),
                    indicator: 'orange'
                });
            }
        }
    });
}

function calculate_passthrough_margin(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    if (row.is_passthrough_item && row.supplier_rate) {
        // Calculate supplier amount
        row.supplier_amount = flt(row.qty) * flt(row.supplier_rate);

        // Calculate margin
        row.margin_amount = flt(row.amount) - flt(row.supplier_amount);

        // Calculate margin percentage (on cost basis)
        row.margin_percentage = row.supplier_amount ?
            (flt(row.margin_amount) / flt(row.supplier_amount) * 100) : 0;

        // Refresh the row
        frm.refresh_field('items');

        // Show warning if negative margin
        if (row.margin_amount < 0) {
            frappe.show_alert({
                message: __('Warning: Negative margin for item {0}!', [row.item_name]),
                indicator: 'red'
            }, 5);
        }
    }
}

function show_passthrough_summary(frm) {
    let passthrough_items = frm.doc.items.filter(item => item.is_passthrough_item);

    if (passthrough_items.length > 0) {
        let total_supplier_cost = 0;
        let total_revenue = 0;
        let suppliers = new Set();

        passthrough_items.forEach(item => {
            total_supplier_cost += flt(item.supplier_amount);
            total_revenue += flt(item.amount);
            if (item.supplier) {
                suppliers.add(item.supplier);
            }
        });

        let total_margin = total_revenue - total_supplier_cost;
        let margin_pct = total_supplier_cost ? (total_margin / total_supplier_cost * 100) : 0;

        frm.dashboard.add_indicator(__('Pass-Through Items: {0}', [passthrough_items.length]), 'blue');
        frm.dashboard.add_indicator(__('Suppliers: {0}', [suppliers.size]), 'blue');
        frm.dashboard.add_indicator(__('Total Margin: {0} ({1}%)',
            [format_currency(total_margin, frm.doc.currency), margin_pct.toFixed(2)]),
            total_margin >= 0 ? 'green' : 'red'
        );
    }
}

function validate_passthrough_items(frm) {
    let errors = [];

    frm.doc.items.forEach((item, idx) => {
        if (item.is_passthrough_item) {
            // Check supplier is set
            if (!item.supplier) {
                errors.push(__('Row {0}: Supplier is required for pass-through item', [idx + 1]));
            }

            // Check supplier rate is set
            if (!item.supplier_rate || item.supplier_rate <= 0) {
                errors.push(__('Row {0}: Supplier rate must be greater than 0', [idx + 1]));
            }

            // Warn on negative margin
            if (item.margin_amount < 0) {
                errors.push(__('Row {0}: Warning - Negative margin ({1})',
                    [idx + 1, format_currency(item.margin_amount, frm.doc.currency)]));
            }

            // Check expense account is set
            if (!item.expense_account) {
                errors.push(__('Row {0}: Expense account is required for pass-through item', [idx + 1]));
            }
        }
    });

    if (errors.length > 0) {
        frappe.msgprint({
            title: __('Pass-Through Validation Errors'),
            message: errors.join('<br>'),
            indicator: 'red'
        });
        return false;
    }

    return true;
}

function view_linked_purchase_invoices(frm) {
    frappe.route_options = {
        "custom_sales_invoice": frm.doc.name
    };
    frappe.set_route("List", "Purchase Invoice");
}

function show_passthrough_detail_dialog(frm) {
    let passthrough_items = frm.doc.items.filter(item => item.is_passthrough_item);

    if (passthrough_items.length === 0) {
        frappe.msgprint(__('No pass-through items in this invoice'));
        return;
    }

    // Group by supplier
    let supplier_groups = {};
    passthrough_items.forEach(item => {
        if (!supplier_groups[item.supplier]) {
            supplier_groups[item.supplier] = [];
        }
        supplier_groups[item.supplier].push(item);
    });

    // Build HTML table
    let html = '<table class="table table-bordered table-sm">';
    html += '<thead><tr><th>Supplier</th><th>Items</th><th>Supplier Cost</th><th>Revenue</th><th>Margin</th><th>Margin %</th><th>PI</th></tr></thead>';
    html += '<tbody>';

    for (let supplier in supplier_groups) {
        let items = supplier_groups[supplier];
        let total_cost = items.reduce((sum, item) => sum + flt(item.supplier_amount), 0);
        let total_revenue = items.reduce((sum, item) => sum + flt(item.amount), 0);
        let margin = total_revenue - total_cost;
        let margin_pct = total_cost ? (margin / total_cost * 100) : 0;
        let pi_link = items[0].purchase_invoice ?
            `<a href="/app/purchase-invoice/${items[0].purchase_invoice}">${items[0].purchase_invoice}</a>` :
            'Not Created';

        html += '<tr>';
        html += `<td><strong>${supplier}</strong></td>`;
        html += `<td>${items.length}</td>`;
        html += `<td>${format_currency(total_cost, frm.doc.currency)}</td>`;
        html += `<td>${format_currency(total_revenue, frm.doc.currency)}</td>`;
        html += `<td style="color: ${margin >= 0 ? 'green' : 'red'}">${format_currency(margin, frm.doc.currency)}</td>`;
        html += `<td>${margin_pct.toFixed(2)}%</td>`;
        html += `<td>${pi_link}</td>`;
        html += '</tr>';
    }

    html += '</tbody></table>';

    frappe.msgprint({
        title: __('Pass-Through Details'),
        message: html,
        wide: true
    });
}
