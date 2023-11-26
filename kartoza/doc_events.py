import frappe

def jv_on_trash(doc, event):
	if doc.docstatus == 0:
		update_employee_jv(doc)

def jv_on_cancel(doc, event):
	update_employee_jv(doc)

def update_employee_jv(doc):
	for row in doc.accounts:
		if row.reference_type and row.reference_type == "Payroll Entry" and row.reference_name and row.party_type == "Employee" and row.party:
			if row.custom_is_payroll_entry:
				frappe.db.set_value("Payroll Employee Detail", {"parent": row.reference_name, "employee": row.party}, "custom_is_bank_entry_creaeted", 0)
			elif row.custom_is_company_contribution:
				frappe.db.set_value("Payroll Employee Detail", {"parent": row.reference_name, "employee": row.party}, "custom_is_company_contribution_created", 0)
