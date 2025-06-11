# Copyright (c) 2025, Aerele and contributors
# For license information, please see license.txt

import frappe
import csv
import os
from frappe.utils.file_manager import save_file
from frappe.utils import format_date, get_site_name, get_site_path, getdate # Added getdate
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
                emp501_doc.reconciliation_period, # For EMP501 record, this is "Interim" or "Final"
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
            for emp201_child in emp501_doc.emp201_submissions: # Renamed loop variable for clarity
                emp201_doc_actual = frappe.get_doc("EMP201 Submission", emp201_child.emp201_submission)
                
                # Construct YYYYMM period for EMP201
                month_map = {
                    "January": "01", "February": "02", "March": "03", "April": "04",
                    "May": "05", "June": "06", "July": "07", "August": "08",
                    "September": "09", "October": "10", "November": "11", "December": "12"
                }
                # Use submission_period_start_date for the year of the EMP201 period
                period_year = str(getdate(emp201_doc_actual.submission_period_start_date).year)
                period_month_str = month_map.get(emp201_doc_actual.month, "00") # Fallback to "00"
                emp201_period_yyyymm = f"{period_year}{period_month_str}"

                writer.writerow([
                    "EMP201",
                    emp501_doc.tax_year, # Tax year of the EMP501
                    emp201_period_yyyymm, # YYYYMM format for the specific EMP201
                    emp501_doc.paye_reference_number, # Should be consistent for the reconciliation
                    emp501_doc.sdl_reference_number,
                    emp501_doc.uif_reference_number,
                    frappe.db.get_value("Company", emp501_doc.company, "company_name"),
                    format_date(emp201_doc_actual.submission_date), # Actual submission date of the EMP201
                    f"{emp201_child.paye:.2f}", # Use values from the child table in EMP501
                    f"{emp201_child.sdl:.2f}",
                    f"{emp201_child.uif:.2f}",
                    f"{emp201_child.eti:.2f}"
                ])
            
            # Add employee certificate records (IRP5/IT3a)
            for irp5_child in emp501_doc.irp5_certificates: # Renamed loop variable
                irp5_doc_actual = frappe.get_doc("IRP5 Certificate", irp5_child.irp5_certificate)
                
                employee_name = frappe.db.get_value("Employee", irp5_doc_actual.employee, "employee_name") or ""
                # Assuming tax_number and id_number are fields on IRP5 Certificate doctype
                tax_number = irp5_doc_actual.get("tax_number") or "" 
                id_number = irp5_doc_actual.get("id_number") or ""
                
                writer.writerow([
                    "IRP5", # Or IT3A depending on certificate_type
                    emp501_doc.tax_year,
                    irp5_doc_actual.get("certificate_type", "IRP5"), # Default to IRP5 if not specified
                    tax_number,
                    id_number,
                    employee_name,
                    irp5_doc_actual.certificate_number,
                    format_date(irp5_doc_actual.get("issue_date") or emp501_doc.submission_date), # Fallback for issue_date
                    f"{irp5_doc_actual.total_income:.2f}",
                    f"{irp5_doc_actual.total_tax:.2f}", # Assuming this is total tax on IRP5
                    f"{irp5_doc_actual.paye:.2f}",
                    f"{irp5_doc_actual.get('sdi', 0.00):.2f}" # Use .get for sdi with fallback
                ])
            
            temp_file.flush()
            temp_file.close()
            
            with open(temp_file.name, 'rb') as file_content_to_read: # Changed variable name
                content = file_content_to_read.read()
            
            file_name = f"EMP501_{emp501_doc.name}_{frappe.utils.random_string(8)}.csv"
            file_doc = save_file(
                fname=file_name,
                content=content,
                dt="EMP501 Reconciliation",
                dn=emp501_doc.name,
                is_private=1
            )
            
            emp501_doc.db_set("e_filing_csv", file_doc.file_url) # Use db_set to avoid triggering hooks if not needed
            
            return {
                "success": True, 
                "file_url": file_doc.file_url,
                "message": "EMP501 CSV file generated successfully"
            }
            
        except Exception as e:
            frappe.log_error(message=frappe.get_traceback(), title=f"Error generating EMP501 CSV for {emp501}")
            frappe.throw(f"Error generating EMP501 CSV: {str(e)}")
        finally:
            try:
                if not temp_file.closed:
                    temp_file.close()
                os.unlink(temp_file.name)
            except Exception: # More specific exception handling could be added
                pass

def format_emp501_number(num_value): # This function is not used in the provided snippet
    """Format a number with 2 decimal places for EMP501 CSV"""
    if not num_value:
        return "0.00"
    return f"{float(num_value):.2f}"
