# Copyright (c) 2026, FSC and contributors
# Script to add Phase 1 enhancement fields to Hybrid Invoice

import frappe
import json


def add_phase1_fields():
	"""Add Phase 1 selective enhancement fields to Hybrid Invoice"""
	
	# Load current Hybrid Invoice JSON
	doctype_path = '/home/frappe/frappe-bench/apps/fsc_custom/fsc_custom/doctype/hybrid_invoice/hybrid_invoice.json'
	
	with open(doctype_path, 'r') as f:
		doctype = json.load(f)
	
	# New fields to add
	new_fields = []
	
	# ===== Address & Contact Fields (after customer_name) =====
	address_fields = [
		{
			"fieldname": "customer_address",
			"fieldtype": "Link",
			"label": "Customer Address",
			"options": "Address"
		},
		{
			"fieldname": "address_display",
			"fieldtype": "Small Text",
			"label": "Address",
			"read_only": 1
		},
		{
			"fieldname": "contact_person",
			"fieldtype": "Link",
			"label": "Contact Person",
			"options": "Contact"
		},
		{
			"fieldname": "contact_display",
			"fieldtype": "Small Text",
			"label": "Contact",
			"read_only": 1
		},
		{
			"fieldname": "contact_mobile",
			"fieldtype": "Small Text",
			"label": "Mobile No",
			"read_only": 1
		},
		{
			"fieldname": "contact_email",
			"fieldtype": "Small Text",
			"label": "Contact Email",
			"read_only": 1
		},
		{
			"fieldname": "territory",
			"fieldtype": "Link",
			"label": "Territory",
			"options": "Territory"
		}
	]
	
	# ===== Shipping Section =====
	shipping_section = [
		{
			"fieldname": "section_break_shipping",
			"fieldtype": "Section Break",
			"label": "Shipping Information",
			"collapsible": 1
		},
		{
			"fieldname": "shipping_address_name",
			"fieldtype": "Link",
			"label": "Shipping Address",
			"options": "Address"
		},
		{
			"fieldname": "shipping_address",
			"fieldtype": "Small Text",
			"label": "Shipping Address Details",
			"read_only": 1
		},
		{
			"fieldname": "column_break_shipping",
			"fieldtype": "Column Break"
		},
		{
			"fieldname": "dispatch_address_name",
			"fieldtype": "Link",
			"label": "Dispatch Address",
			"options": "Address"
		},
		{
			"fieldname": "dispatch_address",
			"fieldtype": "Small Text",
			"label": "Dispatch Address Details",
			"read_only": 1
		}
	]
	
	# ===== Supplier Details Section =====
	supplier_section = [
		{
			"fieldname": "section_break_supplier_details",
			"fieldtype": "Section Break",
			"label": "Supplier Invoice Details",
			"collapsible": 1
		},
		{
			"fieldname": "supplier_invoice_number",
			"fieldtype": "Data",
			"label": "Supplier Invoice Number"
		},
		{
			"fieldname": "bill_no",
			"fieldtype": "Data",
			"label": "Bill No"
		},
		{
			"fieldname": "bill_date",
			"fieldtype": "Date",
			"label": "Bill Date"
		},
		{
			"fieldname": "column_break_supplier_details",
			"fieldtype": "Column Break"
		},
		{
			"fieldname": "supplier_address",
			"fieldtype": "Link",
			"label": "Supplier Address",
			"options": "Address"
		},
		{
			"fieldname": "supplier_address_display",
			"fieldtype": "Small Text",
			"label": "Supplier Address Details",
			"read_only": 1
		}
	]
	
	# ===== Additional Discount Section (before totals) =====
	discount_section = [
		{
			"fieldname": "section_break_additional_discount",
			"fieldtype": "Section Break",
			"label": "Additional Discount",
			"collapsible": 1
		},
		{
			"fieldname": "apply_discount_on",
			"fieldtype": "Select",
			"label": "Apply Additional Discount On",
			"options": "\nGrand Total\nNet Total"
		},
		{
			"fieldname": "additional_discount_percentage",
			"fieldtype": "Percent",
			"label": "Additional Discount Percentage"
		},
		{
			"fieldname": "column_break_discount",
			"fieldtype": "Column Break"
		},
		{
			"fieldname": "discount_amount",
			"fieldtype": "Currency",
			"label": "Additional Discount Amount",
			"options": "currency"
		}
	]
	
	# ===== Payment Terms Section =====
	payment_section = [
		{
			"fieldname": "section_break_payment_terms",
			"fieldtype": "Section Break",
			"label": "Payment Terms",
			"collapsible": 1
		},
		{
			"fieldname": "payment_terms_template",
			"fieldtype": "Link",
			"label": "Payment Terms Template",
			"options": "Payment Terms Template"
		},
		{
			"fieldname": "due_date",
			"fieldtype": "Date",
			"label": "Due Date"
		},
		{
			"fieldname": "payment_schedule",
			"fieldtype": "Table",
			"label": "Payment Schedule",
			"options": "Hybrid Invoice Payment Schedule"
		}
	]
	
	# ===== Tax Withholding Section =====
	tax_withholding_section = [
		{
			"fieldname": "section_break_tax_withholding",
			"fieldtype": "Section Break",
			"label": "Tax Withholding",
			"collapsible": 1
		},
		{
			"fieldname": "tax_withholding_category",
			"fieldtype": "Link",
			"label": "Tax Withholding Category",
			"options": "Tax Withholding Category"
		},
		{
			"fieldname": "apply_tds",
			"fieldtype": "Check",
			"label": "Apply Tax Withholding Amount",
			"default": "0"
		},
		{
			"fieldname": "column_break_tax_withholding",
			"fieldtype": "Column Break"
		},
		{
			"fieldname": "tax_withholding_net_total",
			"fieldtype": "Currency",
			"label": "Tax Withholding Net Total",
			"options": "currency",
			"read_only": 1
		}
	]
	
	# Find insertion points in field_order
	field_order = doctype['field_order']
	
	# Insert address fields after posting_time
	posting_time_idx = field_order.index('posting_time')
	for field in reversed(address_fields):
		field_order.insert(posting_time_idx + 1, field['fieldname'])
	
	# Insert shipping section after accounting section
	accounting_idx = field_order.index('price_list')
	for field in reversed(shipping_section):
		field_order.insert(accounting_idx + 1, field['fieldname'])
	
	# Insert supplier section after items section
	items_idx = field_order.index('items')
	for field in reversed(supplier_section):
		field_order.insert(items_idx + 1, field['fieldname'])
	
	# Insert discount section before totals
	totals_idx = field_order.index('section_break_totals')
	for field in reversed(discount_section):
		field_order.insert(totals_idx, field['fieldname'])
	
	# Insert payment and tax sections after margin section
	margin_idx = field_order.index('margin_percentage')
	for field in reversed(payment_section):
		field_order.insert(margin_idx + 1, field['fieldname'])
	
	payment_schedule_idx = field_order.index('payment_schedule')
	for field in reversed(tax_withholding_section):
		field_order.insert(payment_schedule_idx + 1, field['fieldname'])
	
	# Add all field definitions
	all_new_fields = (address_fields + shipping_section + supplier_section + 
	                 discount_section + payment_section + tax_withholding_section)
	doctype['fields'].extend(all_new_fields)
	
	# Save updated JSON
	with open(doctype_path, 'w') as f:
		json.dump(doctype, f, indent=4)
	
	print(f"✓ Added {len(all_new_fields)} new fields to Hybrid Invoice")
	print("✓ Updated field_order")
	print("\nNew sections added:")
	print("  - Address & Contact Information")
	print("  - Shipping Information")
	print("  - Supplier Invoice Details")
	print("  - Additional Discount")
	print("  - Payment Terms")
	print("  - Tax Withholding")


if __name__ == '__main__':
	add_phase1_fields()
