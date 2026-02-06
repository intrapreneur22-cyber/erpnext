# Copyright (c) 2026, FSC and contributors
# Server-side logic for Sales Invoice Pass-Through functionality

import frappe
from frappe import _
from frappe.utils import flt, getdate


def on_submit(doc, method):
	"""Create Purchase Invoices for pass-through items on Sales Invoice submission"""
	create_purchase_invoices_for_passthrough(doc)


def on_cancel(doc, method):
	"""Cancel linked Purchase Invoices when Sales Invoice is cancelled"""
	cancel_linked_purchase_invoices(doc)


def update_stock_ledger(doc, method):
	"""Override stock ledger updates to exclude pass-through items"""
	# This hook prevents stock updates for pass-through items
	# Implementation depends on how ERPNext processes stock
	pass


def create_purchase_invoices_for_passthrough(sales_invoice):
	"""
	Group pass-through items by supplier and create Purchase Invoices
	"""
	# Group items by supplier
	supplier_items = {}
	
	for item in sales_invoice.items:
		if item.is_passthrough_item and item.supplier:
			# Validate required fields
			if not item.supplier_rate or item.supplier_rate <= 0:
				frappe.throw(_(f"Row {item.idx}: Supplier rate is required for pass-through item {item.item_code}"))
			
			if not item.expense_account:
				frappe.throw(_(f"Row {item.idx}: Expense account is required for pass-through item {item.item_code}"))
			
			# Group by supplier
			if item.supplier not in supplier_items:
				supplier_items[item.supplier] = []
			supplier_items[item.supplier].append(item)
	
	# Create Purchase Invoice for each supplier
	purchase_invoices = []
	
	for supplier, items in supplier_items.items():
		try:
			pi = create_purchase_invoice(sales_invoice, supplier, items)
			purchase_invoices.append(pi.name)
			
			# Update Sales Invoice items with PI reference
			for item in items:
				frappe.db.set_value("Sales Invoice Item", item.name, "purchase_invoice", pi.name, update_modified=False)
			
			frappe.msgprint(
				_("Purchase Invoice {0} created for supplier {1}").format(
					f'<a href="/app/purchase-invoice/{pi.name}">{pi.name}</a>', 
					supplier
				),
				indicator="green",
				alert=True
			)
			
		except Exception as e:
			frappe.log_error(f"Error creating Purchase Invoice for supplier {supplier}: {str(e)}")
			frappe.throw(_(f"Failed to create Purchase Invoice for supplier {supplier}: {str(e)}"))
	
	# Commit the PI references
	frappe.db.commit()
	
	return purchase_invoices


def create_purchase_invoice(sales_invoice, supplier, items):
	"""Create a single Purchase Invoice for a supplier"""
	
	pi = frappe.new_doc("Purchase Invoice")
	
	# Set header fields
	pi.supplier = supplier
	pi.company = sales_invoice.company
	pi.posting_date = sales_invoice.posting_date
	pi.set_posting_time = 1
	pi.posting_time = sales_invoice.posting_time
	pi.currency = sales_invoice.currency
	pi.conversion_rate = sales_invoice.conversion_rate or 1
	pi.buying_price_list = items[0].buying_price_list if items else "Standard Buying"
	
	# Link back to Sales Invoice
	pi.custom_sales_invoice = sales_invoice.name
	
	# Set remarks
	pi.remarks = _(f"Auto-created from Sales Invoice {sales_invoice.name} for pass-through items")
	
	# Add items
	for si_item in items:
		pi.append("items", {
			"item_code": si_item.item_code,
			"item_name": si_item.item_name,
			"description": si_item.description or si_item.item_name,
			"qty": si_item.qty,
			"uom": si_item.uom,
			"stock_uom": si_item.stock_uom,
			"conversion_factor": si_item.conversion_factor or 1,
			"rate": si_item.supplier_rate,
			"amount": si_item.supplier_amount,
			"expense_account": si_item.expense_account,
			"cost_center": si_item.cost_center,
			"project": si_item.project if hasattr(si_item, 'project') else None,
			# Important: Don't update stock for pass-through items
			"update_stock": 0
		})
	
	# Calculate totals
	pi.run_method("calculate_taxes_and_totals")
	
	# Insert without submit (leave as Draft for review)
	# Users can review and submit manually
	pi.flags.ignore_permissions = True
	pi.insert()
	
	# Optional: Auto-submit if configured
	# Uncomment the next two lines to auto-submit
	# pi.submit()
	# frappe.msgprint(_(f"Purchase Invoice {pi.name} submitted"), indicator="green")
	
	return pi


