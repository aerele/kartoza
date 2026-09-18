import calendar
from datetime import datetime, timedelta

from erpnext.accounts.utils import get_account_currency
from frappe.query_builder.functions import Sum
from frappe.utils import (
	cint,
	date_diff,
	flt,
	get_link_to_form,
	getdate,
	month_diff,
)
from hrms.payroll.doctype.employee_benefit_ledger.employee_benefit_ledger import (
	delete_employee_benefit_ledger_entry,
)
from hrms.payroll.doctype.payroll_period.payroll_period import (
	get_period_factor,
)
from hrms.payroll.doctype.salary_slip.salary_slip import (
	SalarySlip,
	calculate_tax_by_tax_slab,
	get_salary_component_data,
	rounded,
)
from hrms.payroll.doctype.salary_slip.salary_slip_loan_utils import (
	set_loan_repayment,
)
from kartoza.custom_py.payroll_entry import (
	get_current_block_period,
	get_employee_frequency_map,
	is_payroll_processed,
)

import frappe
from erpnext import get_company_currency
from frappe import _


class CustomSalarySlip(SalarySlip):
	def validate(self):
		super().validate()
		frequency = get_current_block_period(self)
		employee_frequency = get_employee_frequency_map()
		if self.employee in employee_frequency and is_payroll_processed(
			self.employee, frequency[employee_frequency[self.employee]]
		):
			frappe.throw(
				" Salary Slip already created for current {0}".format(
					employee_frequency[self.employee]
				)
			)
		self.validate_component_account()


	def set_forex_employee(self):
		self.is_forex_employee = False
		self.is_eligible_for_paye = frappe.db.get_value("Employee", self.employee, "eligible_for_paye")

		company_currency = get_company_currency(self.company)

		payroll_payable_account = frappe.get_cached_value("Employee", self.employee, "payroll_payable_account")
		if not payroll_payable_account:
			return

		bank_account = frappe.get_cached_value("Bank Account", payroll_payable_account, "account")
		if not bank_account:
			return

		account_currency = get_account_currency(bank_account)

		self.is_forex_employee = company_currency != account_currency



	def validate_component_account(self):
		for component_type in ["earnings", "deductions"]:
			for row in self.get(component_type):
				if not frappe.db.get_value(
					"Salary Component Account",
					{"parent": row.salary_component, "company": self.company},
					"account",
				):
					frappe.throw(
						_("Please set account in Salary Component {0}").format(
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

		if not tax_components and self.is_forex_employee:
			tax_components = [
				d.name
				for d in frappe.get_all("Salary Component", filters={"variable_based_on_taxable_salary": 1})
				if d.name not in self.other_deduction_components
			]

		self._component_based_variable_tax = {}
		if tax_components and self.payroll_period and self.salary_structure:
			self.tax_slab = self.get_income_tax_slabs()
			self.compute_taxable_earnings_for_year()

		if self.is_forex_employee:
			if self.is_eligible_for_paye:
				taxable_earnings_till_date = self.total_taxable_earnings - self.future_structured_taxable_earnings
				if taxable_earnings_till_date <= self.tax_slab.foreign_tax_threshold:
					return
			else:
				return

		if self.handle_additional_salary_tax_component():
			self._component_based_variable_tax.setdefault(self.additional_salary_component, {})
			self.calculate_variable_tax(self.additional_salary_component, True)
			return

		self._component_based_variable_tax = {}
		for tax_component in tax_components:
			self._component_based_variable_tax.setdefault(tax_component, {})
			self.calculate_variable_based_on_taxable_salary(tax_component)
			if self._component_based_variable_tax[tax_component]:
				tax_amount = self._component_based_variable_tax[tax_component]["current_tax_amount"]
				tax_row = get_salary_component_data(tax_component)
				self.update_component_row(tax_row, tax_amount, "deductions")

	def compute_taxable_earnings_for_year(self):
		super().compute_taxable_earnings_for_year()

		self.annual_bonus = self.get_bonus_amount()

		if self.annual_bonus:
			self.custom_provision_for_tax_on_annual_bonus = flt(
				self.annual_bonus / 12, self.precision("custom_provision_for_tax_on_annual_bonus")
			)

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
			"annual_bonus",
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

	def add_additional_salary_components(self, component_type):
		additional_salaries = get_additional_salaries(
			self.employee, self.start_date, self.end_date, component_type
		)

		for additional_salary in additional_salaries:
			component_data = get_salary_component_data(additional_salary.component)
			self.update_component_row(
				component_data,
				additional_salary.amount,
				component_type,
				additional_salary,
				is_recurring=additional_salary.is_recurring,
			)

			if component_type == "earnings" and hasattr(self, "benefit_ledger_components"):
				if (
					additional_salary.ref_doctype == "Employee Benefit Claim"
					and component_data.is_flexible_benefit
				) or component_data.accrual_component:
					# track benefit claim or accrual component payout to record in Employee Benefit Ledger
					if additional_salary.ref_doctype == "Employee Benefit Claim":
						remarks = f"Payout against Employee Benefit Claim {additional_salary.ref_docname}"
						flexible_benefit = 1
					else:
						remarks = "Accrual Component payout via Additional Salary"
						flexible_benefit = 0

					self.benefit_ledger_components.append(
						{
							"salary_component": additional_salary.component,
							"amount": additional_salary.amount,
							"is_accrual": 0,
							"transaction_type": "Payout",
							"flexible_benefit": flexible_benefit,
							"remarks": remarks,
						}
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
		self.set_forex_employee()

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

		# earnings are calculated after remaining_sub_periods since v16 benefit accruals depend on it
		if self.salary_structure:
			self.calculate_component_amounts("earnings")

		set_gross_pay_and_base_gross_pay()

		if self.salary_structure:
			self.calculate_component_amounts("deductions")

		set_loan_repayment(self)

		self.set_precision_for_component_amounts()
		self.set_net_pay()
		if not skip_tax_breakup_computation:
			self.compute_income_tax_breakup()

		eti_amount = get_eti_deduction(self) or 0

		# amount_before_eti_deduction = 0
		# amount_after_eti_deduction=0
		self.custom_monthly_eti = eti_amount.current_eti_amount
		self.custom_carry_forwarded_eti_amount = eti_amount.carry_forwarded_eti_amount
		self.custom_total_eti_amount = self.custom_monthly_eti + self.custom_carry_forwarded_eti_amount

		tax_amount = self.tax_value or 0
		amount_before_eti_deduction = tax_amount
		tax_amount -= self.custom_total_eti_amount
		amount_after_eti_deduction = self.custom_total_eti_amount - amount_before_eti_deduction

		self.custom_carry_forwarding_eti_amount = amount_after_eti_deduction if amount_after_eti_deduction > 0 else 0

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

		self.taxable_value = getattr(self, "taxable_value_with_deduction", 0)
		self.total_company_contribution = total_company_contribution

		self.total_cost = self.gross_pay + self.total_company_contribution

		# self.set_loan_repayment()
		# self.set_precision_for_component_amounts()
		# self.set_net_pay()
		# self.compute_income_tax_breakup()

	def calculate_variable_tax(self, tax_component, has_additional_salary_tax_component=False):
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
		if self.is_forex_employee and self.is_eligible_for_paye:
			self.total_taxable_earnings_without_full_tax_addl_components = (
				self.total_taxable_earnings_without_full_tax_addl_components - self.tax_slab.foreign_tax_threshold
			)
		self.total_structured_tax_amount, __ = calculate_tax_by_tax_slab(
			self.total_taxable_earnings_without_full_tax_addl_components,
			self.tax_slab,
			self.whitelisted_globals,
			eval_locals,
		)

		if has_additional_salary_tax_component:
			self.current_structured_tax_amount = self.additional_salary_amount
		else:
			self.current_structured_tax_amount = (
				self.total_structured_tax_amount - self.previous_total_paid_taxes
			) / self.remaining_sub_periods
		self.tax_value = self.current_structured_tax_amount

		# Total taxable earnings with additional earnings with full tax
		self.full_tax_on_additional_earnings = 0.0
		if self.current_additional_earnings_with_full_tax:
			if self.is_forex_employee and self.is_eligible_for_paye:
				self.total_taxable_earnings = (
					self.total_taxable_earnings - self.tax_slab.foreign_tax_threshold
				)

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
		if self.total_structured_tax_amount < 0:
			self.total_structured_tax_amount = 0

		self.current_structured_tax_amount = (
			self.total_structured_tax_amount - self.previous_total_paid_taxes
		) / self.remaining_sub_periods

		self.current_tax_amount = max(
			0,
			flt(
				self.current_structured_tax_amount
				if has_additional_salary_tax_component
				else (self.current_structured_tax_amount + self.full_tax_on_additional_earnings)
			),
		)
		if flt(self.current_tax_amount) < 0:
			self.current_tax_amount = 0

		self._component_based_variable_tax[tax_component].update(
			{
				"previous_total_paid_taxes": self.previous_total_paid_taxes,
				"total_structured_tax_amount": self.total_structured_tax_amount,
				"current_structured_tax_amount": self.current_structured_tax_amount,
				"full_tax_on_additional_earnings": self.full_tax_on_additional_earnings,
				"current_tax_amount": self.current_tax_amount,
			}
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

		self.taxable_value = taxable_income.taxable_earnings + taxable_income.additional_income
		self.taxable_value_with_deduction = 0

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
			self.taxable_value_with_deduction = (
				taxable_income.taxable_earnings + taxable_income.additional_income
			)
		return taxable_income


	def get_payment_days(self, include_holidays_in_total_working_days):
		if self.joining_date and self.joining_date > getdate(self.end_date):
			return 0

		if self.relieving_date:
			employee_status = frappe.db.get_value("Employee", self.employee, "status")
			if self.relieving_date < getdate(self.start_date) and employee_status != "Left":
				frappe.throw(
					_("Employee {0} relieved on {1} must be set as 'Left'").format(
						get_link_to_form("Employee", self.employee), self.relieving_date
					)
				)

		start = getdate(self.actual_start_date)
		end = getdate(self.actual_end_date)

		is_full_month = (
			start <= getdate(self.start_date)
			and end >= getdate(self.end_date)
		)


		if is_full_month:
			return self.total_working_days

		return date_diff(end, start) + 1

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

		delete_employee_benefit_ledger_entry("salary_slip", self.name)


def get_retirement_annuity(self):
	ra = frappe.db.get_value(
		"Employee Private Benefit",
		{
			"effective_from": ["<=", self.start_date],
			"disable": 0,
			"employee": self.employee,
		},
		order_by="effective_from",
	)
	res = frappe._dict({})
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
		ra = frappe.get_doc("Employee Private Benefit", ra)
		res["limit_percent"] = ra.maximum_
		res["ra_amount"] = ra.annuity_amount
		if (ra.maximum_amount // 12) < ra.annuity_amount:
			res["ra_amount"] = ra.maximum_amount // 12
	return res


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
	current_eti_amount = 0
	carry_forwarded_eti_amount = 0
	employee_details = (
		frappe.db.get_value(
			"Employee",
			{"name": self.employee},
			["date_of_joining", "date_of_birth", "hours_per_month"],
			as_dict=True,
		)
		or {}
	)

	age = calculate_age(employee_details.get("date_of_birth"))
	eti_details = frappe.db.get_value(
		"ETI Slab",
		{"start_date": ["<=", (self.posting_date)], "docstatus": 1},
		["minimum_age", "maximum_age", "name", "hours_in_a_month"],
		as_dict=True,
	)

	taxable_eti_amount = 0
	if (
		eti_details
		and eti_details.get("minimum_age") <= age
		and eti_details.get("maximum_age") >= age
	):

		prev_eti = frappe.get_all(
			"Employee ETI Log", {"employee": self.employee, "docstatus":1, "date":["<", self.start_date]}, pluck="name"
		)
		prev_eti_count = len(prev_eti)
		if prev_eti_count < 24:
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
			for eti_component in eti_eligible_components:
				eligible_components[eti_component.get("name")] = {
					"taxable_earning_reduce_percentage": eti_component.get(
						"taxable_earning_reduce_percentage"
					),
					"reduce_on_taxable_earning": eti_component.get(
						"reduce_on_taxable_earning"
					),
				}
			for earning in self.earnings:
				if earning.salary_component in eligible_components.keys():

					if float(
						eligible_components.get(earning.salary_component, {}).get(
							"taxable_earning_reduce_percentage"
						)
					) > 0 and eligible_components.get(earning.salary_component, {}).get(
						"reduce_on_taxable_earning"
					):
						taxable_eti_amount += (
							float(
								eligible_components.get(
									earning.salary_component, {}
								).get("taxable_earning_reduce_percentage")
							)
							/ 100
						) * earning.amount
					else:
						taxable_eti_amount += earning.amount
			formula_field = (
				"first_qualifying_12_months"
				if prev_eti_count <= 11
				else "second_qualifying_12_months"
			)
			if taxable_eti_amount:

				formula = frappe.db.get_value(
					"ETI Slab Details",
					{
						"parent": eti_details.get("name"),
						"from_amount": ["<=", taxable_eti_amount],
						"to_amount": [">=", taxable_eti_amount],
					},
					formula_field,
				)

				if formula:

					if not employee_details.hours_per_month:
						frappe.throw(
							"Set <b>Hours Per Month</b> for the Employee: {0}".format(
								self.employee
							)
						)

					if eti_details.hours_in_a_month < employee_details.hours_per_month:
						employee_details.hours_per_month = eti_details.hours_in_a_month

					self.data, self.default_data = self.get_data_for_eval()
					self.data.monthly_remuneration = taxable_eti_amount
					current_eti_amount = frappe.safe_eval(formula, self.data) or 0
					current_eti_amount = (
						current_eti_amount
						/ eti_details.hours_in_a_month
						* employee_details.hours_per_month
					)
					prev_eti_balance_details = frappe.db.sql(
						"""
											SELECT carry_forwarding_eti_amount
												FROM `tabEmployee ETI Log`
											WHERE
												employee = '{0}' AND
												docstatus = 1 AND
												date < '{1}'
											ORDER BY
												date DESC
											LIMIT 1
										""".format(
							self.employee, self.start_date
						),
						as_dict=True
					)
					if prev_eti_balance_details and prev_eti_balance_details[0].get(
						"carry_forwarding_eti_amount"
					):
						carry_forwarded_eti_amount = prev_eti_balance_details[0].get(
							"carry_forwarding_eti_amount"
						)
	return frappe._dict({
		"current_eti_amount":current_eti_amount,
		"carry_forwarded_eti_amount":carry_forwarded_eti_amount
	})


def calculate_age(date_of_birth):
	dob = datetime.strptime(str(date_of_birth), "%Y-%m-%d")
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
	if isinstance(dob, str):
		dob = datetime.strptime(dob, "%y-%m-%d")
	period_end_date = self.payroll_period.end_date
	age = period_end_date.year - dob.year - ((period_end_date.month, period_end_date.day) < (dob.month, dob.day))
	name = frappe.db.get_value(
		"Tax Rebates Rate", {"payroll_period": self.payroll_period.name}
	)
	if name:
		doc = frappe.get_doc("Tax Rebates Rate", name)
		tax_rebate = (doc.primary / 12) or 0

		if age >= 65:
			tax_rebate += (doc.secondary / 12) or 0
			if age >= 75:
				tax_rebate += (doc.tertiary / 12) or 0

		return tax_rebate
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
			additional_sal.ref_doctype,
			additional_sal.ref_docname,
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
