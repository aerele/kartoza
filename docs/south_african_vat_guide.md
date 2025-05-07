# South African VAT Implementation Guide

## Overview

This document provides a comprehensive guide on how South African VAT functionality is implemented in the Kartoza module, including integration with core ERPNext doctypes, common issues, and troubleshooting.

## Table of Contents

1. [VAT Fields in Core DocTypes](#vat-fields-in-core-doctypes)
2. [South African VAT Settings](#south-african-vat-settings)
3. [VAT201 Returns](#vat201-returns)
4. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
5. [Developer Guidelines](#developer-guidelines)

## VAT Fields in Core DocTypes

The Kartoza module adds custom VAT fields to several core ERPNext doctypes to support South African requirements.

### Customer DocType

The following fields are added to the Customer doctype:

| Field Name | Field Type | Purpose |
|------------|------------|---------|
| vat_number | Data | Stores the customer's VAT registration number |
| is_vat_registered | Check | Indicates if the customer is registered for VAT |
| vat_vendor_type | Link | Links to VAT Vendor Type DocType |

### Supplier DocType

The following fields are added to the Supplier doctype:

| Field Name | Field Type | Purpose |
|------------|------------|---------|
| vat_number | Data | Stores the supplier's VAT registration number |
| is_vat_registered | Check | Indicates if the supplier is registered for VAT |
| vat_vendor_type | Link | Links to VAT Vendor Type DocType |

### Company DocType

The following fields are added to the Company doctype:

| Field Name | Field Type | Purpose |
|------------|------------|---------|
| vat_number | Data | Stores the company's VAT registration number |
| vat_registration_date | Date | Date of VAT registration |
| vat_filing_frequency | Select | Monthly or Bi-monthly VAT filing |

## South African VAT Settings

The South African VAT Settings doctype provides centralized configuration for VAT-related functionality:

- VAT registration details
- VAT rates configuration
- Default VAT accounts
- VAT filing periods
- Integration with SARS e-Filing

## VAT201 Returns

The VAT201 Return doctype provides functionality for:

- Generating VAT201 returns for submission to SARS
- Calculating VAT payable/refundable
- Tracking VAT return submission status
- Integration with SARS e-Filing (where supported)

## Common Issues and Troubleshooting

### "Field not permitted in query: vat_number" Error

This error occurs when trying to query the `vat_number` field which has been added as a custom field but not properly whitelisted for queries.

**Cause:**
When custom fields are added to DocTypes, they need to be explicitly whitelisted in the `get_field_map()` function in the doctype's controller. This is especially true when these fields are used in client-side scripting or API calls.

**Solution:**

1. Add the custom fields to the whitelist in the appropriate controller class by modifying the `get_field_map()` method:

```python
# In customer.py controller
def get_field_map(self):
    from frappe.model.document import get_field_map
    field_map = get_field_map("Customer")
    
    # Add the custom VAT field to the field map
    field_map.update({
        "vat_number": "vat_number"
    })
    
    return field_map
```

2. Alternatively, you can override the controller via a custom app:

```python
# In the hooks.py of your kartoza app:
doctype_js = {
    "Customer": "public/js/customer.js"
}

# Then in the js file, use frappe.db.get_value with explicit fieldname
frappe.db.get_value("Customer", {"name": customer_name}, "name,vat_number", function(r) {
    // Use the results
});
```

3. For immediate fixes without code changes, you can use workarounds:

```javascript
// Instead of directly querying the vat_number field
// Get the entire document
frappe.model.with_doc("Customer", customer_name, function() {
    var customer = frappe.get_doc("Customer", customer_name);
    var vat_number = customer.vat_number;
    // Use the vat_number value
});
```

### Other Common Issues

1. **VAT calculations incorrect**
   - Check the VAT rates configured in South African VAT Settings
   - Verify the Item Tax Templates applied to items
   - Review the Tax Account configuration in Chart of Accounts

2. **VAT201 report shows incorrect values**
   - Verify correct posting periods are selected
   - Check tax accounts are correctly mapped in VAT201 doctype
   - Ensure all sales and purchase invoices are properly submitted

3. **Integration with SARS e-Filing fails**
   - Verify correct SARS login credentials in settings
   - Check network connectivity to SARS services
   - Review the format of submission data against SARS requirements

## Developer Guidelines

When extending the VAT functionality, please follow these guidelines:

1. **Adding New Custom Fields**
   - Use hooks.py to declare custom fields
   - Update related controllers to whitelist fields for queries
   - Add appropriate validations for South African VAT number format

2. **Modifying VAT Calculation Logic**
   - Follow the existing patterns in the VAT201 doctype
   - Add comprehensive test cases
   - Document any changes in this guide

3. **Extending SARS e-Filing Integration**
   - Use the existing integration framework
   - Handle error responses appropriately
   - Log all communication with SARS for audit purposes

4. **Security Considerations**
   - Treat VAT numbers as sensitive information
   - Implement appropriate access controls
   - Avoid storing SARS credentials in plain text

By following these guidelines, we can maintain a robust and compliant South African VAT implementation.

---

## Appendix: Implementation Details

### Custom Field Implementation

Custom fields are added through the `custom_field.json` files in the Kartoza module:

```json
{
  "dt": "Customer",
  "fieldname": "vat_number",
  "fieldtype": "Data",
  "label": "VAT Number",
  "insert_after": "tax_id",
  "description": "South African VAT Registration Number"
}
```

### VAT Number Validation

The VAT number validation is implemented in the custom validations through `hooks.py`:

```python
# hooks.py
doc_events = {
    "Customer": {
        "validate": "kartoza.kartoza.utils.validate_south_african_vat_number"
    },
    "Supplier": {
        "validate": "kartoza.kartoza.utils.validate_south_african_vat_number"
    }
}
