import calendar
import math
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.utils import (add_days, cint, date_diff, flt, get_link_to_form,
						  getdate)
from hrms.payroll.doctype.employee_benefit_application.employee_benefit_application import \
	get_benefit_component_amount
from hrms.payroll.doctype.employee_benefit_claim.employee_benefit_claim import \
	get_benefit_claim_amount
from hrms.payroll.doctype.payroll_period.payroll_period import (
	get_payroll_period, get_period_factor)
from frappe.query_builder.functions import Count, Sum
from hrms.payroll.doctype.salary_slip.salary_slip import (
	SalarySlip, calculate_tax_by_tax_slab, get_salary_component_data, rounded)
from kartoza.custom_py.payroll_entry import (get_current_block_period,
											 get_employee_frequency_map,
											 is_payroll_processed)


class CustomSalarySlip(SalarySlip):
	def validate(self):
		super().validate()
		frequency = get_current_block_period(self)
		employee_frequency = get_employee_frequency_map()
		if self.employee in employee_frequency and is_payroll_processed(self.employee, frequency[employee_frequency[self.employee]]):
			frappe.throw(" Salary Slip already created for current {0}".format(employee_frequency[self.employee]))
		self.validate_component_account()

	def validate_component_account(self):
		for component_type in ["earnings", "deductions"]:
			for row in self.get(component_type):
				if not frappe.db.get_value("Salary Component Account", {"parent": row.salary_component, "company": self.company}, "account"):
					frappe.throw(
						_("Please set account in Salary Component {0}").format(
							get_link_to_form("Salary Component", row.salary_component)
						)
					)

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

		self._component_based_variable_tax = {}
		for d in tax_components:
			self._component_based_variable_tax.setdefault(d, {})
			tax_amount = self.calculate_variable_based_on_taxable_salary(d)
			tax_row = get_salary_component_data(d)
			self.update_component_row(tax_row, tax_amount, "deductions")

	def get_tax_rebate(self):
		tax_rebate = 0
		dob = frappe.db.get_value("Employee", self.employee, "date_of_birth")
		if dob:
			tax_rebate = get_tax_rebate(self, dob)

		return tax_rebate

	def get_medical_aid(self):
		medical_aid = 0
		dependant = frappe.db.get_value("Employee Private Benefit", {"effective_from":["<=", self.start_date],"disable":0, "employee":self.employee}, 'medical_aid_dependant')
		if dependant:
			medical_aid = get_medical_aid(self, dependant)
		return medical_aid



	def calculate_net_pay(self):
		# self.payroll_period = frappe.db.get_value('Payroll Period', {"start_date": ("<=", self.start_date),
		# "end_date": (">=", self.end_date), "company": self.company })

		# self.payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)

		super().calculate_net_pay()

		# if self.payroll_period:
		# 	self.payroll_period_ = self.payroll_period.name
		# 	self.remaining_sub_periods = get_remaining_sub_periods(
		# 		self.employee, self.start_date, self.end_date, self.payroll_frequency, self.payroll_period
		# 	)
		current_eti_amount = get_eti_deduction(self) or 0


		amount_before_eti_deduction=0
		# amount_after_eti_deduction=0

		tax_amount = self.tax_value or 0
		amount_before_eti_deduction = tax_amount
		tax_amount -= current_eti_amount
		# amount_after_eti_deduction = current_eti_amount - amount_before_eti_deduction

		self.custom_monthly_eti = current_eti_amount
		# self.custom_carry_forwarding_eti_amount = amount_after_eti_deduction if amount_after_eti_deduction > 0 else 0

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


		# self.set_loan_repayment()
		# self.set_precision_for_component_amounts()
		# self.set_net_pay()
		# self.compute_income_tax_breakup()


	def calculate_variable_tax(self, tax_component):
		self.previous_total_paid_taxes = self.get_tax_paid_in_period(
			self.payroll_period.start_date, self.start_date, tax_component
		)

		tax_rebate = self.get_tax_rebate()
		medical_aid = self.get_medical_aid()
		self.tax_rebate = tax_rebate
		self.medical_aid = medical_aid
		total_months = frappe.utils.month_diff(self.payroll_period.end_date, self.payroll_period.start_date)


		# Structured tax amount
		eval_locals, default_data = self.get_data_for_eval()
		self.total_structured_tax_amount = calculate_tax_by_tax_slab(
			self.total_taxable_earnings_without_full_tax_addl_components,
			self.tax_slab,
			self.whitelisted_globals,
			eval_locals,
		)

		self.current_structured_tax_amount = (
			self.total_structured_tax_amount - self.previous_total_paid_taxes
		) / self.remaining_sub_periods
		self.tax_value = self.current_structured_tax_amount

		# Total taxable earnings with additional earnings with full tax
		self.full_tax_on_additional_earnings = 0.0
		if self.current_additional_earnings_with_full_tax:
			self.total_tax_amount = calculate_tax_by_tax_slab(
				self.total_taxable_earnings, self.tax_slab, self.whitelisted_globals, eval_locals
			)
			self.full_tax_on_additional_earnings = self.total_tax_amount - self.total_structured_tax_amount

		self.total_structured_tax_amount = self.total_structured_tax_amount - (medical_aid * total_months + tax_rebate * total_months)

		self.current_structured_tax_amount = (
			self.total_structured_tax_amount - self.previous_total_paid_taxes
		) / self.remaining_sub_periods

		current_tax_amount = self.current_structured_tax_amount + self.full_tax_on_additional_earnings
		if flt(current_tax_amount) < 0:
			current_tax_amount = 0

		self._component_based_variable_tax[tax_component].update(
			{
				"previous_total_paid_taxes": self.previous_total_paid_taxes,
				"total_structured_tax_amount": self.total_structured_tax_amount,
				"current_structured_tax_amount": self.current_structured_tax_amount,
				"full_tax_on_additional_earnings": self.full_tax_on_additional_earnings,
				"current_tax_amount": current_tax_amount,
			}
		)
		return current_tax_amount

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
		for i in self.earnings:
			tax = 0
			reduce, percent = frappe.db.get_value("Salary Component", i.salary_component, ["reduce_on_taxable_earning", "taxable_earning_reduce_percentage"])
			if reduce:
				tax += i.amount - (i.amount * percent / 100)
			if i.is_flexible_benefit:
				taxable_income.flexi_benefits -= tax
			else:
				taxable_income.taxable_earnings -= tax

		ra = get_retirement_annuity(self)
		if ra:
			ra_percent = ra.ra_amount / taxable_income.taxable_earnings * 100
			if ra_percent > ra.limit_percent:
				ra_percent = ra.limit_percent
			ra_amount = ra_percent * taxable_income.taxable_earnings / 100
			self.retirement_annuity = ra_amount
			taxable_income.taxable_earnings -= ra_amount

		# taxable_income.taxable_earnings += taxable_income.flexi_benefits
		taxable_income.flexi_benefits = 0
		self.taxable_value = taxable_income.taxable_earnings
		return taxable_income

	def get_working_days_details(
		self, joining_date=None, relieving_date=None, lwp=None, for_preview=0
	):
		payroll_based_on = frappe.db.get_value("Payroll Settings", None, "payroll_based_on")
		include_holidays_in_total_working_days = frappe.db.get_single_value(
			"Payroll Settings", "include_holidays_in_total_working_days"
		)

		if not (joining_date and relieving_date):
			joining_date, relieving_date = self.get_joining_and_relieving_dates()

		# if self.payroll_period:
			# payroll_period=frappe.db.get_value("Payroll Period",self.payroll_period,['start_date','end_date'],as_dict=True)
		if type(self.start_date) == str:
			self.start_date = datetime.strptime(self.start_date,"%Y-%m-%d").date()
		if type(self.end_date) == str:
			self.end_date = datetime.strptime(self.end_date,"%Y-%m-%d").date()
		start_date = self.start_date.replace(month=1).replace(day=1)
		end_date = self.end_date.replace(month=12).replace(day=31)
		total_no_days=get_total_days(start_date, end_date+timedelta(days=1))
		total_no_weekend_days=get_total_weekend_days(start_date, end_date)
		working_days=(total_no_days-total_no_weekend_days)/12
		# else:
		# 	working_days = date_diff(self.end_date, self.start_date) + 1
		working_days_list = [add_days(self.start_date, i) for i in range(math.ceil(working_days))]

		if for_preview:
			self.total_working_days = working_days
			self.payment_days = working_days
			return

		holidays = self.get_holidays_for_employee(self.start_date, self.end_date)

		if not cint(include_holidays_in_total_working_days):
			# working_days_list = [i for i in working_days_list if i not in holidays]

			# working_days -= len(holidays)
			if working_days < 0:
				frappe.throw(_("There are more holidays than working days this month."))

		if not payroll_based_on:
			frappe.throw(_("Please set Payroll based on in Payroll settings"))

		if payroll_based_on == "Attendance":
			actual_lwp, absent = self.calculate_lwp_ppl_and_absent_days_based_on_attendance(
				holidays, relieving_date
			)
			self.absent_days = absent
		else:
			actual_lwp = self.calculate_lwp_or_ppl_based_on_leave_application(
				holidays, working_days_list, relieving_date
			)

		if not lwp:
			lwp = actual_lwp
		elif lwp != actual_lwp:
			frappe.msgprint(
				_("Leave Without Pay does not match with approved {} records").format(payroll_based_on)
			)

		self.leave_without_pay = lwp
		self.total_working_days = working_days

		payment_days = self.get_payment_days(
			joining_date, relieving_date, include_holidays_in_total_working_days
		)

		if flt(payment_days) > flt(lwp):
			self.payment_days = flt(payment_days) - flt(lwp)

			if payroll_based_on == "Attendance":
				self.payment_days -= flt(absent)

			consider_unmarked_attendance_as = (
				frappe.db.get_value("Payroll Settings", None, "consider_unmarked_attendance_as") or "Present"
			)

			if payroll_based_on == "Attendance" and consider_unmarked_attendance_as == "Absent":
				unmarked_days = self.get_unmarked_days(include_holidays_in_total_working_days)
				self.absent_days += unmarked_days  # will be treated as absent
				self.payment_days -= unmarked_days
			if payment_days>working_days:
				self.payment_days=working_days

			if self.payment_days < 0:
				self.payment_days = 0
		else:
			self.payment_days = 0

	def get_taxable_earnings_for_prev_period(self, start_date, end_date, allow_tax_exemption=False):
		exempted_amount = 0
		taxable_earnings = self.get_salary_slip_details(
			start_date, end_date, parentfield="earnings", is_tax_applicable=1
		)

		ss = frappe.qb.DocType("Salary Slip")
		sd = frappe.qb.DocType("Salary Detail")
		sc = frappe.qb.DocType("Salary Component")

		partial_taxable_earnings = 0
		query = (
			frappe.qb.from_(ss)
			.join(sd)
			.on(sd.parent == ss.name)
			.join(sc)
			.on(sd.salary_component == sc.name)
			.select(Sum(sd.amount - (sd.amount * sc.taxable_earning_reduce_percentage / 100)))
			.where(sd.parentfield == 'earnings')
			.where(sd.is_flexible_benefit == 0)
			.where(ss.docstatus == 1)
			.where(ss.employee == self.employee)
			.where(sc.reduce_on_taxable_earning == 1)
			.where(ss.start_date.between(start_date, end_date))
			.where(ss.end_date.between(start_date, end_date))
		).run()
		if query:
			partial_taxable_earnings = query[0][0] or 0

		taxable_earnings -= partial_taxable_earnings

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

	def get_amount_based_on_payment_days(self, row, joining_date, relieving_date):
		amount, additional_amount = row.amount, row.additional_amount
		timesheet_component = frappe.db.get_value(
			"Salary Structure", self.salary_structure, "salary_component"
		)

		if (
			self.salary_structure
			and cint(row.depends_on_payment_days)
			and flt(self.total_working_days)
			and not (
				row.additional_salary and row.default_amount
			)  # to identify overwritten additional salary
			and (
				row.salary_component != timesheet_component
				or getdate(self.start_date) < joining_date
				or (relieving_date and getdate(self.end_date) > relieving_date)
			)
		):
			additional_amount = flt(
				(flt(row.additional_amount) * flt(self.payment_days) / flt(self.total_working_days)),
				row.precision("additional_amount"),
			)
			amount = (
				flt(
					(flt(row.default_amount) * flt(self.payment_days) / flt(self.total_working_days)),
					row.precision("amount"),
				)
				+ additional_amount
			)

		elif (
			not self.payment_days
			and row.salary_component != timesheet_component
			and cint(row.depends_on_payment_days)
		):
			amount, additional_amount = 0, 0
		elif not row.amount:
			amount = flt(row.default_amount) + flt(row.additional_amount)

		# apply rounding
		if frappe.get_cached_value(
			"Salary Component", row.salary_component, "round_to_the_nearest_integer"
		):
			amount, additional_amount = rounded(amount or 0), rounded(additional_amount or 0)

		return amount, additional_amount

	def on_submit(self):
		super().on_submit()

		if self.custom_monthly_eti:
			eti_log=frappe.new_doc("Employee ETI Log")
			eti_log.employee=self.employee
			eti_log.date=self.posting_date
			eti_log.eti_amount=self.custom_monthly_eti
			eti_log.carry_forwarding_eti_amount=self.custom_carry_forwarding_eti_amount
			eti_log.against_salary_slip=self.name
			eti_log.insert()
			eti_log.submit()

	def on_cancel(self):
		eti_logs = frappe.db.sql_list("""select name from `tabEmployee ETI Log` where against_salary_slip=%s """, (self.name))
		for log in eti_logs:
			doc = frappe.get_doc("Employee ETI Log", log)
			doc.cancel()


		frappe.delete_doc(
			"Employee ETI Log",
			eti_logs,
		)

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

