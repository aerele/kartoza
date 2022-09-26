from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
import frappe

def after_install():
	make_custom_fields()

def make_custom_fields():
	custom_fields = {
		'HR Settings': [
		]
	}
	if not frappe.get_meta("HR Settings").get_field("amount_per_kilometer"):
		custom_fields["HR Settings"].append(dict(fieldname='amount_per_kilometer', label='Amount Per Kilometer',
                        fieldtype='Currency', insert_after='emp_created_by'))
	create_custom_fields(custom_fields)