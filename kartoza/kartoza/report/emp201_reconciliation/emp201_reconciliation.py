# Copyright (c) 2025, Aerele and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    
    # Optional: Chart data
    # chart = get_chart_data(data)
    
    # Optional: Report summary
    # report_summary = get_report_summary(data)

    return columns, data, None, None, None # No chart or summary for now

def get_columns():
    return [
        {"label": _("Field"), "fieldname": "field_label", "fieldtype": "Data", "width": 200},
        {"label": _("Value"), "fieldname": "field_value", "fieldtype": "Data", "width": 200},
        {"label": _("Details / Source"), "fieldname": "details", "fieldtype": "Data", "width": 300}
    ]

def get_data(filters):
    if not filters or not filters.get("emp201_submission"):
        frappe.throw(_("Please select an EMP201 Submission to view the report."))

    emp201_submission_id = filters.get("emp201_submission")
    company = filters.get("company") # Company filter might be used for additional validation or context

    try:
        emp201_doc = frappe.get_doc("EMP201 Submission", emp201_submission_id)
    except frappe.DoesNotExistError:
        frappe.throw(_("EMP201 Submission {0} not found.").format(emp201_submission_id))

    if company and emp201_doc.company != company:
        frappe.throw(_("Selected EMP201 Submission does not belong to the selected company {0}.").format(company))

    data = []

    # Basic Information
    data.append({
        "field_label": "EMP201 Submission ID",
        "field_value": emp201_doc.name,
        "details": "Document Name"
    })
    data.append({
        "field_label": "Company",
        "field_value": emp201_doc.company,
        "details": ""
    })
    data.append({
        "field_label": "Posting Date",
        "field_value": frappe.utils.formatdate(emp201_doc.posting_date),
        "details": ""
    })
    data.append({
        "field_label": "Payroll Period",
        "field_value": emp201_doc.payroll_period,
        "details": "Linked Payroll Period"
    })
    # Get status options from EMP201 Submission doctype
    status_options = frappe.get_meta("EMP201 Submission").get_field("status").options
    if isinstance(status_options, str):
        status_options = status_options.split('\n')
    
    data.append({
        "field_label": "Status",
        "field_value": emp201_doc.status,
        "details": "",
        "fieldname": "status", # Add fieldname for JS to identify
        "fieldtype": "Select", # Indicate it should be a select
        "options": status_options # Pass options to JS
    })

    # Tax Values from EMP201 Submission
    data.append({"field_label": "--- Tax Values ---", "field_value": "", "details": ""})
    
    data.append({
        "field_label": "PAYE Payable",
        "field_value": frappe.format(emp201_doc.paye_payable, df={"fieldtype": "Currency", "options": "company:company_currency"}),
        "details": "As per EMP201 Submission"
    })
    data.append({
        "field_label": "SDL Payable",
        "field_value": frappe.format(emp201_doc.sdl_payable, df={"fieldtype": "Currency", "options": "company:company_currency"}),
        "details": "As per EMP201 Submission"
    })
    data.append({
        "field_label": "UIF Payable",
        "field_value": frappe.format(emp201_doc.uif_payable, df={"fieldtype": "Currency", "options": "company:company_currency"}),
        "details": "As per EMP201 Submission"
    })
    data.append({
        "field_label": "ETI Calculated",
        "field_value": frappe.format(emp201_doc.eti_calculated, df={"fieldtype": "Currency", "options": "company:company_currency"}),
        "details": "As per EMP201 Submission"
    })
    data.append({
        "field_label": "ETI Utilized (Current Month)",
        "field_value": frappe.format(emp201_doc.eti_utilized_current_month, df={"fieldtype": "Currency", "options": "company:company_currency"}),
        "details": "As per EMP201 Submission"
    })
    data.append({
        "field_label": "Net PAYE Payable",
        "field_value": frappe.format(emp201_doc.net_paye_payable, df={"fieldtype": "Currency", "options": "company:company_currency"}),
        "details": "PAYE Payable - ETI Utilized"
    })
    data.append({
        "field_label": "Total Amount Payable to SARS",
        "field_value": frappe.format(emp201_doc.total_payable_to_sars, df={"fieldtype": "Currency", "options": "company:company_currency"}),
        "details": "Net PAYE + SDL + UIF"
    })

    # Placeholder for reconciliation details - this would involve fetching related data
    # For example, sum of PAYE from salary slips vs. EMP201 PAYE
    data.append({"field_label": "--- Reconciliation Details (Placeholder) ---", "field_value": "", "details": ""})
    data.append({
        "field_label": "PAYE from Salary Slips",
        "field_value": "TODO", # Placeholder
        "details": "Sum of PAYE from all salary slips linked to this submission's payroll entries"
    })
    data.append({
        "field_label": "Difference (PAYE)",
        "field_value": "TODO", # Placeholder
        "details": "EMP201 PAYE - Salary Slip PAYE"
    })

    return data

@frappe.whitelist()
def update_emp201_submission_status(emp201_submission_id, status):
    try:
        # Check permissions - ensure user can write to EMP201 Submission
        if not frappe.has_permission("EMP201 Submission", "write", doc=emp201_submission_id):
            frappe.throw(_("You do not have permission to update this EMP201 Submission."), frappe.PermissionError)

        emp201_doc = frappe.get_doc("EMP201 Submission", emp201_submission_id)
        
        # Validate if the status is a valid option (optional, but good practice)
        valid_statuses = emp201_doc.meta.get_field("status").options
        if isinstance(valid_statuses, str):
            valid_statuses = valid_statuses.split('\n')
        if status not in valid_statuses:
            frappe.throw(_("Invalid status: {0}").format(status))

        emp201_doc.status = status
        emp201_doc.save(ignore_permissions=True) # ignore_permissions because we've already checked
        # frappe.db.commit() # Not usually needed with doc.save() unless specific transaction control is required
        return {"success": True}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Update EMP201 Submission Status Error")
        return {"success": False, "error": str(e)}

# Example of how to get chart data (not used currently)
# def get_chart_data(data):
#     labels = ["PAYE", "SDL", "UIF", "ETI Utilized"]
#     paye_val = 0
#     sdl_val = 0
#     uif_val = 0
#     eti_val = 0

#     for row in data:
#         if row.get("field_label") == "Net PAYE Payable": # Or PAYE Payable depending on what to chart
#             paye_val = frappe.utils.flt(row.get("field_value"))
#         elif row.get("field_label") == "SDL Payable":
#             sdl_val = frappe.utils.flt(row.get("field_value"))
#         elif row.get("field_label") == "UIF Payable":
#             uif_val = frappe.utils.flt(row.get("field_value"))
#         elif row.get("field_label") == "ETI Utilized (Current Month)":
#             eti_val = frappe.utils.flt(row.get("field_value"))
            
#     datasets = [{'name': 'Values', 'values': [paye_val, sdl_val, uif_val, eti_val]}]
#     chart = {'data': {'labels': labels, 'datasets': datasets}, 'type': 'bar'} # or 'pie', 'line'
#     return chart

# Example of how to get report summary (not used currently)
# def get_report_summary(data):
#     total_payable_sars = 0
#     for row in data:
#         if row.get("field_label") == "Total Amount Payable to SARS":
#             total_payable_sars = row.get("field_value") # Already formatted
#             break
    
#     return [
#         {"value": total_payable_sars, "label": "Total Payable to SARS", "datatype": "Currency", "indicator": "Green" }
#     ]
