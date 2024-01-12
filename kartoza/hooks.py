from . import __version__ as app_version

app_name = "kartoza"
app_title = "Kartoza"
app_publisher = "Aerele"
app_description = "kartoza"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "kartoza@gmail.com"
app_license = "MIT"


fixtures = [
	{"dt": "Property Setter", "filters": [["doc_type", '=', 'Salary Structure Assignment'], ["field_name", '=', 'variable']]	},
	{"dt": "Property Setter", "filters": [["doc_type", '=', 'Salary Structure Assignment'], ["field_name", '=', 'base']]	},
	{"dt": "Property Setter", "filters": [["doc_type", '=', 'Salary Slip'], ["field_name", '=', 'payroll_entry']]	},
	{"dt": "Custom Field", "filters": [["dt", '=', 'Employee'], ["fieldname", '=', 'custom_employee_type']]	},
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/kartoza/css/kartoza.css"
# app_include_js = "/assets/kartoza/js/kartoza.js"

# include js, css files in header of web template
# web_include_css = "/assets/kartoza/css/kartoza.css"
# web_include_js = "/assets/kartoza/js/kartoza.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "kartoza/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Payroll Entry" : "custom_js/payroll_entry.js",
	"Employee" : "custom_js/employee.js",
	"Employee Benefit Claim" : "custom_js/employee_benefit_claim.js",
	"Salary Structure": "custom_js/salary_structure.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

#from erpnext.payroll.doctype.payroll_entry import payroll_entry as _payroll_entry
from hrms.payroll.doctype.payroll_entry import payroll_entry as _payroll_entry
from kartoza.custom_py import payroll_entry as _custom_payroll_entry
_payroll_entry.get_payroll_entry_bank_entries = _custom_payroll_entry.get_payroll_entry_bank_entries

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

before_install = "kartoza.install.before_install"
after_install = "kartoza.install.after_install"

after_migrate = [
	"kartoza.install.make_custom_fields"
]

# after_install = "kartoza.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "kartoza.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
	"Salary Slip": "kartoza.custom_py.salary_slip.CustomSalarySlip",
	"Payroll Entry": "kartoza.custom_py.payroll_entry.CustomPayrollEntry"
# 	"ToDo": "custom_app.overrides.CustomToDo"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }
doc_events = {
	"Journal Entry": {
		"on_trash": "kartoza.doc_events.jv_on_trash",
		"on_cancel": "kartoza.doc_events.jv_on_cancel"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"kartoza.tasks.all"
# 	],
# 	"daily": [
# 		"kartoza.tasks.daily"
# 	],
# 	"hourly": [
# 		"kartoza.tasks.hourly"
# 	],
# 	"weekly": [
# 		"kartoza.tasks.weekly"
# 	]
# 	"monthly": [
# 		"kartoza.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "kartoza.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "kartoza.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "kartoza.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"kartoza.auth.validate"
# ]

