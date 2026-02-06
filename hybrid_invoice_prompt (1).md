# Custom Hybrid Invoice DocType - Development Specifications

## Project Overview
Create a custom Frappe DocType called **"Hybrid Invoice"** that combines sales and purchase transactions in a single document. This allows drop-shipping or intermediary scenarios where items are purchased from suppliers and sold to customers simultaneously, with proper accounting entries for both sides of the transaction.

---

## Business Requirements

### Core Functionality
1. **Single Transaction Document** that handles:
   - Direct sales items (inventory we own)
   - Pass-through items (purchased from suppliers and sold to customers)
   - Mixed scenarios (combination of both)

2. **Accounting Treatment**:
   - Customer account is debited for total sales amount
   - Each supplier account is credited for their respective items
   - Revenue recognition for the margin/markup
   - Proper tax handling (input and output taxes)

3. **Multi-Supplier Support**:
   - Each line item can have a different supplier
   - Automatic grouping by supplier for accounting entries
   - Supplier-wise cost tracking

---

## Technical Specifications

### DocType Structure

#### Parent DocType: `Hybrid Invoice`

**Fields:**

```python
# Customer Information
- customer (Link to Customer) - Required
- customer_name (Data) - Read Only, fetched from Customer
- posting_date (Date) - Required, default: Today
- posting_time (Time) - Required, default: Now
- company (Link to Company) - Required
- cost_center (Link to Cost Center)

# Accounting Information
- currency (Link to Currency) - Default from Customer
- conversion_rate (Float) - Default: 1.0
- price_list (Link to Price List)

# Totals Section
- total_qty (Float) - Read Only, Calculated
- base_total (Currency) - Read Only, Calculated
- base_net_total (Currency) - Read Only, Calculated
- total_taxes_and_charges (Currency) - Read Only, Calculated
- base_grand_total (Currency) - Read Only, Calculated
- rounding_adjustment (Currency)
- rounded_total (Currency) - Read Only, Calculated

# Supplier Cost Tracking
- total_supplier_cost (Currency) - Read Only, Calculated
- total_margin (Currency) - Read Only, Calculated
- margin_percentage (Percent) - Read Only, Calculated

# Status and References
- status (Select) - Draft, Submitted, Cancelled
- amended_from (Link to Hybrid Invoice)
```

#### Child Table: `Hybrid Invoice Item`

**Fields:**

```python
# Item Details
- item_code (Link to Item) - Required
- item_name (Data) - Read Only
- description (Text Editor)
- item_group (Link to Item Group) - Read Only
- qty (Float) - Required, default: 1.0
- uom (Link to UOM) - Required
- stock_uom (Link to UOM) - Read Only
- conversion_factor (Float) - Default: 1.0

# Pricing - Sales Side
- rate (Currency) - Required (Selling Price)
- amount (Currency) - Read Only (qty * rate)
- discount_percentage (Percent)
- discount_amount (Currency)
- net_rate (Currency) - Read Only
- net_amount (Currency) - Read Only

# Supplier Information (for pass-through items)
- is_passthrough_item (Check) - Default: 0
- supplier (Link to Supplier) - Required if is_passthrough_item = 1
- supplier_quotation (Link to Supplier Quotation) - Optional
- supplier_cost (Currency) - Required if is_passthrough_item = 1
- supplier_total_cost (Currency) - Read Only (qty * supplier_cost)

# Margin Calculation
- item_margin (Currency) - Read Only (net_amount - supplier_total_cost)
- item_margin_percentage (Percent) - Read Only

# Accounting Dimensions
- cost_center (Link to Cost Center)
- project (Link to Project)
- income_account (Link to Account)
- expense_account (Link to Account) - for passthrough items

# Tax Template
- item_tax_template (Link to Item Tax Template)
```

#### Child Table: `Hybrid Invoice Taxes and Charges`

**Fields:**

```python
- charge_type (Select) - On Net Total, On Previous Row Total, Actual
- account_head (Link to Account) - Required
- description (Small Text)
- rate (Float)
- tax_amount (Currency) - Read Only
- total (Currency) - Read Only
- cost_center (Link to Cost Center)
```

---

## Implementation Guidelines

### Phase 1: DocType Creation

```bash
# Create the custom app structure
bench new-app hybrid_invoice
bench --site [sitename] install-app hybrid_invoice

# Create DocTypes
bench --site [sitename] console
```

**Create following files:**

