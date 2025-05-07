"""
Data migration patch to standardize the VAT number field
from 'vat_number' to 'custom_vat_number' for consistency
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import rename_fieldname

def execute():
    """
    Migrate data from vat_number field to custom_vat_number field
    and standardize field definitions
    """
    # Check if old field exists
    if frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": "vat_number"}):
        # Check if new field exists
        if not frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": "custom_vat_number"}):
            # 1. Create the new field if it doesn't exist
            create_custom_vat_number_field()
            
        # 2. Migrate data from old field to new field
        migrate_vat_numbers()
            
        # 3. Remove old field if new field exists and has data
        if frappe.db.exists("Custom Field", {"dt": "Company", "fieldname": "custom_vat_number"}):
            frappe.db.delete("Custom Field", {
                "dt": "Company", 
                "fieldname": "vat_number"
            })
            
            # Update all references (e.g. Rename all Property Setters)
            update_references()
            
            frappe.db.commit()
            
            print("Successfully migrated VAT number data from 'vat_number' to 'custom_vat_number'")

def create_custom_vat_number_field():
    """Create the new custom_vat_number field"""
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    
    custom_fields = {
        "Company": [{
            "fieldname": "custom_vat_number",
            "label": "VAT Number",
            "fieldtype": "Data",
            "insert_after": "tax_id",
            "description": "South African VAT Number",
            "length": 10
        }]
    }
    
    create_custom_fields(custom_fields)
    
def migrate_vat_numbers():
    """
    Copy data from old field to new field for all companies
    """
    # Get all companies with a VAT number
    companies = frappe.get_all("Company", fields=["name", "vat_number"])
    
    for company in companies:
        if company.get("vat_number"):
            # Update the company with the new field
            frappe.db.set_value(
                "Company", 
                company.name, 
                "custom_vat_number", 
                company.vat_number, 
                update_modified=False
            )
            
    frappe.db.commit()
    
def update_references():
    """
    Update all references from vat_number to custom_vat_number
    """
    # Check for property setters
    property_setters = frappe.get_all(
        "Property Setter",
        filters={
            "doc_type": "Company",
            "field_name": "vat_number"
        },
        fields=["name"]
    )
    
    for ps in property_setters:
        frappe.db.set_value(
            "Property Setter",
            ps.name,
            "field_name",
            "custom_vat_number",
            update_modified=False
        )
    
    # Update any Print Format references
    print_formats = frappe.get_all(
        "Print Format", 
        filters={"doc_type": "Company", "standard": "No"}
    )
    
    for pf in print_formats:
        pf_doc = frappe.get_doc("Print Format", pf.name)
        if "vat_number" in (pf_doc.html or ""):
            pf_doc.html = pf_doc.html.replace("vat_number", "custom_vat_number")
            pf_doc.save()
