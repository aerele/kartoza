import frappe
from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip
from datetime import date,datetime

class CustomSalarySlip(SalarySlip):
	def calculate_net_pay(self):
		super().calculate_net_pay()
		dependant = frappe.db.get_value("Employee", self.employee, "medical_aid_dependant")
		dob = frappe.db.get_value("Employee", self.employee, "date_of_birth")
		medical_aid = 0
		tax_rebate = 0
		if dependant:
			medical_aid = get_medical_aid(dependant)
		if dob:
			tax_rebate = get_tax_rebate(dob)
		for i in self.deductions:
			if frappe.db.get_value("Salary Component", i.salary_component, "is_income_tax_component"):
				self.deductions[i.idx-1].amount -= (medical_aid + tax_rebate)
				
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
	return 0


def get_tax_rebate(dob):
	cur_year = date.today().year
	if isinstance(dob, str):
		dob = datetime.strptime(dob,"%y-%m-%d")
	today = date.today()
	age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
	name = frappe.db.get_value("Tax Rebates Rate", {"year":cur_year})
	if name:
		doc = frappe.get_doc("Tax Rebates Rate", name)
		tax_rebate = doc.primary or 0
		if age >= 65 and age <= 75:
			return doc.secondary or 0
		if age > 75:
			tax_rebate = doc.tertiary or 0
		return tax_rebate
	return 0