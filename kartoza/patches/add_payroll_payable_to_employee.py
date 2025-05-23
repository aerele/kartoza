import frappe

def execute():
    # Check if the column 'payroll_payable_account' already exists in 'tabEmployee'
    if not frappe.db.has_column("Employee", "payroll_payable_account"):
        # Using frappe.db.add_column to add the column.
        # The "Data" fieldtype is suitable for storing the name of a linked document (e.g., a Bank Account name).
        frappe.db.add_column("Employee", "payroll_payable_account", "Data")
        frappe.log_error("Attempted to add column payroll_payable_account to tabEmployee via patch using frappe.db.add_column", "Patch: add_payroll_payable_to_employee")
        # frappe.db.add_column handles its own commit if successful within a patch context usually,
        # but an explicit commit can be added if issues persist.
    else:
        frappe.log_error("Column payroll_payable_account already exists in tabEmployee (checked by patch before attempting add_column)", "Patch: add_payroll_payable_to_employee")

    # Attempt to copy data if both columns exist
    if frappe.db.has_column("Employee", "custom_payroll_payable_account") and \
       frappe.db.has_column("Employee", "payroll_payable_account"):
        try:
            # Check if there are rows where payroll_payable_account is NULL but custom_payroll_payable_account is NOT NULL
            # to avoid unnecessary updates or errors if types are slightly different.
            if frappe.db.sql("""SELECT name FROM `tabEmployee` WHERE `custom_payroll_payable_account` IS NOT NULL AND `payroll_payable_account` IS NULL LIMIT 1"""):
                frappe.db.sql("""
                    UPDATE `tabEmployee`
                    SET `payroll_payable_account` = `custom_payroll_payable_account`
                    WHERE `custom_payroll_payable_account` IS NOT NULL
                    AND `payroll_payable_account` IS NULL
                """)
                frappe.log_error("Copied data from custom_payroll_payable_account to payroll_payable_account via patch", "Patch: add_payroll_payable_to_employee")
                frappe.db.commit() # Ensure change is committed
        except Exception as e:
            frappe.log_error(f"Error copying data in patch: {e}", "Patch: add_payroll_payable_to_employee")
