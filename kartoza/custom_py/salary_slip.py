import calendar
import math
from datetime import date, datetime, timedelta

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Sum
from frappe.utils import (
	add_days,
	cint,
	date_diff,
	flt,
	get_link_to_form,
	getdate,
	month_diff,
	fmt_money,
)
from hrms.payroll.doctype.employee_benefit_application.employee_benefit_application import (
	get_benefit_component_amount,
)
from hrms.payroll.doctype.employee_benefit_claim.employee_benefit_claim import (
	get_benefit_claim_amount,
)
from hrms.payroll.doctype.payroll_period.payroll_period import (
	get_payroll_period,
	get_period_factor,
)
from hrms.payroll.doctype.salary_slip.salary_slip import (
	SalarySlip,
	calculate_tax_by_tax_slab,
	get_salary_component_data,
	rounded,
)
from hrms.payroll.doctype.salary_slip.salary_slip_loan_utils import (
	cancel_loan_repayment_entry,
	make_loan_repayment_entry,
	process_loan_interest_accrual_and_demand,
	set_loan_repayment,
)
from kartoza.custom_py.payroll_entry import (
	get_current_block_period,
	get_employee_frequency_map,
	is_payroll_processed,
)


class CustomSalarySlip(SalarySlip):
	"""
	Extension of the standard SalarySlip class to implement South African payroll requirements.
	
	This class handles South Africa-specific calculations including:
	- Tax calculation with rebates and medical aid credits
	- Employment Tax Incentive (ETI) processing
	- South African working days calculation
	- Retirement annuity deductions
	- Annual bonus handling
	"""
	
	def validate(self):
		"""
		Extends the standard validation to include South Africa-specific validations:
		- Prevents duplicate salary slips for the same payroll period
		- Validates that all salary components have associated accounts
		"""
		super().validate()
		frequency = get_current_block_period(self)
		employee_frequency = get_employee_frequency_map()
		if self.employee in employee_frequency and is_payroll_processed(
			self.employee, frequency[employee_frequency[self.employee]]
		):
			frappe.throw(
				_("Salary Slip already created for current {0}").format(
					employee_frequency[self.employee]
				)
			)
		self.validate_component_account()

	def validate_component_account(self):
		"""
		Ensures all salary components have associated GL accounts.
		This is critical for accurate financial reporting and compliance with 
		South African accounting requirements.
		
		Raises:
			frappe.ValidationError: If any salary component is missing an account
		"""
		for component_type in ["earnings", "deductions"]:
			for row in self.get(component_type):
				if not frappe.db.get_value(
					"Salary Component Account",
					{"parent": row.salary_component, "company": self.company},
					"account",
				):
					frappe.throw(
						_("Please set account in Salary Component {0}. All components must have associated accounts for South African payroll compliance.").format(
							get_link_to_form("Salary Component", row.salary_component)
						)
					)

	def add_tax_components(self):
		# Calculate variable_based_on_taxable_salary after all components updated in salary slip
		tax_components, self.other_deduction_components = [], []
		for d in self._salary_structure_doc.get("deductions"):
			if (
				d.variable_based_on_taxable_salary == 1
				and not d.formula
				and not flt(d.amount)
			):
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

	def compute_taxable_earnings_for_year(self):
		super().compute_taxable_earnings_for_year()

		self.annual_bonus = self.get_bonus_amount()

		self.total_taxable_earnings += self.annual_bonus

		self.total_taxable_earnings_without_full_tax_addl_components = (
			self.total_taxable_earnings - self.current_additional_earnings_with_full_tax
		)

	def get_bonus_amount(self):
		annual_bonus = frappe.db.get_value(
			"Salary Structure Assignment",
			{
				"employee": self.employee,
				"salary_structure": self.salary_structure,
				"docstatus": 1,
				"from_date": ("<=", self.end_date),
			},
			"custom_annual_bonus",
			order_by="from_date desc",
		) or 0

		if not annual_bonus:
			return annual_bonus

		bonus_component = frappe.db.get_all("Salary Component", {"disabled": False, "custom_is_annual_bonus": True})

		if not bonus_component:
			return annual_bonus

		bonus_component = [i.name for i in bonus_component]

		is_bonus_created = frappe.db.get_value(
			"Additional Salary",
				{
					"docstatus": 1,
					"employee": self.employee,
					"salary_component":["in", bonus_component],
					"company": self.company,
					"payroll_date": ["between", [self.payroll_period.start_date, self.end_date]]
				}
			)
		return annual_bonus if not is_bonus_created else 0




	def get_tax_rebate(self):
		tax_rebate = 0
		dob = frappe.db.get_value("Employee", self.employee, "date_of_birth")
		if dob:
			tax_rebate = get_tax_rebate(self, dob)

		return tax_rebate

	def get_medical_aid(self):
		medical_aid = 0
		dependant = frappe.db.get_value(
			"Employee Private Benefit",
			{
				"effective_from": ["<=", self.start_date],
				"disable": 0,
				"employee": self.employee,
			},
			"medical_aid_dependant",
		)
		if dependant:
			medical_aid = get_medical_aid(self, dependant)
		return medical_aid

	def calculate_component_amounts(self, component_type):
		if not getattr(self, "_salary_structure_doc", None):
			self.set_salary_structure_doc()

		self.add_structure_components(component_type)
		self.add_additional_salary_components(component_type)

		if component_type == "earnings":
			self.add_employee_benefits()
		else:
			self.add_tax_components()

	def add_additional_salary_components(self, component_type):
		additional_salaries = get_additional_salaries(
			self.employee, self.start_date, self.end_date, component_type
		)

		for additional_salary in additional_salaries:
			self.update_component_row(
				get_salary_component_data(additional_salary.component),
				additional_salary.amount,
				component_type,
				additional_salary,
				is_recurring=additional_salary.is_recurring,
			)

	def calculate_net_pay(self, skip_tax_breakup_computation: bool = False):
		def set_gross_pay_and_base_gross_pay():
			self.gross_pay = self.get_component_totals("earnings", depends_on_payment_days=1)
			self.base_gross_pay = flt(
				flt(self.gross_pay) * flt(self.exchange_rate), self.precision("base_gross_pay")
			)

		# self.payroll_period = frappe.db.get_value('Payroll Period', {"start_date": ("<=", self.start_date),
		# "end_date": (">=", self.end_date), "company": self.company })

		# self.payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)

		if self.salary_structure:
			self.calculate_component_amounts("earnings")

		# get remaining numbers of sub-period (period for which one salary is processed)
		if self.payroll_period:
			# self.payroll_period_ = self.payroll_period.name
			self.remaining_sub_periods = get_period_factor(
				self.employee,
				self.start_date,
				self.end_date,
				self.payroll_frequency,
				self.payroll_period,
				joining_date=self.joining_date,
				relieving_date=self.relieving_date,
			)[1]

		set_gross_pay_and_base_gross_pay()

		if self.salary_structure:
			self.calculate_component_amounts("deductions")

		set_loan_repayment()

		self.set_precision_for_component_amounts()
		self.set_net_pay()
		if not skip_tax_breakup_computation:
			self.compute_income_tax_breakup()

		current_eti_amount = get_eti_deduction(self) or 0

		# amount_before_eti_deduction = 0
		# amount_after_eti_deduction=0

		tax_amount = self.tax_value or 0
		# amount_before_eti_deduction = tax_amount
		tax_amount -= current_eti_amount
		# amount_after_eti_deduction = current_eti_amount - amount_before_eti_deduction

		self.custom_monthly_eti = current_eti_amount
		# self.custom_carry_forwarding_eti_amount = amount_after_eti_deduction if amount_after_eti_deduction > 0 else 0

		salary_structure_doc = frappe.get_doc("Salary Structure", self.salary_structure)

		self.company_contribution = []
		additional_contribution = get_additional_salaries(self.employee, self.start_date, self.end_date, "company_contributions")
		company_contribution_dict = {}
		data = self.get_data_for_eval()

		if isinstance(data, tuple):
			data = data[0]

		for component in salary_structure_doc.company_contribution:
			component.name = None
			component.amount = self.eval_condition_and_formula(component, data)
			if component.amount <= 0:
				continue
			self.append("company_contribution", component)
			company_contribution_dict[component.salary_component] = len(self.company_contribution) - 1

		for contribution in additional_contribution:
			if contribution.component in company_contribution_dict and contribution.overwrite:
				self.company_contribution[company_contribution_dict[contribution.component]].amount = contribution.amount
			else:
				self.append("company_contribution", {
					"salary_component": contribution.component,
					"amount": contribution.amount
				})

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
		total_months = frappe.utils.month_diff(
			self.payroll_period.end_date, self.payroll_period.start_date
		)

		# Structured tax amount
		eval_locals, default_data = self.get_data_for_eval()
		self.total_structured_tax_amount, __ = calculate_tax_by_tax_slab(
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
			self.total_tax_amount, __ = calculate_tax_by_tax_slab(
				self.total_taxable_earnings,
				self.tax_slab,
				self.whitelisted_globals,
				eval_locals,
			)
			self.full_tax_on_additional_earnings = (
				self.total_tax_amount - self.total_structured_tax_amount
			)

		self.total_structured_tax_amount = self.total_structured_tax_amount - (
			medical_aid * total_months + tax_rebate * total_months
		)

		self.current_structured_tax_amount = (
			self.total_structured_tax_amount - self.previous_total_paid_taxes
		) / self.remaining_sub_periods

		current_tax_amount = (
			self.current_structured_tax_amount + self.full_tax_on_additional_earnings
		)
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
				if (
					frappe.db.get_value(
						"Salary Component",
						struct_row.salary_component,
						"pay_against_benefit_claim",
					)
					!= 1
				):
					benefit_component_amount = get_benefit_component_amount(
						self.employee,
						self.start_date,
						self.end_date,
						struct_row.salary_component,
						self._salary_structure_doc,
						self.payroll_frequency,
						self.payroll_period,
					)
					if benefit_component_amount:
						self.update_component_row(
							struct_row, benefit_component_amount, "earnings"
						)
				else:
					benefit_claim_amount = get_benefit_claim_amount(
						self.employee,
						self.start_date,
						self.end_date,
						struct_row.salary_component,
					)
					if benefit_claim_amount:
						self.update_component_row(
							struct_row, benefit_claim_amount, "earnings"
						)

	def get_taxable_earnings(self, allow_tax_exemption=False, based_on_payment_days=0):
		taxable_income = super().get_taxable_earnings(
			allow_tax_exemption, based_on_payment_days
		)
		for i in self.earnings:
			tax = 0
			reduce, percent = frappe.db.get_value(
				"Salary Component",
				i.salary_component,
				["reduce_on_taxable_earning", "taxable_earning_reduce_percentage"],
			)
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
		if based_on_payment_days:
			self.taxable_value = (
				taxable_income.taxable_earnings + taxable_income.additional_income
			)
		return taxable_income

	def get_working_days_details(
		self, lwp=None, for_preview=0
	):
		payroll_settings = frappe.get_cached_value(
			"Payroll Settings",
			None,
			(
				"payroll_based_on",
				"include_holidays_in_total_working_days",
				"consider_marked_attendance_on_holidays",
				"daily_wages_fraction_for_half_day",
				"consider_unmarked_attendance_as",
			),
			as_dict=1,
		)

		consider_marked_attendance_on_holidays = (
			payroll_settings.include_holidays_in_total_working_days
			and payroll_settings.consider_marked_attendance_on_holidays
		)

		daily_wages_fraction_for_half_day = flt(payroll_settings.daily_wages_fraction_for_half_day) or 0.5

		if not self.start_date or not self.end_date:
			self.get_date_details()

		if isinstance(self.start_date, str):
			self.start_date = datetime.strptime(self.start_date, "%Y-%m-%d").date()
		if isinstance(self.end_date, str):
			self.end_date = datetime.strptime(self.end_date, "%Y-%m-%d").date()

		# working_days = date_diff(self.end_date, self.start_date) + 1
		start_date = self.start_date.replace(month=1).replace(day=1)
		end_date = self.end_date.replace(month=12).replace(day=31)
		total_no_days = get_total_days(start_date, end_date + timedelta(days=1))
		total_no_weekend_days = get_total_weekend_days(start_date, end_date)
		working_days = (total_no_days - total_no_weekend_days) / 12

		working_days_list = [
			add_days(self.start_date, i) for i in range(math.ceil(working_days))
		]

		if for_preview:
			self.total_working_days = working_days
			self.payment_days = working_days
			return

		holidays = self.get_holidays_for_employee(self.start_date, self.end_date)

		if not cint(payroll_settings.include_holidays_in_total_working_days):
			# working_days_list = [i for i in working_days_list if i not in holidays]

			# working_days -= len(holidays)
			if working_days < 0:
				frappe.throw(_("There are more holidays than working days this month."))

		if not payroll_settings.payroll_based_on:
			frappe.throw(_("Please set Payroll based on in Payroll settings"))

		if payroll_settings.payroll_based_on == "Attendance":
			actual_lwp, absent = self.calculate_lwp_ppl_and_absent_days_based_on_attendance(
				holidays, daily_wages_fraction_for_half_day, consider_marked_attendance_on_holidays
			)
			self.absent_days = absent
		else:
			actual_lwp = self.calculate_lwp_or_ppl_based_on_leave_application(
				holidays, working_days_list, daily_wages_fraction_for_half_day
			)

		if not lwp:
			lwp = actual_lwp
		elif lwp != actual_lwp:
			frappe.msgprint(
				_("Leave Without Pay does not match with approved {} records").format(
					payroll_settings.payroll_based_on
				)
			)

		self.leave_without_pay = lwp
		self.total_working_days = working_days

		payment_days = self.get_payment_days(payroll_settings.include_holidays_in_total_working_days)

		if flt(payment_days) > flt(lwp):
			self.payment_days = flt(payment_days) - flt(lwp)

			if payroll_settings.payroll_based_on == "Attendance":
				self.payment_days -= flt(absent)

			consider_unmarked_attendance_as = payroll_settings.consider_unmarked_attendance_as or "Present"

			if (
				payroll_settings.payroll_based_on == "Attendance"
				and consider_unmarked_attendance_as == "Absent"
			):
				unmarked_days = self.get_unmarked_days(
					payroll_settings.include_holidays_in_total_working_days, holidays
				)
				self.absent_days += unmarked_days  # will be treated as absent
				self.payment_days -= unmarked_days
			if payment_days > working_days:
				self.payment_days = working_days

			if self.payment_days < 0:
				self.payment_days = 0
		else:
			self.payment_days = 0

	def get_taxable_earnings_for_prev_period(
		self, start_date, end_date, allow_tax_exemption=False
	):
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
			.select(
				Sum(
					sd.amount - (sd.amount * sc.taxable_earning_reduce_percentage / 100)
				)
			)
			.where(sd.parentfield == "earnings")
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
				start_date,
				end_date,
				parentfield="deductions",
				exempted_from_income_tax=1,
			)

		opening_taxable_earning = self.get_opening_for(
			"taxable_earnings_till_date", start_date, end_date
		)

		ra = frappe.db.sql(
			"""
				select
					sum(retirement_annuity)
				from
					`tabSalary Slip`
				where
					docstatus=1
					and employee=%(employee)s
					and start_date between %(from_date)s and %(to_date)s
					and end_date between %(from_date)s and %(to_date)s
				""",
			{
				"employee": self.employee,
				"from_date": str(start_date),
				"to_date": str(end_date),
			},
		)
		ra = flt(ra[0][0]) if ra else 0

		return (
			taxable_earnings + opening_taxable_earning
		) - exempted_amount - ra, exempted_amount

	def get_amount_based_on_payment_days(self, row):
		# use flt for rounding the total_working_days as it calculated based on year
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
				or getdate(self.start_date) < self.joining_date
				or (self.relieving_date and getdate(self.end_date) > self.relieving_date)
			)
		):
			additional_amount = flt(
				(
					flt(row.additional_amount)
					* flt(self.payment_days)
					/ flt(self.total_working_days)
				),
				row.precision("additional_amount"),
			)
			amount = (
				flt(
					(
						flt(row.default_amount)
						* flt(self.payment_days)
						/ flt(self.total_working_days)
					),
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
			amount, additional_amount = rounded(amount or 0), rounded(
					additional_amount or 0
			)

		return amount, additional_amount


	def on_submit(self):
		super().on_submit()

		if self.custom_monthly_eti:
			eti_log = frappe.new_doc("Employee ETI Log")
			eti_log.employee = self.employee
			eti_log.date = self.posting_date
			eti_log.eti_amount = self.custom_monthly_eti
			eti_log.carry_forwarding_eti_amount = (
				self.custom_carry_forwarding_eti_amount
			)
			eti_log.against_salary_slip = self.name
			eti_log.insert()
			eti_log.submit()

	def on_cancel(self):
		eti_logs = frappe.db.sql_list(
			"""select name from `tabEmployee ETI Log` where against_salary_slip=%s """,
			(self.name),
		)
		for log in eti_logs:
			doc = frappe.get_doc("Employee ETI Log", log)
			doc.cancel()

		frappe.delete_doc(
			"Employee ETI Log",
			eti_logs,
		)


def get_retirement_annuity(self):
	"""
	Calculate retirement annuity deduction for the employee.
	
	Retrieves the employee's private retirement annuity benefit configuration
	and calculates the monthly deduction amount based on South African tax rules.
	
	The function enforces maximum amount limits, ensuring compliance with 
	South African tax regulations for retirement annuity deductions.
	
	Returns:
		frappe._dict: Dictionary containing retirement annuity details:
			- limit_percent: Maximum percentage of income allowed for RA deduction
			- ra_amount: Monthly RA amount to be deducted
	"""
	# Get the most recent applicable retirement annuity benefit record
	try:
		# Query for the employee's applicable private benefit
		ra = frappe.db.get_value(
			"Employee Private Benefit",
			{
				"effective_from": ["<=", self.start_date],
				"disable": 0,
				"employee": self.employee,
			},
			order_by="effective_from desc",  # Get the most recent applicable record
		)
		
		res = frappe._dict({})
		
		# Get private medical aid information in the same query to reduce DB calls
		self.private_medical_aid = (
			frappe.db.get_value(
				"Employee Private Benefit",
				{
					"effective_from": ["<=", self.start_date],
					"disable": 0,
					"employee": self.employee,
				},
				"private_medical_aid",
			)
			or 0
		)
		
		if ra:
			# Get the full document to access all fields
			ra_doc = frappe.get_doc("Employee Private Benefit", ra)
			
			# Set the maximum percentage limit
			if hasattr(ra_doc, 'maximum_'):
				res["limit_percent"] = flt(ra_doc.maximum_)
			else:
				frappe.msgprint(
					_("Maximum percentage limit not set for Retirement Annuity benefit for employee {0}").format(
						self.employee_name or self.employee
					),
					indicator="orange",
					alert=True
				)
				res["limit_percent"] = 0
			
			# Set the monthly RA amount, respecting the maximum monthly amount
			if hasattr(ra_doc, 'annuity_amount'):
				res["ra_amount"] = flt(ra_doc.annuity_amount)
				
				# Apply monthly maximum if specified
				if hasattr(ra_doc, 'maximum_amount') and ra_doc.maximum_amount:
					monthly_max = flt(ra_doc.maximum_amount) / 12
					if monthly_max < res["ra_amount"]:
						res["ra_amount"] = monthly_max
						frappe.msgprint(
							_("Retirement Annuity amount capped at monthly maximum of {0} for employee {1}").format(
								frappe.bold(fmt_money(monthly_max, currency=self.currency)),
								self.employee_name or self.employee
							),
							indicator="blue",
							alert=True
						)
			else:
				res["ra_amount"] = 0
		
		return res
	
	except Exception as e:
		frappe.log_error(
			_("Error in Retirement Annuity calculation: {0} for employee {1}").format(str(e), self.employee),
			"Retirement Annuity Calculation Error"
		)
		frappe.msgprint(
			_("Error in Retirement Annuity calculation. Using zero amount."),
			indicator="red",
			alert=True
		)
		return frappe._dict({"limit_percent": 0, "ra_amount": 0})


def get_medical_aid(self, dependant):
	name = frappe.db.get_value(
		"Medical Tax Credit Rate", {"payroll_period": self.payroll_period.name}
	)
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
	"""
	Calculate Employment Tax Incentive (ETI) deduction according to South African tax law.
	
	The ETI is a South African tax incentive aimed at encouraging employers to hire
	young job seekers. It reduces the cost of hiring young people by allowing employers
	to claim a portion of the PAYE (Pay As You Earn) tax for qualifying employees.
	
	Eligibility criteria:
	1. Employee must be between 18-29 years old (as defined in eti_details)
	2. Employee must have been employed on or after October 1, 2013
	3. Employee's remuneration must be within qualifying thresholds
	4. ETI can only be claimed for the first 24 months of employment
	
	Calculation factors:
	- Monthly remuneration amount
	- Whether in first or second 12-month period of employment
	- Hours worked in the month (proportional calculation)
	- Any carry-forward amounts from previous months
	
	Returns:
		float: The calculated ETI amount for the current month
	"""
	try:
		current_eti_amount = 0
		
		# Get employee details needed for ETI calculation
		employee_details = (
			frappe.db.get_value(
				"Employee",
				{"name": self.employee},
				["date_of_joining", "date_of_birth", "custom_hours_per_month"],
				as_dict=True,
			)
			or {}
		)

		# Validate required employee data
		if not employee_details.get("date_of_birth"):
			frappe.msgprint(
				_("Employee {0} does not have date of birth. ETI calculation skipped.").format(self.employee),
				indicator="orange",
				alert=True
			)
			return 0
			
		if not employee_details.get("date_of_joining"):
			frappe.msgprint(
				_("Employee {0} does not have date of joining. ETI calculation skipped.").format(self.employee),
				indicator="orange",
				alert=True
			)
			return 0

		# Calculate employee's age
		age = calculate_age(employee_details.get("date_of_birth"))
		
		# Get ETI configuration details for the current period
		eti_details = frappe.db.get_value(
			"ETI Slab",
			{"start_date": ["<=", (self.posting_date)], "docstatus": 1},
			["minimum_age", "maximum_age", "name", "hours_in_a_month"],
			as_dict=True,
		)
		
		# Validate ETI configuration
		if not eti_details:
			frappe.msgprint(
				_("No valid ETI Slab found for date {0}. Please ensure ETI slabs are properly configured.").format(
					self.posting_date
				),
				indicator="red",
				alert=True
			)
			return 0

		taxable_eti_amount = 0
		
		# Verify employee meets age requirements
		if (
			eti_details
			and eti_details.get("minimum_age") <= age
			and eti_details.get("maximum_age") >= age
		):
			# Check if employee is within 24-month ETI eligibility period
			prev_eti = frappe.get_all(
				"Employee ETI Log", {"employee": self.employee}, pluck="name"
			)
			prev_eti_count = len(prev_eti)
			
			if prev_eti_count < 24:  # ETI can only be claimed for first 24 months
				# Get salary components eligible for ETI calculation
				eligible_components = {}
				eti_eligible_components = frappe.get_all(
					"Salary Component",
					{"custom_allow_for_eti": 1},
					[
						"name",
						"taxable_earning_reduce_percentage",
						"reduce_on_taxable_earning",
					],
				)
				
				# Check if any eligible components exist
				if not eti_eligible_components:
					frappe.msgprint(
						_("No salary components marked as eligible for ETI. ETI calculation skipped."),
						indicator="orange",
						alert=True
					)
					return 0
					
				# Create lookup dictionary for eligible components
				for eti_component in eti_eligible_components:
					eligible_components[eti_component.get("name")] = {
						"taxable_earning_reduce_percentage": eti_component.get(
							"taxable_earning_reduce_percentage"
						),
						"reduce_on_taxable_earning": eti_component.get(
							"reduce_on_taxable_earning"
						),
					}
				
				# Calculate total ETI-eligible remuneration amount
				for earning in self.earnings:
					if earning.salary_component in eligible_components.keys():
						# Apply special percentage reduction if applicable
						if float(
							eligible_components.get(earning.salary_component, {}).get(
								"taxable_earning_reduce_percentage", 0
							) or 0
						) > 0 and eligible_components.get(earning.salary_component, {}).get(
							"reduce_on_taxable_earning"
						):
							taxable_eti_amount += (
								float(
									eligible_components.get(
										earning.salary_component, {}
									).get("taxable_earning_reduce_percentage", 0) or 0
								)
								/ 100
							) * earning.amount
						else:
							taxable_eti_amount += earning.amount
				
				# Determine which formula to use based on employment period
				formula_field = (
					"first_qualifying_12_months"  # First 12 months of employment
					if prev_eti_count <= 11
					else "second_qualifying_12_months"  # Second 12 months of employment
				)
				
				if taxable_eti_amount:
					# Get the appropriate formula for the ETI calculation based on remuneration amount
					formula = frappe.db.get_value(
						"ETI Slab Details",
						{
							"parent": eti_details.get("name"),
							"from_amount": ["<=", taxable_eti_amount],
							"to_amount": [">=", taxable_eti_amount],
						},
						formula_field,
					)
					
					if not formula:
						frappe.msgprint(
							_("No applicable ETI formula found for remuneration amount {0}. ETI calculation skipped.").format(
								taxable_eti_amount
							),
							indicator="orange",
							alert=True
						)
						return 0

					if formula:
						# Ensure hours per month is set
						if not employee_details.custom_hours_per_month:
							frappe.throw(
								_("Hours Per Month not set for Employee: {0}. This is required for ETI calculation.").format(
									frappe.bold(self.employee_name or self.employee)
								)
							)

						# Cap hours to standard if employee works more than standard hours
						hours_per_month = flt(employee_details.custom_hours_per_month)
						if flt(eti_details.hours_in_a_month) < hours_per_month:
							hours_per_month = flt(eti_details.hours_in_a_month)

						# Apply formula and calculate prorated amount based on hours worked
						self.data, self.default_data = self.get_data_for_eval()
						self.data.monthly_remuneration = taxable_eti_amount
						
						try:
							current_eti_amount = frappe.safe_eval(formula, self.data) or 0
						except Exception as e:
							frappe.log_error(
								_("ETI formula evaluation error: {0}, Formula: {1}").format(str(e), formula),
								"ETI Calculation Error"
							)
							frappe.msgprint(
								_("Error in ETI formula evaluation. Please check the ETI Slab configuration."),
								indicator="red",
								alert=True
							)
							return 0
						
						# Prorate ETI amount based on hours worked
						if flt(eti_details.hours_in_a_month) > 0:  # Avoid division by zero
							current_eti_amount = (
								flt(current_eti_amount)
								/ flt(eti_details.hours_in_a_month)
								* flt(hours_per_month)
							)
						
						# Add any carry-forward amount from previous period
						prev_eti_balance_details = frappe.db.sql(
							"""
							SELECT carry_forwarding_eti_amount
							FROM `tabEmployee ETI Log`
							WHERE
								employee = %(employee)s AND
								docstatus = 1 AND
								date <= %(posting_date)s
							ORDER BY
								date DESC
							LIMIT 1
							""",
							{
								"employee": self.employee,
								"posting_date": self.posting_date
							},
							as_dict=True,
						)
						if prev_eti_balance_details and prev_eti_balance_details[0].get(
							"carry_forwarding_eti_amount"
						):
							current_eti_amount += flt(prev_eti_balance_details[0].get(
								"carry_forwarding_eti_amount"
							))
				else:
					frappe.msgprint(
						_("No eligible earnings found for ETI calculation for employee {0}.").format(
							self.employee_name or self.employee
						),
						indicator="orange",
						alert=True
					)
			else:
				frappe.msgprint(
					_("Employee {0} has exceeded the 24-month ETI eligibility period.").format(
						self.employee_name or self.employee
					),
					indicator="blue",
					alert=True
				)
		else:
			if age < eti_details.get("minimum_age") or age > eti_details.get("maximum_age"):
				frappe.msgprint(
					_("Employee {0} does not meet the age requirement ({1}-{2} years) for ETI.").format(
						self.employee_name or self.employee,
						eti_details.get("minimum_age"),
						eti_details.get("maximum_age")
					),
					indicator="blue",
					alert=True
				)
		
		return flt(current_eti_amount, 2)  # Return with 2 decimal precision
		
	except Exception as e:
		frappe.log_error(
			_("ETI Calculation Error: {0} for employee {1}").format(str(e), self.employee),
			"ETI Calculation Error"
		)
		frappe.msgprint(
			_("Error in ETI calculation. Please check the error log for details."),
			indicator="red",
			alert=True
		)
		return 0


def calculate_age(date_of_birth):
	"""
	Calculate age based on date of birth
	
	Args:
		date_of_birth (str or date): The employee's date of birth
		
	Returns:
		int: Age in years
		
	Raises:
		ValueError: If date_of_birth is invalid or None
	"""
	if not date_of_birth:
		raise ValueError("Date of birth is required to calculate age")
		
	if isinstance(date_of_birth, str):
		try:
			dob = datetime.strptime(date_of_birth, "%Y-%m-%d")
		except ValueError:
			frappe.log_error(
				f"Invalid date format for date of birth: {date_of_birth}",
				"ETI Calculation Error"
			)
			raise ValueError(f"Invalid date format for date of birth: {date_of_birth}")
	else:
		dob = datetime.combine(date_of_birth, datetime.min.time())
		
	current_date = datetime.now()
	age = current_date.year - dob.year
	
	# Adjust age if the birthday hasn't occurred yet this year
	if current_date.month < dob.month or (
		current_date.month == dob.month and current_date.day < dob.day
	):
		age -= 1
		
	return age


def get_total_days(year_start, year_end):
	year_start = year_start
	year_end = year_end
	total_days = (year_end - year_start).days
	return total_days


# Get total no of weekend days(SATURDAY,SUNDAY) in a given period
def get_total_weekend_days(year_start, year_end):
	year_start = year_start
	year_end = year_end
	delta = timedelta(days=1)

	weekend = 0

	while year_start <= year_end:
		if year_start.weekday() in [calendar.SATURDAY, calendar.SUNDAY]:
			weekend += 1
		year_start += delta

	return weekend


def get_tax_rebate(self, dob):
	"""
	Calculate tax rebate based on employee's age according to South African tax rules.
	
	South African tax rebates are age-dependent with three categories:
	- Primary: For all taxpayers
	- Secondary: Additional rebate for those 65 and older
	- Tertiary: Additional rebate for those 75 and older
	
	Args:
		dob (date or str): Employee's date of birth
		
	Returns:
		float: Monthly tax rebate amount based on age and configured rates
	"""
	try:
		# Parse date string if needed
		if isinstance(dob, str):
			try:
				if len(dob.split('-')[0]) == 2:  # If year is in YY format
					dob = datetime.strptime(dob, "%y-%m-%d")
				else:  # If year is in YYYY format
					dob = datetime.strptime(dob, "%Y-%m-%d")
			except ValueError:
				frappe.log_error(
					f"Invalid date format for date of birth: {dob}",
					"Tax Rebate Calculation Error"
				)
				raise ValueError(f"Invalid date format for date of birth: {dob}")
		
		# Get end date of payroll period for age calculation
		period_end_date = self.payroll_period.end_date
		
		# Calculate age as of the end of the tax year (important for tax purposes)
		age = period_end_date.year - dob.year - ((period_end_date.month, period_end_date.day) < (dob.month, dob.day))
		
		# Get applicable tax rebate rates for the payroll period
		name = frappe.db.get_value(
			"Tax Rebates Rate", {"payroll_period": self.payroll_period.name}
		)
		
		if not name:
			frappe.msgprint(
				_("No Tax Rebates Rate found for Payroll Period {0}. Using zero rebate.").format(
					self.payroll_period.name
				),
				indicator="orange",
				alert=True
			)
			return 0
		
		# Get rebate details
		doc = frappe.get_doc("Tax Rebates Rate", name)
		
		# Calculate monthly primary rebate (for all taxpayers)
		tax_rebate = flt(doc.primary / 12) or 0
		
		# Add secondary rebate for taxpayers 65 and older
		if age >= 65:
			tax_rebate += flt(doc.secondary / 12) or 0
			
			# Add tertiary rebate for taxpayers 75 and older
			if age >= 75:
				tax_rebate += flt(doc.tertiary / 12) or 0
		
		return tax_rebate
	except Exception as e:
		frappe.log_error(
			_("Error in Tax Rebate calculation: {0} for employee {1}, DOB: {2}").format(
				str(e), self.employee, dob
			),
			"Tax Rebate Calculation Error"
		)
		frappe.msgprint(
			_("Error in Tax Rebate calculation. Using zero rebate."),
			indicator="red",
			alert=True
		)
		return 0


def get_remaining_sub_periods(
	employee,
	start_date,
	end_date,
	payroll_frequency,
	payroll_period,
	depends_on_payment_days=0,
):
	sub_period = get_period_factor(
		employee, start_date, end_date, payroll_frequency, payroll_period
	)[1]
	salary_slips = frappe.db.sql(
		"""
				select
					count(name)
				from
					`tabSalary Slip`
				where
					docstatus=1
					and employee=%(employee)s
					and start_date between %(from_date)s and %(to_date)s
					and end_date between %(from_date)s and %(to_date)s
				""",
		{
			"employee": employee,
			"from_date": payroll_period.start_date,
			"to_date": payroll_period.end_date,
		},
	)
	salary_slips = flt(salary_slips[0][0]) if salary_slips else 0

	excess_months = 0
	taxable_amount_based_on = frappe.db.get_single_value(
		"Payroll Settings", "calculate_annual_taxable_amount_based_on"
	)
	if not taxable_amount_based_on or (
		taxable_amount_based_on and taxable_amount_based_on == "Payroll Period"
	):
		joining_date, relieving_date = frappe.get_cached_value(
			"Employee", employee, ["date_of_joining", "relieving_date"]
		)

		if joining_date:
			joining_date = getdate(joining_date)

		if relieving_date:
			relieving_date = getdate(relieving_date)

		if joining_date and joining_date > payroll_period.start_date:
			excess_months += month_diff(joining_date, payroll_period.start_date) - 1

		if relieving_date and relieving_date < payroll_period.end_date:
			excess_months += month_diff(payroll_period.end_date, relieving_date) - 1

	return sub_period + excess_months  # - salary_slips


def get_additional_salaries(employee, start_date, end_date, component_type):
	from frappe.query_builder import Criterion

	comp_type = "Earning" if component_type == "earnings" else "Deduction"

	additional_sal = frappe.qb.DocType("Additional Salary")
	component_field = additional_sal.salary_component.as_("component")
	overwrite_field = additional_sal.overwrite_salary_structure_amount.as_("overwrite")

	additional_salary_list = (
		frappe.qb.from_(additional_sal)
		.select(
			additional_sal.name,
			component_field,
			additional_sal.type,
			additional_sal.amount,
			additional_sal.is_recurring,
			overwrite_field,
			additional_sal.deduct_full_tax_on_selected_payroll_date,
		)
		.where(
			(additional_sal.employee == employee)
			& (additional_sal.docstatus == 1)
			# & (additional_sal.type == comp_type)
			& (additional_sal.disabled == 0)
		)
		.where(
			Criterion.any(
				[
					Criterion.all(
						[  # is recurring and additional salary dates fall within the payroll period
							additional_sal.is_recurring == 1,
							additional_sal.from_date <= end_date,
							additional_sal.to_date >= end_date,
						]
					),
					Criterion.all(
						[  # is not recurring and additional salary's payroll date falls within the payroll period
							additional_sal.is_recurring == 0,
							additional_sal.payroll_date[start_date:end_date],
						]
					),
				]
			)
		)
	)
	if component_type in ["earnings", "deductions"]:
		additional_salary_list = additional_salary_list.where(
			(additional_sal.type == comp_type)
			& (additional_sal.is_company_contribution == 0)
		)
	else:
		additional_salary_list = additional_salary_list.where(additional_sal.is_company_contribution == 1)
	additional_salary_list = additional_salary_list.run(as_dict=True)

	additional_salaries = []
	components_to_overwrite = []

	for d in additional_salary_list:
		if d.overwrite:
			if d.component in components_to_overwrite:
				frappe.throw(
					_(
						"Multiple Additional Salaries with overwrite property exist for Salary Component {0} between {1} and {2}."
					).format(frappe.bold(d.component), start_date, end_date),
					title=_("Error"),
				)

			components_to_overwrite.append(d.component)

		additional_salaries.append(d)

	return additional_salaries
