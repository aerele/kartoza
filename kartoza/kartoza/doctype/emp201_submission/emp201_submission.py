# Copyright (c) 2024, Aerele and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, today, add_months, get_first_day, get_last_day, flt
from six import string_types

class EMP201Submission(Document):
    def autoname(self):
        # Ensure month_number is available for autoname
        # This might require set_submission_period_dates to be called before autoname if month_number isn't directly stored
        # Or, we derive month_number here again. For simplicity, let's assume self.month is set.
        if not self.company:
            frappe.throw(_("Company is required to generate the name."))
        if not self.fiscal_year:
            frappe.throw(_("Fiscal Year is required to generate the name."))
        if not self.month:
            frappe.throw(_("Month is required to generate the name."))
            
        company_abbr = frappe.db.get_value("Company", self.company, "abbr")
        month_number_map = {
            "January": "01", "February": "02", "March": "03", "April": "04", "May": "05", "June": "06",
            "July": "07", "August": "08", "September": "09", "October": "10", "November": "11", "December": "12"
        }
        month_num_str = month_number_map.get(self.month, "00")

        self.name = frappe.model.naming.make_autoname(
            f"EMP201-.{company_abbr}.-.{self.fiscal_year}.-.{month_num_str}-.#####"
        )

    def validate(self):
        self.set_submission_period_dates()
        if not self.name.endswith("#####"): # Check if autoname has been applied
            self.autoname() # Call autoname if it wasn't (e.g. during direct save after create)


    def on_submit(self):
        self.db_set("status", "Submitted to SARS")

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    def set_submission_period_dates(self):
        if self.fiscal_year and self.month:
            year = int(self.fiscal_year.split("-")[0]) # Assuming fiscal year format like "2023-2024"
            month_number = {
                "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
            }[self.month]

            # Adjust year for months like Jan, Feb, Mar if fiscal year starts in April
            # This logic depends on how fiscal years are defined in relation to calendar months for EMP201
            # For EMP201, the month is a calendar month. The fiscal year context helps group them.
            # Example: Fiscal Year "2023-2024" (usually Mar 2023 - Feb 2024 for SA tax)
            # If month is "March", year is 2023. If month is "January", year is 2024.

            fiscal_year_doc = frappe.get_doc("Fiscal Year", self.fiscal_year)
            
            # Determine the calendar year for the selected month
            # If the month number is less than the fiscal year's start month, it belongs to the second calendar year of the fiscal span
            # e.g., FY Mar 2023 - Feb 2024. Month "January" (1) < "March" (3), so it's Jan 2024.
            # Month "April" (4) >= "March" (3), so it's Apr 2023.
            calendar_year_for_month = fiscal_year_doc.year_start_date.year
            if month_number < fiscal_year_doc.year_start_date.month:
                calendar_year_for_month = fiscal_year_doc.year_end_date.year
            
            self.submission_period_start_date = get_first_day(getdate(f"{calendar_year_for_month}-{month_number}-01"))
            self.submission_period_end_date = get_last_day(getdate(f"{calendar_year_for_month}-{month_number}-01"))

    @frappe.whitelist()
    def get_previous_eti_carry_forward(self):
        # Get ETI to be carried forward from the last submitted EMP201 for this company
        last_submission = frappe.db.get_all(
            "EMP201 Submission",
            filters={
                "company": self.company,
                "docstatus": 1, # Submitted
                "name": ["!=", self.name], # Exclude current doc if it was saved and submitted
                "submission_period_end_date": ["<", self.submission_period_start_date]
            },
            fields=["name", "submission_period_end_date", "eti_to_be_carried_forward"],
            order_by="submission_period_end_date desc",
            limit=1
        )
        if last_submission:
            return flt(last_submission[0].eti_to_be_carried_forward)
        return 0.0

    @frappe.whitelist()
    def fetch_emp201_data(self):
        if not self.company or not self.submission_period_start_date or not self.submission_period_end_date:
            frappe.throw(_("Company and Submission Period Dates are mandatory."))

        self.gross_paye_before_eti = 0
        self.uif_payable = 0
        self.sdl_payable = 0
        self.eti_generated_current_month = 0

        # Fetch salary slips for the period
        salary_slips = frappe.get_all(
            "Salary Slip",
            filters={
                "company": self.company,
                "docstatus": 1, # Submitted
                "start_date": [">=", self.submission_period_start_date],
                "end_date": ["<=", self.submission_period_end_date]
            },
            fields=["name", "custom_monthly_eti", "employee"] # Add other fields as needed
        )

        paye_component_name = frappe.db.get_single_value("Payroll Settings", "paye_salary_component")
        if not paye_component_name:
            paye_component_name = "Income Tax" # Fallback, should be configured

        uif_employee_component = frappe.db.get_single_value("Payroll Settings", "uif_employee_salary_component")
        uif_employer_component = frappe.db.get_single_value("Payroll Settings", "uif_employer_salary_component")
        sdl_component = frappe.db.get_single_value("Payroll Settings", "sdl_salary_component")


        for ss_ref in salary_slips:
            ss_doc = frappe.get_doc("Salary Slip", ss_ref.name)
            self.eti_generated_current_month += flt(ss_doc.custom_monthly_eti)

            for earning in ss_doc.earnings:
                pass # PAYE is a deduction

            for deduction in ss_doc.deductions:
                if deduction.salary_component == paye_component_name:
                    self.gross_paye_before_eti += flt(deduction.amount)
                if deduction.salary_component == uif_employee_component:
                     self.uif_payable += flt(deduction.amount)
            
            for contribution in ss_doc.company_contribution:
                if contribution.salary_component == uif_employer_component:
                    self.uif_payable += flt(contribution.amount)
                if contribution.salary_component == sdl_component:
                    self.sdl_payable += flt(contribution.amount)


        # ETI Logic
        self.eti_carried_forward_from_previous = self.get_previous_eti_carry_forward()
        self.total_eti_available = flt(self.eti_carried_forward_from_previous) + flt(self.eti_generated_current_month)

        if self.total_eti_available >= self.gross_paye_before_eti:
            self.eti_utilized_current_month = self.gross_paye_before_eti
            self.net_paye_payable = 0
            self.eti_to_be_carried_forward = self.total_eti_available - self.gross_paye_before_eti
        else:
            self.eti_utilized_current_month = self.total_eti_available
            self.net_paye_payable = self.gross_paye_before_eti - self.total_eti_available
            self.eti_to_be_carried_forward = 0
        
        # Rounding (optional, but good for currency)
        precision = frappe.get_precision("Currency", "standard_precision", self.company) or 2
        self.gross_paye_before_eti = flt(self.gross_paye_before_eti, precision)
        self.uif_payable = flt(self.uif_payable, precision)
        self.sdl_payable = flt(self.sdl_payable, precision)
        self.eti_generated_current_month = flt(self.eti_generated_current_month, precision)
        self.eti_carried_forward_from_previous = flt(self.eti_carried_forward_from_previous, precision)
        self.total_eti_available = flt(self.total_eti_available, precision)
        self.eti_utilized_current_month = flt(self.eti_utilized_current_month, precision)
        self.net_paye_payable = flt(self.net_paye_payable, precision)
        self.eti_to_be_carried_forward = flt(self.eti_to_be_carried_forward, precision)

        self.save() # Save the calculated values back to the document
        return self # Return self to update form
