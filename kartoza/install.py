from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
import frappe

def after_install():
	make_custom_fields()

def before_install():
	# Check if Company Contribution DocType already exists
	if frappe.db.exists("DocType", "Company Contribution"):
		return
		
	doc = frappe.get_doc({
			"docstatus": 0,
			"idx": 0,
			"issingle": 0,
			"is_tree": 0,
			"istable": 1,
			"editable_grid": 1,
			"track_changes": 1,
			"module": "Payroll",
			"naming_rule": "",
			"name_case": "",
			"sort_field": "modified",
			"sort_order": "DESC",
			"read_only": 0,
			"in_create": 0,
			"allow_copy": 0,
			"allow_rename": 0,
			"allow_import": 0,
			"hide_toolbar": 0,
			"track_seen": 0,
			"max_attachments": 0,
			"document_type": "",
			"engine": "InnoDB",
			"is_submittable": 0,
			"show_name_in_global_search": 0,
			"custom": 1,
			"beta": 0,
			"has_web_view": 0,
			"allow_guest_to_view": 0,
			"email_append_to": 0,
			"show_title_field_in_link": 0,
			"translated_doctype": 0,
			"is_calendar_and_gantt": 0,
			"quick_entry": 1,
			"track_views": 0,
			"is_virtual": 0,
			"allow_events_in_timeline": 0,
			"allow_auto_repeat": 0,
			"make_attachments_public": 0,
			"default_view": "List",
			"force_re_route_to_default_view": 0,
			"show_preview_popup": 0,
			"index_web_pages_for_search": 1,
			"doctype": "DocType",
			"links": [],
			"states": [],
			"__newname": "Company Contribution",
			"fields": [
				{
					"parent": "Company Contribution",
					"parentfield": "fields",
					"parenttype": "DocType",
					"idx": 1,
					"fieldname": "salary_component",
					"label": "Salary Component",
					"fieldtype": "Link",
					"options": "Salary Component",
					"search_index": 0,
					"show_dashboard": 0,
					"hidden": 0,
					"set_only_once": 0,
					"allow_in_quick_entry": 0,
					"print_hide": 0,
					"report_hide": 0,
					"reqd": 0,
					"bold": 0,
					"in_global_search": 0,
					"collapsible": 0,
					"unique": 0,
					"no_copy": 0,
					"allow_on_submit": 1,
					"show_preview_popup": 0,
					"permlevel": 0,
					"ignore_user_permissions": 0,
					"columns": 0,
					"in_list_view": 1,
					"fetch_if_empty": 0,
					"in_filter": 0,
					"remember_last_selected_value": 0,
					"ignore_xss_filter": 0,
					"print_hide_if_no_value": 0,
					"allow_bulk_edit": 0,
					"in_standard_filter": 0,
					"in_preview": 0,
					"read_only": 0,
					"precision": "",
					"length": 0,
					"translatable": 0,
					"hide_border": 0,
					"hide_days": 0,
					"hide_seconds": 0,
					"non_negative": 0,
					"is_virtual": 0,
					"doctype": "DocField"
				},
				{
					"parent": "Company Contribution",
					"parentfield": "fields",
					"parenttype": "DocType",
					"idx": 2,
					"fieldname": "abbr",
					"label": "Abbr",
					"fieldtype": "Data",
					"search_index": 0,
					"show_dashboard": 0,
					"hidden": 0,
					"set_only_once": 0,
					"allow_in_quick_entry": 0,
					"print_hide": 0,
					"report_hide": 0,
					"reqd": 0,
					"bold": 0,
					"in_global_search": 0,
					"collapsible": 0,
					"unique": 0,
					"no_copy": 0,
					"allow_on_submit": 1,
					"show_preview_popup": 0,
					"permlevel": 0,
					"ignore_user_permissions": 0,
					"columns": 0,
					"in_list_view": 0,
					"fetch_if_empty": 0,
					"in_filter": 0,
					"remember_last_selected_value": 0,
					"ignore_xss_filter": 0,
					"print_hide_if_no_value": 0,
					"allow_bulk_edit": 0,
					"in_standard_filter": 0,
					"in_preview": 0,
					"read_only": 0,
					"precision": "",
					"length": 0,
					"translatable": 0,
					"hide_border": 0,
					"hide_days": 0,
					"hide_seconds": 0,
					"non_negative": 0,
					"is_virtual": 0,
					"fetch_from": "salary_component.salary_component_abbr",
					"doctype": "DocField"
				},
				{
					"parent": "Company Contribution",
					"parentfield": "fields",
					"parenttype": "DocType",
					"idx": 3,
					"fieldname": "amount",
					"label": "Amount ",
					"fieldtype": "Currency",
					"options": "currency",
					"search_index": 0,
					"show_dashboard": 0,
					"hidden": 0,
					"set_only_once": 0,
					"allow_in_quick_entry": 0,
					"print_hide": 0,
					"report_hide": 0,
					"reqd": 0,
					"bold": 0,
					"in_global_search": 0,
					"collapsible": 0,
					"unique": 0,
					"no_copy": 0,
					"allow_on_submit": 1,
					"show_preview_popup": 0,
					"permlevel": 0,
					"ignore_user_permissions": 0,
					"columns": 0,
					"in_list_view": 1,
					"fetch_if_empty": 0,
					"in_filter": 0,
					"remember_last_selected_value": 0,
					"ignore_xss_filter": 0,
					"print_hide_if_no_value": 0,
					"allow_bulk_edit": 0,
					"in_standard_filter": 0,
					"in_preview": 0,
					"read_only": 0,
					"precision": "",
					"length": 0,
					"translatable": 0,
					"hide_border": 0,
					"hide_days": 0,
					"hide_seconds": 0,
					"non_negative": 0,
					"is_virtual": 0,
					"doctype": "DocField"
				},
				{
					"parent": "Company Contribution",
					"parentfield": "fields",
					"parenttype": "DocType",
					"idx": 4,
					"fieldname": "condition_and_formula_section",
					"label": "Condition and formula",
					"fieldtype": "Section Break",
					"search_index": 0,
					"show_dashboard": 0,
					"hidden": 0,
					"set_only_once": 0,
					"allow_in_quick_entry": 0,
					"print_hide": 0,
					"report_hide": 0,
					"reqd": 0,
					"bold": 0,
					"in_global_search": 0,
					"collapsible": 1,
					"unique": 0,
					"no_copy": 0,
					"allow_on_submit": 0,
					"show_preview_popup": 0,
					"permlevel": 0,
					"ignore_user_permissions": 0,
					"columns": 0,
					"in_list_view": 0,
					"fetch_if_empty": 0,
					"in_filter": 0,
					"remember_last_selected_value": 0,
					"ignore_xss_filter": 0,
					"print_hide_if_no_value": 0,
					"allow_bulk_edit": 0,
					"in_standard_filter": 0,
					"in_preview": 0,
					"read_only": 0,
					"precision": "",
					"length": 0,
					"translatable": 0,
					"hide_border": 0,
					"hide_days": 0,
					"hide_seconds": 0,
					"non_negative": 0,
					"is_virtual": 0,
					"doctype": "DocField"
				},
				{
					"parent": "Company Contribution",
					"parentfield": "fields",
					"parenttype": "DocType",
					"idx": 5,
					"fieldname": "condition",
					"label": "Condition",
					"fieldtype": "Code",
					"search_index": 0,
					"show_dashboard": 0,
					"hidden": 0,
					"set_only_once": 0,
					"allow_in_quick_entry": 0,
					"print_hide": 0,
					"report_hide": 0,
					"reqd": 0,
					"bold": 0,
					"in_global_search": 0,
					"collapsible": 0,
					"unique": 0,
					"no_copy": 0,
					"allow_on_submit": 1,
					"show_preview_popup": 0,
					"permlevel": 0,
					"ignore_user_permissions": 0,
					"columns": 0,
					"in_list_view": 0,
					"fetch_if_empty": 0,
					"in_filter": 0,
					"remember_last_selected_value": 0,
					"ignore_xss_filter": 0,
					"print_hide_if_no_value": 0,
					"allow_bulk_edit": 0,
					"in_standard_filter": 0,
					"in_preview": 0,
					"read_only": 0,
					"precision": "",
					"length": 0,
					"translatable": 0,
					"hide_border": 0,
					"hide_days": 0,
					"hide_seconds": 0,
					"non_negative": 0,
					"is_virtual": 0,
					"fetch_from": "salary_component.condition",
					"doctype": "DocField"
				},
				{
					"parent": "Company Contribution",
					"parentfield": "fields",
					"parenttype": "DocType",
					"idx": 6,
					"fieldname": "column_break_6",
					"fieldtype": "Column Break",
					"search_index": 0,
					"show_dashboard": 0,
					"hidden": 0,
					"set_only_once": 0,
					"allow_in_quick_entry": 0,
					"print_hide": 0,
					"report_hide": 0,
					"reqd": 0,
					"bold": 0,
					"in_global_search": 0,
					"collapsible": 0,
					"unique": 0,
					"no_copy": 0,
					"allow_on_submit": 0,
					"show_preview_popup": 0,
					"permlevel": 0,
					"ignore_user_permissions": 0,
					"columns": 0,
					"in_list_view": 0,
					"fetch_if_empty": 0,
					"in_filter": 0,
					"remember_last_selected_value": 0,
					"ignore_xss_filter": 0,
					"print_hide_if_no_value": 0,
					"allow_bulk_edit": 0,
					"in_standard_filter": 0,
					"in_preview": 0,
					"read_only": 0,
					"precision": "",
					"length": 0,
					"translatable": 0,
					"hide_border": 0,
					"hide_days": 0,
					"hide_seconds": 0,
					"non_negative": 0,
					"is_virtual": 0,
					"doctype": "DocField"
				},
				{
					"parent": "Company Contribution",
					"parentfield": "fields",
					"parenttype": "DocType",
					"idx": 7,
					"fieldname": "amount_based_on_formula",
					"label": "Amount based on formula",
					"fieldtype": "Check",
					"search_index": 0,
					"show_dashboard": 0,
					"hidden": 0,
					"set_only_once": 0,
					"allow_in_quick_entry": 0,
					"print_hide": 0,
					"report_hide": 0,
					"reqd": 0,
					"bold": 0,
					"in_global_search": 0,
					"collapsible": 0,
					"unique": 0,
					"no_copy": 0,
					"allow_on_submit": 1,
					"show_preview_popup": 0,
					"permlevel": 0,
					"ignore_user_permissions": 0,
					"columns": 0,
					"default": "0",
					"in_list_view": 0,
					"fetch_if_empty": 0,
					"in_filter": 0,
					"remember_last_selected_value": 0,
					"ignore_xss_filter": 0,
					"print_hide_if_no_value": 0,
					"allow_bulk_edit": 0,
					"in_standard_filter": 0,
					"in_preview": 0,
					"read_only": 0,
					"precision": "",
					"length": 0,
					"translatable": 0,
					"hide_border": 0,
					"hide_days": 0,
					"hide_seconds": 0,
					"non_negative": 0,
					"is_virtual": 0,
					"fetch_from": "salary_component.amount_based_on_formula",
					"doctype": "DocField"
				},
				{
					"parent": "Company Contribution",
					"parentfield": "fields",
					"parenttype": "DocType",
					"idx": 8,
					"fieldname": "formula",
					"label": "Formula",
					"fieldtype": "Code",
					"search_index": 0,
					"show_dashboard": 0,
					"hidden": 0,
					"set_only_once": 0,
					"allow_in_quick_entry": 0,
					"print_hide": 0,
					"report_hide": 0,
					"reqd": 0,
					"bold": 0,
					"in_global_search": 0,
					"collapsible": 0,
					"unique": 0,
					"no_copy": 0,
					"allow_on_submit": 1,
					"show_preview_popup": 0,
					"permlevel": 0,
					"ignore_user_permissions": 0,
					"columns": 0,
					"in_list_view": 0,
					"fetch_if_empty": 0,
					"in_filter": 0,
					"remember_last_selected_value": 0,
					"ignore_xss_filter": 0,
					"print_hide_if_no_value": 0,
					"allow_bulk_edit": 0,
					"in_standard_filter": 0,
					"in_preview": 0,
					"read_only": 0,
					"precision": "",
					"length": 0,
					"translatable": 0,
					"hide_border": 0,
					"hide_days": 0,
					"hide_seconds": 0,
					"non_negative": 0,
					"is_virtual": 0,
					"fetch_from": "salary_component.formula",
					"doctype": "DocField"
				}
			]
		})
	doc.save()

