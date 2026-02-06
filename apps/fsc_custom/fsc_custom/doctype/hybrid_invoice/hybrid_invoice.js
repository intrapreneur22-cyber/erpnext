// Copyright (c) 2026, FSC and contributors
// For license information, please see license.txt

frappe.ui.form.on('Hybrid Invoice', {
    refresh: function (frm) {
        // Add custom buttons for submitted documents
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Accounting Ledger'), function () {
                frappe.route_options = {
                    voucher_no: frm.doc.name,
                    from_date: frm.doc.posting_date,
                    to_date: frm.doc.posting_date,
                    company: frm.doc.company,
                    group_by: ''
                };
                frappe.set_route("query-report", "General Ledger");
            }, __('View'));

            frm.add_custom_button(__('Supplier Breakdown'), function () {
                show_supplier_breakdown(frm);
            }, __('View'));
        }
    },

    customer: function (frm) {
        // Fetch customer defaults when customer is selected
        if (frm.doc.customer) {
            frappe.call({
                method: 'erpnext.accounts.party.get_party_details',
                args: {
                    party: frm.doc.customer,
                    party_type: 'Customer',
                    company: frm.doc.company,
                    posting_date: frm.doc.posting_date
                },
                callback: function (r) {
                    if (r.message) {
                        if (r.message.currency) {
                            frm.set_value('currency', r.message.currency);
                        }
                        if (r.message.selling_price_list) {
                            frm.set_value('price_list', r.message.selling_price_list);
                        }
                    }
                }
            });
        }
    },

    company: function (frm) {
        // Set default currency when company changes
        if (frm.doc.company && !frm.doc.customer) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Company',
                    filters: { name: frm.doc.company },
                    fieldname: ['default_currency', 'cost_center']
                },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value('currency', r.message.default_currency);
                        if (!frm.doc.cost_center) {
                            frm.set_value('cost_center', r.message.cost_center);
                        }
                    }
                }
            });
        }
    },

    // ===== Phase 1 Enhancement Event Handlers =====

    customer_address: function (frm) {
        // Fetch and display customer address
        if (frm.doc.customer_address) {
            frappe.call({
                method: 'frappe.contacts.doctype.address.address.get_address_display',
                args: { address_dict: frm.doc.customer_address },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value('address_display', r.message);
                    }
                }
            });
        }
    },

    shipping_address_name: function (frm) {
        // Fetch and display shipping address
        if (frm.doc.shipping_address_name) {
            frappe.call({
                method: 'frappe.contacts.doctype.address.address.get_address_display',
                args: { address_dict: frm.doc.shipping_address_name },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value('shipping_address', r.message);
                    }
                }
            });
        }
    },

    dispatch_address_name: function (frm) {
        // Fetch and display dispatch address
        if (frm.doc.dispatch_address_name) {
            frappe.call({
                method: 'frappe.contacts.doctype.address.address.get_address_display',
                args: { address_dict: frm.doc.dispatch_address_name },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value('dispatch_address', r.message);
                    }
                }
            });
        }
    },

    supplier_address: function (frm) {
        // Fetch and display supplier address
        if (frm.doc.supplier_address) {
            frappe.call({
                method: 'frappe.contacts.doctype.address.address.get_address_display',
                args: { address_dict: frm.doc.supplier_address },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value('supplier_address_display', r.message);
                    }
                }
            });
        }
    },

    contact_person: function (frm) {
        // Fetch and display contact details
        if (frm.doc.contact_person) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Contact',
                    name: frm.doc.contact_person
                },
                callback: function (r) {
                    if (r.message) {
                        frm.set_value('contact_display', r.message.name);
                        frm.set_value('contact_email', r.message.email_id);
                        frm.set_value('contact_mobile', r.message.mobile_no);
                    }
                }
            });
        }
    },

    payment_terms_template: function (frm) {
        // Generate payment schedule from template
        if (frm.doc.payment_terms_template && frm.doc.posting_date) {
            frappe.call({
                method: 'erpnext.controllers.accounts_controller.get_payment_terms',
                args: {
                    terms_template: frm.doc.payment_terms_template,
                    posting_date: frm.doc.posting_date,
                    grand_total: frm.doc.base_grand_total || frm.doc.rounded_total
                },
                callback: function (r) {
                    if (r.message && r.message.length > 0) {
                        frm.set_value('payment_schedule', r.message);
                        // Set due date from last payment schedule
                        let last_schedule = r.message[r.message.length - 1];
                        if (!frm.doc.due_date && last_schedule.due_date) {
                            frm.set_value('due_date', last_schedule.due_date);
                        }
                    }
                }
            });
        }
    },

    additional_discount_percentage: function (frm) {
        // Calculate discount amount from percentage
        calculate_additional_discount(frm);
    },

    apply_discount_on: function (frm) {
        // Recalculate discount when base selection changes
        calculate_additional_discount(frm);
    },

    discount_amount: function (frm) {
        // Recalculate totals when discount amount changes
        calculate_totals(frm);
    }
});

