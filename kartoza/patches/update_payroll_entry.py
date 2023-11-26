import frappe

def execute():
	for pe in frappe.db.get_list("Payroll Entry"):
		doc = frappe.get_doc("Payroll Entry", pe.name)
		for employee in doc.employees:
			account_currency = None
			if employee.custom_payroll_payable_bank_account:
				account = frappe.db.get_value("Bank Account", employee.custom_payroll_payable_bank_account, "account")
				if account:
					account_currency = frappe.db.get_value("Account", account, "account_currency")
			frappe.db.sql(""" update `tabPayroll Employee Detail` set custom_bank_account_currency='{0}' where parent='{1}' and employee='{2}' """.format(account_currency, pe.name, employee.employee))

