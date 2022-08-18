from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def after_install():
	make_custom_fields()

def make_custom_fields():
	custom_fields = {
		'HR Settings': [
			dict(fieldname='amount_per_kilometer', label='Amount Per Kilometer',
			fieldtype='Currency', insert_after='emp_created_by')
			dict(fieldname='maximum_earnings', label='Maximum Earnings',
			fieldtype='Currency', insert_after='retirement_age', description='Per Month')
		]
	}
	create_custom_fields(custom_fields)

    
