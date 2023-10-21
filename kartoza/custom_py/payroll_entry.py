from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

import erpnext
import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import \
    get_accounting_dimensions
from frappe.utils import flt
from hrms.payroll.doctype.payroll_entry.payroll_entry import (
    PayrollEntry, _, create_salary_slips_for_employees)
from hrms.payroll.doctype.payroll_period.payroll_period import \
    get_payroll_period

from erpnext.setup.utils import get_exchange_rate

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
		for i in self.employees:
			if not i.custom_payroll_payable_bank_account:
				i.custom_payroll_payable_bank_account = frappe.db.get_value("Employee", i.employee, "payroll_payable_account")

			if not i.custom_payroll_payable_bank_account:
				frappe.throw("Payroll Payable Bank Account not found for Employee:<a href='/app/employee/{0}'><b>{0}</b></a>".format(i.employee))

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
		self.employee_based_payroll_payable_entries = {}
		process_payroll_accounting_entry_based_on_employee = frappe.db.get_single_value(
			"Payroll Settings", "process_payroll_accounting_entry_based_on_employee"
		)
		payment_account = self.payment_account
		bank_account = self.bank_account

		for pay_account in self.selected_payment_account:
			if self.selected_payment_account[pay_account] != 1:continue
			emp_list = []
			for employee in self.employees:
				if employee.custom_payroll_payable_bank_account == pay_account:
					emp_list.append(employee.employee)
					frappe.db.set_value("Payroll Employee Detail", employee.name, "custom_is_bank_entry_creaeted", 1)

			account = frappe.db.get_value("Bank Account", pay_account, "account")
			self.bank_account = pay_account
			self.payment_account = account

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
				for salary_slip_name in salary_slip_name_list:
					salary_slip = frappe.get_doc("Salary Slip", salary_slip_name[0])
					for sal_detail in salary_slip.company_contribution:
						if process_payroll_accounting_entry_based_on_employee:
							self.set_employee_based_payroll_payable_entries(
								"company_contribution",
								salary_slip.employee,
								sal_detail.amount,
								salary_slip.salary_structure,
							)
						salary_slip_total += sal_detail.amount

				if salary_slip_total > 0:
					self.jv_for_company_contribution = True
					self.create_journal_entry(salary_slip_total, "salary")

		self.payment_account = payment_account
		self.bank_account = bank_account


	def make_accrual_jv_entry(self):
		jv = super().make_accrual_jv_entry()
		if jv:
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

		return jv







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

		if payment_currency != payroll_payable_currency:
			multi_currency = 1

		amount = je_payment_amount / exchange_rate

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



		if self.employee_based_payroll_payable_entries:
			for employee, employee_details in self.employee_based_payroll_payable_entries.items():
				if self.get("jv_for_company_contribution"):
					je_payment_amount = employee_details.get("company_contribution") or 0
				else:
					je_payment_amount = employee_details.get("earnings") - (
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
								"cost_center": cost_center,
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


		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.voucher_type = "Bank Entry"
		journal_entry.user_remark = _("Payment of {0} from {1} to {2}").format(
			user_remark, self.start_date, self.end_date
		)
		journal_entry.company = self.company
		journal_entry.posting_date = self.posting_date
		journal_entry.multi_currency = multi_currency

		journal_entry.set("accounts", accounts)
		journal_entry.save(ignore_permissions=True)


		for i in journal_entry.accounts:
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







def get_payroll_entry_bank_entries(payroll_entry_name):
	journal_entries = frappe.db.sql(
		'select jea.name from `tabJournal Entry Account` as jea join `tabJournal Entry` as je on je.name=jea.parent '
		'where jea.reference_type="Payroll Entry" '
		'and jea.reference_name=%s and je.docstatus=1 and je.voucher_type="Bank"',
		payroll_entry_name,
		as_dict=1
	)

	return journal_entries
