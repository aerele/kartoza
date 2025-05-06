from frappe import _

def get_data():
    return [
        {
            "label": _("South African Statutory Reports"),
            "items": [
                {
                    "type": "doctype",
                    "name": "EMP201 Submission",
                    "description": _("Monthly SARS EMP201 Return for PAYE, UIF, SDL and ETI"),
                    "onboard": 1,
                },
                {
                    "type": "report",
                    "name": "EMP201 Report",
                    "doctype": "EMP201 Submission",
                    "is_query_report": True,
                    "description": _("Report for EMP201 Submissions"),
                }
            ]
        },
        {
            "label": _("South African Payroll"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Employee ETI Log",
                    "description": _("Employment Tax Incentive (ETI) Log"),
                },
                {
                    "type": "doctype",
                    "name": "ETI Slab",
                    "description": _("ETI Calculation Slabs"),
                },
                {
                    "type": "doctype",
                    "name": "Medical Tax Credit Rate",
                    "description": _("Medical Tax Credit Rates"),
                },
                {
                    "type": "doctype",
                    "name": "Tax Rebates and Medical Tax Credit",
                    "description": _("Tax Rebates and Medical Tax Credit"),
                },
                {
                    "type": "doctype",
                    "name": "Employee Type",
                    "description": _("Employee Type for South African Payroll"),
                }
            ]
        },
        {
            "label": _("Setup"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Employee Payroll Frequency",
                    "description": _("Configure Employee Payroll Frequency"),
                },
                {
                    "type": "doctype",
                    "name": "Employee Private Benefit",
                    "description": _("Configure Employee Private Benefits"),
                }
            ]
        }
    ]
