# Copyright (c) 2025, Aerele and contributors
# For license information, please see license.txt

import frappe
import csv
import os
from frappe.utils.file_manager import save_file
from frappe.utils import format_date, get_site_name, get_site_path
from tempfile import NamedTemporaryFile

@frappe.whitelist()
def generate_emp501_csv(emp501):
    """Generate a CSV file for EMP501 submission to SARS e-Filing
    
    Args:
        emp501 (str): Name of the EMP501 Reconciliation document
        
    Returns:
        dict: Information about the generated file
    """
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
                emp201_doc = frappe.get_doc("EMP201 Submission", emp201.emp201_submission)
                writer.writerow([
                    "EMP201",
                    emp501_doc.tax_year,
                    emp201_doc.submission_period,
                    emp501_doc.paye_reference_number,
                    emp501_doc.sdl_reference_number,
                    emp501_doc.uif_reference_number,
                    frappe.db.get_value("Company", emp501_doc.company, "company_name"),
                    format_date(emp201_doc.submission_date),
                    f"{emp201.paye:.2f}",
                    f"{emp201.sdl:.2f}",
                    f"{emp201.uif:.2f}",
                    f"{emp201.eti:.2f}"
                ])
            
            # Add employee certificate records (IRP5/IT3a)
            for irp5 in emp501_doc.irp5_certificates:
                irp5_doc = frappe.get_doc("IRP5 Certificate", irp5.irp5_certificate)
                
                # Get employee details
                employee_name = frappe.db.get_value("Employee", irp5_doc.employee, "employee_name") or ""
                tax_number = irp5_doc.tax_number or ""
                id_number = irp5_doc.id_number or ""
                
                # Write employee record - this follows SARS specifications for employee data
                writer.writerow([
                    "IRP5",
                    emp501_doc.tax_year,
                    irp5_doc.certificate_type,
                    tax_number,
                    id_number,
                    employee_name,
                    irp5_doc.certificate_number,
                    format_date(irp5_doc.issue_date),
                    f"{irp5_doc.total_income:.2f}",
                    f"{irp5_doc.total_tax:.2f}",
                    f"{irp5_doc.paye:.2f}",
                    f"{irp5_doc.sdi:.2f}" if hasattr(irp5_doc, "sdi") else "0.00"
                ])
            
            # Ensure we flush the file before reading it
            temp_file.flush()
            
            # Close the file to ensure it's written to disk
            temp_file.close()
            
            # Read the file for upload
            with open(temp_file.name, 'rb') as file_content:
                content = file_content.read()
            
            # Save the file in ERPNext
            file_name = f"EMP501_{emp501_doc.name}_{frappe.utils.random_string(8)}.csv"
            file_doc = save_file(
                fname=file_name,
                content=content,
                dt="EMP501 Reconciliation",
                dn=emp501_doc.name,
                is_private=1
            )
            
            # Update EMP501 document with file reference
            emp501_doc.e_filing_csv = file_doc.file_url
            emp501_doc.save()
            
            return {
                "success": True, 
                "file_url": file_doc.file_url,
                "message": "EMP501 CSV file generated successfully"
            }
            
        except Exception as e:
            frappe.log_error(f"Error generating EMP501 CSV: {str(e)}")
            frappe.throw(f"Error generating EMP501 CSV: {str(e)}")
        finally:
            # Delete the temporary file
            try:
                os.unlink(temp_file.name)
            except:
                pass  # Ignore errors in cleanup

def format_emp501_number(num_value):
    """Format a number with 2 decimal places for EMP501 CSV"""
    if not num_value:
        return "0.00"
    return f"{float(num_value):.2f}"
