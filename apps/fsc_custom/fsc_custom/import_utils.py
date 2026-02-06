# Copyright (c) 2026, FSC and contributors
# For license information, please see license.txt

import frappe
import json
import os


def import_doctypes():
	"""Import Hybrid Invoice DocTypes from JSON files into database"""
	# Define the doctypes to import in order (child tables first)
	doctypes = [
		'/home/frappe/frappe-bench/apps/fsc_custom/fsc_custom/doctype/hybrid_invoice_item/hybrid_invoice_item.json',
		'/home/frappe/frappe-bench/apps/fsc_custom/fsc_custom/doctype/hybrid_invoice_taxes_and_charges/hybrid_invoice_taxes_and_charges.json',
		'/home/frappe/frappe-bench/apps/fsc_custom/fsc_custom/doctype/hybrid_invoice/hybrid_invoice.json'
	]
	
	for doctype_path in doctypes:
		if os.path.exists(doctype_path):
			with open(doctype_path, 'r') as f:
				data = json.load(f)
				doctype_name = data.get('name')
				
				# Check if doctype already exists
				if frappe.db.exists('DocType', doctype_name):
					print(f"DocType '{doctype_name}' already exists, updating...")
					doc = frappe.get_doc('DocType', doctype_name)
					doc.update(data)
					doc.save()
				else:
					print(f"Creating DocType '{doctype_name}'...")
					doc = frappe.get_doc(data)
					doc.flags.ignore_permissions = True
					doc.insert()
				
				frappe.db.commit()
				print(f"✓ Successfully saved '{doctype_name}'")
		else:
			print(f"File not found: {doctype_path}")
	
	print("\nAll DocTypes imported successfully!")
