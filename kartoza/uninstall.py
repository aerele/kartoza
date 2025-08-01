import frappe
 
def after_uninstall():
    remove_manual_custom_fields()
    remove_manual_child_doctypes()
 
# All Kartoza custom fields to remove, by Doctype and fieldname
CUSTOM_FIELDS_TO_DELETE = [
    # Payroll Employee Detail
    ("Payroll Employee Detail", "custom_section_break_kjsnl"),
    ("Payroll Employee Detail", "payroll_payable_bank_account"),
    ("Payroll Employee Detail", "custom_payroll_payable_bank_account"),
    # Salary Slip
    ("Salary Slip", "company_contribution_section"),
    ("Salary Slip", "company_contribution"),
    # Salary Detail
    ("Salary Detail", "is_fringe_benefit"),
    # Payroll Settings
    ("Payroll Settings", "south_african_settings_section"),
    ("Payroll Settings", "paye_salary_component"),
    # Journal Entry Account
    ("Journal Entry Account", "custom_party_name"),
    ("Journal Entry Account", "custom_is_payroll_entry"),
    # Company
    ("Company", "coida_registration_number"),
    # Salary Component
    ("Salary Component", "custom_allow_for_eti"),
    ("Salary Component", "custom_is_annual_bonus"),
    # Employee Benefit Claim
    ("Employee Benefit Claim", "kilometer"),
    # Employee
    ("Employee", "custom_id_number"),
    # Salary Structure
    ("Salary Structure", "company_contribution_section"),
    ("Salary Structure", "company_contribution"),
]
 
# All Kartoza custom child doctypes to delete
CHILD_DOCTYPES_TO_DELETE = [
    "Coida Industry Rate",
    "Employee Frequency Detail",
    "Payroll Employee Detail",
    # Add any other custom child DocTypes from your app here
]
 
def remove_manual_custom_fields():
    for doctype, fieldname in CUSTOM_FIELDS_TO_DELETE:
        try:
            frappe.db.delete("Custom Field", {
                "dt": doctype,
                "fieldname": fieldname
            })
            frappe.db.commit()
            frappe.logger().info(f"Deleted custom field '{fieldname}' from '{doctype}'")
        except Exception as e:
            frappe.logger().error(f"Error deleting custom field '{fieldname}' from '{doctype}': {e}")
 
def remove_manual_child_doctypes():
    for doctype in CHILD_DOCTYPES_TO_DELETE:
        try:
            is_custom = frappe.db.get_value("DocType", doctype, "custom")
            if is_custom:
                frappe.delete_doc("DocType", doctype, force=True)
                frappe.logger().info(f"Deleted custom child Doctype '{doctype}'")
        except Exception as e:
            frappe.logger().error(f"Error deleting child Doctype '{doctype}': {e}")