def get_eti_deduction(self):
	current_eti_amount=0
	employee_details = frappe.db.get_value("Employee",{
							"name" : self.employee
						},['date_of_joining','date_of_birth', 'hours_per_month'],as_dict=True) or {}


	age = calculate_age(employee_details.get("date_of_birth"))
	eti_details=frappe.db.get_value("ETI Slab",{"start_date" : ['<=',(self.posting_date)],"docstatus":1},["minimum_age","maximum_age","name", "hours_in_a_month"],as_dict=True)


	taxable_eti_amount=0
	if eti_details and eti_details.get('minimum_age') <= age and eti_details.get('maximum_age') >= age:

		prev_eti = frappe.get_all("Employee ETI Log",{"employee": self.employee},pluck="name")
		prev_eti_count = len(prev_eti)
		if prev_eti_count < 24:
			eligible_components={}
			eti_eligible_components = frappe.get_all("Salary Component",{"custom_allow_for_eti": 1},["name","taxable_earning_reduce_percentage","reduce_on_taxable_earning"])
			for eti_component in eti_eligible_components:
				eligible_components[eti_component.get('name')] = {
												"taxable_earning_reduce_percentage":eti_component.get('taxable_earning_reduce_percentage'),
												"reduce_on_taxable_earning" : eti_component.get('reduce_on_taxable_earning')
											}
			for earning in self.earnings:
				if earning.salary_component in eligible_components.keys():

					if float(eligible_components.get(earning.salary_component,{}).get('taxable_earning_reduce_percentage')) > 0 and eligible_components.get(earning.salary_component,{}).get('reduce_on_taxable_earning'):
						taxable_eti_amount += (float(eligible_components.get(earning.salary_component,{}).get('taxable_earning_reduce_percentage'))/100)*earning.amount
					else:
						taxable_eti_amount += earning.amount
			formula_field = "first_qualifying_12_months" if prev_eti_count <= 11 else "second_qualifying_12_months"
			if taxable_eti_amount:

				formula=frappe.db.get_value("ETI Slab Details",{
							"parent" : eti_details.get('name'),
							"from_amount" : ["<=",taxable_eti_amount],
							"to_amount" : [">=",taxable_eti_amount]
						},formula_field)

				if formula:

					if not employee_details.hours_per_month:
						frappe.throw("Set <b>Hours Per Month</b> for the Employee: {0}".format(self.employee))

					if eti_details.hours_in_a_month < employee_details.hours_per_month:
						employee_details.hours_per_month = eti_details.hours_in_a_month

					self.data, self.default_data = self.get_data_for_eval()
					self.data.monthly_remuneration = taxable_eti_amount
					current_eti_amount = frappe.safe_eval(formula, self.data) or 0
					current_eti_amount = current_eti_amount / eti_details.hours_in_a_month * employee_details.hours_per_month
					prev_eti_balance_details = frappe.db.sql("""
											SELECT carry_forwarding_eti_amount
												FROM `tabEmployee ETI Log`
											WHERE
												employee = '{0}' AND
												docstatus = 1 AND
												date <= '{1}'
											ORDER BY
												date DESC
											LIMIT 1
										""".format(self.employee, self.posting_date),as_dict=True)
					if prev_eti_balance_details and prev_eti_balance_details[0].get('carry_forwarding_eti_amount'):
						current_eti_amount+=prev_eti_balance_details[0].get('carry_forwarding_eti_amount')
	return current_eti_amount

def calculate_age(date_of_birth):
	dob = datetime.strptime(str(date_of_birth), '%Y-%m-%d')
	current_date = datetime.now()
	age = current_date.year - dob.year
	# Adjust age if the birthday hasn't occurred yet this year
	if current_date.month < dob.month or (current_date.month == dob.month and current_date.day < dob.day):
		age -= 1
	return age

def get_total_days(year_start,year_end):
	year_start = year_start
	year_end = year_end
	total_days = (year_end - year_start).days
	return total_days

# Get total no of weekend days(SATURDAY,SUNDAY) in a given period
def get_total_weekend_days(year_start,year_end):
	year_start = year_start
	year_end = year_end
	delta = timedelta(days=1)

	weekend = 0

	while year_start <= year_end:
		if year_start.weekday() in [calendar.SATURDAY,calendar.SUNDAY]:
			weekend += 1
		year_start += delta

	return weekend


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
