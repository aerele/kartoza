import frappe
from hrms.payroll.doctype.payroll_entry.payroll_entry import PayrollEntry, create_salary_slips_for_employees, _
from hrms.payroll.doctype.payroll_period.payroll_period import get_payroll_period
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


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
		super().make_payment_entry()
		self.check_permission("write")

		salary_slip_name_list = frappe.db.sql(
			""" select t1.name from `tabSalary Slip` t1
			where t1.docstatus = 1 and start_date >= %s and end_date <= %s and t1.payroll_entry = %s
			""",
			(self.start_date, self.end_date, self.name),
			as_list=True,
		)

		if salary_slip_name_list and len(salary_slip_name_list) > 0:
			salary_slip_total = 0
			for salary_slip_name in salary_slip_name_list:
				salary_slip = frappe.get_doc("Salary Slip", salary_slip_name[0])
				for sal_detail in salary_slip.company_contribution:
					salary_slip_total += sal_detail.amount
			if salary_slip_total > 0:
				super().create_journal_entry(salary_slip_total, "salary")

	def make_accrual_jv_entry(self):
		jv = super().make_accrual_jv_entry()
		if jv:
			doc = frappe.get_doc("Journal Entry", jv)
			for i in doc.accounts:
				if i.debit_in_account_currency:
					frappe.db.set_value(i.doctype, i.name, 'reference_type', self.doctype)
					frappe.db.set_value(i.doctype, i.name, 'reference_name', self.name)
		return jv



def get_payroll_entry_bank_entries(payroll_entry_name):
	journal_entries = frappe.db.sql(
		'select jea.name from `tabJournal Entry Account` as jea join `tabJournal Entry` as je on je.name=jea.parent '
		'where jea.reference_type="Payroll Entry" '
		'and jea.reference_name=%s and je.docstatus=1 and je.voucher_type="Bank"',
		payroll_entry_name,
		as_dict=1
	)

	return journal_entries
