from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

import erpnext
import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import \
	get_accounting_dimensions
from erpnext.setup.utils import get_exchange_rate
from frappe.query_builder.functions import Coalesce, Count
from frappe.utils import (DATE_FORMAT, add_days, add_to_date, cint, comma_and,
						  date_diff, flt, get_link_to_form, getdate)
from hrms.payroll.doctype.payroll_entry.payroll_entry import (
	PayrollEntry, _, create_salary_slips_for_employees)
from hrms.payroll.doctype.payroll_period.payroll_period import \
	get_payroll_period

FREQUENCY = {
	# "Monthly" : 1,
	"Quarterly" : 3,
	"Half-Yearly" : 6,
	"Yearly" : 12
}

def get_current_block(frequency, date, payroll_period):
	start_date = payroll_period.start_date
	end_date = payroll_period.end_date
	used_block = 0
	while True:
		start_date = datetime.strptime(str(start_date), "%Y-%m-%d").date()
		end_date = (start_date + relativedelta(months=FREQUENCY[frequency]) - timedelta(days=1))

		date = datetime.strptime(str(date),"%Y-%m-%d").date()
		if start_date <= date and end_date >= date:
			return frappe._dict({
				"start_date": start_date,
				"end_date": end_date
			})
		else:
			start_date = end_date + timedelta(days=1)
			used_block += 1



def get_current_block_period(self):
	payroll_period = get_payroll_period(self.start_date, self.end_date, self.company)
	payroll_period_doc = frappe.get_doc("Payroll Period", payroll_period)
	frequency_map = {}
	for freq in FREQUENCY:
		frequency_map[freq] = get_current_block(freq, self.start_date, payroll_period_doc)
	return frequency_map

def get_employee_frequency_map():

	emp_map = {}
	for i in frappe.db.get_all("Employee Frequency Detail", ["employee", "frequency"]):
		emp_map[i.employee] = i.frequency
	return emp_map

def is_payroll_processed(employee, frequency):
	return frappe.db.get_value("Salary Slip", {"employee": employee, "start_date":['>=', frequency.start_date], "end_date":["<=", frequency.end_date], "docstatus":1})

