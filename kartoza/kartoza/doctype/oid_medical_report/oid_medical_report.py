# Copyright (c) 2025, Aerele and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class OIDMedicalReport(Document):
    def validate(self):
        self.validate_dates()
        
    def validate_dates(self):
        """Validate that report date is not in the future"""
        if self.report_date and self.report_date > frappe.utils.nowdate():
            frappe.throw("Medical report date cannot be in the future")
            
        if self.next_assessment_date and self.report_date and self.next_assessment_date < self.report_date:
            frappe.throw("Next assessment date cannot be before the report date")