def make_custom_fields():
	"""
	Create custom fields for South African payroll and tax requirements.
	
	This function adds several custom fields to standard doctypes:
	- HR Settings: Adds kilometer reimbursement rates
	- Payroll Settings: Adds SA tax calculation options and statutory components
	- Employee: Adds SA ID number and payroll account fields 
	- Company: Adds SA-specific registration numbers
	- Additional Salary: Adds company contribution functionality
	"""
	custom_fields = {
		'HR Settings': [],
		'Payroll Settings': [],
		"Employee":[],
		"Additional Salary":[],
		"Salary Structure Assignment":[],
		"Company":[]
	}

	if not frappe.get_meta("HR Settings").get_field("amount_per_kilometer"):
		custom_fields["HR Settings"].append(dict(fieldname='amount_per_kilometer', label='Amount Per Kilometer',
						fieldtype='Currency', insert_after='emp_created_by'))

	if not frappe.get_meta("Payroll Settings").get_field("calculate_annual_taxable_amount_based_on"):
		custom_fields["Payroll Settings"].append(dict(fieldname='calculate_annual_taxable_amount_based_on', label='Calculate Annual Taxable Amount Based On',
						fieldtype='Select', options="\nJoining and Relieving Date\nPayroll Period", default="Payroll Period", insert_after='daily_wages_fraction_for_half_day'))

	if not frappe.get_meta("Employee").get_field("custom_payroll_payable_account"):
		custom_fields["Employee"].append(dict(fieldname='custom_payroll_payable_account', label='Payroll Payable Bank Account',
						fieldtype='Link', options="Bank Account", insert_after='payroll_cost_center'))

	if not frappe.get_meta("Employee").get_field("custom_hours_per_month"):
		custom_fields["Employee"].append(dict(fieldname='custom_hours_per_month', label='Hours Per Month',
						fieldtype='Float', insert_after='custom_payroll_payable_account'))

	if not frappe.get_meta("Additional Salary").get_field("is_company_contribution"):
		custom_fields["Additional Salary"].append(dict(fieldname='is_company_contribution', label='Is Company Contribution',
						fieldtype='Check', insert_after='column_break_8'))

	if not frappe.get_meta("Salary Structure Assignment").get_field("custom_annual_bonus"):
		custom_fields["Salary Structure Assignment"].append(dict(fieldname="custom_annual_bonus", label="Annual Bonus",
						fieldtype="Currency", insert_after="base", allow_on_submit=True))
						
	# COIDA-related custom fields
	if not frappe.get_meta("Payroll Settings").get_field("custom_coida_salary_component"):
		custom_fields["Payroll Settings"].append(dict(fieldname='custom_coida_salary_component', label='COIDA Salary Component',
						fieldtype='Link', options="Salary Component", insert_after='sdl_salary_component',
						description="Salary Component used for Compensation for Occupational Injuries and Diseases Act (COIDA)"))
						
	if not frappe.get_meta("Company").get_field("custom_coida_registration_number"):
		custom_fields["Company"].append(dict(fieldname='custom_coida_registration_number', label='COIDA Registration Number',
						fieldtype='Data', insert_after='tax_id', description="COIDA Registration Number for the company"))
	
	# Add VAT number field to Company
	if not frappe.get_meta("Company").get_field("vat_number"):
		custom_fields["Company"].append(dict(fieldname='vat_number', label='VAT Number',
						fieldtype='Data', insert_after='tax_id', description="South African VAT Number",
						length=10))
						
	if not frappe.get_meta("Employee").get_field("custom_id_number"):
		custom_fields["Employee"].append(dict(fieldname='custom_id_number', label='ID Number',
						fieldtype='Data', insert_after='passport_number', description="South African ID Number", length=13))

	create_custom_fields(custom_fields)
	rename_duplicate_fields(custom_fields)

