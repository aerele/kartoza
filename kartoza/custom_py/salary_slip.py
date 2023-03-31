import frappe
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip, get_salary_component_data, calculate_tax_by_tax_slab
from datetime import date,datetime
from hrms.payroll.doctype.payroll_period.payroll_period import get_period_factor, get_payroll_period
from hrms.payroll.doctype.employee_benefit_application.employee_benefit_application import get_benefit_component_amount
from hrms.payroll.doctype.employee_benefit_claim.employee_benefit_claim import get_benefit_claim_amount
from frappe.utils import flt

class CustomSalarySlip(SalarySlip):
	def add_tax_components(self):
		# Calculate variable_based_on_taxable_salary after all components updated in salary slip
		tax_components, self.other_deduction_components = [], []
		for d in self._salary_structure_doc.get("deductions"):
			if d.variable_based_on_taxable_salary == 1 and not d.formula and not flt(d.amount):
				tax_components.append(d.salary_component)
			else:
				self.other_deduction_components.append(d.salary_component)

		# if not tax_components:
		# 	tax_components = [
		# 		d.name
		# 		for d in frappe.get_all("Salary Component", filters={"variable_based_on_taxable_salary": 1})
		# 		if d.name not in self.other_deduction_components
		# 	]

		if tax_components and self.payroll_period and self.salary_structure:
			self.tax_slab = self.get_income_tax_slabs()
			self.compute_taxable_earnings_for_year()

		self.component_based_veriable_tax = {}
		for d in tax_components:
			self.component_based_veriable_tax.setdefault(d, {})
			tax_amount = self.calculate_variable_based_on_taxable_salary(d)
			tax_row = get_salary_component_data(d)
			self.update_component_row(tax_row, tax_amount, "deductions")

	def calculate_net_pay(self):
		# self.payroll_period = frappe.db.get_value('Payroll Period', {"start_date": ("<=", self.start_date),
		# "end_date": (">=", self.end_date), "company": self.company })

		self.payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)

		super().calculate_net_pay()

		if self.payroll_period:
			self.remaining_sub_periods = get_remaining_sub_periods(
				self.employee, self.start_date, self.end_date, self.payroll_frequency, self.payroll_period
			)

		# dependant = frappe.db.get_value("Employee", self.employee, "medical_aid_dependant")
		dependant = frappe.db.get_value("Employee Private Benefit", {"effective_from":["<=", self.start_date],"disable":0, "employee":self.employee}, 'medical_aid_dependant')
		dob = frappe.db.get_value("Employee", self.employee, "date_of_birth")
		medical_aid = 0
		tax_rebate = 0
		if dependant:
			medical_aid = get_medical_aid(self, dependant)
		if dob:
			tax_rebate = get_tax_rebate(self, dob)

		for i in self.deductions:
			if frappe.db.get_value("Salary Component", i.salary_component, "is_income_tax_component") and frappe.db.get_value("Salary Component", i.salary_component, "variable_based_on_taxable_salary"):
				self.tax_value = self.deductions[i.idx-1].amount
				self.deductions[i.idx-1].amount -= (medical_aid + tax_rebate)
				self.tax_rebate = tax_rebate
				self.medical_aid = medical_aid
				if self.deductions[i.idx-1].amount < 0:
					self.deductions[i.idx-1].amount = 0

		salary_structure_doc = frappe.get_doc('Salary Structure', self.salary_structure)

		self.company_contribution = []
		data = self.get_data_for_eval()
		if type(data) == tuple:
			data = data[0]
		for component in salary_structure_doc.company_contribution:
			component.name = None
			component.amount = self.eval_condition_and_formula(component, data)
			if component.amount <= 0:
				continue
			self.append('company_contribution', component)
		total_company_contribution = 0
		for i in self.company_contribution:
			total_company_contribution += i.amount or 0
		self.total_company_contribution = total_company_contribution

		self.total_cost = self.gross_pay + self.total_company_contribution


		super().set_loan_repayment()
		super().set_precision_for_component_amounts()
		super().set_net_pay()
		super().compute_income_tax_breakup()


	def add_employee_benefits(self):
		for struct_row in self._salary_structure_doc.get("earnings"):
			if struct_row.is_flexible_benefit == 1:
				if frappe.db.get_value("Salary Component", struct_row.salary_component, "pay_against_benefit_claim") != 1:
					benefit_component_amount = get_benefit_component_amount(self.employee, self.start_date, self.end_date,
						struct_row.salary_component, self._salary_structure_doc, self.payroll_frequency, self.payroll_period)
					if benefit_component_amount:
						self.update_component_row(struct_row, benefit_component_amount, "earnings")
				else:
					benefit_claim_amount = get_benefit_claim_amount(self.employee, self.start_date, self.end_date, struct_row.salary_component)
					if benefit_claim_amount:
						self.update_component_row(struct_row, benefit_claim_amount, "earnings")

	def get_taxable_earnings(self, allow_tax_exemption=False, based_on_payment_days=0):
		taxable_income = super().get_taxable_earnings(allow_tax_exemption, based_on_payment_days)
		ra = get_retirement_annuity(self)
		if ra:
			ra_percent = ra.ra_amount / taxable_income.taxable_earnings * 100
			if ra_percent > ra.limit_percent:
				ra_percent = ra.limit_percent
			ra_amount = ra_percent * taxable_income.taxable_earnings / 100
			self.retirement_annuity = ra_amount
			taxable_income.taxable_earnings -= ra_amount
		for i in self.earnings:
			tax = 0
			reduce, percent = frappe.db.get_value("Salary Component", i.salary_component, ["reduce_on_taxable_earning", "taxable_earning_reduce_percentage"])
			if reduce:
				tax += i.amount - (i.amount * percent / 100)
			if i.is_flexible_benefit:
				taxable_income.flexi_benefits -= tax
			else:
				taxable_income.taxable_earnings -= tax
		taxable_income.taxable_earnings += taxable_income.flexi_benefits
		taxable_income.flexi_benefits = 0
		self.taxable_value = taxable_income.taxable_earnings
		return taxable_income

	def get_taxable_earnings_for_prev_period(self, start_date, end_date, allow_tax_exemption=False):
		exempted_amount = 0
		taxable_earnings = self.get_salary_slip_details(
			start_date, end_date, parentfield="earnings", is_tax_applicable=1
		)

		if allow_tax_exemption:
			exempted_amount = self.get_salary_slip_details(
				start_date, end_date, parentfield="deductions", exempted_from_income_tax=1
			)

		opening_taxable_earning = self.get_opening_for(
			"taxable_earnings_till_date", start_date, end_date
		)

		ra = frappe.db.sql("""
				select
					sum(retirement_annuity)
				from
					`tabSalary Slip`
				where
					docstatus=1
					and employee=%(employee)s
					and start_date between %(from_date)s and %(to_date)s
					and end_date between %(from_date)s and %(to_date)s
				""", {
					"employee": self.employee,
					"from_date": str(start_date),
					"to_date": str(end_date)
				})
		ra = flt(ra[0][0]) if ra else 0

		return (taxable_earnings + opening_taxable_earning) - exempted_amount - ra, exempted_amount


