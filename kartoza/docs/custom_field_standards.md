# Custom Field Standardization Guide

This document outlines the standards for custom field implementation in the Kartoza module to ensure consistency, maintainability, and proper integration with ERPNext and HRMS.

## Field Naming Conventions

### Current Inconsistencies Found

Our codebase analysis revealed inconsistent custom field naming patterns:

1. **Mixed Prefixing**: Some custom fields use the `custom_` prefix while others don't:
   - **With prefix**: `custom_id_number`, `custom_hours_per_month`, `custom_payroll_payable_account`
   - **Without prefix**: `vat_number`, `amount_per_kilometer`, `calculate_annual_taxable_amount_based_on`

2. **Inconsistent References**: Some code references fields with the prefix while other code references the same fields without the prefix, leading to failures.

3. **Special Cases**: Some fields like VAT-related fields don't follow the established patterns.

## Standardization Rules

### 1. Custom Field Naming

All custom fields added to standard doctypes **should** use the `custom_` prefix:

```python
# CORRECT
custom_fields["Company"].append(dict(
    fieldname='custom_vat_number',  # Use prefix
    label='VAT Number',
    fieldtype='Data'
))

# INCORRECT
custom_fields["Company"].append(dict(
    fieldname='vat_number',  # Missing prefix
    label='VAT Number',
    fieldtype='Data'
))
```

### 2. Field Referencing

When referencing custom fields in code, always use the exact fieldname (with prefix):

```python
# CORRECT
vat_number = frappe.db.get_value("Company", self.company, "custom_vat_number")

# INCORRECT
vat_number = frappe.db.get_value("Company", self.company, "vat_number")
```

### 3. Custom Field Checks

Always check for the existence of a field with the correct name:

```python
# CORRECT
if not frappe.get_meta("Company").get_field("custom_vat_number"):
    # Add the field

# INCORRECT
if not frappe.get_meta("Company").get_field("vat_number"):
    # Add the field
```

### 4. Exceptions to the Prefix Rule

The only exceptions to the prefix rule are fields that:

1. Extend standard functionality in a way that might be incorporated into core in the future
2. Fields required by regulatory standards where the prefix would cause confusion

Document these exceptions clearly with code comments.

## Implementation Approach

### For New Fields

All new custom fields should follow the standards above without exception.

### For Existing Fields

For existing fields with inconsistent naming:

1. Create a data migration plan
2. Update field definitions in `make_custom_fields()`
3. Create database migration patches to rename fields
4. Update all references in code

### Handling Inconsistencies

The `rename_duplicate_fields()` function handles cases where both prefixed and non-prefixed versions of a field exist:

```python
def rename_duplicate_fields(custom_fields):
    """
    Handles duplicate fields by either deleting or renaming them.
    
    This ensures we don't have both a regular field and a custom_prefixed
    version of the same field.
    """
    from frappe.custom.doctype.custom_field.custom_field import rename_fieldname

    for doctype in custom_fields:
        for field in custom_fields[doctype]:
            field_name = frappe.db.get_value("Custom Field", 
                {'dt': doctype, "fieldname": field["fieldname"]})
            custom_field_name = frappe.db.get_value("Custom Field", 
                {'dt': doctype, "fieldname": "custom_" + field["fieldname"]})
            
            if field_name and custom_field_name:
                frappe.db.delete("Custom Field", custom_field_name)
            elif not field_name and custom_field_name:
                rename_fieldname(custom_field_name, field["fieldname"])
```

## Examples of Standardized Field Definitions

```python
# HR Settings
if not frappe.get_meta("HR Settings").get_field("custom_amount_per_kilometer"):
    custom_fields["HR Settings"].append(dict(
        fieldname='custom_amount_per_kilometer',
        label='Amount Per Kilometer',
        fieldtype='Currency',
        insert_after='emp_created_by'
    ))

# Company
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

## Migration Plan for the Kartoza Module

### 1. Field Audit

We've identified these inconsistent fields that need standardization:

| Current Field Name | Recommended Name | Doctype | References |
|-------------------|------------------|---------|------------|
| vat_number | custom_vat_number | Company | VAT201 Return |
| amount_per_kilometer | custom_amount_per_kilometer | HR Settings | Expense Claim |
| calculate_annual_taxable_amount_based_on | custom_calculate_annual_taxable_amount_based_on | Payroll Settings | Salary Slip |

### 2. Implementation Schedule

1. **Create patches** to rename fields in the database
2. **Update install.py** with the standardized field names
3. **Update references** in all Python and JavaScript files
4. **Regression testing** of all affected functionality

### 3. Code Standards Enforcement

- Add the custom field standards to code review checklists
- Create automated checks for prefixing patterns
- Document exceptions with clear comments

## Benefits of Standardization

1. **Improved Code Readability**: Clearly identifies custom fields vs standard fields
2. **Reduced Bugs**: Prevents inconsistent field access issues
3. **Better Maintainability**: Makes upgrading to new versions of ERPNext easier
4. **Simplified Development**: Clear patterns for new team members to follow

## References

- [Frappe Framework Custom Fields Documentation](https://frappeframework.com/docs/user/en/customize-erpnext/custom-field)
- [ERPNext Development Conventions](https://github.com/frappe/frappe/wiki/Developer-Conventions)
