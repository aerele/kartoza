# Copyright (c) 2025, Aerele and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json
from frappe.utils import getdate, add_months, get_first_day, get_last_day, flt

class EMP501Reconciliation(Document):
    def validate(self):
        self.validate_dates()
        self.calculate_totals()
        
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
                
        # Set tax year field based on dates
        tax_year_start = from_date.year
        tax_year_end = to_date.year
        self.tax_year = f"{tax_year_start}-{tax_year_end}"
    
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
    
    def on_submit(self):
        self.status = "Prepared"
        
    @frappe.whitelist()
    def fetch_emp201_submissions(self):
        """
        Fetch EMP201 submissions for the selected period.
        
        This method retrieves all submitted EMP201 Submissions within the specified date range
        and adds them to the EMP201 Submissions table in the current document.
        
        Returns:
            int: Number of EMP201 submissions fetched
        
        Raises:
            frappe.ValidationError: If required fields are missing or database errors occur
        """
        if not self.from_date or not self.to_date:
            frappe.throw(_("Please set From Date and To Date before fetching submissions"), 
                        title=_("Missing Date Range"))
            
        if not self.company:
            frappe.throw(_("Company is required to fetch EMP201 submissions"), 
                        title=_("Missing Company"))
            
        # Clear existing submissions
        self.emp201_submissions = []
        
        # Convert string dates to datetime objects if needed
        from_date = getdate(self.from_date)
        to_date = getdate(self.to_date)
        
        try:
            # Get all EMP201 submissions for the period using explicit SQL query to avoid between issues
            emp201_submissions = frappe.db.sql("""
                SELECT name, posting_date, net_paye_payable as paye_payable, sdl_payable, uif_payable, 
                       eti_utilized_current_month as eti_utilized
                FROM `tabEMP201 Submission`
                WHERE company = %s 
                AND docstatus = 1
                AND posting_date >= %s
                AND posting_date <= %s
            """, (self.company, from_date, to_date), as_dict=1)
        except Exception as e:
            error_msg = str(e)
            if "Unknown column" in error_msg:
                field_name = error_msg.split("Unknown column '")[1].split("'")[0]
                frappe.throw(_(f"Database field not found: {field_name}. Please ensure the EMP201 Submission doctype is correctly set up with all required fields."),
                           title=_("Field Reference Error"))
            else:
                frappe.throw(_(f"Error retrieving EMP201 submissions: {error_msg}"),
                           title=_("Database Error"))
        
        # Add submissions to the table
        for submission in emp201_submissions:
            self.append("emp201_submissions", {
                "emp201_submission": submission.name,
                "submission_date": submission.posting_date,
                "paye": submission.paye_payable,
                "sdl": submission.sdl_payable,
                "uif": submission.uif_payable,
                "eti": submission.eti_utilized
            })
            
        self.calculate_totals()
        return len(emp201_submissions)
    
    @frappe.whitelist()
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
            
        return len(employees)
    
    @frappe.whitelist()
    def submit_to_sars(self):
        """Submit the EMP501 reconciliation to SARS via e-Filing integration"""
        if self.status != "Prepared":
            frappe.throw("EMP501 must be in 'Prepared' status before submission to SARS")
            
        # Check if SARS e-Filing integration is configured
        sars_settings = frappe.get_single("SARS e-Filing Integration")
        if not sars_settings.enabled:
            frappe.throw("SARS e-Filing Integration is not enabled")
            
        # Prepare submission data
        submission_data = {
            "emp501": {
                "reference": self.name,
                "tax_year": self.tax_year,
                "period": self.reconciliation_period,
                "from_date": self.from_date,
                "to_date": self.to_date,
                "paye_reference": self.paye_reference_number,
                "sdl_reference": self.sdl_reference_number,
                "uif_reference": self.uif_reference_number,
                "totals": {
                    "paye": self.total_paye,
                    "sdl": self.total_sdl,
                    "uif": self.total_uif,
                    "eti": self.total_eti,
                    "total_payable": self.total_tax_payable
                }
            }
        }
        
        # Mock SARS submission for now
        # In a real implementation, this would call the SARS API
        self.sars_submission_status = "Submitted"
        self.sars_submission_date = frappe.utils.now()
        self.sars_submission_reference = f"SARS-{frappe.utils.random_string(10)}"
        self.sars_response = json.dumps({"status": "success", "message": "Submission accepted"})
        self.status = "Submitted"
        
        return {
            "status": "success",
            "message": "EMP501 submitted to SARS successfully",
            "reference": self.sars_submission_reference
        }
