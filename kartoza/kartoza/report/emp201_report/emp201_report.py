# Copyright (c) 2024, Aerele and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data

def get_columns():
    return [
        {
            "label": _("EMP201 Reference"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "EMP201 Submission",
            "width": 180
        },
        {
            "label": _("Company"),
            "fieldname": "company",
            "fieldtype": "Link",
            "options": "Company",
            "width": 120
        },
        {
            "label": _("Month"),
            "fieldname": "month",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": _("Fiscal Year"),
            "fieldname": "fiscal_year",
            "fieldtype": "Link",
            "options": "Fiscal Year",
            "width": 100
        },
        {
            "label": _("Period Start Date"),
            "fieldname": "submission_period_start_date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": _("Period End Date"),
            "fieldname": "submission_period_end_date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": _("Gross PAYE"),
            "fieldname": "gross_paye_before_eti",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("ETI Utilized"),
            "fieldname": "eti_utilized_current_month",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Net PAYE Payable"),
            "fieldname": "net_paye_payable",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("UIF Payable"),
            "fieldname": "uif_payable",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("SDL Payable"),
            "fieldname": "sdl_payable",
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "label": _("Total Payable"),
            "fieldname": "total_payable",
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        }
    ]

def get_data(filters):
    conditions = get_conditions(filters)
    
    emp201_submissions = frappe.db.sql("""
        SELECT 
            name, 
            company, 
            month, 
            fiscal_year, 
            submission_period_start_date, 
            submission_period_end_date, 
            gross_paye_before_eti, 
            eti_utilized_current_month, 
            net_paye_payable, 
            uif_payable, 
            sdl_payable, 
            status
        FROM 
            `tabEMP201 Submission`
        WHERE 
            docstatus < 2
            {conditions}
        ORDER BY 
            submission_period_start_date DESC
    """.format(conditions=conditions), filters, as_dict=1)
    
    # Calculate total payable for each submission
    for submission in emp201_submissions:
        submission.total_payable = flt(submission.net_paye_payable) + flt(submission.uif_payable) + flt(submission.sdl_payable)
    
    return emp201_submissions

def get_conditions(filters):
    conditions = []
    
    if filters.get("company"):
        conditions.append("company = %(company)s")
    
    if filters.get("fiscal_year"):
        conditions.append("fiscal_year = %(fiscal_year)s")
    
    if filters.get("month"):
        conditions.append("month = %(month)s")
    
    if filters.get("from_date"):
        conditions.append("submission_period_start_date >= %(from_date)s")
    
    if filters.get("to_date"):
        conditions.append("submission_period_end_date <= %(to_date)s")
    
    return " AND " + " AND ".join(conditions) if conditions else ""
