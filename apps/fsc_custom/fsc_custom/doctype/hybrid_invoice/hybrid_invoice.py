# Copyright (c) 2026, FSC and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class HybridInvoice(Document):
	def validate(self):
		"""Validation before saving"""
		self.validate_customer()
		self.validate_items()
		# Phase 1 enhancements
		self.set_address_display()
		self.validate_payment_terms()
		self.calculate_totals()
		self.calculate_additional_discount()
		self.calculate_tax_withholding()
		self.set_status()
	
	def validate_customer(self):
		"""Validate customer exists and is active"""
		if self.customer:
			customer = frappe.get_doc("Customer", self.customer)
			if customer.disabled:
				frappe.throw(_("Customer {0} is disabled").format(self.customer))
	
	def validate_items(self):
		"""Validate items and supplier information"""
		if not self.items:
			frappe.throw(_("Please add at least one item"))
		
		for item in self.items:
			# Validate passthrough items have supplier and cost
			if item.is_passthrough_item:
				if not item.supplier:
					frappe.throw(_("Row {0}: Supplier is required for passthrough items").format(item.idx))
				if not item.supplier_cost or item.supplier_cost <= 0:
					frappe.throw(_("Row {0}: Supplier cost must be greater than 0 for passthrough items").format(item.idx))
				
				# Validate selling rate is greater than supplier cost
				if item.rate <= item.supplier_cost:
					frappe.throw(_("Row {0}: Selling rate must be greater than supplier cost for passthrough items").format(item.idx))
			
			# Validate item exists and is active
			if item.item_code:
				item_doc = frappe.get_doc("Item", item.item_code)
				if item_doc.disabled:
					frappe.throw(_("Row {0}: Item {1} is disabled").format(item.idx, item.item_code))
	
	def calculate_totals(self):
		"""Calculate all totals"""
		self.total_qty = 0
		self.base_total = 0
		self.base_net_total = 0
		self.total_supplier_cost = 0
		
		# Calculate item-level amounts
		for item in self.items:
			# Calculate sales amounts
			item.amount = flt(item.qty) * flt(item.rate)
			
			# Calculate discount
			if item.discount_percentage:
				item.discount_amount = flt(item.amount) * flt(item.discount_percentage) / 100
			
			item.net_amount = flt(item.amount) - flt(item.discount_amount)
			item.net_rate = flt(item.net_amount) / flt(item.qty) if item.qty else 0
			
			# Calculate supplier costs for passthrough items
			if item.is_passthrough_item:
				item.supplier_total_cost = flt(item.qty) * flt(item.supplier_cost)
				item.item_margin = flt(item.net_amount) - flt(item.supplier_total_cost)
				item.item_margin_percentage = (flt(item.item_margin) / flt(item.supplier_total_cost) * 100) if item.supplier_total_cost else 0
				
				self.total_supplier_cost += item.supplier_total_cost
			else:
				item.supplier_total_cost = 0
				item.item_margin = item.net_amount
				item.item_margin_percentage = 0
			
			# Add to totals
			self.total_qty += flt(item.qty)
			self.base_total += flt(item.amount)
			self.base_net_total += flt(item.net_amount)
		
		# Calculate taxes
		self.calculate_taxes()
		
		# Calculate grand total
		self.base_grand_total = flt(self.base_net_total) + flt(self.total_taxes_and_charges)
		self.rounded_total = round(flt(self.base_grand_total) + flt(self.rounding_adjustment))
		
		# Calculate total margin
		self.total_margin = flt(self.base_net_total) - flt(self.total_supplier_cost)
		self.margin_percentage = (flt(self.total_margin) / flt(self.total_supplier_cost) * 100) if self.total_supplier_cost else 0
	
	def calculate_taxes(self):
		"""Calculate taxes and charges"""
		self.total_taxes_and_charges = 0
		cumulative_total = self.base_net_total
		
		for tax in self.taxes:
			if tax.charge_type == "On Net Total":
				tax.tax_amount = flt(self.base_net_total) * flt(tax.rate) / 100
			elif tax.charge_type == "Actual":
				tax.tax_amount = flt(tax.rate)
			elif tax.charge_type == "On Previous Row Total":
				tax.tax_amount = flt(cumulative_total) * flt(tax.rate) / 100
			
			cumulative_total += flt(tax.tax_amount)
			tax.total = cumulative_total
			self.total_taxes_and_charges += flt(tax.tax_amount)
	
	def set_status(self):
		"""Set document status"""
		if self.docstatus == 0:
			self.status = "Draft"
		elif self.docstatus == 1:
			self.status = "Submitted"
		elif self.docstatus == 2:
			self.status = "Cancelled"
	
	def before_submit(self):
		"""Validations before submission"""
		# Validate company
		if not self.company:
			frappe.throw(_("Company is required"))
		
		# Validate accounting dimensions
		self.validate_accounting_dimensions()
		
		# Check customer credit limit (optional, can be implemented)
		# self.check_credit_limit()
	
	def validate_accounting_dimensions(self):
		"""Validate that all items have proper accounts set"""
		for item in self.items:
			if not item.income_account:
				frappe.throw(_("Row {0}: Income Account is required").format(item.idx))
			
			if item.is_passthrough_item and not item.expense_account:
				frappe.throw(_("Row {0}: Expense Account is required for passthrough items").format(item.idx))
	
	# ===== Phase 1 Enhancement Methods =====
	
	def set_address_display(self):
		"""Fetch and display address details for customer, shipping, dispatch, and supplier"""
		from frappe.contacts.doctype.address.address import get_address_display
		
		# Customer address
		if self.customer_address:
			self.address_display = get_address_display(frappe.get_doc("Address", self.customer_address).as_dict())
		
		# Shipping address
		if self.shipping_address_name:
			self.shipping_address = get_address_display(frappe.get_doc("Address", self.shipping_address_name).as_dict())
		
		# Dispatch address
		if self.dispatch_address_name:
			self.dispatch_address = get_address_display(frappe.get_doc("Address", self.dispatch_address_name).as_dict())
		
		# Supplier address
		if self.supplier_address:
			self.supplier_address_display = get_address_display(frappe.get_doc("Address", self.supplier_address).as_dict())
		
		# Contact details
		if self.contact_person:
			contact = frappe.get_doc("Contact", self.contact_person)
			self.contact_display = contact.get_link_title()
			self.contact_email = contact.email_id
			self.contact_mobile = contact.mobile_no
	
	def validate_payment_terms(self):
		"""Validate and generate payment schedule from template"""
		if self.payment_terms_template and not self.payment_schedule:
			# Generate payment schedule from template
			self.payment_schedule = []
			
			template = frappe.get_doc("Payment Terms Template", self.payment_terms_template)
			
			for term in template.terms:
				payment_term = frappe.new_doc("Hybrid Invoice Payment Schedule")
				payment_term.payment_term = term.payment_term
				payment_term.description = term.description
				payment_term.invoice_portion = term.invoice_portion
				payment_term.mode_of_payment = term.mode_of_payment
				
				# Calculate due date
				if term.credit_days or term.credit_months:
					from frappe.utils import add_days, add_months
					due = getdate(self.posting_date)
					if term.credit_days:
						due = add_days(due, term.credit_days)
					if term.credit_months:
						due = add_months(due, term.credit_months)
					payment_term.due_date = due
				else:
					payment_term.due_date = self.posting_date
				
				self.payment_schedule.append(payment_term)
		
		# Calculate payment amounts
		if self.payment_schedule and self.base_grand_total:
			for schedule in self.payment_schedule:
				schedule.payment_amount = flt(self.base_grand_total) * flt(schedule.invoice_portion) / 100
				schedule.outstanding = flt(schedule.payment_amount) - flt(schedule.paid_amount)
		
		# Set due date to last payment schedule date
		if self.payment_schedule and not self.due_date:
			self.due_date = self.payment_schedule[-1].due_date
	
	def calculate_additional_discount(self):
		"""Apply additional discount on grand total or net total"""
		if self.apply_discount_on and (self.additional_discount_percentage or self.discount_amount):
			# Determine base amount for discount
			if self.apply_discount_on == "Grand Total":
				base_amount = flt(self.base_grand_total)
			else:  # Net Total
				base_amount = flt(self.base_net_total)
			
			# Calculate discount amount if percentage is given
			if self.additional_discount_percentage:
				self.discount_amount = base_amount * flt(self.additional_discount_percentage) / 100
			
			# Apply discount to grand total
			self.base_grand_total = flt(self.base_grand_total) - flt(self.discount_amount)
			self.rounded_total = round(flt(self.base_grand_total) + flt(self.rounding_adjustment))
	
	def calculate_tax_withholding(self):
		"""Calculate tax withholding (TDS) if applicable"""
		if self.apply_tds and self.tax_withholding_category:
			# Get tax withholding details
			try:
				from erpnext.accounts.doctype.tax_withholding_category.tax_withholding_category import (
					get_party_tax_withholding_details
				)
				
				# Calculate TDS on net total
				self.tax_withholding_net_total = flt(self.base_net_total)
				
				# Note: TDS calculation would require integration with ERPNext's tax withholding system
				# This is a placeholder for the basic structure
			except ImportError:
				pass
	
	def on_submit(self):
		"""Actions on document submission"""
		self.make_gl_entries()
	
	def on_cancel(self):
		"""Actions on document cancellation"""
		self.make_gl_entries(cancel=True)
		self.status = "Cancelled"
	
	def make_gl_entries(self, cancel=False):
		"""Create General Ledger entries"""
		from erpnext.accounts.general_ledger import make_gl_entries
		
		gl_entries = []
		
		# Get customer account
		customer_account = frappe.get_value("Party Account", 
			{"parent": self.customer, "company": self.company}, "account") or \
			frappe.get_value("Company", self.company, "default_receivable_account")
		
		if not customer_account:
			frappe.throw(_("Customer account not found for {0}").format(self.customer))
		
		# 1. Debit Customer (Total Invoice Amount)
		gl_entries.append(
			self.get_gl_dict({
				"account": customer_account,
				"party_type": "Customer",
				"party": self.customer,
				"debit": flt(self.rounded_total),
				"debit_in_account_currency": flt(self.rounded_total),
				"against": self.get_against_accounts(),
				"remarks": self.get_remarks(),
			}, item=None)
		)
		
		# 2. Process items grouped by supplier
		supplier_groups = self.group_items_by_supplier()
		
		for supplier, items in supplier_groups.items():
			if supplier:  # Passthrough items with supplier
				total_supplier_cost = sum(flt(item.supplier_total_cost) for item in items)
				total_revenue = sum(flt(item.net_amount) for item in items)
				
				# Get supplier account
				supplier_account = frappe.get_value("Party Account", 
					{"parent": supplier, "company": self.company}, "account") or \
					frappe.get_value("Company", self.company, "default_payable_account")
				
				if not supplier_account:
					frappe.throw(_("Supplier account not found for {0}").format(supplier))
				
				# Credit Supplier (payable)
				gl_entries.append(
					self.get_gl_dict({
						"account": supplier_account,
						"party_type": "Supplier",
						"party": supplier,
						"credit": total_supplier_cost,
						"credit_in_account_currency": total_supplier_cost,
						"against": self.customer,
						"remarks": self.get_remarks(),
					}, item=None)
				)
				
				# Debit Expense Account
				for item in items:
					gl_entries.append(
						self.get_gl_dict({
							"account": item.expense_account,
							"debit": flt(item.supplier_total_cost),
							"debit_in_account_currency": flt(item.supplier_total_cost),
							"against": supplier,
							"cost_center": item.cost_center or self.cost_center,
							"project": item.project,
							"remarks": self.get_remarks(),
						}, item=item)
					)
				
				# Credit Income Account
				for item in items:
					gl_entries.append(
						self.get_gl_dict({
							"account": item.income_account,
							"credit": flt(item.net_amount),
							"credit_in_account_currency": flt(item.net_amount),
							"against": self.customer,
							"cost_center": item.cost_center or self.cost_center,
							"project": item.project,
							"remarks": self.get_remarks(),
						}, item=item)
					)
			
			else:  # Direct sales items (no supplier)
				for item in items:
					gl_entries.append(
						self.get_gl_dict({
							"account": item.income_account,
							"credit": flt(item.net_amount),
							"credit_in_account_currency": flt(item.net_amount),
							"against": self.customer,
							"cost_center": item.cost_center or self.cost_center,
							"project": item.project,
							"remarks": self.get_remarks(),
						}, item=item)
					)
		
		# 3. Tax Entries
		for tax in self.taxes:
			if flt(tax.tax_amount) != 0:
				gl_entries.append(
					self.get_gl_dict({
						"account": tax.account_head,
						"credit": flt(tax.tax_amount),
						"credit_in_account_currency": flt(tax.tax_amount),
						"against": self.customer,
						"cost_center": tax.cost_center or self.cost_center,
						"remarks": self.get_remarks(),
					}, item=None)
				)
		
		# Make GL Entries
		if gl_entries:
			make_gl_entries(gl_entries, cancel=cancel, adv_adj=False)
	
	def group_items_by_supplier(self):
		"""Group items by supplier for GL entries"""
		supplier_dict = {}
		
		for item in self.items:
			supplier = item.supplier if item.is_passthrough_item else None
			
			if supplier not in supplier_dict:
				supplier_dict[supplier] = []
			
			supplier_dict[supplier].append(item)
		
		return supplier_dict
	
	def get_gl_dict(self, args, item=None):
		"""Get GL entry dict with default values"""
		gl_dict = frappe._dict({
			"posting_date": self.posting_date,
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"company": self.company,
			"remarks": args.get("remarks") or self.get_remarks(),
			"debit": 0,
			"credit": 0,
			"debit_in_account_currency": 0,
			"credit_in_account_currency": 0,
			"is_opening": "No",
		})
		
		gl_dict.update(args)
		return gl_dict
	
	def get_remarks(self):
		"""Get remarks for GL entry"""
		return _("Hybrid Invoice for Customer: {0}").format(self.customer_name or self.customer)
	
	def get_against_accounts(self):
		"""Get comma-separated list of accounts for 'against' field"""
		accounts = []
		
		# Add all income accounts
		for item in self.items:
			if item.income_account and item.income_account not in accounts:
				accounts.append(item.income_account)
		
		# Add all supplier accounts
		for item in self.items:
			if item.is_passthrough_item and item.supplier:
				supplier_account = frappe.get_value("Party Account", 
					{"parent": item.supplier, "company": self.company}, "account")
				if supplier_account and supplier_account not in accounts:
					accounts.append(supplier_account)
		
		# Add tax accounts
		for tax in self.taxes:
			if tax.account_head and tax.account_head not in accounts:
				accounts.append(tax.account_head)
		
		return ", ".join(accounts)
