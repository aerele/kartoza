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
        if self.from_date and self.to_date and getdate(self.from_date) > getdate(self.to_date):
            frappe.throw("From Date cannot be after To Date")
            
        # Validate reconciliation period
        if self.reconciliation_period == "Interim":
            # Interim period is March to August
            if not (getdate(self.from_date).month == 3 and getdate(self.from_date).day == 1 and 
                    getdate(self.to_date).month == 8 and getdate(self.to_date).day == 31):
                frappe.throw("Interim period must be from March 1 to August 31")
        elif self.reconciliation_period == "Final":
            # Final period is March to February
            if not (getdate(self.from_date).month == 3 and getdate(self.from_date).day == 1 and 
                    getdate(self.to_date).month == 2 and getdate(self.to_date).day in [28, 29]):
                frappe.throw("Final period must be from March 1 to end of February")
    
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
                    self.total_paye += flt(emp201.paye_payable)
                    self.total_sdl += flt(emp201.sdl_payable)
                    self.total_uif += flt(emp201.uif_payable)
                    self.total_eti += flt(emp201.eti_utilized)
        
        # Calculate total tax payable
        self.total_tax_payable = self.total_paye + self.total_sdl + self.total_uif - self.total_eti
    
    def on_submit(self):
        self.status = "Prepared"
        
    def fetch_emp201_submissions(self):
        """Fetch EMP201 submissions for the selected period"""
        if not self.from_date or not self.to_date:
            frappe.throw("Please set From Date and To Date first")
            
        # Clear existing submissions
        self.emp201_submissions = []
        
        # Get all EMP201 submissions for the period
        emp201_submissions = frappe.get_all(
            "EMP201 Submission",
            filters={
                "company": self.company,
                "submission_date": ["between", [self.from_date, self.to_date]],
                "docstatus": 1
            },
            fields=["name", "submission_date", "paye_payable", "sdl_payable", "uif_payable", "eti_utilized"]
        )
        
        # Add submissions to the table
        for submission in emp201_submissions:
            self.append("emp201_submissions", {
                "emp201_submission": submission.name,
                "submission_date": submission.submission_date,
                "paye": submission.paye_payable,
                "sdl": submission.sdl_payable,
                "uif": submission.uif_payable,
                "eti": submission.eti_utilized
            })
            
        self.calculate_totals()
        return len(emp201_submissions)
    
    def generate_irp5_certificates(self):
        """Generate IRP5 certificates for all employees for the period"""
        if not self.from_date or not self.to_date:
            frappe.throw("Please set From Date and To Date first")
            
        # Get all employees who received salary during the period
        employees = frappe.db.sql("""
            SELECT DISTINCT employee, employee_name
            FROM `tabSalary Slip`
            WHERE company = %s
            AND start_date >= %s
            AND end_date <= %s
            AND docstatus = 1
        """, (self.company, self.from_date, self.to_date), as_dict=1)
        
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