def get_retirement_annuity(self):
	ra = frappe.db.get_value("Employee Private Benefit", {"effective_from":["<=", self.start_date],"disable":0, "employee":self.employee}, order_by='effective_from')
	res = frappe._dict({})
	self.private_medical_aid = frappe.db.get_value("Employee Private Benefit", {"effective_from":["<=", self.start_date],"disable":0, "employee":self.employee}, 'private_medical_aid') or 0
	if ra:
		ra = frappe.get_doc("Employee Private Benefit", ra)
		res['limit_percent'] = ra.maximum_
		res["ra_amount"] = ra.annuity_amount
		if (ra.maximum_amount // 12) < ra.annuity_amount:
			res["ra_amount"] = ra.maximum_amount // 12
	return res

def get_medical_aid(self, dependant):
	name = frappe.db.get_value("Medical Tax Credit Rate", {"payroll_period":self.payroll_period.name})
	medical_aid = 0
	if name:
		doc = frappe.get_doc("Medical Tax Credit Rate", name)
		if dependant == 1:
			return doc.one_dependant or 0
		medical_aid = doc.two_dependant or 0
		dependant -= 2
		if dependant:
			medical_aid = (medical_aid + (dependant * doc.additional_dependant)) or 0
	return medical_aid


def get_tax_rebate(self, dob):
	if isinstance(dob, str):
		dob = datetime.strptime(dob,"%y-%m-%d")
	today = date.today()
	age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
	name = frappe.db.get_value("Tax Rebates Rate", {"payroll_period":self.payroll_period.name})
	if name:
		doc = frappe.get_doc("Tax Rebates Rate", name)
		tax_rebate = (doc.primary / 12) or 0
		if age >= 65 and age < 75:
			return (doc.secondary / 12) or 0
		if age >= 75:
			tax_rebate = (doc.tertiary / 12) or 0
		return tax_rebate
	return 0

def get_remaining_sub_periods(employee, start_date, end_date, payroll_frequency, payroll_period, depends_on_payment_days=0):
	sub_period = get_period_factor(employee, start_date, end_date, payroll_frequency, payroll_period)[1]
	salary_slips = frappe.db.sql("""
				select
					count(name)
				from
					`tabSalary Slip`
				where
					docstatus=1
					and employee=%(employee)s
					and start_date between %(from_date)s and %(to_date)s
					and end_date between %(from_date)s and %(to_date)s
				""", {
					"employee": employee,
					"from_date": payroll_period.start_date,
					"to_date": payroll_period.end_date
				})
	salary_slips = flt(salary_slips[0][0]) if salary_slips else 0
	return sub_period #- salary_slips
