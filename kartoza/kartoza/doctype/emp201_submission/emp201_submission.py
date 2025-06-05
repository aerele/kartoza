# Copyright (c) 2024, Aerele and contributors
# For license information, please see license.txt

import frappe
from frappe import _ # Add missing import for translation
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
        frappe.log_error(
            f"EMP201 Validate: Company='{self.company}', FiscalYear='{self.fiscal_year}', Month='{self.month}'",
            "EMP201 Submission Debug"
        )
        frappe.log_error(
            f"EMP201 Validate: Current StartDate='{self.submission_period_start_date}', EndDate='{self.submission_period_end_date}'",
            "EMP201 Submission Debug"
        )
        
        # --- BEGIN DUPLICATE CHECK ---
        # Ensure company, fiscal_year, and month are set before checking for duplicates
        if self.company and self.fiscal_year and self.month:
            name_to_exclude = ""
            if self.is_new():
                # For a new document, generate a random hash. This ensures that the duplicate check,
                # which excludes documents by name, correctly identifies other conflicting documents,
                # as self.name might be temporary or not yet uniquely assigned by autoname.
                name_to_exclude = frappe.generate_hash(length=12)
            else:
                # For an existing document, self.name is its actual, unique name.
                name_to_exclude = self.name
            
            existing_submission = frappe.db.exists(
                "EMP201 Submission",
                {
                    "company": self.company,
                    "fiscal_year": self.fiscal_year,
                    "month": self.month,
                    "name": ["!=", name_to_exclude],
                    "docstatus": ["!=", 2],  # Not Cancelled (0 = Draft, 1 = Submitted)
                },
            )

            if existing_submission:
                frappe.throw(
                    _("An active EMP201 Submission for company '{0}', fiscal year '{1}', and month '{2}' already exists: {3}. Please cancel or delete the existing submission before creating a new one for the same period.").format(
                        self.company, self.fiscal_year, self.month, frappe.utils.get_link_to_form("EMP201 Submission", existing_submission)
                    ),
                    title=_("Duplicate Submission Period"),
                    exc=frappe.DuplicateEntryError,
                )
        # --- END DUPLICATE CHECK ---

        self.set_submission_period_dates()
        frappe.log_error(
            f"EMP201 Validate: After set_submission_period_dates: StartDate='{self.submission_period_start_date}', EndDate='{self.submission_period_end_date}'",
            "EMP201 Submission Debug"
        )
        
        # Autoname logic should ideally run after essential fields for naming are confirmed
        # If name is still the temporary 'new-...', try to set it.
        # The autoname format itself uses fiscal_year and month (via MM derivation)
        # Rely on Frappe's standard doc.insert() to call autoname for new documents.
        # Explicitly calling autoname in validate can sometimes lead to issues if validate is called multiple times
        # or if the naming series relies on data not yet available/committed during all validate calls.
        # if self.name and self.name.startswith("new-emp201-submission-") and self.company and self.fiscal_year and self.month:
        #      if not self.name.endswith("#####"): # Check if autoname has been applied
        #         self.autoname() # Call autoname if it wasn't (e.g. during direct save after create)
        # elif not self.name: # If name is completely unset for some reason
        #     if self.company and self.fiscal_year and self.month:
        #         self.autoname()


    def on_submit(self):
        self.db_set("status", "Submitted to SARS")

    def on_cancel(self):
        self.db_set("status", "Cancelled")

    @frappe.whitelist() # Add whitelist decorator
    def set_submission_period_dates(self):
        frappe.log_error(
            f"set_submission_period_dates called. Company='{self.company}', FiscalYear='{self.fiscal_year}', Month='{self.month}'",
            "EMP201 Submission Debug"
        )
        if self.fiscal_year and self.month and self.company: # Added self.company check for robustness
            # Ensure fiscal_year exists before trying to get_doc
            if not frappe.db.exists("Fiscal Year", self.fiscal_year):
                frappe.log_error(f"Fiscal Year '{self.fiscal_year}' not found in database.", "EMP201 Submission Error")
                # Do not throw error here, let validate handle missing dates if it results in that.
                # Or, we could frappe.throw if Fiscal Year is mandatory for this calculation to proceed.
                # For now, it will just not set the dates, and the reqd check on dates will fail.
                return

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
            # Return the calculated dates for client-side updates if needed
            return {
                "submission_period_start_date": self.submission_period_start_date,
                "submission_period_end_date": self.submission_period_end_date
            }
        return None # Or return existing dates if not recalculated / inputs missing

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
        if not self.company: # Company must be set first
            frappe.throw(_("Company is mandatory."))

        # Ensure submission period dates are set if month and fiscal_year are available
        if self.month and self.fiscal_year and (not self.submission_period_start_date or not self.submission_period_end_date):
            try:
                self.set_submission_period_dates()
            except Exception as e:
                frappe.log_error(f"Error in set_submission_period_dates called from fetch_emp201_data: {e}", "EMP201 Submission Error")
                frappe.throw(_("Could not calculate submission period dates. Ensure Fiscal Year and Month are correct. Error: {0}").format(e))
        
        # Now, re-check if dates are populated
        if not self.submission_period_start_date or not self.submission_period_end_date:
            frappe.throw(_("Submission Period Dates could not be determined. Ensure Fiscal Year and Month are set correctly and the document is saved or Fiscal Year exists."))

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

        frappe.log_error(f"EMP201 Data Fetch for {self.name}: Attempting to fetch component names from Payroll Settings.", "EMP201 Calculation Debug")

        # Fetch and log each component name individually
        ps_paye_field = "paye_salary_component"
        paye_component_name = frappe.db.get_single_value("Payroll Settings", ps_paye_field)
        frappe.log_error(f"  Fetched Payroll Settings.{ps_paye_field}: '{paye_component_name}'", "EMP201 Calculation Debug")
        if not paye_component_name:
            paye_component_name = "Income Tax" # Fallback
            frappe.log_error(f"  Using fallback PAYE Component: {paye_component_name}", "EMP201 Calculation Debug")
        else:
            frappe.log_error(f"  Using PAYE Component: {paye_component_name}", "EMP201 Calculation Debug")

        ps_uif_emp_field = "uif_employee_salary_component"
        uif_employee_component = frappe.db.get_single_value("Payroll Settings", ps_uif_emp_field)
        frappe.log_error(f"  Fetched Payroll Settings.{ps_uif_emp_field}: '{uif_employee_component}'. Using: {uif_employee_component or 'None'}", "EMP201 Calculation Debug")
        
        ps_uif_empr_field = "uif_employer_salary_component"
        uif_employer_component = frappe.db.get_single_value("Payroll Settings", ps_uif_empr_field)
        frappe.log_error(f"  Fetched Payroll Settings.{ps_uif_empr_field}: '{uif_employer_component}'. Using: {uif_employer_component or 'None'}", "EMP201 Calculation Debug")

        ps_sdl_field = "sdl_salary_component"
        sdl_component = frappe.db.get_single_value("Payroll Settings", ps_sdl_field)
        frappe.log_error(f"  Fetched Payroll Settings.{ps_sdl_field}: '{sdl_component}'. Using: {sdl_component or 'None'}", "EMP201 Calculation Debug")

        for ss_ref in salary_slips:
            ss_doc = frappe.get_doc("Salary Slip", ss_ref.name)
            frappe.log_error(f"Processing Salary Slip: {ss_doc.name} for Employee: {ss_doc.employee}", "EMP201 Calculation Debug")

            current_slip_eti = flt(ss_doc.get("custom_monthly_eti")) # Use .get for custom fields
            self.eti_generated_current_month += current_slip_eti
            frappe.log_error(f"  Adding ETI: {current_slip_eti}. Total ETI Generated: {self.eti_generated_current_month}", "EMP201 Calculation Debug")

            # PAYE is a deduction, so iterate through deductions
            # No earnings are directly summed for EMP201 main fields

            for deduction in ss_doc.deductions:
                if deduction.salary_component == paye_component_name:
                    self.gross_paye_before_eti += flt(deduction.amount)
                    frappe.log_error(f"  Adding PAYE: {flt(deduction.amount)} from component '{deduction.salary_component}'. Total Gross PAYE: {self.gross_paye_before_eti}", "EMP201 Calculation Debug")
                
                if deduction.salary_component == uif_employee_component:
                     self.uif_payable += flt(deduction.amount)
                     frappe.log_error(f"  Adding Employee UIF: {flt(deduction.amount)} from component '{deduction.salary_component}'. Total UIF: {self.uif_payable}", "EMP201 Calculation Debug")
            
            for contribution in ss_doc.company_contribution:
                if contribution.salary_component == uif_employer_component:
                    self.uif_payable += flt(contribution.amount)
                    frappe.log_error(f"  Adding Employer UIF: {flt(contribution.amount)} from component '{contribution.salary_component}'. Total UIF: {self.uif_payable}", "EMP201 Calculation Debug")

                if contribution.salary_component == sdl_component:
                    self.sdl_payable += flt(contribution.amount)
                    frappe.log_error(f"  Adding SDL: {flt(contribution.amount)} from component '{contribution.salary_component}'. Total SDL: {self.sdl_payable}", "EMP201 Calculation Debug")

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
        
        # Rounding (optional, but good for currency)
        precision = 2 # Default precision
        company_currency_symbol = frappe.db.get_value("Company", self.company, "default_currency")
        if company_currency_symbol:
            try:
                # Get precision from the currency document's number_format
                currency_doc = frappe.get_doc("Currency", company_currency_symbol)
                number_format = currency_doc.number_format
                if number_format and "." in number_format:
                    precision = len(number_format.split(".")[-1].replace(",", "")) # Count digits after decimal, ignore thousands separators
                elif number_format and "," in number_format and not "." in number_format : # Handle formats like #.###,## (e.g. German)
                    precision = len(number_format.split(",")[-1].replace(".", ""))
                else: # No decimal part in format or format is unusual
                    precision = 0

                # Ensure precision is an integer, fallback if parsing failed unexpectedly
                precision = frappe.utils.cint(precision) # Correctly call cint
                if precision < 0: precision = 0 # Cannot be negative

            except Exception as e:
                frappe.log_error(f"Could not determine currency precision for currency {company_currency_symbol} / company {self.company}. Error: {e}. Defaulting to 2.", "EMP201 Submission Warning")
                precision = 2
        else:
            # Fallback if company or its default currency is not set
            frappe.log_error(f"Company default currency not set for {self.company}. Defaulting precision to 2.", "EMP201 Submission Warning")
            precision = 2

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
