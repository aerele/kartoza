import frappe
from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip
from datetime import date

class CustomSalarySlip(SalarySlip):
	def calculate_net_pay(self):
		super().calculate_net_pay()
		dependant = frappe.db.get_value("Employee", self.employee, "medical_aid_dependant")
		medical_aid = 0
		if dependant:
			medical_aid = get_medical_aid(dependant)
		for i in self.deductions:
			if frappe.db.get_value("Salary Component", i.salary_component, "is_income_tax_component"):
				self.deductions[i.idx-1].amount -= medical_aid
		super().set_loan_repayment()
		super().set_precision_for_component_amounts()
		super().set_net_pay()
		


def get_medical_aid(dependant):
	cur_year = date.today().year
	name = frappe.db.get_value("Medical Tax Credit Rate", {"year":cur_year})
	if name:
		doc = frappe.get_doc("Medical Tax Credit Rate", name)
		if dependant == 1:
			return doc.one_dependant or 0
		medical_aid = doc.two_dependant or 0
		dependant -= 2
		if dependant:
			medical_aid = (medical_aid + (dependant * doc.additional_dependant)) or 0
		return medical_aid