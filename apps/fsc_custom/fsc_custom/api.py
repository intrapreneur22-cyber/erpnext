# Copyright (c) 2026, FSC and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_last_purchase_rate(item_code, supplier):
	"""Get last purchase rate for an item from a supplier"""
	rate = frappe.db.sql("""
		SELECT pi_item.rate 
		FROM `tabPurchase Invoice Item` pi_item
		INNER JOIN `tabPurchase Invoice` pi ON pi.name = pi_item.parent
		WHERE pi_item.item_code = %s 
		AND pi.supplier = %s 
		AND pi.docstatus = 1
		ORDER BY pi.posting_date DESC, pi.creation DESC
		LIMIT 1
	""", (item_code, supplier), as_dict=1)
	
	return {'rate': rate[0].rate if rate else 0}


@frappe.whitelist()
def get_supplier_breakdown(invoice_name):
	"""Get supplier-wise breakdown of costs and margins"""
	doc = frappe.get_doc('Hybrid Invoice', invoice_name)
	
	breakdown = {}
	for item in doc.items:
		if item.is_passthrough_item and item.supplier:
			if item.supplier not in breakdown:
				breakdown[item.supplier] = {
					'total_cost': 0,
					'total_revenue': 0,
					'total_margin': 0,
					'items': []
				}
			
			breakdown[item.supplier]['total_cost'] += item.supplier_total_cost or 0
			breakdown[item.supplier]['total_revenue'] += item.net_amount or 0
			breakdown[item.supplier]['total_margin'] += item.item_margin or 0
			breakdown[item.supplier]['items'].append({
				'item_code': item.item_code,
				'item_name': item.item_name,
				'qty': item.qty,
				'cost': item.supplier_total_cost,
				'revenue': item.net_amount,
				'margin': item.item_margin
			})
	
	return breakdown
