# Employment Tax Incentive (ETI) Guide

This guide explains the South African Employment Tax Incentive (ETI) implementation in the Kartoza module for ERPNext/HRMS.

## Overview

The Employment Tax Incentive (ETI) is a South African tax incentive aimed at encouraging employers to hire young and less experienced job seekers. It reduces the cost of hiring young people by allowing employers to claim a portion of the PAYE tax for qualifying employees.

## ETI Eligibility Criteria

For an employee to qualify for ETI, they must meet the following criteria:

1. **Age**: Between 18-29 years old on the last day of the month
2. **Remuneration**: Monthly remuneration within qualifying thresholds
3. **Employment Period**: First 24 months of employment only
4. **Hiring Date**: Employed on or after October 1, 2013
5. **Documentation**: Valid South African ID or Asylum Seeker permit
6. **Minimum Wage**: Meet applicable minimum wage requirements

## ETI Calculation in Kartoza

The ETI calculation in the Kartoza module is implemented through several components:

### 1. ETI Slabs Configuration

ETI calculations depend on salary ranges with different formulas:

| Monthly Remuneration | First 12 Months | Second 12 Months |
|----------------------|-----------------|------------------|
| R0 - R2,000          | 50% of monthly remuneration | 25% of monthly remuneration |
| R2,001 - R4,500      | R1,000 | R500 |
| R4,501 - R6,500      | R1,000 - (0.5 × (Monthly Remuneration - R4,500)) | R500 - (0.25 × (Monthly Remuneration - R4,500)) |
| Above R6,500         | R0 | R0 |

These formulas are configured in the ETI Slab doctype.

### 2. Implementation in Salary Slip

The `get_eti_deduction` function in `salary_slip.py` implements the ETI calculation:

```python
def get_eti_deduction(self):
    """
    Calculate Employment Tax Incentive (ETI) deduction according to South African tax law.
    
    Eligibility criteria:
    1. Employee must be between 18-29 years old
    2. Employee's remuneration must be within qualifying thresholds
    3. ETI can only be claimed for the first 24 months of employment
    
    Calculation factors:
    - Monthly remuneration amount
    - Whether in first or second 12-month period of employment
    - Hours worked in the month (proportional calculation)
    - Any carry-forward amounts from previous months
    """
    # Function implementation...
```

### 3. ETI Log Tracking

The system maintains an `Employee ETI Log` to:
- Track ETI claims for each employee
- Calculate the 24-month eligibility period
- Manage carry-forward amounts

## Implementation Details

### Setup Steps

1. **Configure ETI Slabs**:
   - Navigate to ETI Slab list and create a new entry
   - Set valid date range, age limits, and standard work hours
   - Configure formulas for each remuneration bracket

2. **ETI-Eligible Components**:
   - Mark salary components eligible for ETI
   - Configure reduction percentages if applicable
   - Set "Allow for ETI" flag on qualifying components

3. **Employee Configuration**:
   - Ensure employee birth dates are correctly recorded
   - Set employee working hours per month
   - Verify South African ID numbers are valid

### Monthly ETI Process

1. **Calculation during Payroll**:
   - ETI is automatically calculated during salary slip generation
   - System checks age and employment duration eligibility
   - Monthly remuneration is calculated from ETI-eligible components
   - Appropriate formula is applied based on employment period
   - Amount is pro-rated based on actual hours worked

2. **ETI Tracking**:
   - ETI Log entries are created for each qualifying employee
   - Carries forward unused ETI amounts to subsequent months
   - Tracks 24-month eligibility period

3. **Reporting**:
   - ETI amounts are included in EMP201 monthly submissions
   - Accumulated in EMP501 bi-annual reconciliations

## Validation and Error Handling

The module implements several validation checks:

1. **Employee Age Validation**:
   - Validates birth date to ensure employee is 18-29 years old
   - Calculates age as of the last day of the tax period

2. **Hours Check**:
   - Ensures employee hours per month are configured
   - Pro-rates ETI amount based on actual hours worked
   - Caps at standard hours defined in ETI Slab

3. **Employment Duration**:
   - Tracks previous ETI claims to determine 12/24 month periods
   - Prevents claims beyond 24-month eligibility window

## Best Practices

1. **Regular Updates**:
   - Keep ETI Slabs updated with latest SARS thresholds
   - ETI parameters are typically updated annually in the budget speech

2. **Validation**:
   - Regularly audit ETI claims against eligibility criteria
   - Ensure all required employee data is captured

3. **Documentation**:
   - Maintain records of all ETI claims for SARS audits
   - Document carry-forward amounts in case of system issues

## Troubleshooting

### Common Issues

1. **No ETI Calculated**:
   - Verify employee age falls within eligible range
   - Check employee has valid South African ID
   - Ensure hours per month are configured
   - Verify remuneration falls within qualifying thresholds

2. **Incorrect ETI Amount**:
   - Check ETI Slab configuration matches current regulations
   - Verify ETI-eligible components are correctly marked
   - Ensure pro-ration calculation is correct

3. **ETI Tracking Issues**:
   - Check Employee ETI Log entries for completeness
   - Verify carry-forward amounts are accurately tracked

## Technical Reference

The ETI implementation uses several custom doctypes:

1. **ETI Slab**: Configures calculation formulas and parameters
2. **ETI Slab Details**: Defines calculation formulas by remuneration bracket
3. **Employee ETI Log**: Tracks ETI claims and carry-forward amounts

The main calculation occurs in `get_eti_deduction()` in `salary_slip.py` with supporting data from employee records and ETI configuration.
