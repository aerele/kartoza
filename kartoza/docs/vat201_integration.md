# VAT201 Integration Guide

This guide explains South African Value-Added Tax (VAT) functionality in the Kartoza module, including setup, configuration, and troubleshooting common issues.

## Overview

The VAT201 return is a declaration submitted to the South African Revenue Service (SARS) that details a vendor's VAT transactions for a specific tax period.

## Configuration Requirements

### Company Setup

Before using VAT functionality, ensure your company is properly configured:

1. **VAT Number**: Each company must have a valid VAT registration number
   - Navigate to **Company** > your company
   - Ensure the **VAT Number** field is populated
   - VAT numbers must be 10 digits and start with '4'

2. **VAT Vendor Type**: Set your VAT vendor type
   - Options include Category A-F vendors based on filing frequency

### South African VAT Settings

Configure global VAT settings:

1. Navigate to **South African VAT Settings**
2. Configure:
   - Standard VAT rate (currently 15%)
   - VAT registration number (as backup if not set in Company)
   - Filing frequency
   - Output and Input VAT accounts
   - E-Filing credentials (optional)

## Troubleshooting

### Field Not Permitted in Query: vat_number

This error occurs when the system attempts to access the `vat_number` field but cannot find it in the permissions or field list.

**Solutions**:

1. **Ensure the VAT Number field exists**:
   - The custom field `custom_vat_number` should be added to the Company doctype
   - This is handled in the `make_custom_fields` function in install.py
   - If missing, run `bench execute kartoza.install.make_custom_fields`

2. **Check permissions**:
   - The user should have permissions to read the Company doctype
   - Verify field permissions if using field-level permissions

3. **Validate field syntax**:
   - Ensure calls to access the field use the correct fieldname: `custom_vat_number`
   - Some legacy code might still use `vat_number` inconsistently

## VAT201 Return Process

1. **Create New VAT201 Return**
   - Navigate to VAT201 Return list and click "New"
   - Select company and tax period
   - The system will automatically fetch the VAT number from the company

2. **Enter Supply Details**
   - Standard-rated supplies
   - Zero-rated supplies
   - Exempt supplies

3. **Input Tax Credits**
   - Capital goods
   - Other goods and services
   - Change in use
   - Bad debts

4. **Output Tax**
   - The system will automatically calculate output tax based on standard rate
   - Add other output tax items as needed

5. **Submission to SARS**
   - Generate submission reference
   - Use "Submit to SARS" button if e-Filing integration is configured
   - Otherwise, use as reference for manual submission

## VAT Reports

The module includes VAT analysis reporting to:
- Track input and output VAT by period
- Analyze VAT by vendor
- View transaction details supporting VAT returns

## Technical Implementation Notes

### VAT Number Field Handling

The VAT number field is added to the Company doctype during installation:

```python
if not frappe.get_meta("Company").get_field("custom_vat_number"):
    custom_fields["Company"].append(dict(
        fieldname='custom_vat_number',
        label='VAT Number',
        fieldtype='Data',
        insert_after='tax_id',
        description="South African VAT Number",
        length=10
    ))
```

### VAT201 Return Document

The `VAT201Return` doctype includes methods to:
1. Validate submission dates
2. Set the VAT registration number from company
3. Calculate totals based on configured VAT rates
4. Submit to SARS via API (if configured)

### VAT Number Validation

South African VAT numbers should be validated:
- Must be 10 digits
- Must start with '4'
- Should have valid check digit

## Integration with Accounting

VAT transactions are processed through:
1. **Sales Invoices**: For collecting output VAT
2. **Purchase Invoices**: For recording input VAT
3. **Journal Entries**: For manual VAT adjustments

The system automatically categorizes and summarizes these transactions for VAT reporting.