function calculate_additional_discount(frm) {
    // Calculate additional discount based on percentage
    if (frm.doc.apply_discount_on && frm.doc.additional_discount_percentage) {
        let base_amount = frm.doc.apply_discount_on === "Grand Total"
            ? flt(frm.doc.base_grand_total)
            : flt(frm.doc.base_net_total);

        let discount = base_amount * flt(frm.doc.additional_discount_percentage) / 100;
        frm.set_value('discount_amount', discount);
    }
    calculate_totals(frm);
}

frappe.ui.form.on('Hybrid Invoice Item', {
    item_code: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code && frm.doc.company) {
            // Use ERPNext's standard method to get item details
            frappe.call({
                method: 'erpnext.stock.get_item_details.get_item_details',
                args: {
                    args: {
                        item_code: row.item_code,
                        company: frm.doc.company,
                        price_list: frm.doc.price_list,
                        currency: frm.doc.currency,
                        doctype: 'Hybrid Invoice',
                        conversion_rate: frm.doc.conversion_rate || 1,
                        customer: frm.doc.customer,
                        qty: row.qty || 1,
                        transaction_date: frm.doc.posting_date
                    }
                },
                callback: function (r) {
                    if (r.message) {
                        // Set all the item details
                        frappe.model.set_value(cdt, cdn, 'item_name', r.message.item_name);
                        frappe.model.set_value(cdt, cdn, 'description', r.message.description);
                        frappe.model.set_value(cdt, cdn, 'item_group', r.message.item_group);
                        frappe.model.set_value(cdt, cdn, 'uom', r.message.uom || r.message.stock_uom);
                        frappe.model.set_value(cdt, cdn, 'stock_uom', r.message.stock_uom);
                        frappe.model.set_value(cdt, cdn, 'conversion_factor', r.message.conversion_factor || 1);

                        // Set rate from price list if available
                        if (r.message.price_list_rate) {
                            frappe.model.set_value(cdt, cdn, 'rate', r.message.price_list_rate);
                        }

                        // Set accounts - these are company-specific
                        if (r.message.income_account) {
                            frappe.model.set_value(cdt, cdn, 'income_account', r.message.income_account);
                        }
                        if (r.message.expense_account) {
                            frappe.model.set_value(cdt, cdn, 'expense_account', r.message.expense_account);
                        }

                        // Set cost center if available
                        if (r.message.cost_center) {
                            frappe.model.set_value(cdt, cdn, 'cost_center', r.message.cost_center);
                        }
                    }
                }
            });
        }
    },

    qty: function (frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },

    rate: function (frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },

    discount_percentage: function (frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },

    discount_amount: function (frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },

    supplier_cost: function (frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },

    is_passthrough_item: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (!row.is_passthrough_item) {
            // Clear supplier fields if unchecked
            frappe.model.set_value(cdt, cdn, 'supplier', '');
            frappe.model.set_value(cdt, cdn, 'supplier_cost', 0);
            frappe.model.set_value(cdt, cdn, 'supplier_total_cost', 0);
        }
        calculate_item_amount(frm, cdt, cdn);
    },

    supplier: function (frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.supplier && row.item_code && row.is_passthrough_item) {
            // Fetch last purchase rate from supplier
            frappe.call({
                method: 'fsc_custom.api.get_last_purchase_rate',
                args: {
                    item_code: row.item_code,
                    supplier: row.supplier
                },
                callback: function (r) {
                    if (r.message && r.message.rate) {
                        frappe.model.set_value(cdt, cdn, 'supplier_cost', r.message.rate);
                    }
                }
            });
        }
    },

    items_remove: function (frm) {
        calculate_totals(frm);
    }
});

frappe.ui.form.on('Hybrid Invoice Taxes and Charges', {
    rate: function (frm, cdt, cdn) {
        calculate_totals(frm);
    },

    charge_type: function (frm, cdt, cdn) {
        calculate_totals(frm);
    },

    taxes_remove: function (frm) {
        calculate_totals(frm);
    }
});

