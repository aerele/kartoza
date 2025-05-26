import frappe

def execute():
    if frappe.db.has_column("Employee", "custom_payroll_payable_account") and \
       frappe.db.has_column("Employee", "payroll_payable_account"):
        
        # Select employees where custom_payroll_payable_account is set 
        # and payroll_payable_account is either NULL or different.
        employees_to_update = frappe.db.sql("""
            SELECT name, custom_payroll_payable_account
            FROM `tabEmployee`
            WHERE custom_payroll_payable_account IS NOT NULL
            AND (payroll_payable_account IS NULL OR payroll_payable_account != custom_payroll_payable_account)
        """, as_dict=True)

        if not employees_to_update:
            frappe.log_message("No employees found needing payroll_payable_account update from custom_payroll_payable_account.", "Data Migration Patch")
            return

        updated_count = 0
        for emp in employees_to_update:
            try:
                frappe.db.set_value("Employee", emp.name, "payroll_payable_account", emp.custom_payroll_payable_account)
                updated_count += 1
            except Exception as e:
                frappe.log_error(f"Error updating payroll_payable_account for Employee {emp.name}: {e}", "Data Migration Patch")
        
        if updated_count > 0:
            frappe.db.commit()
            frappe.log_message(f"Successfully updated payroll_payable_account for {updated_count} employees from custom_payroll_payable_account.", "Data Migration Patch")
        else:
            frappe.log_message("No employees were updated in this run (possibly due to errors, or data already matched).", "Data Migration Patch")

    else:
        missing_cols = []
        if not frappe.db.has_column("Employee", "custom_payroll_payable_account"):
            missing_cols.append("custom_payroll_payable_account")
        if not frappe.db.has_column("Employee", "payroll_payable_account"):
            missing_cols.append("payroll_payable_account")
        frappe.log_message(f"Skipping payroll account migration: Column(s) {', '.join(missing_cols)} not found in Employee table.", "Data Migration Patch")
