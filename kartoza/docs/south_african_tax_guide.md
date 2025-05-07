# South African Tax Guide for Kartoza Module

This document provides comprehensive guidance on South African tax features implemented in the Kartoza module for Frappe HRMS/ERPNext.

## Overview

The Kartoza module extends ERPNext and HRMS with South African tax compliance features, including:
- Employment Tax Incentive (ETI)
- Pay As You Earn (PAYE) tax
- Unemployment Insurance Fund (UIF)
- Skills Development Levy (SDL)
- Compensation for Occupational Injuries and Diseases Act (COIDA)
- Value-Added Tax (VAT201)
- EMP201/EMP501 tax forms

## ID Number Validation

South African ID numbers follow a specific format and include checksums to validate their authenticity:

Format: `YYMMDD SSSS CAZ`
- `YYMMDD`: Date of birth
- `SSSS`: Gender (Females: 0000-4999, Males: 5000-9999)
- `C`: Citizenship (0: SA, 1: Permanent resident)
- `A`: Usually 8 or 9 (historical)
- `Z`: Checksum digit

The module includes validation using the Luhn algorithm to verify the checksum digit.

## Tax Rebates

Tax rebates are reductions in the amount of tax that must be paid, based on:
- Primary rebate: Available to all taxpayers
- Secondary rebate: For taxpayers aged 65 and over
- Tertiary rebate: For taxpayers aged 75 and over

The module calculates these based on the employee's age and the configured rebate amounts for the current tax year.

## Medical Tax Credits

Medical tax credits reduce tax liability based on:
- Number of dependents covered on medical aid
- Fixed monthly amounts determined by SARS
- Adjusted annually in the national budget

The module allows configuration of:
- Base credit amount for main member
- Additional credit for first dependent
- Additional credit for each subsequent dependent

## Employment Tax Incentive (ETI)

The ETI encourages employers to hire young job seekers by allowing tax reductions for eligible employees:

### Eligibility Criteria
- Employee must be 18-29 years old
- Monthly remuneration must be within qualifying thresholds
- First 24 months of employment only

### ETI Calculation Factors
- Monthly remuneration amount
- Whether in first or second 12-month period of employment
- Hours worked in the month (proportional calculation)
- Any carry-forward amounts from previous months

## Retirement Annuity and Pension Deductions

The module supports:
- Calculating maximum allowable retirement annuity deductions
- Processing pension fund contributions
- Annual limits on tax-deductible contributions

## COIDA (Compensation for Occupational Injuries and Diseases Act)

COIDA provides compensation for workplace injuries:
- Annual returns required by the Compensation Fund
- Industry-specific rates based on risk classification
- Integration with payroll for accurate reporting

## Configuration Steps

1. **Employee Setup**
   - Configure South African ID numbers 
   - Set up Employee Types
   - Configure working hours for ETI calculations

2. **Salary Components**
   - Set up PAYE, UIF, SDL components
   - Configure ETI-eligible components
   - Set up COIDA components

3. **Tax Configuration**
   - Configure tax rebate rates
   - Set up medical tax credit rates
   - Configure ETI calculation formulas

4. **VAT Settings**
   - Set up VAT vendor type
   - Configure standard VAT rate (currently 15%)
   - Set filing frequency

5. **Reporting Period**
   - Configure monthly, bi-monthly or annual return periods
   - Set up tax year dates

## Integration with Government Systems

The module provides foundational data for submissions to:
- SARS e-Filing for tax returns
- UIF submissions
- Compensation Fund for COIDA
- Department of Labour for compliance reporting

## Annual Updates

Tax parameters require annual updates based on:
- Annual budget speech changes
- SARS tax tables
- Rebate and credit adjustments
- ETI qualification thresholds

Ensure the system is updated at the beginning of each tax year (typically March 1st) with the latest values from SARS.
