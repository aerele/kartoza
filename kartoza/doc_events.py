import frappe
from erpnext.accounts.utils import get_account_currency
from erpnext import get_company_currency

def jv_on_trash(doc, event):
	if doc.docstatus == 0:
		update_employee_jv(doc)

def jv_on_cancel(doc, event):
	update_employee_jv(doc)

def update_employee_jv(doc):
	reset_company_contribution_flags(doc.name)
	for row in doc.accounts:
		if row.reference_type and row.reference_type == "Payroll Entry" and row.reference_name and row.party_type == "Employee" and row.party:
			if row.custom_is_payroll_entry:
				frappe.db.set_value("Payroll Employee Detail", {"parent": row.reference_name, "employee": row.party}, "custom_is_bank_entry_creaeted", 0)
			elif row.custom_is_company_contribution:
				frappe.db.set_value("Payroll Employee Detail", {"parent": row.reference_name, "employee": row.party}, "custom_is_company_contribution_created", 0)

def reset_company_contribution_flags(journal_entry):
	detail = frappe.qb.DocType("Payroll Employee Detail")
	(
		frappe.qb.update(detail)
		.set(detail.custom_is_company_contribution_created, 0)
		.set(detail.custom_company_contribution_journal_entry, None)
		.where(detail.custom_company_contribution_journal_entry == journal_entry)
	).run()

def employee_onload(doc, event):
	doc.set_onload("is_forex_employee", False)
	if not (doc.company and doc.payroll_payable_account):
		return

	company_currency = get_company_currency(doc.company)

	payment_account = frappe.get_cached_value("Bank Account", doc.payroll_payable_account, "account")
	if not payment_account:
		return

	payment_account_currency = get_account_currency(payment_account)

	if company_currency != payment_account_currency:
		doc.set_onload("is_forex_employee", True)