1. `hybrid_invoice/hybrid_invoice/doctype/hybrid_invoice/hybrid_invoice.json`
2. `hybrid_invoice/hybrid_invoice/doctype/hybrid_invoice/hybrid_invoice.py`
3. `hybrid_invoice/hybrid_invoice/doctype/hybrid_invoice_item/hybrid_invoice_item.json`
4. `hybrid_invoice/hybrid_invoice/doctype/hybrid_invoice_taxes_and_charges/hybrid_invoice_taxes_and_charges.json`

### Phase 2: Server-Side Logic (Python)

**File: `hybrid_invoice.py`**

Implement the following methods:

```python
class HybridInvoice(Document):
    def validate(self):
        """Validation before saving"""
        - Validate customer exists and is active
        - Validate each item's supplier if is_passthrough_item
        - Ensure supplier_cost is provided for passthrough items
        - Validate selling rate > supplier cost for passthrough items
        - Calculate all totals
        - Validate accounting dimensions
        
    def before_submit(self):
        """Before submission checks"""
        - Ensure all mandatory fields are filled
        - Validate GL accounts exist
        - Check if customer credit limit is not exceeded
        
    def on_submit(self):
        """Create accounting entries on submit"""
        - Create GL Entries
        - Update customer outstanding
        - Update supplier outstanding for passthrough items
        - Create stock ledger entries (if applicable)
        
    def on_cancel(self):
        """Reverse entries on cancellation"""
        - Cancel GL Entries
        - Reverse customer outstanding
        - Reverse supplier outstanding
        
    def calculate_totals(self):
        """Calculate document totals"""
        - Sum all item amounts
        - Calculate total supplier costs
        - Calculate total margin
        - Apply taxes and charges
        - Calculate grand total
        
    def make_gl_entries(self):
        """Generate accounting entries"""
        # See detailed implementation below
```

### Phase 3: GL Entry Logic

**Accounting Entry Structure:**

For each Hybrid Invoice, create the following GL entries:

```python
def make_gl_entries(self):
    gl_entries = []
    
    # 1. Debit Customer (Total Invoice Amount)
    gl_entries.append({
        'account': customer_account,
        'party_type': 'Customer',
        'party': self.customer,
        'debit': self.rounded_total,
        'credit': 0,
        'against': suppliers_list,  # Comma-separated supplier list
        'voucher_type': 'Hybrid Invoice',
        'voucher_no': self.name,
        'posting_date': self.posting_date,
        'company': self.company
    })
    
    # 2. Group items by supplier and create entries
    supplier_wise_items = self.group_items_by_supplier()
    
    for supplier, items in supplier_wise_items.items():
        if supplier:  # Passthrough items
            total_cost = sum(item.supplier_total_cost for item in items)
            total_revenue = sum(item.net_amount for item in items)
            margin = total_revenue - total_cost
            
            # Credit Supplier (Cost amount)
            gl_entries.append({
                'account': supplier_account,
                'party_type': 'Supplier',
                'party': supplier,
                'debit': 0,
                'credit': total_cost,
                'against': self.customer,
                'voucher_type': 'Hybrid Invoice',
                'voucher_no': self.name,
                'posting_date': self.posting_date,
                'company': self.company
            })
            
            # Debit Expense Account (Cost)
            gl_entries.append({
                'account': items[0].expense_account,
                'debit': total_cost,
                'credit': 0,
                'against': supplier,
                'voucher_type': 'Hybrid Invoice',
                'voucher_no': self.name,
                'posting_date': self.posting_date,
                'cost_center': items[0].cost_center,
                'company': self.company
            })
            
            # Credit Income Account (Revenue)
            gl_entries.append({
                'account': items[0].income_account,
                'debit': 0,
                'credit': total_revenue,
                'against': self.customer,
                'voucher_type': 'Hybrid Invoice',
                'voucher_no': self.name,
                'posting_date': self.posting_date,
                'cost_center': items[0].cost_center,
                'company': self.company
            })
            
        else:  # Direct sales items (no supplier)
            for item in items:
                # Credit Income Account
                gl_entries.append({
                    'account': item.income_account,
                    'debit': 0,
                    'credit': item.net_amount,
                    'against': self.customer,
                    'voucher_type': 'Hybrid Invoice',
                    'voucher_no': self.name,
                    'posting_date': self.posting_date,
                    'cost_center': item.cost_center,
                    'company': self.company
                })
    
    # 3. Tax Entries
    for tax in self.taxes:
        gl_entries.append({
            'account': tax.account_head,
            'debit': 0,
            'credit': tax.tax_amount,
            'against': self.customer,
            'voucher_type': 'Hybrid Invoice',
            'voucher_no': self.name,
            'posting_date': self.posting_date,
            'cost_center': tax.cost_center,
            'company': self.company
        })
    
    # Submit GL Entries
    from erpnext.accounts.general_ledger import make_gl_entries
    make_gl_entries(gl_entries, cancel=(self.docstatus == 2))
```

