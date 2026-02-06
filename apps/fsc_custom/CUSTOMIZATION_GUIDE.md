# FSC Custom App - Customization Guide

## Overview
This custom app (`fsc_custom`) has been created to house all your customizations for ERPNext and other Frappe apps. This approach keeps your customizations separate from the core apps, making upgrades easier and your changes more maintainable.

## App Structure

```
fsc_custom/
├── fsc_custom/           # Main module directory
│   ├── config/          # Desk configuration
│   ├── fsc_custom/      # Module for custom DocTypes
│   ├── public/          # Static files (JS, CSS, images)
│   ├── templates/       # Custom web templates
│   ├── www/             # Web pages
│   ├── hooks.py         # App hooks and customizations
│   └── patches.txt      # Database patches
```

## Common Customization Types

### 1. Custom DocTypes
Create custom DocTypes specific to your business needs:
```bash
bench --site frappe.com new-doctype
```
Place them in: `fsc_custom/fsc_custom/doctype/`

### 2. Custom Scripts (Client-Side)
Add client scripts using `hooks.py`:

```python
# In hooks.py
app_include_js = [
    "/assets/fsc_custom/js/custom_scripts.js"
]

# For specific DocTypes
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "Item": "public/js/item.js"
}
```

### 3. Server Scripts (Python)
Override or extend methods:

```python
# In hooks.py
doc_events = {
    "Sales Invoice": {
        "validate": "fsc_custom.overrides.sales_invoice.validate",
        "on_submit": "fsc_custom.overrides.sales_invoice.on_submit"
    }
}
```

Create the override file:
```python
# fsc_custom/overrides/sales_invoice.py
import frappe

def validate(doc, method):
    # Your custom logic here
    pass

def on_submit(doc, method):
    # Your custom logic here
    pass
```

### 4. Custom Reports
Create custom reports:
```bash
bench --site frappe.com make-report
```

### 5. Custom API Endpoints
Create API endpoints in `fsc_custom/api.py`:

```python
import frappe

@frappe.whitelist()
def custom_api_method(param1, param2):
    # Your logic here
    return {"status": "success"}
```

### 6. Custom Pages
Add custom pages to the desk or web interface in the `www/` directory.

### 7. Fixtures
Export and manage fixtures (e.g., Custom Fields, Property Setters) in `hooks.py`:

```python
fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            ["name", "in", ["Item-custom_field_1", "Sales Invoice-custom_field_2"]]
        ]
    },
    {
        "doctype": "Property Setter",
        "filters": [
            ["doc_type", "in", ["Item", "Sales Invoice"]]
        ]
    }
]
```

Export fixtures:
```bash
bench --site frappe.com export-fixtures
```

## Workflow for Customizations

### Step 1: Make Your Customization
Make your changes in the UI (Custom Fields, Print Formats, etc.) or create code files.

### Step 2: Export Fixtures (for UI customizations)
```bash
bench --site frappe.com export-fixtures
```

### Step 3: Migrate Changes to Other Sites
```bash
bench --site frappe.com migrate
```

### Step 4: Version Control
```bash
cd apps/fsc_custom
git add .
git commit -m "Add: Description of your customization"
git push
```

## Best Practices

1. **Use Fixtures**: For customizations made through the UI (Custom Fields, Property Setters), use fixtures to export them.

2. **Module Organization**: Create separate modules for different functional areas:
   - `fsc_custom/sales/` - Sales customizations
   - `fsc_custom/inventory/` - Inventory customizations
   - `fsc_custom/accounts/` - Accounting customizations

3. **Documentation**: Document your customizations in code comments and maintain a CHANGELOG.

4. **Testing**: Test all customizations on a development site before deploying to production.

5. **Backup**: Always backup your site before major customizations:
   ```bash
   bench --site frappe.com backup
   ```

## Migration to Other Sites

To install this app on another site:

```bash
# Install the app
bench --site <site-name> install-app fsc_custom

# Migrate the database
bench --site <site-name> migrate
```

## Useful Commands

```bash
# Restart bench to apply changes
bench restart

# Clear cache
bench --site frappe.com clear-cache

# Rebuild assets
bench build --app fsc_custom

# Run migrations
bench --site frappe.com migrate

# Console access for testing
bench --site frappe.com console
```

## Further Reading

- [Frappe Framework Documentation](https://frappeframework.com/docs)
- [Hooks Documentation](https://frappeframework.com/docs/user/en/python-api/hooks)
- [DocType Development](https://frappeframework.com/docs/user/en/basics/doctypes)
- [Client Scripting](https://frappeframework.com/docs/user/en/desk/scripting)

## Support

For questions specific to this custom app, contact: support@fsc.com