def cancel_linked_purchase_invoices(sales_invoice):
	"""Cancel all Purchase Invoices linked to this Sales Invoice"""
	
	# Find all linked Purchase Invoices
	linked_pis = frappe.db.sql("""
		SELECT DISTINCT name
		FROM `tabPurchase Invoice`
		WHERE custom_sales_invoice = %s
		AND docstatus = 1
	""", sales_invoice.name, as_dict=1)
	
	for pi_row in linked_pis:
		try:
			pi = frappe.get_doc("Purchase Invoice", pi_row.name)
			pi.flags.ignore_permissions = True
			pi.cancel()
			
			frappe.msgprint(
				_("Purchase Invoice {0} cancelled").format(pi.name),
				indicator="orange"
			)
			
		except Exception as e:
			frappe.log_error(f"Error cancelling Purchase Invoice {pi_row.name}: {str(e)}")
			# Don't throw error, just log it - allow SI cancellation to proceed
			frappe.msgprint(
				_("Warning: Could not cancel Purchase Invoice {0}: {1}").format(pi_row.name, str(e)),
				indicator="red"
			)
	
	# Also cancel draft PIs (remove reference but don't cancel since they're not submitted)
	draft_pis = frappe.db.sql("""
		SELECT DISTINCT name
		FROM `tabPurchase Invoice`
		WHERE custom_sales_invoice = %s
		AND docstatus = 0
	""", sales_invoice.name, as_dict=1)
	
	for pi_row in draft_pis:
		try:
			frappe.delete_doc("Purchase Invoice", pi_row.name, force=1)
			frappe.msgprint(
				_("Draft Purchase Invoice {0} deleted").format(pi_row.name),
				indicator="orange"
			)
		except Exception as e:
			frappe.log_error(f"Error deleting draft Purchase Invoice {pi_row.name}: {str(e)}")


@frappe.whitelist()
def get_passthrough_summary(sales_invoice_name):
	"""Get summary of pass-through items in a Sales Invoice"""
	
	doc = frappe.get_doc("Sales Invoice", sales_invoice_name)
	
	passthrough_items = [item for item in doc.items if item.is_passthrough_item]
	
	if not passthrough_items:
		return {
			"total_items": 0,
			"total_suppliers": 0,
			"total_cost": 0,
			"total_revenue": 0,
			"total_margin": 0,
			"margin_percentage": 0,
			"supplier_breakdown": {}
		}
	
	# Group by supplier
	supplier_groups = {}
	for item in passthrough_items:
		if item.supplier not in supplier_groups:
			supplier_groups[item.supplier] = {
				"items": [],
				"total_cost": 0,
				"total_revenue": 0,
				"total_margin": 0,
				"purchase_invoice": item.purchase_invoice
			}
		
		supplier_groups[item.supplier]["items"].append({
			"item_code": item.item_code,
			"item_name": item.item_name,
			"qty": item.qty,
			"supplier_rate": item.supplier_rate,
			"supplier_amount": item.supplier_amount,
			"rate": item.rate,
			"amount": item.amount,
			"margin_amount": item.margin_amount,
			"margin_percentage": item.margin_percentage
		})
		
		supplier_groups[item.supplier]["total_cost"] += flt(item.supplier_amount)
		supplier_groups[item.supplier]["total_revenue"] += flt(item.amount)
		supplier_groups[item.supplier]["total_margin"] += flt(item.margin_amount)
	
	# Calculate totals
	total_cost = sum(flt(item.supplier_amount) for item in passthrough_items)
	total_revenue = sum(flt(item.amount) for item in passthrough_items)
	total_margin = total_revenue - total_cost
	margin_percentage = (total_margin / total_cost * 100) if total_cost else 0
	
	return {
		"total_items": len(passthrough_items),
		"total_suppliers": len(supplier_groups),
		"total_cost": total_cost,
		"total_revenue": total_revenue,
		"total_margin": total_margin,
		"margin_percentage": margin_percentage,
		"supplier_breakdown": supplier_groups
	}
