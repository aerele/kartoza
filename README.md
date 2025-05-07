# Cohenix Kartoza - South African Localization for Cohenix ERP

## Overview

Cohenix Kartoza is a comprehensive South African localization module for Cohenix ERPthat provides essential features for businesses operating in South Africa. It covers statutory compliance requirements, tax regulations, payroll localization, and financial reporting specific to the South African context.

This module extends Cohenix ERP's functionality to meet South African regulatory requirements, including SARS (South African Revenue Service) compliance, COIDA (Compensation for Occupational Injuries and Diseases Act) management, VAT (Value Added Tax) handling, and more.

## Table of Contents

1. [Installation](#installation)
2. [Features](#features)
3. [Module Structure](#module-structure)
4. [Payroll and Tax Compliance](#payroll-and-tax-compliance)
5. [COIDA Management](#coida-management)
6. [VAT Management](#vat-management)
7. [Regulatory Compliance](#regulatory-compliance)
8. [Custom Fields and Integrations](#custom-fields-and-integrations)
9. [Reports](#reports)
10. [Configuration](#configuration)
11. [Development Guide](#development-guide)
12. [ETI Implementation](#eti-implementation)
13. [IRP5 Certificates](#irp5-certificates)
14. [Integration with HRMS](#integration-with-hrms)
15. [Customized Salary Slip Calculation](#customized-salary-slip-calculation)
16. [Documentation and Resources](#documentation-and-resources)
17. [License](#license)

## Installation

To install the Cohenix Kartoza module:

```bash
# Navigate to your bench directory
cd /path/to/your/bench

# Get the app from the repository
bench get-app https://github.com/your-organization/kartoza.git

# Install the app on your site
bench --site your-site.local install-app kartoza

# Run migrations to create necessary database tables
bench --site your-site.local migrate
```

After installation, the module will add South African localization features to your Cohenix ERPinstance.

## Features

### Payroll and Tax Compliance
- PAYE (Pay As You Earn) tax calculation and management
- UIF (Unemployment Insurance Fund) contributions
- SDL (Skills Development Levy) calculations
- ETI (Employment Tax Incentive) processing
- EMP201 monthly submissions to SARS
- EMP501 bi-annual reconciliations
- IRP5/IT3(a) tax certificates for employees

### COIDA Management
- COIDA settings and configuration
- Annual returns to the Compensation Fund
- Workplace injury recording and management
- OID claims processing
- Medical reports for workplace injuries

### VAT Management
- South African VAT settings and configuration
- Support for standard rate (15%), zero-rated, and exempt items
- VAT vendor type classification
- VAT201 returns for SARS submissions
- VAT analysis reporting

### Regulatory Compliance
- B-BBEE (Broad-Based Black Economic Empowerment) compliance
- Employment equity reporting
- SETA (Sector Education and Training Authority) reporting
- Bargaining council management
- South African leave management

### Custom Fields and Integrations
- Extended company and employee records for South African requirements
- SARS e-Filing integration
- Custom fields for South African statutory requirements

## Module Structure

The Cohenix Kartoza module follows the standard Frappe/Cohenix ERPapp structure with the following key components:

```
kartoza/
├── kartoza/
│   ├── __init__.py
│   ├── hooks.py                  # App hooks for Cohenix ERPintegration
│   ├── config/                   # Module configuration
│   │   └── kartoza.py            # Module configuration and desktop icons
│   ├── kartoza/                  # Main module code
│   │   ├── doctype/              # Document types
│   │   │   ├── emp201_submission/
│   │   │   ├── emp501_reconciliation/
│   │   │   ├── coida_settings/
│   │   │   ├── south_african_vat_settings/
│   │   │   └── ...
│   │   ├── report/               # Reports
│   │   │   ├── emp201_report/
│   │   │   ├── vat_analysis/
│   │   │   └── ...
│   │   └── custom/               # Custom fields for existing doctypes
│   │       ├── company.json
│   │       ├── employee.json
│   │       └── payroll_settings.json
│   └── custom_js/               # Client-side JavaScript customizations
│       ├── coida_annual_return.js
│       ├── workplace_injury.js
│       └── ...
├── license.txt
├── MANIFEST.in
├── requirements.txt
└── setup.py
```

## Payroll and Tax Compliance

### EMP201 Submission

The EMP201 submission process handles monthly returns to SARS for PAYE, UIF, SDL, and ETI.

**Key Files:**
- `kartoza/doctype/emp201_submission/emp201_submission.json`: Document definition
- `kartoza/doctype/emp201_submission/emp201_submission.py`: Server-side controller
- `kartoza/doctype/emp201_submission/emp201_submission.js`: Client-side controller
- `kartoza/report/emp201_report/emp201_report.py`: Report generation

**How It Works:**
1. The system collects payroll data for the specified period
2. It calculates PAYE, UIF, SDL, and ETI amounts
3. The EMP201 submission document is created with these values
4. Users can review, adjust if necessary, and submit the document
5. The submission can be exported for SARS e-Filing

**Code Example (EMP201 Calculation):**
```python
def calculate_totals(self):
    """Calculate totals for EMP201 submission"""
    # Get payroll entries for the period
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

### EMP501 Reconciliation

The EMP501 reconciliation handles bi-annual employer reconciliation declarations to SARS.

**Key Files:**
- `kartoza/doctype/emp501_reconciliation/emp501_reconciliation.json`: Document definition
- `kartoza/doctype/emp501_reconciliation/emp501_reconciliation.py`: Server-side controller
- `kartoza/doctype/emp501_reconciliation/emp501_reconciliation.js`: Client-side controller
- `kartoza/doctype/emp501_emp201_reference/emp501_emp201_reference.py`: Child table for EMP201 references
- `kartoza/doctype/emp501_irp5_reference/emp501_irp5_reference.py`: Child table for IRP5 references

**How It Works:**
1. The system collects all EMP201 submissions for the reconciliation period
2. It also collects all IRP5/IT3(a) certificates issued during the period
3. The EMP501 reconciliation document is created with references to these documents
4. The system reconciles the values between EMP201 submissions and IRP5 certificates
5. Any discrepancies are highlighted for correction
6. The reconciliation can be exported for SARS e-Filing

## COIDA Management

### COIDA Settings

The COIDA settings manage the configuration for Compensation for Occupational Injuries and Diseases Act compliance.

**Key Files:**
- `kartoza/doctype/coida_settings/coida_settings.json`: Document definition
- `kartoza/doctype/coida_settings/coida_settings.py`: Server-side controller
- `kartoza/doctype/coida_industry_rate/coida_industry_rate.json`: Industry rates child table

**How It Works:**
1. Users configure their COIDA registration details
2. Industry rates are set up based on the company's activities
3. These settings are used for COIDA annual returns and workplace injury management

### Workplace Injury Management

The workplace injury management system handles recording and processing of workplace injuries.

**Key Files:**
- `kartoza/doctype/workplace_injury/workplace_injury.json`: Document definition
- `kartoza/doctype/workplace_injury/workplace_injury.py`: Server-side controller
- `kartoza/doctype/workplace_injury/workplace_injury.js`: Client-side controller
- `kartoza/doctype/oid_claim/oid_claim.json`: OID claim document definition
- `kartoza/doctype/oid_claim/oid_claim.py`: OID claim server-side controller
- `kartoza/doctype/oid_medical_report/oid_medical_report.json`: Medical report document definition

**How It Works:**
1. When a workplace injury occurs, it is recorded in the system
2. Details of the injury, including date, time, location, and nature are captured
3. If necessary, an OID claim is created from the workplace injury
4. Medical reports can be attached to the claim
5. The claim process is tracked through various statuses

## VAT Management

### South African VAT Settings

The VAT settings manage the configuration for Value Added Tax compliance.

**Key Files:**
- `kartoza/doctype/south_african_vat_settings/south_african_vat_settings.json`: Document definition
- `kartoza/doctype/south_african_vat_settings/south_african_vat_settings.py`: Server-side controller
- `kartoza/doctype/south_african_vat_rate/south_african_vat_rate.json`: VAT rates child table
- `kartoza/doctype/south_african_vat_rate/south_african_vat_rate.py`: VAT rates server-side controller

**How It Works:**
1. Users configure their VAT registration details
2. VAT rates are set up (standard 15%, zero-rated, exempt)
3. VAT accounts are configured for input and output VAT
4. Filing frequency and other settings are established
5. These settings are used for VAT201 returns and VAT analysis

**Code Example (VAT Rate Validation):**
```python
def validate_rate_flags(self):
    """Validate that rate flags are consistent"""
    # Standard rate cannot be zero-rated or exempt
    if self.is_standard_rate:
        if self.is_zero_rated:
            self.is_zero_rated = 0
            frappe.msgprint("Standard rate cannot be zero-rated. Zero-rated flag has been reset.", alert=True)
            
        if self.is_exempt:
            self.is_exempt = 0
            frappe.msgprint("Standard rate cannot be exempt. Exempt flag has been reset.", alert=True)
            
    # Zero-rated items must have 0% rate
    if self.is_zero_rated and self.rate != 0:
        self.rate = 0
        frappe.msgprint("Zero-rated items must have 0% rate. Rate has been set to 0%.", alert=True)
```

### VAT201 Return

The VAT201 return handles VAT submissions to SARS.

**Key Files:**
- `kartoza/doctype/vat201_return/vat201_return.json`: Document definition
- `kartoza/doctype/vat201_return/vat201_return.py`: Server-side controller
- `kartoza/doctype/vat201_return/vat201_return.js`: Client-side controller

**How It Works:**
1. The system collects VAT transaction data for the specified period
2. It calculates standard rated supplies, zero-rated supplies, and exempt supplies
3. Input and output VAT amounts are calculated
4. The VAT201 return document is created with these values
5. Users can review, adjust if necessary, and submit the document
6. The submission can be exported for SARS e-Filing

**Code Example (VAT Calculation):**
```python
def calculate_totals(self):
    """Calculate all totals"""
    # Calculate total supplies
    self.total_supplies = flt(self.standard_rated_supplies) + flt(self.zero_rated_supplies) + flt(self.exempt_supplies)
    
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

## Regulatory Compliance

### B-BBEE Compliance

The B-BBEE compliance features handle Broad-Based Black Economic Empowerment requirements.

**Key Files:**
- `kartoza/doctype/b_bbee_certificate/b_bbee_certificate.json`: Document definition
- `kartoza/doctype/b_bbee_certificate/b_bbee_certificate.py`: Server-side controller

**How It Works:**
1. B-BBEE certificates are recorded in the system
2. The system tracks B-BBEE levels, scores, and expiry dates
3. Notifications are sent when certificates are approaching expiry

### Employment Equity

The employment equity features handle reporting requirements for employment equity.

**Key Files:**
- `kartoza/doctype/employment_equity_report/employment_equity_report.json`: Document definition
- `kartoza/doctype/employment_equity_report/employment_equity_report.py`: Server-side controller

**How It Works:**
1. The system collects employee demographic data
2. It generates employment equity reports as required by legislation
3. Reports can be exported in the required format for submission

## Custom Fields and Integrations

### Custom Fields

The module adds custom fields to existing Cohenix ERPdoctypes to support South African requirements.

**Key Files:**
- `kartoza/kartoza/custom/company.json`: Custom fields for Company doctype
- `kartoza/kartoza/custom/employee.json`: Custom fields for Employee doctype
- `kartoza/kartoza/custom/payroll_settings.json`: Custom fields for Payroll Settings doctype

**Example Custom Fields:**
- Company: VAT Registration Number, COIDA Registration Number, SDL Number, UIF Number
- Employee: South African ID Number, Tax Number, Employee Type
- Payroll Settings: PAYE, UIF, and SDL calculation methods

### SARS e-Filing Integration

The module provides integration with SARS e-Filing for electronic submission of returns.

**Key Files:**
- `kartoza/doctype/sars_e_filing_integration/sars_e_filing_integration.json`: Document definition
- `kartoza/doctype/sars_e_filing_integration/sars_e_filing_integration.py`: Server-side controller

**How It Works:**
1. Users configure their SARS e-Filing credentials
2. The system can generate submission files in the required format
3. Returns can be submitted electronically to SARS

## Reports

### EMP201 Report

The EMP201 report provides analysis of PAYE, UIF, SDL, and ETI for monthly submissions.

**Key Files:**
- `kartoza/report/emp201_report/emp201_report.json`: Report definition
- `kartoza/report/emp201_report/emp201_report.py`: Report generation script

**How It Works:**
1. The report collects payroll data for the specified period
2. It calculates PAYE, UIF, SDL, and ETI amounts
3. The report displays these values in a format suitable for review and submission

### VAT Analysis Report

The VAT analysis report provides detailed analysis of VAT transactions.

**Key Files:**
- `kartoza/report/vat_analysis/vat_analysis.json`: Report definition
- `kartoza/report/vat_analysis/vat_analysis.py`: Report generation script

**How It Works:**
1. The report collects sales and purchase invoice data for the specified period
2. It extracts VAT information from these transactions
3. The report displays VAT amounts by document type, party, and VAT rate
4. This information can be used for VAT201 return preparation and reconciliation

**Code Example (VAT Analysis):**
```python
def get_sales_invoices(filters, from_date, to_date, vat_settings):
    """Get sales invoices with VAT"""
    result = []
    
    # Query sales invoices
    conditions = ""
    if from_date:
        conditions += f" AND posting_date >= '{from_date}'"
    if to_date:
        conditions += f" AND posting_date <= '{to_date}'"
    if filters.get("company"):
        conditions += f" AND company = '{filters.get('company')}'"
        
    sales_invoices = frappe.db.sql(f"""
        SELECT 
            name, posting_date, customer, customer_name, 
            base_net_total, base_total, base_total_taxes_and_charges
        FROM 
            `tabSales Invoice`
        WHERE 
            docstatus = 1 
            AND base_total_taxes_and_charges > 0
            {conditions}
        ORDER BY 
            posting_date
    """, as_dict=1)
    
    # Process each invoice
    for invoice in sales_invoices:
        # Get tax details
        taxes = frappe.db.sql(f"""
            SELECT 
                account_head, rate, tax_amount, item_wise_tax_detail
            FROM 
                `tabSales Taxes and Charges`
            WHERE 
                parent = '{invoice.name}'
                AND account_head = '{vat_settings.output_vat_account}'
        """, as_dict=1)
        
        for tax in taxes:
            result.append({
                "document_type": "Sales Invoice",
                "document": invoice.name,
                "date": invoice.posting_date,
                "party": invoice.customer_name or invoice.customer,
                "vat_rate": tax.rate,
                "net_amount": invoice.base_net_total,
                "vat_amount": tax.tax_amount,
                "total_amount": invoice.base_total,
                "vat_type": "Output VAT",
                "vat_account": tax.account_head
            })
            
    return result
```

## Configuration

### Module Configuration

The module configuration is defined in `kartoza/config/kartoza.py` and provides the desktop icons and navigation structure.

**Example Configuration:**
```python
def get_data():
    return [
        {
            "label": _("COIDA Management"),
            "items": [
                {
                    "type": "doctype",
                    "name": "COIDA Settings",
                    "description": _("Configure COIDA Settings"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "COIDA Annual Return",
                    "description": _("Annual Return for Compensation for Occupational Injuries and Diseases Act"),
                    "onboard": 1,
                },
                # More items...
            ]
        },
        {
            "label": _("South African VAT"),
            "items": [
                {
                    "type": "doctype",
                    "name": "South African VAT Settings",
                    "description": _("Configure South African VAT Settings"),
                    "onboard": 1,
                },
                # More items...
            ]
        },
        # More sections...
    ]
```

### Hooks

The module hooks are defined in `kartoza/hooks.py` and integrate the module with Cohenix ERP.

**Example Hooks:**
```python
app_name = "kartoza"
app_title = "Kartoza"
app_publisher = "Your Organization"
app_description = "South African Localization for Cohenix ERP"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@your-organization.com"
app_license = "MIT"

# Fixtures
fixtures = [
    {"doctype": "Custom Field", "filters": [["module", "=", "Kartoza"]]},
    {"doctype": "Property Setter", "filters": [["module", "=", "Kartoza"]]}
]

# DocTypes
doctype_js = {
    "Employee": "custom_js/employee.js",
    "Salary Slip": "custom_js/salary_slip.js",
    "Payroll Entry": "custom_js/payroll_entry.js"
}

# Include JS in doctype views
doctype_list_js = {"Employee": "custom_js/employee_list.js"}
doctype_tree_js = {"Employee": "custom_js/employee_tree.js"}
doctype_calendar_js = {"Employee": "custom_js/employee_calendar.js"}

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "kartoza.kartoza.doctype.coida_annual_return.coida_annual_return.send_reminder"
    ],
    "monthly": [
        "kartoza.kartoza.doctype.emp201_submission.emp201_submission.create_monthly_submissions"
    ]
}
```

## Development Guide

### Adding a New Feature

To add a new feature to the Cohenix Kartoza module:

1. Create a new DocType in the appropriate directory:
```bash
bench --site your-site.local make-doctype "New Feature" kartoza
```

2. Define the fields and behavior in the DocType JSON and Python controller

3. Add the feature to the module configuration in `kartoza/config/kartoza.py`

4. If needed, create custom JavaScript for client-side behavior

5. Update this documentation to include the new feature

### Customizing Existing Features

To customize existing features:

1. Modify the DocType JSON file to add or change fields

2. Update the Python controller to implement new behavior

3. Modify the JavaScript file for client-side changes

4. Run migrations to apply the changes:
```bash
bench --site your-site.local migrate
```

## ETI Implementation

The Employment Tax Incentive (ETI) is a South African tax incentive aimed at encouraging employers to hire young and less experienced job seekers.

### ETI Eligibility

For an employee to qualify for ETI, they must meet the following criteria:

- **Age**: Between 18-29 years old on the last day of the month
- **Remuneration**: Monthly remuneration within qualifying thresholds
- **Employment Period**: First 24 months of employment only
- **Hiring Date**: Employed on or after October 1, 2013
- **Documentation**: Valid South African ID or Asylum Seeker permit
- **Minimum Wage**: Meet applicable minimum wage requirements

### ETI Calculation

The ETI amount is calculated based on the employee's monthly remuneration and period of employment:

| Monthly Remuneration | First 12 Months | Second 12 Months |
|----------------------|-----------------|------------------|
| R0 - R2,000          | 50% of monthly remuneration | 25% of monthly remuneration |
| R2,001 - R4,500      | R1,000 | R500 |
| R4,501 - R6,500      | R1,000 - (0.5 × (Monthly Remuneration - R4,500)) | R500 - (0.25 × (Monthly Remuneration - R4,500)) |
| Above R6,500         | R0 | R0 |

### Technical Implementation

ETI is implemented through several components:

1. **Custom Employee Fields**:
   - Hours per month for ETI calculation
   - Date of birth for age validation
   - Employment type and date of joining for eligibility

2. **ETI Configuration Doctypes**:
   - ETI Slab: Configuration for calculation parameters
   - ETI Slab Details: Formulas for different remuneration brackets

3. **ETI Calculation in Salary Slip**:
   The ETI amount is calculated during salary slip generation using the following process:
   - Validate employee eligibility (age, employment period)
   - Determine appropriate remuneration bracket
   - Apply correct formula based on employment period
   - Prorate based on hours worked
   - Track ETI utilization in Employee ETI Log

4. **ETI Reporting**:
   - Monthly reporting in EMP201 submissions
   - Bi-annual reconciliation in EMP501 submissions

## IRP5 Certificates

IRP5 certificates provide a summary of employee earnings and tax deductions for the tax year. They are issued to employees annually and submitted to SARS as part of the EMP501 reconciliation.

### Certificate Structure

The IRP5 certificate in Cohenix Kartoza is structured as follows:

1. **Main Certificate Document**:
   - Employee and tax period information
   - Certificate type (IRP5 or IT3(a))
   - Certificate status and submission status

2. **Income Details**:
   - Income sources categorized by SARS income codes
   - Normal income, allowances, fringe benefits
   - Non-taxable income

3. **Deduction Details**:
   - Deductions categorized by SARS deduction codes
   - Retirement contributions, medical aid
   - PAYE, UIF, and other statutory deductions

### Certificate Generation

IRP5 certificates can be generated through several methods:

1. **Automatic Generation**:
   - During EMP501 reconciliation
   - Scheduled task for all employees

2. **Manual Generation**:
   - Individual certificate creation
   - Batch generation for selected employees

### Technical Implementation

The IRP5 certificate functionality involves:

1. **Data Collection**:
   - Salary slip data for the tax year
   - Income and deduction categorization
   - Tax calculation summaries

2. **SARS Compliance**:
   - Use of standard SARS codes
   - Validation against SARS requirements
   - Support for e-Filing submissions

## Integration with HRMS

Cohenix Kartoza integrates seamlessly with the HRMS module to extend its functionality for South African requirements.

### Payroll Extensions

1. **Salary Structure Extensions**:
   - Support for South African statutory components
   - Configuration for tax-specific salary components
   - Special handling for annual bonuses

2. **Salary Slip Customization**:
   - South African tax calculation
   - ETI processing
   - Medical aid tax credits
   - Tax rebates based on age

3. **Leave Management**:
   - South African public holidays
   - Standard leave types required by law
   - Integration with workplace injury management

### Employee Extensions

1. **Employee Record Extensions**:
   - South African ID validation and processing
   - Tax number management
   - ETI eligibility tracking

2. **Benefits Administration**:
   - Medical aid scheme integration
   - Retirement fund management
   - Company contributions tracking

## Customized Salary Slip Calculation

The Cohenix Kartoza module extends the standard salary slip calculation to accommodate South African requirements.

### South African Tax Calculation

1. **PAYE Calculation**:
   - Progressive tax rates based on annual income
   - Age-based tax rebates (primary, secondary, tertiary)
   - Medical aid tax credits

2. **ETI Processing**:
   - Eligibility determination
   - Amount calculation based on remuneration brackets
   - Pro-rating based on hours worked

3. **Statutory Deductions**:
   - UIF (1% from employee, 1% from employer)
   - SDL (1% from employer)
   - COIDA (industry-specific rate from employer)

### Technical Implementation

The customization is implemented through:

1. **Class Extension**:
   ```python
   class CustomSalarySlip(SalarySlip):
       def validate(self):
           super().validate()
           # South African specific validations
           
       def calculate_net_pay(self):
           # Extended calculation with South African specifics
           
       def calculate_variable_tax(self):
           # South African tax calculation with rebates and credits
   ```

2. **Hooks Integration**:
   ```python
   # In hooks.py
   doc_events = {
       "Salary Slip": {
           "validate": "kartoza.custom_py.salary_slip.CustomSalarySlip.validate",
           "on_submit": "kartoza.custom_py.salary_slip.CustomSalarySlip.on_submit",
           "on_cancel": "kartoza.custom_py.salary_slip.CustomSalarySlip.on_cancel"
       }
   }
   ```

## Documentation and Resources

Comprehensive documentation for the Cohenix Kartoza module is available in the following locations:

1. **In-App Documentation**:
   - Help sections in each DocType
   - Field-level descriptions and tooltips

2. **External Documentation**:
   - [Comprehensive Technical & Functional Documentation](docs/comprehensive_documentation.md)
   - [South African VAT Guide](docs/south_african_vat_guide.md)
   - [PAYE and Payroll Guide](docs/payroll_guide.md)
   - [COIDA Compliance Guide](docs/coida_guide.md)

3. **Reference Materials**:
   - Links to SARS documentation
   - Relevant legislation references
   - Calculation examples and case studies

4. **Regular Updates**:
   - Documentation is kept up to date with regulatory changes
   - Budget speech updates are incorporated annually
   - Legislative amendments are reflected promptly

## License

This module is licensed under the MIT License. See the LICENSE file for details.

---

## Support

For support, please contact:
- Email: support@your-organization.com
- Website: https://your-organization.com
- GitHub: https://github.com/your-organization/kartoza
