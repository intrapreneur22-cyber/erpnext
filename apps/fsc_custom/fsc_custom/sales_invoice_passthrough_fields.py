# Copyright (c) 2026, FSC and contributors
# Custom fields for Sales Invoice Pass-Through functionality

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def create_sales_invoice_passthrough_fields():
	"""Create custom fields for Sales Invoice Item to support pass-through items"""
	
	custom_fields = {
		"Sales Invoice Item": [
			{
				"fieldname": "is_passthrough_item",
				"label": "Is Pass-Through Item",
				"fieldtype": "Check",
				"insert_after": "item_name",
				"allow_on_submit": 0,
				"description": "Check if this item is delivered directly by supplier (pass-through)"
			},
			{
				"fieldname": "passthrough_section",
				"label": "Pass-Through Details",
				"fieldtype": "Section Break",
				"insert_after": "is_passthrough_item",
				"collapsible": 1,
				"depends_on": "eval:doc.is_passthrough_item==1"
			},
			{
				"fieldname": "supplier",
				"label": "Supplier",
				"fieldtype": "Link",
				"options": "Supplier",
				"insert_after": "passthrough_section",
				"mandatory_depends_on": "eval:doc.is_passthrough_item==1"
			},
			{
				"fieldname": "buying_price_list",
				"label": "Buying Price List",
				"fieldtype": "Link",
				"options": "Price List",
				"insert_after": "supplier",
				"default": "Standard Buying"
			},
			{
				"fieldname": "column_break_passthrough",
				"fieldtype": "Column Break",
				"insert_after": "buying_price_list"
			},
			{
				"fieldname": "supplier_rate",
				"label": "Supplier Rate",
				"fieldtype": "Currency",
				"insert_after": "column_break_passthrough",
				"options": "currency",
				"precision": "2"
			},
			{
				"fieldname": "supplier_amount",
				"label": "Supplier Amount",
				"fieldtype": "Currency",
				"insert_after": "supplier_rate",
				"options": "currency",
				"read_only": 1,
				"precision": "2"
			},
			{
				"fieldname": "section_break_margin",
				"label": "Margin Analysis",
				"fieldtype": "Section Break",
				"insert_after": "supplier_amount",
				"collapsible": 1,
				"depends_on": "eval:doc.is_passthrough_item==1"
			},
			{
				"fieldname": "margin_amount",
				"label": "Margin Amount",
				"fieldtype": "Currency",
				"insert_after": "section_break_margin",
				"options": "currency",
				"read_only": 1,
				"precision": "2"
			},
			{
				"fieldname": "margin_percentage",
				"label": "Margin %",
				"fieldtype": "Percent",
				"insert_after": "margin_amount",
				"read_only": 1,
				"precision": "2"
			},
			{
				"fieldname": "column_break_margin",
				"fieldtype": "Column Break",
				"insert_after": "margin_percentage"
			},
			{
				"fieldname": "purchase_invoice",
				"label": "Purchase Invoice",
				"fieldtype": "Link",
				"options": "Purchase Invoice",
				"insert_after": "column_break_margin",
				"read_only": 1,
				"description": "Auto-created Purchase Invoice for this pass-through item"
			}
		],
		"Purchase Invoice": [
			{
				"fieldname": "custom_sales_invoice",
				"label": "Source Sales Invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"insert_after": "title",
				"read_only": 1,
				"description": "Sales Invoice that triggered this Purchase Invoice (for pass-through items)"
			}
		]
	}
	
	create_custom_fields(custom_fields, update=True)
	print("✓ Created custom fields for Sales Invoice pass-through functionality")


if __name__ == "__main__":
	frappe.connect()
	create_sales_invoice_passthrough_fields()
	frappe.db.commit()
