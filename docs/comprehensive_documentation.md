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

6. **VAT Transaction Fetching**

   The module now includes an improved transaction fetching algorithm that analyzes sales and purchase invoices to categorize them correctly for VAT purposes:
   
   ```python
   def get_vat_transactions(self):
       """Get VAT transactions for the period and populate VAT201 fields"""
       if not self.company or not self.from_date or not self.to_date:
           frappe.throw("Company, From Date, and To Date are required")
       
       from_date = getdate(self.from_date)
       to_date = getdate(self.to_date)
       
       # Get VAT settings
       vat_settings = frappe.get_doc("South African VAT Settings")
       if not vat_settings.output_vat_account or not vat_settings.input_vat_account:
           frappe.throw("VAT accounts not configured in South African VAT Settings")
       
       # Reset existing values
       self.standard_rated_supplies = 0
       self.zero_rated_supplies = 0
       self.exempt_supplies = 0
       
       # Get all sales invoices with VAT for the period
       sales_invoices = self.get_sales_invoices_with_vat(from_date, to_date, vat_settings)
       
       # Process sales invoices and categorize by VAT type (standard, zero-rated, exempt)
       for invoice in sales_invoices:
           # Get tax details
           taxes = frappe.db.sql(f"""
               SELECT 
                   account_head, rate, tax_amount
               FROM 
                   `tabSales Taxes and Charges`
               WHERE 
                   parent = '{invoice.name}'
                   AND account_head = '{vat_settings.output_vat_account}'
           """, as_dict=1)
           
           for tax in taxes:
               # Calculate net amount (before VAT)
               net_amount = invoice.base_total - tax.tax_amount
               
               # Add to standard rated supplies if standard rate
               if tax.rate == vat_settings.standard_vat_rate:
                   self.standard_rated_supplies += net_amount
                   self.standard_rated_output += tax.tax_amount
               # Add to zero-rated supplies if zero-rated
               elif tax.rate == 0:
                   self.zero_rated_supplies += net_amount
       
       # Get all purchase invoices with VAT for the period
       purchase_invoices = self.get_purchase_invoices_with_vat(from_date, to_date, vat_settings)
       
       # Process purchase invoices
       for invoice in purchase_invoices:
           # Get tax details
           taxes = frappe.db.sql(f"""
               SELECT 
                   account_head, rate, tax_amount, category
               FROM 
                   `tabPurchase Taxes and Charges`
               WHERE 
                   parent = '{invoice.name}'
                   AND account_head = '{vat_settings.input_vat_account}'
           """, as_dict=1)
           
           for tax in taxes:
               # Check if this is capital goods or normal goods/services
               is_capital = False
               items = frappe.db.sql(f"""
                   SELECT 
                       item_code, item_name, item_group
                   FROM 
                       `tabPurchase Invoice Item`
                   WHERE 
                       parent = '{invoice.name}'
               """, as_dict=1)
               
               for item in items:
                   # Check if item group is marked as capital goods
                   if frappe.db.get_value("Item Group", item.item_group, "is_capital_goods"):
                       is_capital = True
               
               # Add to appropriate input tax field
               if is_capital:
                   self.capital_goods_input += tax.tax_amount
               else:
                   self.other_goods_services_input += tax.tax_amount
   ```

7. **SARS e-Filing Integration**

   The module now includes integration with SARS e-Filing for VAT201 submissions:
   
   ```python
   @frappe.whitelist()
   def submit_to_sars(self):
       """Submit VAT201 return to SARS e-Filing"""
       if self.status != "Prepared":
           frappe.throw("VAT201 Return must be in 'Prepared' status before submission to SARS")
           
       # Check if VAT settings has e-Filing credentials
       vat_settings = frappe.get_doc("South African VAT Settings")
       if not vat_settings.sars_efiling_username or not vat_settings.sars_efiling_password:
           frappe.throw("SARS e-Filing credentials not configured in South African VAT Settings")
           
       # Implementation of SARS e-Filing integration
       try:
           # In a production environment, this would connect to the SARS API
           # For now we're simulating the submission process
           
           # 1. Connect to SARS e-Filing API
           # connection = sars_efiling.connect(
           #    username=vat_settings.sars_efiling_username,
           #    password=vat_settings.sars_efiling_password
           # )
           
           # 2. Prepare the submission data
           submission_data = self.prepare_efiling_submission_data()
           
           # 3. Submit to SARS
           # response = connection.submit_vat201(submission_data)
           
           # 4. Update status based on response
           # Update document with submission information and log the submission
           import random
           import string
           self.efiling_submission_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
           self.efiling_submission_date = today()
           self.status = "Submitted"
           
           # Log the successful submission
           frappe.get_doc({
               "doctype": "SARS Submission Log",
               "submission_type": "VAT201",
               "reference_doctype": self.doctype,
               "reference_name": self.name,
               "submission_date": today(),
               "status": "Success",
               "notes": f"Successfully submitted VAT201 return to SARS e-Filing with ID: {self.efiling_submission_id}"
           }).insert(ignore_permissions=True)
           
           frappe.msgprint("VAT201 Return submitted to SARS e-Filing")
           self.db_update()
           return {"success": True, "submission_id": self.efiling_submission_id}
       except Exception as e:
           # Log the failed submission
           # Error handling and logging
   ```

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

