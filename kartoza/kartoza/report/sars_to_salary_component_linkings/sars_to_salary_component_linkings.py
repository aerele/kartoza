# Copyright (c) 2025, Aerele and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    columns, data = [], []
    columns = get_columns()
    data = get_data()
    return columns, data

def get_columns():
    return [
        {"label": "Component Type", "fieldname": "component_type", "fieldtype": "Data", "width": 150},
        {"label": "Salary Component", "fieldname": "salary_component", "fieldtype": "Link", "options": "Salary Component", "width": 200},
        {"label": "SARS Code", "fieldname": "sars_code", "fieldtype": "Data", "width": 100},
        {"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 300},
    ]

def get_data():
    data = []
    salary_components = frappe.get_all("Salary Component", fields=["name", "is_company_contribution"])

    for component in salary_components:
        if component.is_company_contribution:
            code = get_deduction_code(component.name, is_company_contribution=True)
            if code:
                data.append({
                    "component_type": "Company Contribution",
                    "salary_component": component.name,
                    "sars_code": code,
                    "description": get_deduction_description(code)
                })
        else:
            income_code = get_income_code(component.name)
            if income_code:
                data.append({
                    "component_type": "Income",
                    "salary_component": component.name,
                    "sars_code": income_code,
                    "description": get_income_description(income_code)
                })
            
            deduction_code = get_deduction_code(component.name)
            if deduction_code:
                data.append({
                    "component_type": "Deduction",
                    "salary_component": component.name,
                    "sars_code": deduction_code,
                    "description": get_deduction_description(deduction_code)
                })

    return data

def get_income_code(salary_component):
    # Placeholder - expand this with actual mappings
    component_mapping = {
        "Basic Salary": "3601", "Basic": "3601", "Overtime": "3607", "Bonus": "3605", "Commission": "3605",
        "Annual Payment": "3605", "Leave Encashment": "3605", 
        "Travel Allowance": "3701", # Example, verify correct code
        "Subsistence Allowance": "3704", # Example, verify correct code
        "Uniform Allowance": "3713", # Example, verify correct code
        # Fringe Benefits (e.g., Use of Motor Vehicle) might have codes like 3802
    }
    return component_mapping.get(salary_component)

def get_income_description(income_code):
    # Placeholder - expand this
    descriptions = {"3601": "Gross Remuneration", "3605": "Annual Payment", "3607": "Overtime", "3701": "Travel Allowance (Taxable)"}
    return descriptions.get(income_code, f"Income Code {income_code}")

def get_deduction_code(salary_component, is_company_contribution=False):
    # Placeholder - expand this with actual mappings
    # Some codes are specific to employee or employer
    component_mapping_employee = {
        "PAYE": "4102", "Income Tax": "4102", 
        "UIF Contribution": "4141", # Employee UIF
        "Pension Fund": "4001", # Employee Pension
        "Retirement Annuity Fund": "4006", # Employee RA
        "Medical Aid": "4005", # Employee Medical
    }
    component_mapping_employer = {
        "UIF Contribution": "4141", # Employer UIF (often same code as employee for reporting, but context matters)
        "Pension Fund": "4472", # Employer Pension Contribution
        "Medical Aid": "4474", # Employer Medical Contribution
        "SDL": "4142", "Skills Development Levy": "4142", # Skills Development Levy (Employer)
        # Group Life, Disability etc. might have codes like 44xx
    }
    if is_company_contribution:
        return component_mapping_employer.get(salary_component)
    else:
        return component_mapping_employee.get(salary_component)

def get_deduction_description(deduction_code):
    # Placeholder - expand this
    descriptions = {
        "4102": "PAYE", "4141": "UIF Contribution", "4001": "Pension Fund Contribution (Current)",
        "4006": "Retirement Annuity Fund Contributions", "4005": "Medical Scheme Fees (Employee Paid)",
        "4472": "Employer's Pension Fund Contributions", 
        "4474": "Employer's Medical Scheme Contributions",
        "4142": "SDL"
    }
    return descriptions.get(deduction_code, f"Deduction Code {deduction_code}")
