# Kartoza: South African Localization for ERPNext

## Comprehensive Technical & Functional Documentation

This comprehensive documentation provides detailed information about the Kartoza module, which delivers South African localization features for ERPNext and HRMS. This documentation covers the technical architecture, core functionality, integration points, compliance implementations, and developer guidance.

## Table of Contents

1. [Introduction](#introduction)
2. [Technical Architecture](#technical-architecture)
3. [South African Compliance Framework](#south-african-compliance-framework)
   - [VAT (Value Added Tax)](#vat-value-added-tax)
   - [Payroll & Tax Compliance](#payroll--tax-compliance)
   - [ETI (Employment Tax Incentive)](#eti-employment-tax-incentive)
   - [COIDA (Compensation for Occupational Injuries and Diseases)](#coida-compensation-for-occupational-injuries-and-diseases)
   - [Workplace Injuries Management](#workplace-injuries-management)
4. [Integration with ERPNext/HRMS](#integration-with-erpnexthems)
5. [Custom Fields & Customizations](#custom-fields--customizations)
6. [Data Flow & Processing](#data-flow--processing)
7. [Developer Guide](#developer-guide)
8. [Compliance Updates & Maintenance](#compliance-updates--maintenance)
9. [Troubleshooting](#troubleshooting)
10. [References & Supporting Documents](#references--supporting-documents)

---

## Introduction

Kartoza is a comprehensive South African localization module for ERPNext and HRMS. It extends the core functionality to meet statutory requirements specific to South African businesses, including tax regulations, payroll localization, and financial reporting requirements.

### Purpose

The primary purpose of Kartoza is to ensure that ERPNext installations for South African businesses are fully compliant with local regulations, particularly:

- South African Revenue Service (SARS) requirements
- Department of Labour regulations
- Compensation Fund requirements
- Banking and financial reporting standards

### Key Features

- VAT (Value Added Tax) management and reporting
- PAYE, UIF, and SDL calculation and submissions
- Employment Tax Incentive (ETI) processing
- COIDA annual returns and workplace injury management
- IRP5/IT3(a) tax certificates
- EMP201 and EMP501 submissions
- South African ID validation and processing
- Bank-specific payment file formats
- Regulatory compliance reporting

---

## Technical Architecture

### Module Structure

The Kartoza module follows the standard Frappe/ERPNext application structure:

```
kartoza/
├── kartoza/               # Main app directory
│   ├── __init__.py
│   ├── hooks.py           # App hooks for ERPNext integration
│   ├── patches.txt        # Database migration patches
│   ├── config/            # Module configuration 
│   ├── custom_js/         # Client-side JavaScript customizations
│   ├── custom_py/         # Server-side Python customizations
│   ├── docs/              # Documentation files
│   ├── fixtures/          # Data fixtures
│   ├── kartoza/           # Module-specific code
│   │   ├── doctype/       # Document types
│   │   ├── report/        # Reports
│   │   ├── custom/        # Custom fields for existing doctypes
│   ├── patches/           # Python patch files
│   ├── templates/         # Template files
│   └── tests/             # Test files
└── docs/                  # External documentation
```

### Integration Points

Kartoza integrates with ERPNext/HRMS through several key mechanisms:

1. **Custom Fields**: Adding South African-specific fields to core doctypes (e.g., VAT numbers to Company and Customer)
2. **Server-side Hooks**: Extending core functionality through Python hooks
3. **Client-side Scripts**: Enhancing UI with custom JavaScript
4. **Custom DocTypes**: Creating South Africa-specific document types
5. **Custom Reports**: Providing statutory and analytical reports

### Core Dependencies

- Frappe Framework
- ERPNext Core
- HRMS Module (for payroll functionality)

---

## South African Compliance Framework

### VAT (Value Added Tax)

VAT in South Africa is regulated by SARS and operates at a standard rate of 15% (as of 2025) with specific types of supplies being zero-rated or exempt.

#### VAT Implementation in Kartoza

The VAT system in Kartoza is implemented through several key components:

1. **Custom Fields**

   Custom fields are added to existing doctypes to store VAT-related information:
   
   | DocType | Field | Purpose |
   |---------|-------|---------|
   | Company | vat_number | Stores company's VAT registration number |
   | Company | vat_registration_date | Date of VAT registration |
   | Company | vat_filing_frequency | Monthly or Bi-monthly filing |
   | Customer | vat_number | Customer's VAT registration number |
   | Customer | is_vat_registered | Boolean flag for VAT status |
   | Customer | vat_vendor_type | Links to VAT Vendor Type |
   | Supplier | vat_number | Supplier's VAT registration number |
   | Supplier | is_vat_registered | Boolean flag for VAT status |
   | Supplier | vat_vendor_type | Links to VAT Vendor Type |

2. **DocTypes**

   Kartoza includes several VAT-specific doctypes:
   
   - **South African VAT Settings**: Central configuration for VAT-related functionality
   - **South African VAT Rate**: Configurable VAT rates (standard 15%, zero-rated, exempt)
   - **VAT Vendor Type**: Classification of VAT vendors
   - **VAT201 Return**: VAT submissions to SARS

3. **Technical Implementation**

   The VAT201 return functionality is implemented in `vat201_return.py` and `vat201_return.js`. Key functions include:
   
   ```python
   # Server-side VAT calculations (Python)
   def calculate_totals(self):
       """Calculate all totals"""
       # Calculate total supplies
       self.total_supplies = flt(self.standard_rated_supplies) + 
                             flt(self.zero_rated_supplies) + 
                             flt(self.exempt_supplies)
       
       # Calculate standard rated output tax
       vat_settings = frappe.get_doc("South African VAT Settings")
       standard_rate = flt(vat_settings.standard_vat_rate) / 100
       self.standard_rated_output = flt(self.standard_rated_supplies) * standard_rate
       
       # Calculate total output tax
       self.total_output_tax = (
           flt(self.standard_rated_output) + 
           flt(self.change_in_use_output) + 
           flt(self.bad_debts_output) + 
           flt(self.other_output)
       )
       
       # Calculate total input tax
       self.total_input_tax = (
           flt(self.capital_goods_input) + 
           flt(self.other_goods_services_input) + 
           flt(self.change_in_use_input) + 
           flt(self.bad_debts_input)
       )
       
       # Calculate VAT payable or refundable
       if self.total_output_tax > self.total_input_tax:
           self.vat_payable = self.total_output_tax - self.total_input_tax
           self.vat_refundable = 0
       else:
           self.vat_refundable = self.total_input_tax - self.total_output_tax
           self.vat_payable = 0
   ```
   
   The client-side functionality in `vat201_return.js` provides:
   - UI for VAT return preparation
   - VAT calculation triggers
   - Dashboard indicators for VAT status
   - SARS submission integration

4. **VAT201 Submission Workflow**

   The VAT submission workflow follows these steps:
   1. User creates a new VAT201 Return for a specific period
   2. System collects transaction data for the period
   3. Output VAT (sales) and input VAT (purchases) are calculated
   4. User reviews and submits the return
   5. Return can be exported/submitted to SARS

5. **VAT Reports**

   The module includes VAT analysis reports that provide detailed breakdowns of:
   - VAT by transaction type
   - VAT by rate type
   - VAT reconciliation

#### VAT Compliance with SARS Requirements

The implementation adheres to SARS requirements by:

1. Following the prescribed VAT201 form structure
2. Supporting the correct VAT rates
3. Handling special cases like bad debts, change in use
4. Providing audit trails for VAT transactions
5. Supporting e-Filing integration

### Payroll & Tax Compliance

South African payroll includes several statutory components:

- PAYE (Pay As You Earn) - Income tax
- UIF (Unemployment Insurance Fund)
- SDL (Skills Development Levy)
- COIDA (Compensation for Occupational Injuries and Diseases Act) contributions
- ETI (Employment Tax Incentive)

#### EMP201 & EMP501 Implementation

EMP201 (monthly) and EMP501 (bi-annual) submissions are key compliance requirements for employers in South Africa.

1. **EMP201 Submission**

   The EMP201 submission process is implemented in the `emp201_submission.py` and related files, handling monthly returns to SARS for PAYE, UIF, SDL, and ETI.

   Key functionality:
   ```python
   def calculate_totals(self):
       """Calculate totals for EMP201 submission"""
       payroll_entries = self.get_payroll_entries()
       
       # Initialize totals
       self.paye_collected = 0
       self.sdl_collected = 0
       self.uif_collected = 0
       self.eti_calculated = 0
       
       # Calculate totals from payroll entries
       for entry in payroll_entries:
           self.paye_collected += entry.paye_amount
           self.sdl_collected += entry.sdl_amount
           self.uif_collected += entry.uif_amount
           self.eti_calculated += entry.eti_amount
       
       # Calculate payable amounts
       self.paye_payable = self.paye_collected
       self.sdl_payable = self.sdl_collected
       self.uif_payable = self.uif_collected
       self.eti_utilized = min(self.eti_calculated, self.paye_payable)
       
       # Calculate total payable
       self.total_payable = (
           self.paye_payable + 
           self.sdl_payable + 
           self.uif_payable - 
           self.eti_utilized
       )
   ```

2. **EMP501 Reconciliation**

   The EMP501 reconciliation (`emp501_reconciliation.py`) handles bi-annual employer reconciliation declarations to SARS.
   
   The implementation provides:
   - Collection of EMP201 submissions for the period
   - Collection of IRP5/IT3(a) certificates issued
   - Reconciliation of values between submissions and certificates
   - Identification of discrepancies
   - SARS e-Filing integration

   Key functions:
   ```python
   def calculate_totals(self):
       self.total_paye = 0
       self.total_sdl = 0
       self.total_uif = 0
       self.total_eti = 0
       
       # Calculate totals from EMP201 submissions
       if self.emp201_submissions:
           for submission in self.emp201_submissions:
               if submission.emp201_submission:
                   emp201 = frappe.get_doc("EMP201 Submission", submission.emp201_submission)
                   self.total_paye += flt(emp201.net_paye_payable)
                   self.total_sdl += flt(emp201.sdl_payable)
                   self.total_uif += flt(emp201.uif_payable)
                   self.total_eti += flt(emp201.eti_utilized_current_month)
       
       # Calculate total tax payable
       self.total_tax_payable = self.total_paye + self.total_sdl + self.total_uif - self.total_eti
   ```

3. **Date Validations**

   The EMP501 implementation includes rigorous validation for reconciliation periods:
   ```python
   def validate_dates(self):
       """
       Validate date ranges for EMP501 Reconciliation.
       
       The method enforces:
       1. From Date is before To Date
       2. Correct date ranges for Interim and Final periods according to SARS requirements
       3. Valid tax year format
       """
       if not self.from_date or not self.to_date:
           frappe.throw(_("Both From Date and To Date are required"), title=_("Missing Required Dates"))
           
       from_date = getdate(self.from_date)
       to_date = getdate(self.to_date)
       
       if from_date > to_date:
           frappe.throw(_("From Date cannot be after To Date"), title=_("Invalid Date Range"))
           
       # Validate reconciliation period
       if self.reconciliation_period == "Interim":
           # Interim period is March to August
           if not (from_date.month == 3 and from_date.day == 1):
               frappe.throw(_("For Interim reconciliation, From Date must be March 1"), 
                          title=_("Invalid Interim Period Start Date"))
               
           if not (to_date.month == 8 and to_date.day == 31):
               frappe.throw(_("For Interim reconciliation, To Date must be August 31"), 
                          title=_("Invalid Interim Period End Date"))
               
           # Ensure same calendar year
           if from_date.year != to_date.year:
               frappe.throw(_("Interim period must be within the same calendar year"), 
                          title=_("Invalid Year Range"))
               
       elif self.reconciliation_period == "Final":
           # Final period is March to February
           if not (from_date.month == 3 and from_date.day == 1):
               frappe.throw(_("For Final reconciliation, From Date must be March 1"), 
                          title=_("Invalid Final Period Start Date"))
               
           if not (to_date.month == 2 and to_date.day in [28, 29]):
               frappe.throw(_("For Final reconciliation, To Date must be the last day of February"), 
                          title=_("Invalid Final Period End Date"))
               
           # Ensure correct tax year - February should be the year after March
           if to_date.year != from_date.year + 1:
               frappe.throw(_("Final period must span from March 1 to February of the next year"), 
                          title=_("Invalid Tax Year"))
   ```

4. **IRP5 Certificate Generation**

   The EMP501 module can generate IRP5/IT3(a) tax certificates for employees:
   ```python
   def generate_irp5_certificates(self):
       """Generate IRP5 certificates for all employees for the period"""
       if not self.from_date or not self.to_date:
           frappe.throw("Please set From Date and To Date first")
           
       # Convert string dates to datetime objects if needed
       from_date = getdate(self.from_date)
       to_date = getdate(self.to_date)
           
       # Get all employees who received salary during the period
       employees = frappe.db.sql("""
           SELECT DISTINCT employee, employee_name
           FROM `tabSalary Slip`
           WHERE company = %s
           AND start_date >= %s
           AND end_date <= %s
           AND docstatus = 1
       """, (self.company, from_date, to_date), as_dict=1)
       
       # Clear existing certificates
       self.irp5_certificates = []
       
       # Create IRP5 certificates
       for employee in employees:
           # Check if certificate already exists
           existing_cert = frappe.db.exists("IRP5 Certificate", {
               "employee": employee.employee,
               "tax_year": self.tax_year,
               "company": self.company
           })
           
           if existing_cert:
               cert = frappe.get_doc("IRP5 Certificate", existing_cert)
               status = cert.status
           else:
               # Create new certificate
               cert = frappe.new_doc("IRP5 Certificate")
               cert.employee = employee.employee
               cert.employee_name = employee.employee_name
               cert.tax_year = self.tax_year
               cert.company = self.company
               cert.from_date = self.from_date
               cert.to_date = self.to_date
               cert.status = "Draft"
               cert.save()
               status = "Draft"
           
           # Add to table
           self.append("irp5_certificates", {
               "irp5_certificate": cert.name,
               "employee": employee.employee,
               "employee_name": employee.employee_name,
               "status": status
           })
   ```

#### IRP5 Certificates

IRP5 certificates provide a summary of employee earnings and tax deductions for the tax year. They are issued to employees annually and submitted to SARS as part of the EMP501 reconciliation.

1. **IRP5 Certificate Structure**

   The IRP5 certificate in Kartoza is implemented as a DocType with child tables for income and deduction details:
   
   - **IRP5 Certificate**: Main document with employee and tax period information
   - **IRP5 Income Detail**: Child table for income sources (using SARS income codes)
   - **IRP5 Deduction Detail**: Child table for deductions (using SARS deduction codes)
   
   The certificate structure maps directly to the SARS IRP5 form, ensuring compliance with tax reporting requirements.

2. **Income and Deduction Codes**

   The system uses standard SARS codes for income and deductions:
   
   | Type | Code Range | Purpose |
   |------|------------|---------|
   | Income | 3601-3619, 3651-3669 | Normal income, allowances |
   | Income | 3701-3724 | Fringe benefits |
   | Income | 3801-3816, 3851-3866 | Non-taxable income |
   | Deduction | 4001-4007 | Pension, provident fund, etc. |
   | Deduction | 4101-4102 | PAYE and UIF |
   | Deduction | 4149-4150 | Medical contributions |

3. **Certificate Generation Process**

   Certificates can be generated:
   - Automatically during EMP501 reconciliation
   - Manually for individual employees
   - In batch for all employees in a company

4. **Technical Implementation**

   The IRP5 certificate functionality is structured with:
   - JSON schema defining certificate fields and structure
   - Python controller handling certificate generation and calculations
   - JavaScript client-side code for user interactions
   - Integration with salary slip data for certificate compilation

### ETI (Employment Tax Incentive)

The Employment Tax Incentive (ETI) is a South African tax incentive aimed at encouraging employers to hire young and less experienced job seekers.

#### ETI Implementation in Kartoza

The ETI functionality is one of the most complex implementations in the Kartoza module, requiring precise calculations and tracking.

1. **ETI Eligibility Criteria**

   For an employee to qualify for ETI, they must meet the following criteria:
   
   - **Age**: Between 18-29 years old on the last day of the month
   - **Remuneration**: Monthly remuneration within qualifying thresholds
   - **Employment Period**: First 24 months of employment only
   - **Hiring Date**: Employed on or after October 1, 2013
   - **Documentation**: Valid South African ID or Asylum Seeker permit
   - **Minimum Wage**: Meet applicable minimum wage requirements

2. **ETI Calculation Rules**

   ETI calculations depend on salary ranges with different formulas:
   
   | Monthly Remuneration | First 12 Months | Second 12 Months |
   |----------------------|-----------------|------------------|
   | R0 - R2,000          | 50% of monthly remuneration | 25% of monthly remuneration |
   | R2,001 - R4,500      | R1,000 | R500 |
   | R4,501 - R6,500      | R1,000 - (0.5 × (Monthly Remuneration - R4,500)) | R500 - (0.25 × (Monthly Remuneration - R4,500)) |
   | Above R6,500         | R0 | R0 |

3. **ETI DocTypes**

   The Kartoza module includes several ETI-specific doctypes:
   
   - **ETI Slab**: Configures calculation formulas and parameters
   - **ETI Slab Details**: Defines calculation formulas by remuneration bracket
   - **Employee ETI Log**: Tracks ETI claims and carry-forward amounts

4. **Technical Implementation**

   The core ETI calculation functionality is implemented in `get_eti_deduction()` in `salary_slip.py`:
   
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
       current_eti_amount = 0
       
       # Get employee details needed for ETI calculation
       employee_details = (
           frappe.db.get_value(
               "Employee",
               {"name": self.employee},
               ["date_of_joining", "date_of_birth", "custom_hours_per_month"],
               as_dict=True,
           )
           or {}
       )
   
       # Calculate employee's age
       age = calculate_age(employee_details.get("date_of_birth"))
       
       # Get ETI configuration details for the current period
       eti_details = frappe.db.get_value(
           "ETI Slab",
           {"start_date": ["<=", (self.posting_date)], "docstatus": 1},
           ["minimum_age", "maximum_age", "name", "hours_in_a_month"],
           as_dict=True,
       )
   
       taxable_eti_amount = 0
       
       # Verify employee meets age requirements
       if (
           eti_details
           and eti_details.get("minimum_age") <= age
           and eti_details.get("maximum_age") >= age
       ):
           # Check if employee is within 24-month ETI eligibility period
           prev_eti = frappe.get_all(
               "Employee ETI Log", {"employee": self.employee}, pluck="name"
           )
           prev_eti_count = len(prev_eti)
           
           if prev_eti_count < 24:  # ETI can only be claimed for first 24 months
               # Get salary components eligible for ETI calculation
               eligible_components = {}
               eti_eligible_components = frappe.get_all(
                   "Salary Component",
                   {"custom_allow_for_eti": 1},
                   [
                       "name",
                       "taxable_earning_reduce_percentage",
                       "reduce_on_taxable_earning",
                   ],
               )
               
               # Create lookup dictionary for eligible components
               for eti_component in eti_eligible_components:
                   eligible_components[eti_component.get("name")] = {
                       "taxable_earning_reduce_percentage": eti_component.get(
                           "taxable_earning_reduce_percentage"
                       ),
                       "reduce_on_taxable_earning": eti_component.get(
                           "reduce_on_taxable_earning"
                       ),
                   }
               
               # Calculate total ETI-eligible remuneration amount
               for earning in self.earnings:
                   if earning.salary_component in eligible_components.keys():
                       # Apply special percentage reduction if applicable
                       if float(
                           eligible_components.get(earning.salary_component, {}).get(
                               "taxable_earning_reduce_percentage"
                           )
                       ) > 0 and eligible_components.get(earning.salary_component, {}).get(
                           "reduce_on_taxable_earning"
                       ):
                           taxable_eti_amount += (
                               float(
                                   eligible_components.get(
                                       earning.salary_component, {}
                                   ).get("taxable_earning_reduce_percentage")
                               )
                               / 100
                           ) * earning.amount
                       else:
                           taxable_eti_amount += earning.amount
               
               # Determine which formula to use based on employment period
               formula_field = (
                   "first_qualifying_12_months"  # First 12 months of employment
                   if prev_eti_count <= 11
                   else "second_qualifying_12_months"  # Second 12 months of employment
               )
               
               if taxable_eti_amount:
                   # Get the appropriate formula for the ETI calculation based on remuneration amount
                   formula = frappe.db.get_value(
                       "ETI Slab Details",
                       {
                           "parent": eti_details.get("name"),
                           "from_amount": ["<=", taxable_eti_amount],
                           "to_amount": [">=", taxable_eti_amount],
                       },
                       formula_field,
                   )
   
                   if formula:
                       # Ensure hours per month is set
                       if not employee_details.custom_hours_per_month:
                           frappe.throw(
                               "Set <b>Hours Per Month</b> for the Employee: {0}".format(
                                   self.employee
                               )
                           )
   
                       # Cap hours to standard if employee works more than standard hours
                       hours_per_month = employee_details.custom_hours_per_month
                       if eti_details.hours_in_a_month < hours_per_month:
                           hours_per_month = eti_details.hours_in_a_month
   
                       # Apply formula and calculate prorated amount based on hours worked
                       self.data, self.default_data = self.get_data_for_eval()
                       self.data.monthly_remuneration = taxable_eti_amount
                       current_eti_amount = frappe.safe_eval(formula, self.data) or 0
                       
                       # Prorate ETI amount based on hours worked
                       current_eti_amount = (
                           current_eti_amount
                           / eti_details.hours_in_a_month
                           * hours_per_month
                       )
       
       return current_eti_amount
   ```

5. **ETI Tracking and Reporting**

   The ETI system maintains logs of ETI claims for:
   - Tracking the 24-month eligibility period
   - Carrying forward unused ETI amounts
   - Reporting ETI utilization in EMP201 submissions
   - Reconciling ETI values in EMP501 reconciliations

6. **Integration with SARS Requirements**

   The ETI implementation adheres to SARS requirements by:
   - Following calculation formulas specified by SARS
   - Maintaining appropriate records for audit purposes
   - Reflecting ETI claims correctly on EMP201 and EMP501 forms
   - Supporting changes in ETI parameters with version-controlled ETI slabs

### COIDA (Compensation for Occupational Injuries and Diseases)

The Compensation for Occupational Injuries and Diseases Act (COIDA) provides a framework for compensation for disablement caused by occupational injuries or diseases sustained or contracted by employees during their employment.

#### COIDA Implementation in Kartoza

1. **COIDA Settings**

   The COIDA functionality is centered around several doctypes:
   
   - **COIDA Settings**: Central configuration for COIDA-related functionality
   - **COIDA Industry Rate**: Industry-specific assessment rates
   - **COIDA Annual Return**: Annual returns to the Compensation Fund
   - **Workplace Injury**: Records of workplace injuries
   - **OID Claim**: Claims for occupational injuries and diseases

2. **Technical Implementation**

   The COIDA annual return is implemented in `coida_annual_return.py`:
   
   ```python
   def calculate_assessment_fee(self):
       """Calculate the assessment fee based on earnings and rate"""
       if not self.assessment_rate:
           # Try to get the rate from COIDA Settings
           if self.industry_class:
               coida_settings = frappe.get_single("COIDA Settings")
               for rate in coida_settings.industry_rates:
                   if rate.industry_class == self.industry_class:
                       self.assessment_rate = rate.assessment_rate
                       break
       
       if self.total_annual_earnings and self.assessment_rate:
           self.assessment_fee = flt(self.total_annual_earnings) * flt(self.assessment_rate) / 100
   ```

3. **Employee Data Collection**

   The system collects employee earnings data for COIDA annual returns:
   
   ```python
   def fetch_employee_data(self):
       """Fetch employee count and earnings data from salary slips"""
       if not self.company or not self.from_date or not self.to_date:
           frappe.throw(_("Company and date range are required to fetch data"))
       
       # Get total employees
       employees = frappe.db.sql("""
           SELECT COUNT(DISTINCT employee) as count
           FROM `tabSalary Slip`
           WHERE company = %s 
           AND start_date >= %s 
           AND end_date <= %s
           AND docstatus = 1
       """, (self.company, self.from_date, self.to_date), as_dict=True)
       
       if employees and employees[0].count:
           self.total_employees = employees[0].count
       
       # Get total earnings
       earnings = frappe.db.sql("""
           SELECT SUM(gross_pay) as total
           FROM `tabSalary Slip`
           WHERE company = %s 
           AND start_date >= %s 
           AND end_date <= %s
           AND docstatus = 1
       """, (self.company, self.from_date, self.to_date), as_dict=True)
       
       if earnings and earnings[0].total:
           self.total_annual_earnings = earnings[0].total
   ```

4. **Assessment Fee Calculation**

   The COIDA assessment fee is calculated based on:
   - Total annual employee earnings
   - Industry-specific assessment rate
   - Special rules for director earnings

5. **Compliance with Compensation Fund Requirements**

   The implementation ensures compliance with Compensation Fund requirements:
   - Correct calculation of assessment fees
   - Proper record-keeping of employee earnings
   - Support for annual returns
   - Handling of industry-specific rates

### Workplace Injuries Management

The Workplace Injuries Management system handles recording and processing of workplace injuries in compliance with COIDA requirements.

1. **Workplace Injury DocType**

   The Workplace Injury doctype captures:
   - Employee information
   - Injury date and details
   - Injury type and severity
   - Medical details
   - Required leave and compensation

2. **Technical Implementation**

   The Workplace Injury functionality is implemented in `workplace_injury.py`:
   
   ```python
   def on_submit(self):
       """Create leave application and OID claim if required"""
       if self.requires_leave:
           self.create_leave_application()
       
       if self.requires_claim:
           self.create_oid_claim()
   
   def create_leave_application(self):
       """Create a leave application for the injured employee"""
       if self.leave_application:
           return