function calculate_item_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    // Calculate sales amount
    row.amount = flt(row.qty) * flt(row.rate);

    // Calculate discount
    if (row.discount_percentage) {
        row.discount_amount = flt(row.amount) * flt(row.discount_percentage) / 100;
    }

    row.net_amount = flt(row.amount) - flt(row.discount_amount);
    row.net_rate = row.qty ? flt(row.net_amount) / flt(row.qty) : 0;

    // Calculate supplier cost and margin
    if (row.is_passthrough_item) {
        row.supplier_total_cost = flt(row.qty) * flt(row.supplier_cost);
        row.item_margin = flt(row.net_amount) - flt(row.supplier_total_cost);
        row.item_margin_percentage = row.supplier_total_cost ?
            (flt(row.item_margin) / flt(row.supplier_total_cost) * 100) : 0;
    } else {
        row.supplier_total_cost = 0;
        row.item_margin = row.net_amount;
        row.item_margin_percentage = 0;
    }

    frm.refresh_field('items');
    calculate_totals(frm);
}

function calculate_totals(frm) {
    let total_qty = 0;
    let base_total = 0;
    let base_net_total = 0;
    let total_supplier_cost = 0;

    // Sum up items
    frm.doc.items.forEach(function (item) {
        total_qty += flt(item.qty);
        base_total += flt(item.amount);
        base_net_total += flt(item.net_amount);
        if (item.is_passthrough_item) {
            total_supplier_cost += flt(item.supplier_total_cost);
        }
    });

    frm.set_value('total_qty', total_qty);
    frm.set_value('base_total', base_total);
    frm.set_value('base_net_total', base_net_total);
    frm.set_value('total_supplier_cost', total_supplier_cost);

    // Calculate taxes
    calculate_taxes(frm);

    // Calculate grand total
    let base_grand_total = flt(base_net_total) + flt(frm.doc.total_taxes_and_charges);
    frm.set_value('base_grand_total', base_grand_total);
    frm.set_value('rounded_total', Math.round(flt(base_grand_total) + flt(frm.doc.rounding_adjustment)));

    // Calculate margin
    let total_margin = flt(base_net_total) - flt(total_supplier_cost);
    frm.set_value('total_margin', total_margin);

    let margin_percentage = total_supplier_cost ?
        (flt(total_margin) / flt(total_supplier_cost) * 100) : 0;
    frm.set_value('margin_percentage', margin_percentage);
}

function calculate_taxes(frm) {
    let total_taxes = 0;
    let cumulative_total = flt(frm.doc.base_net_total);

    frm.doc.taxes.forEach(function (tax) {
        if (tax.charge_type === "On Net Total") {
            tax.tax_amount = flt(frm.doc.base_net_total) * flt(tax.rate) / 100;
        } else if (tax.charge_type === "Actual") {
            tax.tax_amount = flt(tax.rate);
        } else if (tax.charge_type === "On Previous Row Total") {
            tax.tax_amount = flt(cumulative_total) * flt(tax.rate) / 100;
        }

        cumulative_total += flt(tax.tax_amount);
        tax.total = cumulative_total;
        total_taxes += flt(tax.tax_amount);
    });

    frm.set_value('total_taxes_and_charges', total_taxes);
    frm.refresh_field('taxes');
}


function show_supplier_breakdown(frm) {
    // Show supplier-wise breakdown in a dialog
    frappe.call({
        method: 'fsc_custom.api.get_supplier_breakdown',
        args: {
            invoice_name: frm.doc.name
        },
        callback: function (r) {
            if (r.message) {
                let breakdown = r.message;
                let html = '<table class="table table-bordered"><thead><tr>' +
                    '<th>Supplier</th><th>Total Cost</th><th>Total Revenue</th>' +
                    '<th>Total Margin</th><th>Margin %</th></tr></thead><tbody>';

                for (let supplier in breakdown) {
                    let data = breakdown[supplier];
                    let margin_pct = data.total_cost ?
                        ((data.total_margin / data.total_cost) * 100).toFixed(2) : 0;

                    html += '<tr>' +
                        '<td>' + supplier + '</td>' +
                        '<td>' + format_currency(data.total_cost, frm.doc.currency) + '</td>' +
                        '<td>' + format_currency(data.total_revenue, frm.doc.currency) + '</td>' +
                        '<td>' + format_currency(data.total_margin, frm.doc.currency) + '</td>' +
                        '<td>' + margin_pct + '%</td>' +
                        '</tr>';
                }

                html += '</tbody></table>';

                frappe.msgprint({
                    title: __('Supplier Breakdown'),
                    message: html,
                    wide: true
                });
            }
        }
    });
}
