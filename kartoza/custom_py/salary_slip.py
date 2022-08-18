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
		earning_limit = float(frappe.db.get_value("HR Settings", "HR Settings", "maximum_earnings"))
		for i in self.deductions:
			if frappe.db.get_value("Salary Component", i.salary_component, "is_income_tax_component"):
				self.deductions[i.idx-1].amount -= (medical_aid + tax_rebate)
				self.tax_rebate = tax_rebate
				self.medical_aid = medical_aid
			if "4141" in i.salary_component:
				self.deductions[i.idx-1].amount = self.gross_pay / 100 if earning_limit > self.gross_pay else earning_limit / 100

		# for i in self.
		super().set_loan_repayment()
		super().set_precision_for_component_amounts()
		super().set_net_pay()

	def get_taxable_earnings(self, allow_tax_exemption=False, based_on_payment_days=0):
		taxable_income = super().get_taxable_earnings(allow_tax_exemption, based_on_payment_days)
		ra = get_retirement_annuity(self)
		if ra:
			ra_percent = ra.ra_amount / taxable_income.taxable_earnings *100
			if ra_percent > ra.limit_percent:
				ra_percent = ra.limit_percent
			ra_amount = ra_percent * taxable_income.taxable_earnings / 100
			self.retirement_annuity = ra_amount
			taxable_income.taxable_earnings -= ra_amount
		return taxable_income

def get_retirement_annuity(self):
	ra = frappe.db.get_value("Retirement Annuity", {"effective_from":["<=", self.start_date], "disable":0, "employee":self.employee})
	res = frappe._dict({})
	if ra:
		ra = frappe.get_doc("Retirement Annuity", ra)
		res['limit_percent'] = ra.maximum_
		res["ra_amount"] = ra.annuity_amount
		if (ra.maximum_amount // 12) < ra.annuity_amount:
			res["ra_amount"] = ra.maximum_amount // 12
	return res

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