### Phase 4: Client-Side Logic (JavaScript)

**File: `hybrid_invoice.js`**

```javascript
frappe.ui.form.on('Hybrid Invoice', {
    refresh: function(frm) {
        // Add custom buttons
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Accounting Ledger'), function() {
                frappe.route_options = {
                    voucher_no: frm.doc.name,
                    from_date: frm.doc.posting_date,
                    to_date: frm.doc.posting_date,
                    company: frm.doc.company
                };
                frappe.set_route("query-report", "General Ledger");
            });
            
            frm.add_custom_button(__('View Supplier Breakdown'), function() {
                show_supplier_breakdown(frm);
            });
        }
    },
    
    customer: function(frm) {
        // Fetch customer defaults
        if (frm.doc.customer) {
            frappe.call({
                method: 'erpnext.accounts.party.get_party_details',
                args: {
                    party: frm.doc.customer,
                    party_type: 'Customer',
                    company: frm.doc.company
                },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('currency', r.message.currency);
                        frm.set_value('price_list', r.message.price_list);
                    }
                }
            });
        }
    },
    
    calculate_totals: function(frm) {
        let total_qty = 0;
        let base_total = 0;
        let total_supplier_cost = 0;
        
        frm.doc.items.forEach(function(item) {
            total_qty += item.qty;
            base_total += item.amount;
            if (item.is_passthrough_item) {
                total_supplier_cost += item.supplier_total_cost;
            }
        });
        
        frm.set_value('total_qty', total_qty);
        frm.set_value('base_total', base_total);
        frm.set_value('total_supplier_cost', total_supplier_cost);
        
        calculate_taxes(frm);
    }
});

frappe.ui.form.on('Hybrid Invoice Item', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.item_code) {
            frappe.call({
                method: 'frappe.client.get',
                args: {
                    doctype: 'Item',
                    name: row.item_code
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'item_name', r.message.item_name);
                        frappe.model.set_value(cdt, cdn, 'description', r.message.description);
                        frappe.model.set_value(cdt, cdn, 'uom', r.message.stock_uom);
                        frappe.model.set_value(cdt, cdn, 'income_account', r.message.income_account);
                        frappe.model.set_value(cdt, cdn, 'expense_account', r.message.expense_account);
                    }
                }
            });
        }
    },
    
    qty: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    rate: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    supplier_cost: function(frm, cdt, cdn) {
        calculate_item_amount(frm, cdt, cdn);
    },
    
    is_passthrough_item: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.is_passthrough_item) {
            frm.script_manager.trigger('supplier', cdt, cdn);
        }
    },
    
    supplier: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.supplier && row.item_code) {
            // Fetch last purchase rate from supplier
            frappe.call({
                method: 'your_app.api.get_last_purchase_rate',
                args: {
                    item_code: row.item_code,
                    supplier: row.supplier
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'supplier_cost', r.message.rate);
                    }
                }
            });
        }
    }
});

function calculate_item_amount(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    
    // Calculate sales amount
    row.amount = row.qty * row.rate;
    row.net_amount = row.amount - (row.discount_amount || 0);
    
    // Calculate supplier cost
    if (row.is_passthrough_item) {
        row.supplier_total_cost = row.qty * (row.supplier_cost || 0);
        row.item_margin = row.net_amount - row.supplier_total_cost;
        row.item_margin_percentage = row.supplier_total_cost ? 
            (row.item_margin / row.supplier_total_cost * 100) : 0;
    } else {
        row.supplier_total_cost = 0;
        row.item_margin = row.net_amount;
    }
    
    frm.refresh_field('items');
    frm.trigger('calculate_totals');
}
```

### Phase 5: API Methods

**File: `api.py`**

```python
import frappe
from frappe import _

@frappe.whitelist()
def get_last_purchase_rate(item_code, supplier):
    """Get last purchase rate for an item from a supplier"""
    rate = frappe.db.sql("""
        SELECT rate 
        FROM `tabPurchase Invoice Item`
        WHERE item_code = %s 
        AND parent IN (
            SELECT name FROM `tabPurchase Invoice`
            WHERE supplier = %s AND docstatus = 1
        )
        ORDER BY creation DESC
        LIMIT 1
    """, (item_code, supplier))
    
    return {'rate': rate[0][0] if rate else 0}

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
            
            breakdown[item.supplier]['total_cost'] += item.supplier_total_cost
            breakdown[item.supplier]['total_revenue'] += item.net_amount
            breakdown[item.supplier]['total_margin'] += item.item_margin
            breakdown[item.supplier]['items'].append({
                'item_code': item.item_code,
                'qty': item.qty,
                'cost': item.supplier_total_cost,
                'revenue': item.net_amount,
                'margin': item.item_margin
            })
    
    return breakdown
```

