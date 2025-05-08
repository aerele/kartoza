import unittest
from datetime import date, datetime, timedelta

import frappe
from frappe.utils import (
    add_months,
    cint,
    flt,
    getdate,
    nowdate,
)

from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip
from hrms.payroll.doctype.salary_structure.test_salary_structure import make_salary_structure
from kartoza.custom_py.salary_slip import (
    CustomSalarySlip,
    calculate_age,
    get_eti_deduction,
    get_retirement_annuity,
    get_tax_rebate
)


class TestSouthAfricanPayroll(unittest.TestCase):
    """
    Test cases for South African payroll functionality including:
    - Employment Tax Incentive (ETI) calculations
    - Tax rebate calculations based on age
    - Retirement annuity calculations
    - Medical aid tax credits
    """
    
    @classmethod
    def setUpClass(cls):
        # Create test data
        cls.create_test_company()
        cls.create_test_employee()
        cls.create_tax_parameters()
        cls.create_tax_settings()
        cls.create_eti_slab()
        
    @classmethod
    def tearDownClass(cls):
        # Clean up test data
        cls.clean_up_test_data()
    
    @classmethod
    def create_test_company(cls):
        if not frappe.db.exists("Company", "_Test SA Company"):
            company = frappe.new_doc("Company")
            company.company_name = "_Test SA Company"
            company.abbr = "TSA"
            company.default_currency = "ZAR"
            company.country = "South Africa"
            company.coida_registration_number = "TEST123456789"
            company.insert()
            
    @classmethod
    def create_test_employee(cls):
        # Create employee age groups for testing different rebate scenarios
        # Standard employee (under 65)
        if not frappe.db.exists("Employee", "_TSA-EMP-00001"):
            employee = frappe.new_doc("Employee")
            employee.first_name = "John"
            employee.last_name = "Doe"
            employee.date_of_birth = add_months(getdate(), -(30 * 12))  # 30 years old
            employee.date_of_joining = add_months(getdate(), -12)  # 1 year of service
            employee.company = "_Test SA Company"
            employee.status = "Active"
            employee.gender = "Male"
            employee.employee_number = "_TSA-EMP-00001"
            employee.custom_hours_per_month = 160
            employee.custom_id_number = "8001015009087"
            employee.custom_employee_type = "Normal"
            employee.insert()
            
        # Employee over 65 (for secondary rebate)
        if not frappe.db.exists("Employee", "_TSA-EMP-00002"):
            employee = frappe.new_doc("Employee")
            employee.first_name = "Jane"
            employee.last_name = "Doe"
            employee.date_of_birth = add_months(getdate(), -(67 * 12))  # 67 years old
            employee.date_of_joining = add_months(getdate(), -24)  # 2 years of service
            employee.company = "_Test SA Company"
            employee.status = "Active"
            employee.gender = "Female"
            employee.employee_number = "_TSA-EMP-00002"
            employee.custom_hours_per_month = 160
            employee.custom_id_number = "5501015009087" 
            employee.custom_employee_type = "Normal"
            employee.insert()
            
        # Employee over 75 (for tertiary rebate)
        if not frappe.db.exists("Employee", "_TSA-EMP-00003"):
            employee = frappe.new_doc("Employee")
            employee.first_name = "Robert"
            employee.last_name = "Smith"
            employee.date_of_birth = add_months(getdate(), -(77 * 12))  # 77 years old
            employee.date_of_joining = add_months(getdate(), -36)  # 3 years of service
            employee.company = "_Test SA Company"
            employee.status = "Active"
            employee.gender = "Male"
            employee.employee_number = "_TSA-EMP-00003"
            employee.custom_hours_per_month = 80  # Part-time
            employee.custom_id_number = "4501015009087"
            employee.custom_employee_type = "Normal"
            employee.insert()
    
    @classmethod
    def create_tax_parameters(cls):
        # Create payroll period
        if not frappe.db.exists("Payroll Period", f"_Test Payroll Period {date.today().year}"):
            payroll_period = frappe.new_doc("Payroll Period")
            payroll_period.name = f"_Test Payroll Period {date.today().year}"
            payroll_period.company = "_Test SA Company"
            payroll_period.start_date = date(date.today().year, 3, 1)
            payroll_period.end_date = date(date.today().year + 1, 2, 28)
            payroll_period.insert()
            
        # Create Tax Rebate Rates
        if not frappe.db.exists("Tax Rebates Rate", f"_Test Tax Rebates {date.today().year}"):
            rebate = frappe.new_doc("Tax Rebates Rate")
            rebate.payroll_period = f"_Test Payroll Period {date.today().year}"
            rebate.primary = 17235  # Example values in ZAR - annual amounts
            rebate.secondary = 9444
            rebate.tertiary = 3145
            rebate.insert()
            
        # Create Medical Tax Credit Rates
        if not frappe.db.exists("Medical Tax Credit Rate", f"_Test Medical Credits {date.today().year}"):
            medical = frappe.new_doc("Medical Tax Credit Rate")
            medical.payroll_period = f"_Test Payroll Period {date.today().year}"
            medical.no_dependant = 347  # Example values in ZAR - monthly amounts
            medical.one_dependant = 694
            medical.two_dependant = 902
            medical.additional_dependant = 605
            medical.insert()
            
    @classmethod
    def create_tax_settings(cls):
        # Create income tax slab
        if not frappe.db.exists("Income Tax Slab", f"_Test Tax Slab {date.today().year}"):
            tax_slab = frappe.new_doc("Income Tax Slab")
            tax_slab.name = f"_Test Tax Slab {date.today().year}"
            tax_slab.effective_from = date(date.today().year, 3, 1)
            tax_slab.company = "_Test SA Company"
            tax_slab.currency = "ZAR"
            
            # Add tax brackets
            tax_slab.append("slabs", {
                "from_amount": 0,
                "to_amount": 237100,
                "percent_deduction": 18,
                "condition": ""
            })
            
            tax_slab.append("slabs", {
                "from_amount": 237101,
                "to_amount": 370500,
                "percent_deduction": 26,
                "condition": ""
            })
            
            tax_slab.append("slabs", {
                "from_amount": 370501,
                "to_amount": 512800,
                "percent_deduction": 31,
                "condition": ""
            })
            
            tax_slab.append("slabs", {
                "from_amount": 512801,
                "to_amount": 673000,
                "percent_deduction": 36,
                "condition": ""
            })
            
            tax_slab.append("slabs", {
                "from_amount": 673001,
                "to_amount": 857900,
                "percent_deduction": 39,
                "condition": ""
            })
            
            tax_slab.append("slabs", {
                "from_amount": 857901,
                "to_amount": 1817000,
                "percent_deduction": 41,
                "condition": ""
            })
            
            tax_slab.append("slabs", {
                "from_amount": 1817001,
                "to_amount": 0,
                "percent_deduction": 45,
                "condition": ""
            })
            
            tax_slab.insert()
            
    @classmethod
    def create_eti_slab(cls):
        if not frappe.db.exists("ETI Slab", f"_Test ETI Slab {date.today().year}"):
            eti_slab = frappe.new_doc("ETI Slab")
            eti_slab.name = f"_Test ETI Slab {date.today().year}"
            eti_slab.start_date = date(date.today().year, 3, 1)
            eti_slab.minimum_age = 18
            eti_slab.maximum_age = 29
            eti_slab.hours_in_a_month = 160
            
            # Add ETI brackets
            eti_slab.append("eti_slabs", {
                "from_amount": 0,
                "to_amount": 2000,
                "first_qualifying_12_months": "monthly_remuneration * 0.5",
                "second_qualifying_12_months": "monthly_remuneration * 0.25"
            })
            
            eti_slab.append("eti_slabs", {
                "from_amount": 2001,
                "to_amount": 4500,
                "first_qualifying_12_months": "1000",
                "second_qualifying_12_months": "500"
            })
            
            eti_slab.append("eti_slabs", {
                "from_amount": 4501,
                "to_amount": 6500,
                "first_qualifying_12_months": "1000 - (0.5 * (monthly_remuneration - 4500))",
                "second_qualifying_12_months": "500 - (0.25 * (monthly_remuneration - 4500))"
            })
            
            eti_slab.append("eti_slabs", {
                "from_amount": 6501,
                "to_amount": 9999999,
                "first_qualifying_12_months": "0",
                "second_qualifying_12_months": "0"
            })
            
            eti_slab.insert()
            eti_slab.submit()  # ETI slabs need to be submitted
            
    @classmethod
    def clean_up_test_data(cls):
        """Clean up test data after tests are complete"""
        for doctype, filters in [
            ("Salary Slip", {"company": "_Test SA Company"}),
            ("Employee", {"company": "_Test SA Company"}),
            ("ETI Slab", {"name": f"_Test ETI Slab {date.today().year}"}),
            ("Income Tax Slab", {"name": f"_Test Tax Slab {date.today().year}"}),
            ("Medical Tax Credit Rate", {"name": f"_Test Medical Credits {date.today().year}"}),
            ("Tax Rebates Rate", {"name": f"_Test Tax Rebates {date.today().year}"}),
            ("Payroll Period", {"name": f"_Test Payroll Period {date.today().year}"}),
        ]:
            records = frappe.get_all(doctype, filters=filters)
            for record in records:
                if frappe.db.exists(doctype, record.name):
                    doc = frappe.get_doc(doctype, record.name)
                    if doc.docstatus == 1:
                        doc.cancel()
                    frappe.delete_doc(doctype, record.name, force=True, ignore_permissions=True)
    
    def test_calculate_age(self):
        """Test age calculation function"""
        # Test with date object
        dob = date(1990, 1, 1)
        today = date.today()
        expected_age = today.year - 1990 - ((today.month, today.day) < (1, 1))
        self.assertEqual(calculate_age(dob), expected_age)
        
        # Test with string date
        dob_str = "1985-05-15"
        today = date.today()
        expected_age = today.year - 1985 - ((today.month, today.day) < (5, 15))
        self.assertEqual(calculate_age(dob_str), expected_age)
        
        # Test error handling
        with self.assertRaises(ValueError):
            calculate_age(None)
            
        with self.assertRaises(ValueError):
            calculate_age("invalid-date")
    
    def test_tax_rebate_calculation(self):
        """Test tax rebate calculation for different age groups"""
        # Create a mock salary slip for testing
        slip = frappe.new_doc("Salary Slip")
        slip.employee = "_TSA-EMP-00001"
        slip.payroll_period = f"_Test Payroll Period {date.today().year}"
        
        # Test rebate for employee under 65 (primary rebate only)
        dob_under_65 = add_months(getdate(), -(30 * 12))
        rebate = get_tax_rebate(slip, dob_under_65)
        expected_rebate = 17235 / 12  # Monthly primary rebate
        self.assertAlmostEqual(rebate, expected_rebate, places=2)
        
        # Test rebate for employee over 65 (primary + secondary rebate)
        dob_over_65 = add_months(getdate(), -(67 * 12))
        rebate = get_tax_rebate(slip, dob_over_65)
        expected_rebate = (17235 + 9444) / 12  # Monthly primary + secondary rebate
        self.assertAlmostEqual(rebate, expected_rebate, places=2)
        
        # Test rebate for employee over 75 (primary + secondary + tertiary rebate)
        dob_over_75 = add_months(getdate(), -(77 * 12))
        rebate = get_tax_rebate(slip, dob_over_75)
        expected_rebate = (17235 + 9444 + 3145) / 12  # Monthly primary + secondary + tertiary rebate
        self.assertAlmostEqual(rebate, expected_rebate, places=2)
    
    def create_test_salary_slip(self, employee_id, earnings_amount=30000):
        """Helper method to create a test salary slip"""
        # Create salary structure for testing
        salary_structure = make_salary_structure(
            f"_Test SA Salary Structure {employee_id}",
            "Monthly",
            employee=employee_id,
            company="_Test SA Company",
            currency="ZAR"
        )
        
        # Create earnings component
        if not frappe.db.exists("Salary Component", "_Test Basic Salary"):
            component = frappe.new_doc("Salary Component")
            component.salary_component = "_Test Basic Salary"
            component.custom_allow_for_eti = 1
            component.type = "Earning"
            component.is_tax_applicable = 1
            component.round_to_the_nearest_integer = 1
            component.insert()
            
        # Create tax component
        if not frappe.db.exists("Salary Component", "_Test PAYE"):
            component = frappe.new_doc("Salary Component")
            component.salary_component = "_Test PAYE"
            component.type = "Deduction"
            component.variable_based_on_taxable_salary = 1
            component.round_to_the_nearest_integer = 1
            component.insert()
        
        # Create salary slip
        slip = frappe.new_doc("Salary Slip")
        slip.salary_structure = salary_structure
        slip.employee = employee_id
        slip.company = "_Test SA Company"
        slip.start_date = getdate().replace(day=1)
        slip.end_date = getdate().replace(day=28)
        slip.payroll_frequency = "Monthly"
        slip.posting_date = getdate()
        slip.insert()
        
        # Ensure the earnings component is properly set
        found = False
        for earning in slip.earnings:
            if earning.salary_component == "_Test Basic Salary":
                earning.amount = earnings_amount
                found = True
                break
                
        if not found:
            slip.append("earnings", {
                "salary_component": "_Test Basic Salary",
                "amount": earnings_amount,
                "is_tax_applicable": 1
            })
            
        slip.save()
        return slip
    
    def test_eti_calculation(self):
        """Test ETI calculation for eligible employees"""
        # Test for eligible employee (age within range)
        slip = self.create_test_salary_slip("_TSA-EMP-00001", earnings_amount=4000)
        eti_amount = get_eti_deduction(slip)
        # For a 4000 ZAR salary in the first 12 months, ETI should be 1000 ZAR
        self.assertEqual(eti_amount, 1000)
        
        # Test for employee outside age range (should be 0)
        slip = self.create_test_salary_slip("_TSA-EMP-00002", earnings_amount=4000)
        eti_amount = get_eti_deduction(slip)
        self.assertEqual(eti_amount, 0)
        
        # Test for eligible employee with partial hours
        slip = self.create_test_salary_slip("_TSA-EMP-00003", earnings_amount=4000)
        eti_amount = get_eti_deduction(slip)
        # Employee works 80 hours out of 160 standard - should get 50% of ETI
        self.assertEqual(eti_amount, 0)  # Should be 0 since employee is not in eligible age range
    
    def test_end_to_end_salary_slip(self):
        """Test the entire salary slip calculation process"""
        # Create and process a salary slip
        slip = self.create_test_salary_slip("_TSA-EMP-00001", earnings_amount=30000)
        slip.calculate_net_pay()
        
        # Verify it's using the custom salary slip class
        self.assertTrue(isinstance(slip, CustomSalarySlip))
        
        # Verify tax calculation includes rebates
        self.assertTrue(hasattr(slip, 'tax_rebate'))
        
        # Verify ETI is calculated
        self.assertTrue(hasattr(slip, 'custom_monthly_eti'))
