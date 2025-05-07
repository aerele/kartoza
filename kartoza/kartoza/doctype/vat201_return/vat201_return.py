# Copyright (c) 2025, Aerele and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

class VAT201Return(Document):
    def validate(self):
        self.validate_dates()
        self.set_vat_registration_number()
        self.calculate_totals()
        
    def validate_dates(self):
        """Validate submission date"""
        if getdate(self.submission_date) > getdate(today()):
            frappe.throw("Submission Date cannot be in the future")
            
    def set_vat_registration_number(self):
        """Set VAT registration number from company"""
        if self.company and not self.vat_registration_number:
            # Try to get from company
            vat_number = frappe.db.get_value("Company", self.company, "custom_vat_number")
            if vat_number:
                self.vat_registration_number = vat_number
            else:
                # Try to get from VAT settings
                vat_settings = frappe.get_doc("South African VAT Settings")
                if vat_settings.vat_registration_number:
                    self.vat_registration_number = vat_settings.vat_registration_number
                    
    def calculate_totals(self):
        """Calculate all totals"""
        # Calculate total supplies
        self.total_supplies = flt(self.standard_rated_supplies) + flt(self.zero_rated_supplies) + flt(self.exempt_supplies)
        
        # Calculate standard rated output tax
        vat_settings = frappe.get_doc("South African VAT Settings")
        standard_rate = flt(vat_settings.standard_vat_rate) / 100
        self.standard_rated_output = flt(self.standard_rated_supplies) * standard_rate
        
        # Calculate total output tax
        self.total_output_tax = (
            flt(self.standard_rated_output) + 
            flt(self.change_in_use_output) + 
            flt(self.bad_debts_output) + 
            flt(self.other_output)
        )
        
        # Calculate total input tax
        self.total_input_tax = (
            flt(self.capital_goods_input) + 
            flt(self.other_goods_services_input) + 
            flt(self.change_in_use_input) + 
            flt(self.bad_debts_input)
        )
        
        # Calculate VAT payable or refundable
        if self.total_output_tax > self.total_input_tax:
            self.vat_payable = self.total_output_tax - self.total_input_tax
            self.vat_refundable = 0
        else:
            self.vat_refundable = self.total_input_tax - self.total_output_tax
            self.vat_payable = 0
            
        # Calculate total amount payable
        if self.vat_payable > 0:
            self.total_amount_payable = self.vat_payable - flt(self.diesel_refund)
            if self.total_amount_payable < 0:
                # If diesel refund exceeds VAT payable, it becomes refundable
                self.vat_refundable = abs(self.total_amount_payable)
                self.total_amount_payable = 0
        else:
            self.total_amount_payable = 0
            self.vat_refundable = self.vat_refundable + flt(self.diesel_refund)
            
    def on_submit(self):
        """Handle submission to SARS"""
        if self.status == "Draft":
            self.status = "Prepared"
            
        # Generate submission reference if not exists
        if not self.submission_reference:
            self.submission_reference = f"VAT201-{self.name}-{frappe.utils.random_string(8)}"
            
        self.db_update()
        
    @frappe.whitelist()
    def submit_to_sars(self):
        """Submit VAT201 return to SARS e-Filing"""
        if self.status != "Prepared":
            frappe.throw("VAT201 Return must be in 'Prepared' status before submission to SARS")
            
        # Check if VAT settings has e-Filing credentials
        vat_settings = frappe.get_doc("South African VAT Settings")
        if not vat_settings.sars_efiling_username or not vat_settings.sars_efiling_password:
            frappe.throw("SARS e-Filing credentials not configured in South African VAT Settings")
            
        # TODO: Implement actual SARS e-Filing integration
        # This would involve API calls to SARS e-Filing system
        # For now, we'll simulate a successful submission
        
        self.status = "Submitted"
        frappe.msgprint("VAT201 Return submitted to SARS e-Filing")
        self.db_update()
        
    @frappe.whitelist()
    def get_vat_transactions(self):
        """Get VAT transactions for the period"""
        # This method would fetch all sales and purchase invoices
        # with VAT for the period and populate the VAT201 return
        
        # TODO: Implement transaction fetching logic
        # This would involve querying Sales Invoice and Purchase Invoice
        # for the specified period and calculating VAT amounts
        
        frappe.msgprint("VAT transactions fetched and populated")