class CustomPayrollEntry(PayrollEntry):
	def validate(self):
		super().validate()
		employees_without_employee_type = ""
		for i in self.employees:

			if not i.custom_employee_type:
				i.custom_employee_type = frappe.db.get_value("Employee", i.employee, "custom_employee_type")

			if not i.custom_payroll_payable_bank_account:
				i.custom_payroll_payable_bank_account = frappe.db.get_value("Employee", i.employee, "payroll_payable_account")

			if i.custom_payroll_payable_bank_account:
				account = frappe.db.get_value("Bank Account", i.custom_payroll_payable_bank_account, "account")
				if account:
					i.custom_bank_account_currency = frappe.db.get_value("Account", account, "account_currency")

			if not i.custom_payroll_payable_bank_account:
				frappe.throw("Payroll Payable Bank Account not found for Employee:<a href='/app/employee/{0}'><b>{0}</b></a>".format(i.employee))

			if not i.custom_employee_type:
				employees_without_employee_type += "<li><a href='/app/employee/{0}' target='_blank' >{0}: {1}</a></li>".format(i.employee, i.employee_name)

		if employees_without_employee_type:
			frappe.throw("Employee Type not found for below Employees<br /><br /><ul>{0}</ul>".format(employees_without_employee_type))

	@frappe.whitelist()
	def fill_employee_details(self):
		self.set("employees", [])
		employees = self.get_emp_list()
		if not employees:
			error_msg = _(
				"No employees found for the mentioned criteria:<br>Company: {0}<br> Currency: {1}<br>Payroll Payable Account: {2}"
			).format(
				frappe.bold(self.company),
				frappe.bold(self.currency),
				frappe.bold(self.payroll_payable_account),
			)
			if self.branch:
				error_msg += "<br>" + _("Branch: {0}").format(frappe.bold(self.branch))
			if self.department:
				error_msg += "<br>" + _("Department: {0}").format(frappe.bold(self.department))
			if self.designation:
				error_msg += "<br>" + _("Designation: {0}").format(frappe.bold(self.designation))
			if self.start_date:
				error_msg += "<br>" + _("Start date: {0}").format(frappe.bold(self.start_date))
			if self.end_date:
				error_msg += "<br>" + _("End date: {0}").format(frappe.bold(self.end_date))
			frappe.throw(error_msg, title=_("No employees found"))

		frequency = get_current_block_period(self)
		employee_frequency = get_employee_frequency_map()

		pay_at = frappe.db.get_value("Employee Payroll Frequency", "Employee Payroll Frequency", "pay_at")

		for d in employees:
			if d.employee in employee_frequency:
				if pay_at == "Beginning of the period" and str(frequency[employee_frequency[d.employee]].start_date) != str(self.start_date):
					continue
				if pay_at == "End of the period" and str(frequency[employee_frequency[d.employee]].end_date) != str(self.end_date):
					continue

			self.append("employees", d)

		self.number_of_employees = len(self.employees)
		return self.get_employees_with_unmarked_attendance()


	@frappe.whitelist()
	def create_salary_slips(self):
		"""
		Creates salary slip for selected employees if already not created
		"""
		self.check_permission("write")
		employees = []
		frequency = get_current_block_period(self)
		employee_frequency = get_employee_frequency_map()
		for emp in self.employees:
			if emp.employee in employee_frequency and is_payroll_processed(emp.employee, frequency[employee_frequency[emp.employee]]):
				continue
			employees.append(emp.employee)

		if employees:
			args = frappe._dict(
				{
					"salary_slip_based_on_timesheet": self.salary_slip_based_on_timesheet,
					"payroll_frequency": self.payroll_frequency,
					"start_date": self.start_date,
					"end_date": self.end_date,
					"company": self.company,
					"posting_date": self.posting_date,
					"deduct_tax_for_unclaimed_employee_benefits": self.deduct_tax_for_unclaimed_employee_benefits,
					"deduct_tax_for_unsubmitted_tax_exemption_proof": self.deduct_tax_for_unsubmitted_tax_exemption_proof,
					"payroll_entry": self.name,
					"exchange_rate": self.exchange_rate,
					"currency": self.currency,
				}
			)
			if len(employees) > 30 or frappe.flags.enqueue_payroll_entry:
				self.db_set("status", "Queued")
				frappe.enqueue(
					create_salary_slips_for_employees,
					timeout=600,
					employees=employees,
					args=args,
					publish_progress=False,
				)
				frappe.msgprint(
					_("Salary Slip creation is queued. It may take a few minutes"),
					alert=True,
					indicator="blue",
				)
			else:
				create_salary_slips_for_employees(employees, args, publish_progress=False)
				# since this method is called via frm.call this doc needs to be updated manually
				self.reload()
	# def get_salary_components(self, component_type):
	# 	salary_components = super().get_salary_components(component_type)
	# 	salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)

	# 	if salary_slips and component_type == "earnings":
	# 		ss = frappe.qb.DocType("Salary Slip")
	# 		ssd = frappe.qb.DocType("Company Contribution")
	# 		salary_components += (
	# 			frappe.qb.from_(ss)
	# 			.join(ssd)
	# 			.on(ss.name == ssd.parent)
	# 			.select(ssd.salary_component, ssd.amount, ssd.parentfield, ss.salary_structure, ss.employee)
	# 			.where(
	# 				(ssd.parentfield == "company_contribution") & (ss.name.isin(tuple([d.name for d in salary_slips])))
	# 			)
	# 		).run(as_dict=True)

	# 	return salary_components

	@frappe.whitelist()
	def make_payment_entry(self):
		self.check_permission("write")
		process_payroll_accounting_entry_based_on_employee = frappe.db.get_single_value(
			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
		)
		payment_account = self.payment_account
		bank_account = self.bank_account

		self.company_currency = frappe.db.get_value("Company", self.company, "default_currency")
		self.sdl_payment_bank_account = None

		for employee in self.employees:
			if employee.custom_bank_account_currency == self.company_currency:
				self.sdl_payment_bank_account = employee.custom_payroll_payable_bank_account

			if self.sdl_payment_bank_account:
				break

		self.sdl_payment_account = frappe.db.get_value("Bank Account", self.sdl_payment_bank_account, "account")
		self.sdl_payment_account_currency = frappe.db.get_value("Account", self.sdl_payment_account, "account_currency")

		for pay_account in self.selected_payment_account:
			self.employee_based_payroll_payable_entries = {}
			# if self.selected_payment_account[pay_account] != 1:continue
			emp_list = self.selected_payment_account[pay_account]["employees"]
			# for employee in self.employees:
			# 	if employee.custom_payroll_payable_bank_account == pay_account:
			# 		emp_list.append(employee.employee)
			# 		frappe.db.set_value("Payroll Employee Detail", employee.name, "custom_is_bank_entry_creaeted", 1)

			account = frappe.db.get_value("Bank Account", pay_account, "account")
			self.bank_account = pay_account
			self.payment_account = account
			self.payment_account_currency = frappe.db.get_value("Account", account, "account_currency")

			salary_slip_name_list = frappe.db.sql(
				""" select t1.name from `tabSalary Slip` t1
				where t1.docstatus = 1 and start_date >= %s and end_date <= %s and t1.payroll_entry = %s and employee in ('{}')
				""".format("', '".join(emp_list)),
				(self.start_date, self.end_date, self.name),
				as_list=True
			)


			if salary_slip_name_list and len(salary_slip_name_list) > 0:
				salary_slip_total = 0
				for salary_slip_name in salary_slip_name_list:
					salary_slip = frappe.get_doc("Salary Slip", salary_slip_name[0])
					is_bank_entry_created = frappe.db.get_value("Payroll Employee Detail", {"parent":self.name, "employee": salary_slip.employee}, "custom_is_bank_entry_creaeted")
					self.set_employee_based_payroll_payable_entries(
									"is_bank_entry_created",
									salary_slip.employee,
									is_bank_entry_created,
									salary_slip.salary_structure,
								)
					if is_bank_entry_created:
						continue
					for sal_detail in salary_slip.earnings:
						(
							is_flexible_benefit,
							only_tax_impact,
							create_separate_je,
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
							if is_flexible_benefit == 1 and create_separate_je == 1:
								self.create_journal_entry(sal_detail.amount, sal_detail.salary_component)
							else:
								if process_payroll_accounting_entry_based_on_employee:
									self.set_employee_based_payroll_payable_entries(
										"earnings",
										salary_slip.employee,
										sal_detail.amount,
										salary_slip.salary_structure,
									)
								salary_slip_total += sal_detail.amount

					for sal_detail in salary_slip.deductions:
						statistical_component = frappe.db.get_value(
							"Salary Component", sal_detail.salary_component, "statistical_component"
						)
						if statistical_component != 1:
							if process_payroll_accounting_entry_based_on_employee:
								self.set_employee_based_payroll_payable_entries(
									"deductions",
									salary_slip.employee,
									sal_detail.amount,
									salary_slip.salary_structure,
								)

							salary_slip_total -= sal_detail.amount


				if salary_slip_total > 0:
					self.create_journal_entry(salary_slip_total, "salary")





			if salary_slip_name_list and len(salary_slip_name_list) > 0:
				salary_slip_total = 0
				self.sdl_payment_amount = 0
				self.provisional_payment = {}
				for salary_slip_name in salary_slip_name_list:
					salary_slip = frappe.get_doc("Salary Slip", salary_slip_name[0])
					is_company_contribution_created = frappe.db.get_value("Payroll Employee Detail", {"parent":self.name, "employee": salary_slip.employee}, "custom_is_company_contribution_created")
					self.set_employee_based_payroll_payable_entries(
									"is_company_contribution_created",
									salary_slip.employee,
									is_company_contribution_created,
									salary_slip.salary_structure,
								)
					if is_company_contribution_created:
						continue


					department = frappe.db.get_value("Employee", salary_slip.employee, "department")
					business_unit = None
					if department:
						department_name = frappe.db.get_value("Department", department, "department_name")
						business_unit = frappe.db.get_value("Business Unit", department_name)

					employee_type = frappe.db.get_value("Employee", salary_slip.employee, "custom_employee_type")


					for sal_detail in salary_slip.company_contribution:
						# if process_payroll_accounting_entry_based_on_employee:
							# self.set_employee_based_payroll_payable_entries(
							# 	"company_contribution",
							# 	salary_slip.employee,
							# 	sal_detail.amount,
							# 	salary_slip.salary_structure,
							# )
						component_account = frappe.db.get_value("Salary Component Account", {"parent":sal_detail.salary_component, "company": self.company}, "account")
						provisional_key = (component_account, business_unit, employee_type)
						# if provisional_key not in self.provisional_payment:
						# 	self.provisional_payment[provisional_key] = 0
						self.provisional_payment[provisional_key] = self.provisional_payment.get(provisional_key, 0) + sal_detail.amount

						if self.payment_account_currency != self.company_currency and frappe.db.get_value("Salary Component", sal_detail.salary_component, "is_company_contribution") and frappe.db.get_value("Salary Component", sal_detail.salary_component, "custom_is_sdl"):
							self.sdl_payment_amount += sal_detail.amount
						else:
							salary_slip_total += sal_detail.amount

					for sal_detail in salary_slip.deductions:
						variable_salary, income_tax_component = frappe.db.get_value("Salary Component", sal_detail.salary_component, ["variable_based_on_taxable_salary", "is_income_tax_component"])
						if (variable_salary and income_tax_component) or (frappe.db.get_value("Salary Component", sal_detail.salary_component, "is_company_contribution") and not frappe.db.get_value("Salary Component", sal_detail.salary_component, "custom_is_sdl")):
							component_account = frappe.db.get_value("Salary Component Account", {"parent":sal_detail.salary_component, "company": self.company}, "account")
							provisional_key = (component_account, business_unit, employee_type)
							# if provisional_key not in self.provisional_payment:
							# 	self.provisional_payment[provisional_key] = 0
							self.provisional_payment[provisional_key] = self.provisional_payment.get(provisional_key, 0) + sal_detail.amount
							salary_slip_total += sal_detail.amount

				if salary_slip_total > 0 or self.sdl_payment_amount > 0:
					self.jv_for_company_contribution = True
					self.create_journal_entry(salary_slip_total, "Company Contribution")
					self.jv_for_company_contribution = False

		self.payment_account = payment_account
		self.bank_account = bank_account

	def get_sal_slip_list(self, ss_status, as_dict=False):
		"""
		Returns list of salary slips based on selected criteria
		"""
		employees = [i.employee for i in self.employees]
		ss = frappe.qb.DocType("Salary Slip")
		ss_list = (
			frappe.qb.from_(ss)
			.select(ss.name, ss.salary_structure)
			.where(
				(ss.docstatus == ss_status)
				& (ss.start_date >= self.start_date)
				& (ss.end_date <= self.end_date)
				& (ss.payroll_entry == self.name)
				& ((ss.journal_entry.isnull()) | (ss.journal_entry == ""))
				& (Coalesce(ss.salary_slip_based_on_timesheet, 0) == self.salary_slip_based_on_timesheet)
				& (ss.employee.isin(tuple(employees)))
			)
		).run(as_dict=as_dict)

		return ss_list

	def get_salary_component_account(self, salary_component):
		if frappe.db.get_value("Salary Component", salary_component, "type") == "Earning":
			return self.earnings_payable_account

		account = frappe.db.get_value(
			"Salary Component Account", {"parent": salary_component, "company": self.company}, "account"
		)

		if not account:
			frappe.throw(
				_("Please set account in Salary Component {0}").format(
					get_link_to_form("Salary Component", salary_component)
				)
			)

		return account

	def get_salary_components(self, component_type):
		salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)
		employees = [i.employee for i in self.employees]

		if salary_slips:
			ss = frappe.qb.DocType("Salary Slip")
			ssd = frappe.qb.DocType("Salary Detail")
			salary_components = (
				frappe.qb.from_(ss)
				.join(ssd)
				.on(ss.name == ssd.parent)
				.select(
					ssd.salary_component,
					ssd.amount,
					ssd.parentfield,
					ssd.additional_salary,
					ss.salary_structure,
					ss.employee,
				)
				.where(
					(ssd.parentfield == component_type) & (ss.name.isin(tuple([d.name for d in salary_slips ])) & (ss.employee.isin(tuple(employees))))
				)
			).run(as_dict=True)

			return salary_components

	def separate_based_on_employee_type(self):
		employee_type_map = {}
		for row in self.employees:
			if row.custom_employee_type in employee_type_map:
				employee_type_map[row.custom_employee_type].append(row)
			else:
				employee_type_map[row.custom_employee_type] = [row]


		return employee_type_map

	def update_reference(self, jv):
		doc = frappe.get_doc("Journal Entry", jv)
		for i in doc.accounts:
			if i.debit_in_account_currency:
				frappe.db.set_value(i.doctype, i.name, 'reference_type', self.doctype)
				frappe.db.set_value(i.doctype, i.name, 'reference_name', self.name)

			if i.party_type == "Employee" and i.party:
				department = frappe.db.get_value("Employee", i.party, "department")
				if department:
					department_name = frappe.db.get_value("Department", department, "department_name")
					business_unit = frappe.db.get_value("Business Unit", department_name)
					if business_unit:
						frappe.db.set_value(i.doctype, i.name, 'business_unit', business_unit)

				employee_type = frappe.db.get_value("Employee", i.party, "custom_employee_type")
				if employee_type:
					frappe.db.set_value(i.doctype, i.name, 'employee_type', employee_type)

	def make_accrual_jv_entry(self):
		self.backup_employees = self.employees

		employee_type_map = self.separate_based_on_employee_type()

		for employee_type in employee_type_map:
			self.earnings_payable_account = frappe.db.get_value("Employee Type", employee_type, "payroll_payable_account")
			self.employees = employee_type_map[employee_type]
			jv = self.create_accrual_jv_entry()


		self.employees = self.backup_employees


		return jv


	def get_sum_value(self, accounts, key):
		total = 0
		for account in accounts:
			total += account[key]

		return total


	def get_company_component_total(
		self,
		component_type=None,
		process_payroll_accounting_entry_based_on_employee=False,
	):
		salary_components = [] #self.get_salary_components(component_type)


		salary_slips = self.get_sal_slip_list(ss_status=1, as_dict=True)

		if salary_slips:
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


		if salary_components:
			component_dict = {}

			for item in salary_components:
				if not self.should_add_component_to_accrual_jv(component_type, item):
					continue

				employee_cost_centers = self.get_payroll_cost_centers_for_employee(
					item.employee, item.salary_structure
				)
				employee_advance = self.get_advance_deduction(component_type, item)

				for cost_center, percentage in employee_cost_centers.items():
					amount_against_cost_center = flt(item.amount) * percentage / 100

					if employee_advance:
						self.add_advance_deduction_entry(
							item, amount_against_cost_center, cost_center, employee_advance
						)
					else:
						key = (item.salary_component, cost_center)
						component_dict[key] = component_dict.get(key, 0) + amount_against_cost_center

					if process_payroll_accounting_entry_based_on_employee:
						self.set_employee_based_payroll_payable_entries(
							component_type, item.employee, amount_against_cost_center
						)

			account_details = self.get_account(component_dict=component_dict)

			return account_details


	def create_accrual_jv_entry(self):
		self.check_permission("write")
		process_payroll_accounting_entry_based_on_employee = frappe.db.get_single_value(
			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
		)
		self.employee_based_payroll_payable_entries = {}
		self._advance_deduction_entries = []

		earnings = (
			self.get_salary_component_total(
				component_type="earnings",
				process_payroll_accounting_entry_based_on_employee=process_payroll_accounting_entry_based_on_employee,
			)
			or {}
		)

		deductions = (
			self.get_salary_component_total(
				component_type="deductions",
				process_payroll_accounting_entry_based_on_employee=process_payroll_accounting_entry_based_on_employee,
			)
			or {}
		)

		company_contribution = (
			self.get_company_component_total(
				component_type="company_contribution",
				process_payroll_accounting_entry_based_on_employee=process_payroll_accounting_entry_based_on_employee,
			)
			or {}
		)

		payroll_payable_account = self.payroll_payable_account
		jv_name = ""
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")


		if earnings or deductions:
			accounting_dimensions = get_accounting_dimensions() or []

			jv_accounts = []
			currencies = []
			payable_amount = 0
			multi_currency = 0
			company_currency = erpnext.get_company_currency(self.company)

			# Earnings
			for acc_cc, amount in earnings.items():
				payable_amount = self.get_accounting_entries_and_payable_amount(
					acc_cc[0],
					acc_cc[1] or self.cost_center,
					amount,
					currencies,
					company_currency,
					payable_amount,
					accounting_dimensions,
					precision,
					entry_type="debit",
					accounts=jv_accounts,
				)

			# Deductions
			for acc_cc, amount in deductions.items():
				payable_amount = self.get_accounting_entries_and_payable_amount(
					acc_cc[0],
					acc_cc[1] or self.cost_center,
					amount,
					currencies,
					company_currency,
					payable_amount,
					accounting_dimensions,
					precision,
					entry_type="credit",
					accounts=jv_accounts,
				)

			earning_entry = jv_accounts[0]
			provisional_entry = jv_accounts[1:]
			earning_entry["debit_in_account_currency"] = earning_entry["debit_in_account_currency"] - self.get_sum_value(provisional_entry, "credit_in_account_currency")
			accounts = [earning_entry]

			# payable_amount = self.set_accounting_entries_for_advance_deductions(
			# 	accounts,
			# 	currencies,
			# 	company_currency,
			# 	accounting_dimensions,
			# 	precision,
			# 	payable_amount,
			# )

			# Payable amount
			if process_payroll_accounting_entry_based_on_employee:
				"""
				employee_based_payroll_payable_entries = {
						'HR-EMP-00004': {
										'earnings': 83332.0,
										'deductions': 2000.0
								},
						'HR-EMP-00005': {
								'earnings': 50000.0,
								'deductions': 2000.0
						}
				}
				"""
				for employee, employee_details in self.employee_based_payroll_payable_entries.items():
					payable_amount = employee_details.get("earnings") - (employee_details.get("deductions") or 0)

					payable_amount = self.get_accounting_entries_and_payable_amount(
						payroll_payable_account,
						self.cost_center,
						payable_amount,
						currencies,
						company_currency,
						0,
						accounting_dimensions,
						precision,
						entry_type="payable",
						party=employee,
						accounts=accounts,
					)

			else:
				payable_amount = self.get_accounting_entries_and_payable_amount(
					payroll_payable_account,
					self.cost_center,
					payable_amount,
					currencies,
					company_currency,
					0,
					accounting_dimensions,
					precision,
					entry_type="payable",
					accounts=accounts,
				)

			journal_entry = frappe.new_doc("Journal Entry")
			journal_entry.voucher_type = "Journal Entry"
			journal_entry.user_remark = _("Accrual Journal Entry for salaries from {0} to {1}").format(
				self.start_date, self.end_date
			)
			journal_entry.company = self.company
			journal_entry.posting_date = self.posting_date

			journal_entry.set("accounts", accounts)
			if len(currencies) > 1:
				multi_currency = 1
			journal_entry.multi_currency = multi_currency
			journal_entry.title = payroll_payable_account
			journal_entry.save()

			try:
				journal_entry.submit()
				jv_name = journal_entry.name
				self.update_reference(jv_name)
				self.update_salary_slip_status(jv_name=jv_name)
			except Exception as e:
				if type(e) in (str, list, tuple):
					frappe.msgprint(e)
				raise


			earning_entry = jv_accounts[0]
			provisional_entry = jv_accounts[1:]
			# earning_entry["debit_in_account_currency"] = self.get_sum_value(provisional_entry, "credit_in_account_currency")
			for acc_cc, amount in company_contribution.items():
				payable_amount = self.get_accounting_entries_and_payable_amount(
					acc_cc[0],
					acc_cc[1] or self.cost_center,
					amount,
					currencies,
					company_currency,
					payable_amount,
					accounting_dimensions,
					precision,
					entry_type="credit",
					accounts=provisional_entry,
				)
			earning_entry["debit_in_account_currency"] = self.get_sum_value(provisional_entry, "credit_in_account_currency")
			accounts = [earning_entry, *provisional_entry]

			journal_entry = frappe.new_doc("Journal Entry")
			journal_entry.voucher_type = "Journal Entry"
			journal_entry.user_remark = _("Accrual Journal Entry for salaries from {0} to {1}").format(
				self.start_date, self.end_date
			)
			journal_entry.company = self.company
			journal_entry.posting_date = self.posting_date

			journal_entry.set("accounts", accounts)
			if len(currencies) > 1:
				multi_currency = 1
			journal_entry.multi_currency = multi_currency
			journal_entry.title = payroll_payable_account
			journal_entry.save()

			try:
				journal_entry.submit()
				jv_name = journal_entry.name
				self.update_reference(jv_name)
				self.update_salary_slip_status(jv_name=jv_name)
			except Exception as e:
				if type(e) in (str, list, tuple):
					frappe.msgprint(e)
				raise

		return jv_name


	def create_journal_entry(self, je_payment_amount, user_remark):
		payroll_payable_account = self.payroll_payable_account
		precision = frappe.get_precision("Journal Entry Account", "debit_in_account_currency")

		accounts = []
		currencies = []
		multi_currency = 0
		company_currency = erpnext.get_company_currency(self.company)
		accounting_dimensions = get_accounting_dimensions() or []

		# exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
		# 	self.payment_account, je_payment_amount, company_currency, currencies
		# )

		payment_currency = frappe.db.get_value("Account", self.payment_account, "account_currency")
		payroll_payable_currency = frappe.db.get_value("Account", payroll_payable_account, "account_currency")

		exchange_rate = get_exchange_rate(payment_currency, payroll_payable_currency, self.posting_date)

		if self.bank_account in self.selected_payment_account and "exchange_rate" in self.selected_payment_account[self.bank_account] and self.selected_payment_account[self.bank_account]["exchange_rate"]:
			exchange_rate = self.selected_payment_account[self.bank_account]["exchange_rate"]

		if payment_currency != payroll_payable_currency:
			multi_currency = 1

		amount = je_payment_amount / exchange_rate

		if amount:
			accounts.append(
				self.update_accounting_dimensions(
					{
						"account": self.payment_account,
						"bank_account": self.bank_account,
						"credit_in_account_currency": flt(amount, precision),
						"exchange_rate": flt(exchange_rate),
						"cost_center": self.cost_center,
					},
					accounting_dimensions,
				)
			)

		if self.get("jv_for_company_contribution") and self.sdl_payment_amount:
			accounts.append(
				self.update_accounting_dimensions(
					{
						"account": self.sdl_payment_account,
						"bank_account": self.sdl_payment_bank_account,
						"credit_in_account_currency": flt(self.sdl_payment_amount, precision),
						"exchange_rate": flt(1),
						"cost_center": self.cost_center,
					},
					accounting_dimensions,
				)
			)



		if self.get("jv_for_company_contribution"):
			for acc in self.provisional_payment:
				exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
					acc[0], self.provisional_payment[acc], company_currency, currencies
				)

				row_account = self.update_accounting_dimensions(
						{
							"account": acc[0],
							"debit_in_account_currency": flt(amount, precision),
							"exchange_rate": flt(exchange_rate),
							"reference_type": self.doctype,
							"reference_name": self.name,
							"cost_center": self.cost_center,
						},
						accounting_dimensions,
					)

				row_account["business_unit"] = acc[1]
				row_account["employee_type"] = acc[2]

				if row_account["debit_in_account_currency"]:
					accounts.append(
						row_account
					)


		else:
			if self.employee_based_payroll_payable_entries:
				for employee, employee_details in self.employee_based_payroll_payable_entries.items():
					if self.get("jv_for_company_contribution"):
						if employee_details.get("is_company_contribution_created"):
							continue
						je_payment_amount = employee_details.get("company_contribution") or 0
					else:
						if employee_details.get("is_bank_entry_created"):
							continue
						je_payment_amount = (employee_details.get("earnings") or 0) - (
							employee_details.get("deductions") or 0
						)


					exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
						self.payment_account, je_payment_amount, company_currency, currencies
					)

					cost_centers = self.get_payroll_cost_centers_for_employee(
						employee, employee_details.get("salary_structure")
					)

					for cost_center, percentage in cost_centers.items():
						amount_against_cost_center = flt(amount) * percentage / 100
						if amount_against_cost_center:
							accounts.append(
								self.update_accounting_dimensions(
									{
										"account": payroll_payable_account,
										"debit_in_account_currency": flt(amount_against_cost_center, precision),
										"exchange_rate": flt(exchange_rate),
										"reference_type": self.doctype,
										"reference_name": self.name,
										"party_type": "Employee",
										"party": employee,
										"custom_party_name": frappe.db.get_value("Employee", employee, "employee_name"),
										"cost_center": cost_center,
										"custom_is_payroll_entry": 0 if self.get("jv_for_company_contribution") else 1,
										"custom_is_company_contribution": 1 if self.get("jv_for_company_contribution") else 0
										# "business_unit": business_unit,
									},
									accounting_dimensions,
								)
							)
			else:
				exchange_rate, amount = self.get_amount_and_exchange_rate_for_journal_entry(
					payroll_payable_account, je_payment_amount, company_currency, currencies
				)
				accounts.append(
					self.update_accounting_dimensions(
						{
							"account": payroll_payable_account,
							"debit_in_account_currency": flt(amount, precision),
							"exchange_rate": flt(exchange_rate),
							"reference_type": self.doctype,
							"reference_name": self.name,
							"cost_center": self.cost_center,
						},
						accounting_dimensions,
					)
				)

		if len(currencies) > 1:
			multi_currency = 1

		posting_date = self.posting_date
		if self.bank_account in self.selected_payment_account and "posting_date" in self.selected_payment_account[self.bank_account] and self.selected_payment_account[self.bank_account]["posting_date"]:
			posting_date = self.selected_payment_account[self.bank_account]["posting_date"]

		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.voucher_type = "Bank Entry"
		journal_entry.user_remark = _("Payment of {0} from {1} to {2}").format(
			user_remark, self.start_date, self.end_date
		)
		journal_entry.company = self.company
		journal_entry.posting_date = posting_date
		journal_entry.multi_currency = multi_currency

		if accounts:
			journal_entry.set("accounts", accounts)
			journal_entry.save(ignore_permissions=True)



		flag_field_name = "custom_is_bank_entry_creaeted"
		if self.get("jv_for_company_contribution"):
			flag_field_name = "custom_is_company_contribution_created"

		for i in journal_entry.accounts:
			if i.debit_in_account_currency:
				frappe.db.set_value(i.doctype, i.name, 'reference_type', self.doctype)
				frappe.db.set_value(i.doctype, i.name, 'reference_name', self.name)

			if i.party_type == "Employee" and i.party:
				department = frappe.db.get_value("Employee", i.party, "department")
				frappe.db.set_value("Payroll Employee Detail", {"parent": self.name, "employee":i.party}, flag_field_name, 1)
				if department:
					department_name = frappe.db.get_value("Department", department, "department_name")
					business_unit = frappe.db.get_value("Business Unit", department_name)
					if business_unit:
						frappe.db.set_value(i.doctype, i.name, 'business_unit', business_unit)

				employee_type = frappe.db.get_value("Employee", i.party, "custom_employee_type")
				if employee_type:
					frappe.db.set_value(i.doctype, i.name, 'employee_type', employee_type)







def get_payroll_entry_bank_entries(payroll_entry_name):
	journal_entries = frappe.db.sql(
		'select jea.name from `tabJournal Entry Account` as jea join `tabJournal Entry` as je on je.name=jea.parent '
		'where jea.reference_type="Payroll Entry" '
		'and jea.reference_name=%s and je.docstatus=1 and je.voucher_type="Bank"',
		payroll_entry_name,
		as_dict=1
	)

	return journal_entries
