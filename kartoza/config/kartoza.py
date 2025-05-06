from frappe import _

def get_data():
    return [
        {
            "label": _("COIDA Management"),
            "items": [
                {
                    "type": "doctype",
                    "name": "COIDA Settings",
                    "description": _("Configure COIDA Settings"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "COIDA Annual Return",
                    "description": _("Annual Return for Compensation for Occupational Injuries and Diseases Act"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Workplace Injury",
                    "description": _("Record and manage workplace injuries"),
                },
                {
                    "type": "doctype",
                    "name": "OID Claim",
                    "description": _("Manage Occupational Injury and Disease claims"),
                }
            ]
        },
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
            "label": _("Tax Certificates and Reconciliations"),
            "items": [
                {
                    "type": "doctype",
                    "name": "EMP501 Reconciliation",
                    "description": _("Bi-annual Employer Reconciliation Declaration"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "IRP5 Certificate",
                    "description": _("Employee Tax Certificate"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "IT3a Certificate",
                    "description": _("Employee Tax Certificate for Investment Income"),
                },
                {
                    "type": "doctype",
                    "name": "SARS e-Filing Integration",
                    "description": _("Configure SARS e-Filing Integration"),
                }
            ]
        },
        {
            "label": _("Regulatory Compliance"),
            "items": [
                {
                    "type": "doctype",
                    "name": "B-BBEE Certificate",
                    "description": _("Broad-Based Black Economic Empowerment Certificate"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Employment Equity Report",
                    "description": _("Employment Equity Reporting"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "SETA Report",
                    "description": _("Sector Education and Training Authority Report"),
                }
            ]
        },
        {
            "label": _("Bargaining Councils"),
            "items": [
                {
                    "type": "doctype",
                    "name": "Bargaining Council",
                    "description": _("Configure Bargaining Councils"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Bargaining Council Deduction",
                    "description": _("Bargaining Council Deductions"),
                }
            ]
        },
        {
            "label": _("South African VAT"),
            "items": [
                {
                    "type": "doctype",
                    "name": "South African VAT Settings",
                    "description": _("Configure South African VAT Settings"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "VAT201 Return",
                    "description": _("VAT201 Return Submission"),
                    "onboard": 1,
                },
                {
                    "type": "report",
                    "name": "VAT Analysis",
                    "doctype": "Sales Invoice",
                    "is_query_report": True,
                    "description": _("VAT Analysis Report"),
                },
                {
                    "type": "doctype",
                    "name": "VAT Vendor Type",
                    "description": _("Configure VAT Vendor Types"),
                }
            ]
        },
        {
            "label": _("South African Leave Management"),
            "items": [
                {
                    "type": "doctype",
                    "name": "South African Holiday",
                    "description": _("South African Public Holidays"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Leave Policy Assignment",
                    "description": _("South African Leave Policy Assignment"),
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
