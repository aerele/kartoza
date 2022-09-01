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
				for sal_detail in salary_slip.earnings:
					(
						is_flexible_benefit,
						only_tax_impact,
						creat_separate_je,
						statistical_component,
					) = frappe.db.get_value(
						"Salary Component",
						sal_detail.salary_component,
						[
							"is_flexible_benefit",
							"only_tax_impact",
							"create_separate_payment_entry_against_benefit_claim",
							"statistical_component",
						],
					)
					if only_tax_impact != 1 and statistical_component != 1:
						if is_flexible_benefit == 1 and creat_separate_je == 1:
							self.create_journal_entry(sal_detail.amount, sal_detail.salary_component)
						else:
							salary_slip_total += sal_detail.amount
				for sal_detail in salary_slip.deductions:
					statistical_component = frappe.db.get_value(
						"Salary Component", sal_detail.salary_component, "statistical_component"
					)
					if statistical_component != 1:
						salary_slip_total -= sal_detail.amount
				for sal_detail in salary_slip.company_contribution:
					salary_slip_total += sal_detail.amount
					print(sal_detail.amount)
			if salary_slip_total > 0:
				self.create_journal_entry(salary_slip_total, "salary")