def rename_duplicate_fields(custom_fields):
	"""
	Handles duplicate fields by either deleting or renaming them.
	
	This ensures we don't have both a regular field and a custom_prefixed
	version of the same field.
	"""
	from frappe.custom.doctype.custom_field.custom_field import rename_fieldname

	for doctype in custom_fields:
		for field in custom_fields[doctype]:
			field_name = frappe.db.get_value("Custom Field", {'dt': doctype, "fieldname": field["fieldname"]})
			custom_field_name = frappe.db.get_value("Custom Field", {'dt': doctype, "fieldname": "custom_" + field["fieldname"]})
			if field_name and custom_field_name:
				frappe.db.delete("Custom Field", custom_field_name)
			elif not field_name and custom_field_name:
				rename_fieldname(custom_field_name, field["fieldname"])
				
def validate_south_african_id(id_number):
	"""
	Validate South African ID number format and checksum.
	
	Format: YYMMDD SSSS CAZ
	- YYMMDD: Date of birth
	- SSSS: Gender (Females: 0000-4999, Males: 5000-9999)
	- C: Citizenship (0: SA, 1: Permanent resident)
	- A: Usually 8 or 9 (historical)
	- Z: Checksum digit
	
	Returns:
		bool: True if valid, False otherwise
	"""
	if not id_number or not id_number.isdigit() or len(id_number) != 13:
		return False
		
	# Birth date validation
	year = int(id_number[:2])
	month = int(id_number[2:4])
	day = int(id_number[4:6])
	
	if month < 1 or month > 12 or day < 1 or day > 31:
		return False
		
	# Calculate checksum using Luhn algorithm
	checksum = 0
	for i, digit in enumerate(id_number[:-1]):
		num = int(digit)
		if i % 2 == 0:
			checksum += num
		else:
			checksum += (num * 2 if num * 2 <= 9 else num * 2 - 9)
			
	check_digit = (10 - (checksum % 10)) % 10
	return check_digit == int(id_number[-1])
