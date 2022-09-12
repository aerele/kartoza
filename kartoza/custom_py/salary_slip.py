import frappe
from erpnext.payroll.doctype.salary_slip.salary_slip import SalarySlip, get_salary_component_data
from datetime import date,datetime
from erpnext.payroll.doctype.payroll_period.payroll_period import (
	get_payroll_period,
	get_period_factor,
)
from frappe.utils import (
	add_days,
	cint,
	cstr,
	date_diff,
	flt,
	formatdate,
	get_first_day,
	getdate,
	money_in_words,
	rounded,
)
import math
class CustomSalarySlip(SalarySlip):
	def calculate_net_pay(self):
		super().calculate_net_pay()
		dependant = frappe.db.get_value("Employee", self.employee, "medical_aid_dependant")
		dob = frappe.db.get_value("Employee", self.employee, "date_of_birth")
		medical_aid = 0
		tax_rebate = 0
		if dependant:
			medical_aid = get_medical_aid(dependant,self.start_date, self.employee)
		if dob:
			tax_rebate = get_tax_rebate(dob,self.start_date)
		# earning_limit = float(frappe.db.get_value("HR Settings", "HR Settings", "maximum_earnings") or 0)
		# if not earning_limit:
		# 	frappe.throw("Set Earning Limit in HR Setting to Calculate Deduction")
		# uif_in_component = None
		# sal_structure = frappe.get_doc("Salary Structure", self.salary_structure)
		# for i in sal_structure.deductions:
		# 	if "4141" in i.salary_component:
		# 		uif_in_component = i.salary_component
		# has_uif_in_slip = False
		# basic = 0
		# for i in self.earnings:
			# if "3601" in i.salary_component:
			# 	basic = i.amount
		for i in self.deductions:
			if frappe.db.get_value("Salary Component", i.salary_component, "is_income_tax_component") and frappe.db.get_value("Salary Component", i.salary_component, "variable_based_on_taxable_salary"):
				self.tax_value = self.deductions[i.idx-1].amount
				self.deductions[i.idx-1].amount -= (medical_aid + tax_rebate)
				self.tax_rebate = tax_rebate
				self.medical_aid = medical_aid
			# if "4141" in i.salary_component:
			# 	has_uif_in_slip = True
			# 	self.deductions[i.idx-1].amount = basic / 100 if earning_limit > basic else earning_limit / 100
		# if uif_in_component and not has_uif_in_slip:
		# 	super().update_component_row(
		# 		get_salary_component_data(uif_in_component),
		# 		basic / 100 if earning_limit > basic else earning_limit / 100,
		# 		"deductions"
		# 	)
		salary_structure_doc = frappe.get_doc('Salary Structure', self.salary_structure)

		self.company_contribution = []
		data = self.get_data_for_eval()
		for component in salary_structure_doc.company_contribution:
			component.name = None
			component.amount = self.eval_condition_and_formula(component, data)
			if component.amount <= 0:
				continue
			self.append('company_contribution', component)


		super().set_loan_repayment()
		super().set_precision_for_component_amounts()
		super().set_net_pay()

	def get_taxable_earnings(self, allow_tax_exemption=False, based_on_payment_days=0, payroll_period=None):
		taxable_income = super().get_taxable_earnings(allow_tax_exemption, based_on_payment_days, payroll_period)
		ra = get_retirement_annuity(self)
		if ra:
			ra_percent = ra.ra_amount / taxable_income.taxable_earnings * 100
			if ra_percent > ra.limit_percent:
				ra_percent = ra.limit_percent
			ra_amount = ra_percent * taxable_income.taxable_earnings / 100
			self.retirement_annuity = ra_amount
			taxable_income.taxable_earnings -= ra_amount
		travel_tax = 0
		for i in self.earnings:
			reduce, percent = frappe.db.get_value("Salary Component", i.salary_component, ["reduce_on_taxable_earning", "taxable_earning_reduce_percentage"])
			if reduce:
				# travel_tax += i.amount - i.amount * percent / 100
				print(i.amount * percent / 100)
		taxable_income.taxable_earnings -= travel_tax
		return taxable_income
	def get_taxable_earnings_for_prev_period(self, start_date, end_date, allow_tax_exemption=False):
		taxable_earnings = frappe.db.sql("""
			select sum(sd.amount)
			from
				`tabSalary Detail` sd join `tabSalary Slip` ss on sd.parent=ss.name
			where
				sd.parentfield='earnings'
				and sd.is_tax_applicable=1
				and is_flexible_benefit=0
				and ss.docstatus=1
				and ss.employee=%(employee)s
				and ss.start_date between %(from_date)s and %(to_date)s
				and ss.end_date between %(from_date)s and %(to_date)s
			""", {
				"employee": self.employee,
				"from_date": start_date,
				"to_date": end_date
			})
		taxable_earnings = flt(taxable_earnings[0][0]) if taxable_earnings else 0

		exempted_amount = 0
		if allow_tax_exemption:
			exempted_amount = frappe.db.sql("""
				select sum(sd.amount)
				from
					`tabSalary Detail` sd join `tabSalary Slip` ss on sd.parent=ss.name
				where
					sd.parentfield='deductions'
					and sd.exempted_from_income_tax=1
					and is_flexible_benefit=0
					and ss.docstatus=1
					and ss.employee=%(employee)s
					and ss.start_date between %(from_date)s and %(to_date)s
					and ss.end_date between %(from_date)s and %(to_date)s
				""", {
					"employee": self.employee,
					"from_date": start_date,
					"to_date": end_date
				})
			exempted_amount = flt(exempted_amount[0][0]) if exempted_amount else 0
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
					"from_date": start_date,
					"to_date": end_date
				})
		ra = flt(ra[0][0]) if ra else 0
		return taxable_earnings - exempted_amount - ra
	def calculate_variable_tax(self, payroll_period, tax_component):
		# get Tax slab from salary structure assignment for the employee and payroll period
		tax_slab = self.get_income_tax_slabs(payroll_period)

		# get remaining numbers of sub-period (period for which one salary is processed)
		remaining_sub_periods = get_remaining_sub_periods(self.employee, self.start_date, self.end_date, self.payroll_frequency, payroll_period)
		# get taxable_earnings, paid_taxes for previous period
		previous_taxable_earnings = self.get_taxable_earnings_for_prev_period(
			payroll_period.start_date, self.start_date, tax_slab.allow_tax_exemption
		)
		previous_total_paid_taxes = self.get_tax_paid_in_period(
			payroll_period.start_date, self.start_date, tax_component
		)

		# get taxable_earnings for current period (all days)
		current_taxable_earnings = self.get_taxable_earnings(
			tax_slab.allow_tax_exemption, payroll_period=payroll_period
		)
		future_structured_taxable_earnings = current_taxable_earnings.taxable_earnings * (
			math.ceil(remaining_sub_periods) - 1
		)

		# get taxable_earnings, addition_earnings for current actual payment days
		current_taxable_earnings_for_payment_days = self.get_taxable_earnings(
			tax_slab.allow_tax_exemption, based_on_payment_days=1, payroll_period=payroll_period
		)
		current_structured_taxable_earnings = current_taxable_earnings_for_payment_days.taxable_earnings
		current_additional_earnings = current_taxable_earnings_for_payment_days.additional_income
		current_additional_earnings_with_full_tax = (
			current_taxable_earnings_for_payment_days.additional_income_with_full_tax
		)

		# Get taxable unclaimed benefits
		unclaimed_taxable_benefits = 0
		if self.deduct_tax_for_unclaimed_employee_benefits:
			unclaimed_taxable_benefits = self.calculate_unclaimed_taxable_benefits(payroll_period)
			unclaimed_taxable_benefits += current_taxable_earnings_for_payment_days.flexi_benefits

		# Total exemption amount based on tax exemption declaration
		total_exemption_amount = self.get_total_exemption_amount(payroll_period, tax_slab)

		# Employee Other Incomes
		other_incomes = self.get_income_form_other_sources(payroll_period) or 0.0

		# Total taxable earnings including additional and other incomes
		total_taxable_earnings = (
			previous_taxable_earnings
			+ current_structured_taxable_earnings
			+ future_structured_taxable_earnings
			+ current_additional_earnings
			+ other_incomes
			+ unclaimed_taxable_benefits
			- total_exemption_amount
		)

		# Total taxable earnings without additional earnings with full tax
		total_taxable_earnings_without_full_tax_addl_components = (
			total_taxable_earnings - current_additional_earnings_with_full_tax
		)

		# Structured tax amount
		total_structured_tax_amount = self.calculate_tax_by_tax_slab(
			total_taxable_earnings_without_full_tax_addl_components, tax_slab
		)
		current_structured_tax_amount = (
			total_structured_tax_amount - previous_total_paid_taxes
		) / remaining_sub_periods

		# Total taxable earnings with additional earnings with full tax
		full_tax_on_additional_earnings = 0.0
		if current_additional_earnings_with_full_tax:
			total_tax_amount = self.calculate_tax_by_tax_slab(total_taxable_earnings, tax_slab)
			full_tax_on_additional_earnings = total_tax_amount - total_structured_tax_amount

		current_tax_amount = current_structured_tax_amount + full_tax_on_additional_earnings
		if flt(current_tax_amount) < 0:
			current_tax_amount = 0
		return current_tax_amount
