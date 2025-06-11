# Copyright (c) 2024, Kartoza and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_months, get_first_day, get_last_day
from frappe import _

class EMP201Submission(Document):
    def validate(self):
        # Ensure company, fiscal_year, and month are set before checking for duplicates
        if self.company and self.fiscal_year and self.month:
            # For new documents, self.name will be temporary (e.g., "New EMP201 Submission-X")
            # and won't match existing records. For existing records, self.name is its unique ID.
            # This check prevents a document from conflicting with itself during an update.
            existing_submission = frappe.db.exists(
                "EMP201 Submission",
                {
                    "company": self.company,
                    "fiscal_year": self.fiscal_year,
                    "month": self.month,
                    "name": ["!=", self.name], # Exclude the current document itself
                    "docstatus": ["!=", 2],  # Not Cancelled (i.e., Draft or Submitted ones count as active)
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

        self.set_submission_period_dates()

    def set_submission_period_dates(self):
        if self.month and self.fiscal_year:
            year = int(self.fiscal_year.split("-")[0])
            month_number = {
                "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12
            }[self.month]

            # Adjust year for months that fall in the next calendar year of the fiscal year
            if month_number < 3: # Jan & Feb belong to the previous fiscal year's start
                year += 1
            
            self.submission_period_start_date = get_first_day(f"{year}-{month_number}-01")
            self.submission_period_end_date = get_last_day(f"{year}-{month_number}-01")

    def on_submit(self):
        self.status = "Submitted"

    def on_cancel(self):
        self.status = "Cancelled"
