# Copyright (c) 2025, Aerele and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, flt, today, add_months, get_first_day, get_last_day
import os
import json
import base64
from io import BytesIO

# Conditional imports for PDF generation
pdf_generation_available = False
try:
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import black
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdf_generation_available = True
except ImportError:
    frappe.log_error("PDF generation libraries not installed. Install PyPDF2 and reportlab for PDF functionality.")

class IRP5Certificate(Document):
    def validate(self):
        self.validate_dates()
        if not self.certificate_number:
            self.set_certificate_number()
        self.validate_employee()
        if not self.status:
            self.status = "Draft"
        
    def validate_dates(self):
        """Validate that the tax year dates are valid"""
        if not self.from_date or not self.to_date:
            frappe.throw(_("Both From Date and To Date are required"), title=_("Missing Required Dates"))
            
        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        
        if from_date > to_date:
            frappe.throw(_("From Date cannot be after To Date"), title=_("Invalid Date Range"))
            
        # Validate tax period based on reconciliation period
        if self.reconciliation_period == "Interim":
            # Interim period typically March to August
            if not (from_date.month == 3 and from_date.day == 1):
                frappe.throw(_("For Interim reconciliation, From Date must be March 1"), 
                            title=_("Invalid Interim Period Start Date"))
            
            if not (to_date.month == 8 and to_date.day == 31):
                frappe.throw(_("For Interim reconciliation, To Date must be August 31"), 
                            title=_("Invalid Interim Period End Date"))
        
        elif self.reconciliation_period == "Final":
            # Final period is typically March to February
            if not (from_date.month == 3 and from_date.day == 1):
                frappe.throw(_("For Final reconciliation, From Date must be March 1"), 
                            title=_("Invalid Final Period Start Date"))
            
            expected_end_month = 2
            expected_end_day = 28
            if (from_date.year + 1) % 4 == 0 and ((from_date.year + 1) % 100 != 0 or (from_date.year + 1) % 400 == 0):
                expected_end_day = 29  # Leap year
                
            if not (to_date.month == expected_end_month and to_date.day == expected_end_day):
                frappe.throw(_("For Final reconciliation, To Date must be the last day of February"), 
                            title=_("Invalid Final Period End Date"))
            
            # Ensure correct tax year
            if to_date.year != from_date.year + 1:
                frappe.throw(_("Final period must span from March 1 to February of the next year"), 
                            title=_("Invalid Tax Year"))
                
        # Set tax year field based on dates if not already set
        tax_year_start = from_date.year
        tax_year_end = to_date.year
        if not self.tax_year:
            self.tax_year = f"{tax_year_start}-{tax_year_end}"

    def validate_employee(self):
        """Validate employee details and fetch additional information"""
        if not self.employee:
            frappe.throw(_("Employee is required"), title=_("Missing Employee"))
            
        if not self.employee_name:
            self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
            
        if not self.company:
            self.company = frappe.db.get_value("Employee", self.employee, "company")
            
    def set_certificate_number(self):
        """Set a unique certificate number"""
        # Format: IRP5-{TAX_YEAR}-{EMPLOYEE_ID}-{UNIQUE}
        employee_id = frappe.db.get_value("Employee", self.employee, "name")
        tax_year = self.tax_year or "XXXX-XXXX"
        unique = frappe.generate_hash(length=8)
        self.certificate_number = f"IRP5-{tax_year}-{employee_id}-{unique}"

    def before_submit(self):
        """Actions to perform before submission"""
        self.status = "Prepared"
        self.calculate_totals()
        
    def calculate_totals(self):
        """Calculate total tax amounts from income and deduction details"""
        # Reset totals
        self.paye = 0
        self.uif = 0
        self.sdl = 0
        self.eti = 0
        
        # Sum up deductions
        for deduction in self.deduction_details:
            # Map South African tax codes to our fields
            if deduction.deduction_code == "4102":  # PAYE
                self.paye += flt(deduction.amount)
            elif deduction.deduction_code == "4141":  # UIF
                self.uif += flt(deduction.amount)
            
        # Calculate total payable
        self.total_tax_payable = self.paye + self.uif + self.sdl - self.eti
        
    @frappe.whitelist()
    def generate_certificate_data(self):
        """Generate certificate data from salary slips"""
        if not self.employee or not self.from_date or not self.to_date:
            frappe.throw(_("Employee, From Date, and To Date are required"))
            
        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        
        # Clear existing details
        self.income_details = []
        self.deduction_details = []
        
        # Get all salary slips for the employee in the specified period
        salary_slips = frappe.get_all("Salary Slip",
            filters={
                "employee": self.employee,
                "start_date": [">=", from_date],
                "end_date": ["<=", to_date],
                "docstatus": 1  # Only posted salary slips
            },
            fields=["name", "start_date", "end_date", "gross_pay", "total_deduction", "net_pay"],
            order_by="start_date"
        )
        
        if not salary_slips:
            frappe.msgprint(_("No salary slips found for this employee in the specified period"))
            return
            
        # Initialize income and deduction trackers
        income_map = {}
        deduction_map = {}
        
        # Process each salary slip
        for slip in salary_slips:
            # Get salary slip details
            salary_slip = frappe.get_doc("Salary Slip", slip.name)
            
            # Process earnings
            for earning in salary_slip.earnings:
                # Map earning type to South African SARS income code
                income_code = self.get_income_code(earning.salary_component)
                if not income_code:
                    continue  # Skip if no mapping exists
                    
                if income_code not in income_map:
                    income_map[income_code] = {
                        "code": income_code,
                        "description": self.get_income_description(income_code),
                        "amount": 0
                    }
                
                income_map[income_code]["amount"] += flt(earning.amount)
            
            # Process deductions
            for deduction in salary_slip.deductions:
                # Map deduction type to South African SARS deduction code
                deduction_code = self.get_deduction_code(deduction.salary_component)
                if not deduction_code:
                    continue  # Skip if no mapping exists
                    
                if deduction_code not in deduction_map:
                    deduction_map[deduction_code] = {
                        "code": deduction_code,
                        "description": self.get_deduction_description(deduction_code),
                        "amount": 0
                    }
                
                deduction_map[deduction_code]["amount"] += flt(deduction.amount)
                
        # Add income details to certificate
        for code, details in income_map.items():
            self.append("income_details", {
                "income_code": code,
                "description": details["description"],
                "amount": details["amount"],
                "tax_year": self.tax_year,
                "period": self.reconciliation_period
            })
            
        # Add deduction details to certificate
        for code, details in deduction_map.items():
            self.append("deduction_details", {
                "deduction_code": code,
                "description": details["description"],
                "amount": details["amount"],
                "tax_year": self.tax_year,
                "period": self.reconciliation_period
            })
            
        # Calculate totals
        self.calculate_totals()
        
        # Get ETI amount if applicable
        self.calculate_eti()
        
        return {"income_count": len(income_map), "deduction_count": len(deduction_map)}
        
    def get_income_code(self, salary_component):
        """Map salary component to South African SARS income code"""
        # This mapping should ideally come from a configuration table
        # For now, using a simple dictionary
        component_mapping = {
            "Basic Salary": "3601",  # Normal Income
            "House Rent Allowance": "3606",  # Special Allowance
            "Conveyance Allowance": "3606",  # Special Allowance
            "Leave Encashment": "3605",  # Annual payments
            "Special Allowance": "3607",  # Overtime
            "Overtime": "3607",  # Overtime
            "Bonus": "3605",  # Annual payments
            "Commission": "3605"  # Annual payments
        }
        
        return component_mapping.get(salary_component)
    
    def get_income_description(self, income_code):
        """Get description for South African SARS income code"""
        descriptions = {
            "3601": "Income - Normal",
            "3602": "Income - Non-Taxable",
            "3603": "Pension",
            "3604": "Provident Fund",
            "3605": "Annual Payment",
            "3606": "Special Allowances",
            "3607": "Overtime",
            "3608": "Commission",
            "3609": "Travel Allowance",
            "3610": "Interest",
            "3611": "Non-Taxable Earnings"
        }
        
        return descriptions.get(income_code, f"Income Code {income_code}")
    
    def get_deduction_code(self, salary_component):
        """Map salary component to South African SARS deduction code"""
        component_mapping = {
            "TDS": "4102",  # PAYE
            "PAYE": "4102",  # PAYE
            "Tax": "4102",  # PAYE
            "Income Tax": "4102",  # PAYE
            "UIF": "4141",  # UIF Employee Contribution
            "Professional Tax": "4149",  # Other Deductions
            "Provident Fund": "4001",  # Pension Fund Contributions
            "Medical Insurance": "4005",  # Medical Aid Contributions
            "SDL": "4142"  # SDL Employer Contribution
        }
        
        return component_mapping.get(salary_component)
    
    def get_deduction_description(self, deduction_code):
        """Get description for South African SARS deduction code"""
        descriptions = {
            "4001": "Pension Fund Contributions",
            "4002": "Retirement Annuity Fund Contributions",
            "4003": "Provident Fund Contributions",
            "4005": "Medical Aid Contributions",
            "4102": "PAYE",
            "4141": "UIF Employee Contribution",
            "4142": "SDL Employer Contribution",
            "4149": "Other Deductions",
            "4116": "Medical Tax Credit"
        }
        
        return descriptions.get(deduction_code, f"Deduction Code {deduction_code}")
        
    def calculate_eti(self):
        """Calculate Employment Tax Incentive amount"""
        # Check if ETI is applicable
        # Must be between 18-29 years old or in a special economic zone
        employee = frappe.get_doc("Employee", self.employee)
        
        # Skip if no date of birth
        if not employee.date_of_birth:
            return
            
        # Calculate employee age at the end of the tax year
        end_date = getdate(self.to_date)
        birth_date = getdate(employee.date_of_birth)
        
        # Calculate age in years
        age_years = end_date.year - birth_date.year
        if end_date.month < birth_date.month or (end_date.month == birth_date.month and end_date.day < birth_date.day):
            age_years -= 1
            
        # Check if eligible for ETI based on age
        if not (18 <= age_years <= 29):
            # Check if special economic zone exemption applies
            # This would require custom fields on Employee
            if not frappe.db.get_value("Employee", employee.name, "custom_special_economic_zone"):
                return
                
        # Check employment history
        date_of_joining = getdate(employee.date_of_joining)
        
        # Must be employed on or after 1 October 2013
        eti_start_date = getdate("2013-10-01")
        if date_of_joining < eti_start_date:
            return
            
        # Calculate months of employment
        employment_months = (end_date.year - date_of_joining.year) * 12 + (end_date.month - date_of_joining.month)
        if end_date.day < date_of_joining.day:
            employment_months -= 1
            
        # ETI only applies for the first 24 months of employment
        if employment_months > 24:
            return
            
        # Find total remuneration for the period
        total_income = sum(d.amount for d in self.income_details if d.income_code in ["3601", "3602", "3603"])
        
        # Monthly average remuneration
        months_in_period = 0
        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        
        while from_date <= to_date:
            months_in_period += 1
            from_date = get_first_day(add_months(from_date, 1))
            
        if months_in_period == 0:
            return
            
        monthly_remuneration = total_income / months_in_period
        
        # Calculate ETI based on monthly remuneration and employment period
        eti_amount = self.calculate_eti_amount(monthly_remuneration, employment_months <= 12)
        
        # Multiply by months in period
        self.eti = eti_amount * months_in_period
        
    def calculate_eti_amount(self, monthly_remuneration, first_12_months):
        """
        Calculate ETI amount based on South African regulations
        
        Parameters:
        monthly_remuneration (float): Employee's monthly remuneration
        first_12_months (bool): Whether the employee is in the first 12 months of employment
        
        Returns:
        float: Monthly ETI amount
        """
        # As of 2024-2025 tax year - update these values as regulations change
        if monthly_remuneration < 2000:
            # Below minimum wage
            return 0
            
        if monthly_remuneration <= 4500:
            # First bracket: full benefit
            return 1000 if first_12_months else 500
            
        if monthly_remuneration <= 6500:
            # Second bracket: phase out
            if first_12_months:
                return 1000 - (0.5 * (monthly_remuneration - 4500))
            else:
                return 500 - (0.25 * (monthly_remuneration - 4500))
                
        # Above maximum threshold
        return 0
        
    @frappe.whitelist()
    def export_pdf(self):
        """Export IRP5 certificate as PDF"""
        if self.status == "Draft":
            frappe.throw(_("Cannot export draft certificate. Submit the certificate first."))

        # Check if PDF generation libraries are available
        if not pdf_generation_available:
            frappe.throw(_("PDF generation functionality requires PyPDF2 and reportlab libraries. "
                         "Please install these libraries using 'pip install PyPDF2 reportlab' "
                         "or by running 'bench pip install -r apps/kartoza/requirements.txt'."))
            
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

    def generate_irp5_pdf(self):
        """Generate PDF for IRP5 certificate based on SARS template"""
        # Verify PDF generation libraries are available
        if not pdf_generation_available:
            frappe.throw(_("PDF generation functionality requires PyPDF2 and reportlab libraries."))
            
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
        
        # Certificate details - assuming coordinates based on SARS template
        can.drawString(150, 800, self.certificate_number)
        can.drawString(150, 780, self.tax_year or "")
        
        # Employer details
        can.drawString(150, 720, company_doc.company_name or "")
        
        # Try to get employer registration numbers - these would be custom fields
        company_vat = frappe.db.get_value("Company", self.company, "custom_vat_number") or ""
        company_paye = frappe.db.get_value("Company", self.company, "custom_paye_reference_number") or ""
        company_sdl = frappe.db.get_value("Company", self.company, "custom_sdl_reference_number") or ""
        
        can.drawString(150, 700, company_paye)
        can.drawString(150, 680, company_sdl)
        can.drawString(150, 660, company_vat)
        can.drawString(150, 640, company_doc.company_address or "")
        
        # Employee details
        can.drawString(450, 720, employee_doc.employee_name or "")
        
        # Try to get ID number - this would be a custom field
        id_number = frappe.db.get_value("Employee", self.employee, "custom_id_number") or ""
        tax_number = frappe.db.get_value("Employee", self.employee, "custom_tax_number") or ""
        
        can.drawString(450, 700, id_number)
        can.drawString(450, 680, tax_number)
        can.drawString(450, 640, employee_doc.get("custom_residential_address") or "")
        
        # Add income and deduction details - assuming coordinates
        y_pos = 500  # Starting Y position for income items
        
        for income in self.income_details:
            can.drawString(100, y_pos, income.income_code or "")
            can.drawString(150, y_pos, income.description or "")
            can.drawString(400, y_pos, str(income.amount) or "0.00")
            y_pos -= 15  # Move down for next item
            
        y_pos = 300  # Starting Y position for deduction items
        
        for deduction in self.deduction_details:
            can.drawString(100, y_pos, deduction.deduction_code or "")
            can.drawString(150, y_pos, deduction.description or "")
            can.drawString(400, y_pos, str(deduction.amount) or "0.00")
            y_pos -= 15  # Move down for next item
            
        # Add tax calculation summary
        can.drawString(400, 180, str(self.paye or "0.00"))
        can.drawString(400, 160, str(self.uif or "0.00"))
        can.drawString(400, 140, str(self.sdl or "0.00"))
        can.drawString(400, 120, str(self.eti or "0.00"))
        can.drawString(400, 100, str(self.total_tax_payable or "0.00"))
        
        # Finalize the PDF
        can.save()
        
        # Move to the beginning of the StringIO buffer
        packet.seek(0)
        overlay = PdfReader(packet)
        
        # Get the PDF template
        template = PdfReader(template_path)
        
        # Merge the two PDFs
        output = PdfWriter()
        page = template.pages[0]  # Assuming single-page template
        page.merge_page(overlay.pages[0])
        output.add_page(page)
        
        # Save the result to a new PDF
        result_pdf = BytesIO()
        output.write(result_pdf)
        result_pdf.seek(0)
        
        return result_pdf.getvalue()

def save_file(file_name, content, dt, dn, is_private=False):
    """Save a file in Frappe"""
    from frappe.core.doctype.file.file import create_new_folder
    from frappe.utils.file_manager import save_file as _save_file
    
    # Convert binary content to base64 for saving
    if isinstance(content, bytes):
        content = base64.b64encode(content).decode('utf-8')
    
    folder = create_new_folder("IRP5 Certificates", "Home")
    file_url = _save_file(file_name, content, dt, dn, folder=folder, is_private=is_private).file_url
    
    return file_url