def get_retirement_annuity(self):
  ra = frappe.db.get_value("Employee Benefit", {"effective_from":["<=", self.start_date], "to":[">=", self.end_date] ,"disable":0, "employee":self.employee})
  res = frappe._dict({})
  if ra:
    ra = frappe.get_doc("Employee Benefit", ra)
    res['limit_percent'] = ra.maximum_
    res["ra_amount"] = ra.annuity_amount
    if (ra.maximum_amount // 12) < ra.annuity_amount:
      res["ra_amount"] = ra.maximum_amount // 12
  return res




def get_medical_aid(dependant , date ,employee):
  cur_year = datetime.strptime(str(date), "%Y-%m-%d").year
  name = frappe.db.sql("""select mt.name from `tabEmployee Benefit` as eb join `tabMedical Tax Credit Rate` as mt on mt.parent = eb.name where eb.employee = '{0}' and mt.year = '{1}' and eb.effective_from <= '{2}' and eb.to >= '{2}'""".format(employee,cur_year,date),as_dict = True)  
  if name:
    doc = frappe.get_doc("Medical Tax Credit Rate", name[0].name)
    if dependant == 1:
      return doc.one_dependant or 0
    medical_aid = doc.two_dependant or 0
    dependant -= 2
    if dependant:
      medical_aid = (medical_aid + (dependant * doc.additional_dependant)) or 0
    return medical_aid
  return 0


def get_tax_rebate(dob,start_date):
	cur_year = datetime.strptime(str(start_date), "%Y-%m-%d").year
	if isinstance(dob, str):
		dob = datetime.strptime(dob,"%y-%m-%d")
	today = date.today()
	age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
	name = frappe.db.get_value("Tax Rebates Rate", {"year":cur_year})
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
	sub_period = get_period_factor(employee, start_date, end_date, payroll_frequency, payroll_period)[0]
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
	return sub_period - salary_slips