---

## User Interface Requirements

### Form Layout

**Section 1: Customer Details**
- Customer (3 columns width)
- Posting Date (1.5 columns)
- Posting Time (1.5 columns)
- Company (3 columns)

**Section 2: Items Table**
- Full-width table with columns:
  - Item Code
  - Description
  - Qty
  - UOM
  - Rate (Selling)
  - Amount
  - Is Passthrough? (checkbox)
  - Supplier (conditional: show if passthrough)
  - Supplier Cost (conditional: show if passthrough)
  - Margin (read-only)
  - Margin % (read-only)

**Section 3: Taxes and Charges**
- Standard taxes child table

**Section 4: Totals**
- Display in two columns:
  - Left: Sales totals (Total, Net Total, Taxes, Grand Total)
  - Right: Cost analysis (Total Supplier Cost, Total Margin, Margin %)

### Reports to Create

1. **Hybrid Invoice Register**
   - List all hybrid invoices with totals
   - Filter by date range, customer, status
   
2. **Supplier Wise Margin Analysis**
   - Show margin by supplier across all invoices
   - Comparative analysis
   
3. **Hybrid Invoice Profitability**
   - Invoice-wise profit margins
   - Item-wise contribution

---

## Permissions

**Role Permission Manager settings:**

```
Role: Sales User
- Read: Yes
- Write: Yes
- Create: Yes
- Submit: No

Role: Sales Manager
- Read: Yes
- Write: Yes
- Create: Yes
- Submit: Yes
- Cancel: Yes
- Amend: Yes

Role: Accounts Manager
- Read: Yes
- Write: Yes (for accounting corrections)
- Submit: Yes
- Cancel: Yes
```

---

## Testing Scenarios

### Test Case 1: Pure Passthrough Transaction
- Create invoice with only passthrough items
- Verify customer is debited
- Verify each supplier is credited
- Verify margin accounts are correct

### Test Case 2: Mixed Transaction
- Include both direct sales and passthrough items
- Verify accounting entries for both types
- Verify totals calculation

### Test Case 3: Multiple Suppliers
- Create invoice with items from 3 different suppliers
- Verify separate GL entries for each supplier
- Verify supplier outstanding updates

### Test Case 4: Cancellation
- Submit and then cancel invoice
- Verify all GL entries are reversed
- Verify customer and supplier balances

### Test Case 5: Taxes
- Apply multiple taxes (CGST, SGST, IGST)
- Verify tax calculation on passthrough items
- Verify tax accounts are credited correctly

---

## Migration and Deployment

```bash
# After development
bench --site [sitename] migrate
bench --site [sitename] clear-cache
bench restart

# Set up default accounts in Company
# Create Item Tax Templates
# Configure Print Formats
```

---

## Additional Considerations

### Performance Optimization
- Add indexes on frequently queried fields
- Cache customer and supplier account lookups
- Optimize GL entry creation for bulk items

### Audit Trail
- Log all submissions and cancellations
- Track margin changes
- Monitor supplier cost updates

### Integration Points
- Hook into Purchase Invoice (optional: auto-create PI for suppliers)
- Link with Delivery Notes (for logistics)
- Integration with Payment Entry

### Future Enhancements
- Auto-email breakdown to suppliers
- Supplier portal access to view their items
- Automatic Purchase Order creation
- Commission calculation for sales team
- Multi-currency support for international suppliers

---

## Expected Deliverables

1. ✅ Fully functional Hybrid Invoice DocType
2. ✅ Client and server-side validations
3. ✅ Accurate GL entries for all scenarios
4. ✅ User-friendly form with conditional fields
5. ✅ Reports for analysis
6. ✅ API endpoints for integrations
7. ✅ Comprehensive test cases
8. ✅ Documentation and user guide
9. ✅ Permission roles configured
10. ✅ Sample data for demo

---

## Development Timeline Estimate

- **Phase 1**: DocType structure and basic fields (4-6 hours)
- **Phase 2**: Server-side logic and validations (8-10 hours)
- **Phase 3**: GL Entry implementation (6-8 hours)
- **Phase 4**: Client-side scripts and UX (6-8 hours)
- **Phase 5**: Reports and analytics (4-6 hours)
- **Testing & Refinement**: (8-10 hours)

**Total Estimate**: 36-48 hours for full implementation

---

## Support and Maintenance

- Document all custom methods
- Create wiki/knowledge base articles
- Set up error logging and monitoring
- Plan for quarterly reviews and optimizations