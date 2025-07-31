import frappe
from kartoza.install import rename_duplicate_fields
def execute():
	custom_fields = {
		'HR Settings': [
			dict(fieldname='amount_per_kilometer', label='Amount Per Kilometer',
						fieldtype='Currency', insert_after='emp_created_by')
		],
		'Payroll Settings': [
			dict(fieldname='calculate_annual_taxable_amount_based_on', label='Calculate Annual Taxable Amount Based On',
						fieldtype='Select', options="\nJoining and Relieving Date\nPayroll Period", default="Payroll Period", insert_after='daily_wages_fraction_for_half_day')
		],
		"Employee":[
			dict(fieldname='payroll_payable_bank_account', label='Payroll Payable Bank Account',
						fieldtype='Link', options="Bank Account", insert_after='payroll_cost_center'),
			dict(fieldname='hours_per_month', label='Hours Per Month',
						fieldtype='Float', insert_after='payroll_payable_bank_account')
		],
		"Additional Salary":[
			dict(fieldname='is_company_contribution', label='Is Company Contribution',
						fieldtype='Check', insert_after='column_break_8')
		],
		"Salary Structure Assignment":[
			dict(fieldname="annual_bonus", label="Annual Bonus",
						fieldtype="Currency", insert_after="base", allow_on_submit=True)
		]
	}
	rename_duplicate_fields(custom_fields)