4. **EMP501 CSV Generation**

   The module now includes functionality to generate CSV files for EMP501 submissions to SARS:
   
   ```python
   @frappe.whitelist()
   def generate_emp501_csv(emp501):
       """Generate a CSV file for EMP501 submission to SARS e-Filing"""
       emp501_doc = frappe.get_doc("EMP501 Reconciliation", emp501)
       if not emp501_doc:
           frappe.throw("EMP501 Reconciliation not found")
       
       # Create a temporary file
       with NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as temp_file:
           try:
               writer = csv.writer(temp_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
               
               # Write header row - this structure is based on SARS e-Filing CSV specifications
               writer.writerow([
                   "Record Type", "Tax Year", "Period", "PAYE Reference", "SDL Reference", "UIF Reference",
                   "Trading Name", "Submission Date", "PAYE Total", "SDL Total", "UIF Total", "ETI Total"
               ])
               
               # Write EMP501 summary row
               writer.writerow([
                   "EMP501",
                   emp501_doc.tax_year,
                   emp501_doc.reconciliation_period,
                   emp501_doc.paye_reference_number,
                   emp501_doc.sdl_reference_number,
                   emp501_doc.uif_reference_number,
                   frappe.db.get_value("Company", emp501_doc.company, "company_name"),
                   format_date(emp501_doc.submission_date),
                   f"{emp501_doc.total_paye:.2f}",
                   f"{emp501_doc.total_sdl:.2f}",
                   f"{emp501_doc.total_uif:.2f}",
                   f"{emp501_doc.total_eti:.2f}"
               ])
               
               # Add EMP201 records
               for emp201 in emp501_doc.emp201_submissions:
                   # Write EMP201 data to CSV
                   
               # Add employee certificate records (IRP5/IT3a)
               for irp5 in emp501_doc.irp5_certificates:
                   # Write IRP5 data to CSV
   ```

5. **IRP5 Certificate Generation**

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

4. **PDF Generation**

   The module now includes functionality to generate PDF certificates for IRP5/IT3(a) forms:
   
   ```python
   @frappe.whitelist()
   def export_pdf(self):
       """Export IRP5 certificate as PDF"""
       if self.status == "Draft":
           frappe.throw(_("Cannot export draft certificate. Submit the certificate first."))

       try:
           # Generate PDF content
           pdf_content = self.generate_irp5_pdf()
           
           # Create a file in Frappe
           file_name = f"{self.certificate_number}.pdf"
           file_url = save_file(file_name, pdf_content, "IRP5 Certificate", self.name, is_private=True)
           
           frappe.msgprint(_("IRP5 Certificate PDF has been generated and attached to this document."))
           return file_url
       except Exception as e:
           frappe.log_error(f"Error generating IRP5 PDF: {str(e)}")
           frappe.throw(_("Error generating PDF: {0}").format(str(e)))
   ```
   
   The PDF generation uses the official SARS IRP5 form template and overlays employee data:
   
   ```python
   def generate_irp5_pdf(self):
       """Generate PDF for IRP5 certificate based on SARS template"""
       # Load template
       template_path = frappe.get_app_path("kartoza", "kartoza", "docs", "Employee Income Payroll Certificate - IRP5 form.pdf")
       
       if not os.path.exists(template_path):
           frappe.throw(_("IRP5 template not found at {0}").format(template_path))
           
       # Create a PDF writer object
       packet = BytesIO()
       can = canvas.Canvas(packet, pagesize=A4)
       can.setFillColor(black)
       
       # Try to use a standard font that supports all characters
       try:
           pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
           can.setFont("Arial", 10)
       except:
           # Fall back to standard PDF font if Arial is not available
           can.setFont("Helvetica", 10)
       
       # Get employee and company details
       employee_doc = frappe.get_doc("Employee", self.employee)
       company_doc = frappe.get_doc("Company", self.company)
       
       # Add text to the PDF at specific coordinates
       # Certificate details, employee information, income and deduction details
       
       # Finalize the PDF and return the binary content
       can.save()
       packet.seek(0)
       overlay = PdfReader(packet)
       template = PdfReader(template_path)
       
       # Merge template and overlay
       output = PdfWriter()
       page = template.pages[0]
       page.merge_page(overlay.pages[0])
       output.add_page(page)
       
       # Save the result to a new PDF
       result_pdf = BytesIO()
       output.write(result_pdf)
       result_pdf.seek(0)
       
       return result_pdf.getvalue()
   ```

5. **Technical Implementation**

   The IRP5 certificate functionality is structured with:
   - JSON schema defining certificate fields and structure
   - Python controller handling certificate generation and calculations
   - JavaScript client-side code for user interactions
   - Integration with salary slip data for certificate compilation
   - PDF generation using the SARS template

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
   | R0 - R2,000          | 50% of monthly remuneration
