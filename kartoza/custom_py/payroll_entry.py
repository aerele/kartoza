import frappe
from erpnext.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry


class CustomPayrollEntry(PayrollEntry):
	def get_salary_components(self, component_type):
		salary_components = super().get_salary_components(component_type)
		salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)

		if salary_slips and component_type == "earnings":
			ss = frappe.qb.DocType("Salary Slip")
			ssd = frappe.qb.DocType("Company Contribution")
			salary_components += (
				frappe.qb.from_(ss)
				.join(ssd)
				.on(ss.name == ssd.parent)
				.select(ssd.salary_component, ssd.amount, ssd.parentfield, ss.salary_structure, ss.employee)
				.where(
					(ssd.parentfield == "company_contribution") & (ss.name.isin(tuple([d.name for d in salary_slips])))
				)
			).run(as_dict=True)

		return salary_components

	@frappe.whitelist()
	def make_payment_entry(self):
		super().make_payment_entry()
		self.check_permission("write")

		salary_slip_name_list = frappe.db.sql(
			""" select t1.name from `tabSalary Slip` t1
			where t1.docstatus = 1 and start_date >= %s and end_date <= %s and t1.payroll_entry = %s
			""",
			(self.start_date, self.end_date, self.name),
			as_list=True,
		)

		if salary_slip_name_list and len(salary_slip_name_list) > 0:
			salary_slip_total = 0
			for salary_slip_name in salary_slip_name_list:
				salary_slip = frappe.get_doc("Salary Slip", salary_slip_name[0])
				for sal_detail in salary_slip.company_contribution:
					salary_slip_total += sal_detail.amount
			if salary_slip_total > 0:
				super().create_journal_entry(salary_slip_total, "salary")

	def make_accrual_jv_entry(self):
		jv = super().make_accrual_jv_entry()
		if jv:
			doc = frappe.get_doc("Journal Entry", jv)
			for i in doc.accounts:
				if i.debit_in_account_currency:
					frappe.db.set_value(i.doctype, i.name, 'reference_type', self.doctype)
					frappe.db.set_value(i.doctype, i.name, 'reference_name', self.name)
		return jv



def get_payroll_entry_bank_entries(payroll_entry_name):
	journal_entries = frappe.db.sql(
		'select jea.name from `tabJournal Entry Account` as jea join `tabJournal Entry` as je on je.name=jea.parent '
		'where jea.reference_type="Payroll Entry" '
		'and jea.reference_name=%s and je.docstatus=1 and je.voucher_type="Bank"',
		payroll_entry_name,
		as_dict=1
	)

	return journal_entries