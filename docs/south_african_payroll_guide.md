# South African Payroll Guide

## Overview

The Kartoza module extends the standard HRMS payroll functionality with South Africa-specific features to handle tax compliance, Employment Tax Incentive (ETI), and other mandatory requirements for South African businesses. This document provides detailed information on how the module implements South African payroll requirements.

## Key Features

1. **Tax Calculation**
   - Progressive tax rates based on SARS tax tables
   - Age-based tax rebates (primary, secondary for 65+, tertiary for 75+)
   - Medical aid tax credits based on number of dependents

2. **Employment Tax Incentive (ETI)**
   - Automatic calculation of ETI for eligible employees
   - Age verification (18-29 years)
   - Monthly remuneration thresholds
   - First/second 12-month period differentiation
   - Hours-worked proration
   - Carry-forward of unused ETI amounts

3. **Retirement Annuity**
   - Tax-deductible retirement contributions
   - Enforcement of maximum allowable deduction limits

4. **South African Working Days Calculation**
   - Custom working days calculation methodology
   - Handling of weekends and public holidays
   - Support for different payroll frequencies

5. **Annual Bonus Handling**
   - Proper tax treatment of annual bonuses
   - Integration with bonus provisioning

## Technical Implementation

### CustomSalarySlip Class

The module extends the standard `SalarySlip` class to create a `CustomSalarySlip` class that implements South African payroll requirements:

```python
class CustomSalarySlip(SalarySlip):
    """
    Extension of the standard SalarySlip class to implement South African payroll requirements.
    
    This class handles South Africa-specific calculations including:
    - Tax calculation with rebates and medical aid credits
    - Employment Tax Incentive (ETI) processing
    - South African working days calculation
    - Retirement annuity deductions
    - Annual bonus handling
    """
```

The custom class overrides key methods to implement South African payroll requirements:
- `calculate_net_pay()` - Adds ETI and company contributions
- `get_taxable_earnings()` - Handles retirement annuity deductions
- `validate()` - Adds South African-specific validations
- `calculate_variable_tax()` - Applies tax rebates and medical credits

### Employment Tax Incentive (ETI)

The ETI is a South African tax incentive aimed at encouraging employers to hire young job seekers. The module implements ETI calculation according to SARS rules:

1. **Employee Eligibility**:
   - Age between 18-29 years
   - Employed on or after October 1, 2013
   - Remuneration within qualifying thresholds
   - Limited to first 24 months of employment

2. **Calculation Logic**:
   - The amount is calculated based on monthly remuneration
   - Different formulas for first vs. second 12 months of employment
   - Prorated based on actual hours worked vs. standard hours
   - Carry-forward mechanism for unused ETI amounts

3. **ETI Tracking**:
   - `Employee ETI Log` doctype stores historical ETI claims
   - Monitors the 24-month eligibility period
   - Tracks carry-forward amounts

### Tax Rebates and Medical Credits

South African tax law provides for:

1. **Tax Rebates**:
   - Primary rebate (all taxpayers)
   - Secondary rebate (65 years and older)
   - Tertiary rebate (75 years and older)

2. **Medical Tax Credits**:
   - Fixed monthly amount per taxpayer
   - Additional credits for first dependent
   - Additional credits for subsequent dependents

The module implements both of these through dedicated functions that calculate the appropriate amounts based on employee age and dependent count.

### Retirement Annuity

The module handles retirement annuity contributions as tax deductions:

1. **Maximum Deduction**:
   - Enforces maximum percentage of taxable income
   - Enforces absolute maximum amount limits
   - Calculates monthly deduction amounts from annual limits

2. **Tax Impact**:
   - Reduces taxable income accordingly
   - Properly reports deductions on tax certificates

## Configuration

### Required DocTypes

To use South African payroll features, the following DocTypes need to be configured:

1. **Income Tax Slabs**
   - Create tax slabs with progressive tax rates
   - Update annually with new SARS tables

2. **Tax Rebates Rate**
   - Set primary, secondary, and tertiary rebate amounts
   - Link to appropriate Payroll Period

3. **Medical Tax Credit Rate**
   - Set credit amounts for different dependent counts
   - Link to appropriate Payroll Period

4. **ETI Slab**
   - Define ETI calculation formulas for different remuneration levels
   - Set age limits and standard hours per month
   - Create new slabs when rates change

5. **Employee Private Benefit**
   - Record employee's retirement annuity contributions
   - Record medical aid scheme details and dependents

### Employee Setup for South African Payroll

For proper South African payroll processing, ensure these fields are set:

1. **Standard Employee Fields**:
   - Date of Birth (critical for tax rebate and ETI calculations)
   - Date of Joining (critical for ETI eligibility period)
   - Tax ID Number

2. **Custom Fields**:
   - `custom_hours_per_month` - Standard working hours (for ETI proration)
   - `custom_id_number` - South African ID number
   - `custom_employee_type` - Classification for reporting

### Company Configuration

Set up the following company-specific information:

1. In Company DocType:
   - COIDA registration number
   - UIF registration number
   - PAYE reference number

2. In Payroll Settings:
   - South African settings section with appropriate salary components for:
     - PAYE
     - UIF (Employee)
     - UIF (Employer)
     - SDL
     - COIDA

## Best Practices

1. **Regular Updates**
   - Keep tax tables and rates updated annually
   - Update ETI slabs when legislation changes

2. **Validation**
   - Ensure all employees have complete date of birth information
   - Validate tax calculations periodically against manual calculations

3. **Audit Trail**
   - Use the ETI logs to maintain records for SARS audits
   - Generate and store IRP5 certificates properly

4. **Testing**
   - Use the provided test suite to verify calculations
   - Run tests after any system updates that could affect payroll

## Troubleshooting

### Common Issues

1. **Tax Calculation Errors**
   - Check tax slab configuration matches current SARS tables
   - Verify employee age is calculated correctly
   - Check the medical aid tax credits are configured correctly

2. **ETI Calculation Issues**
   - Verify employee age is within eligible range (18-29)
   - Check that employee hasn't exceeded 24 months of ETI claims
   - Ensure custom_hours_per_month is set correctly

3. **Retirement Annuity Deduction Issues**
   - Verify maximum percentage and amount limits are set correctly
   - Check that taxable earnings are sufficient for the deduction

### Logging and Error Handling

The module includes enhanced error handling with:
- Comprehensive error logging to the error log
- User-friendly error messages
- Warning messages for potential configuration issues
- Detailed logging of calculation results for audit purposes

## System Requirements

- Frappe/ERPNext version: v14 or higher
- HRMS app installed and configured
- South African locale settings

## Testing South African Payroll

The Kartoza module includes a comprehensive test suite for verifying South African payroll calculations:

```
bench --site [site-name] run-tests --app kartoza --test test_south_african_payroll
```

The test suite verifies:
- Age calculation accuracy
- Tax rebate calculations for different age groups
- ETI eligibility and calculation
- End-to-end salary slip processing with South African rules

## Regulatory Compliance

This module aims to comply with:
- Income Tax Act of South Africa
- Employment Tax Incentive Act
- Basic Conditions of Employment Act
- UIF and SDL requirements

Regular updates are required to maintain compliance with changing legislation.
