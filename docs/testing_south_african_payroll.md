# Testing South African Payroll in Kartoza

This guide explains how the test suite for South African payroll works in the Kartoza module and how to implement more comprehensive end-to-end testing.

## Understanding the Test Framework

### Overview of Frappe Testing

The Kartoza module uses the standard unittest framework integrated with Frappe's test runner. Tests in Frappe/ERPNext follow these principles:

1. **Test Isolation**: Each test runs in its own transaction, which gets rolled back at the end, ensuring tests don't affect each other
2. **Test Data Setup**: Test data is created within the test class, typically in `setUpClass` or `setUp` methods
3. **Test Cleanup**: Resources are properly cleaned up in `tearDown` or `tearDownClass` methods
4. **Independence**: Tests should be independent of production data and other tests

### How `test_south_african_payroll.py` Works

The `test_south_african_payroll.py` file contains unit tests that verify different components of South African payroll functionality:

1. **Test Structure**:
   - `TestSouthAfricanPayroll` class inherits from `unittest.TestCase`
   - Setup methods create test data (companies, employees, tax parameters)
   - Individual test methods verify specific functionality
   - Cleanup methods ensure all test data is removed

2. **Test Data Creation**:
   - `create_test_company()` - Creates a test South African company
   - `create_test_employee()` - Creates employees with different ages for testing
   - `create_tax_parameters()` - Creates tax configuration (rebates, medical credits)
   - `create_tax_settings()` - Creates income tax slabs
   - `create_eti_slab()` - Creates ETI calculation formulas

3. **Test Methods**:
   - `test_calculate_age()` - Tests the age calculation function
   - `test_tax_rebate_calculation()` - Tests rebates for different age groups
   - `test_eti_calculation()` - Tests ETI calculations for different scenarios
   - `test_end_to_end_salary_slip()` - Tests the entire salary slip process

## Running the Tests

### Command Line Execution

To run the South African payroll tests from the command line:

```bash
# Run specific test file
bench --site your-site-name run-tests --app kartoza --test kartoza.kartoza.tests.test_south_african_payroll

# Run specific test case
bench --site your-site-name run-tests --app kartoza --test kartoza.kartoza.tests.test_south_african_payroll.TestSouthAfricanPayroll

# Run specific test method
bench --site your-site-name run-tests --app kartoza --test kartoza.kartoza.tests.test_south_african_payroll.TestSouthAfricanPayroll.test_eti_calculation
```

### Running in Development

During development, you can run tests directly from VS Code using the Python Test Explorer extension, or by using the Frappe test runner in the web UI (Developer Tools > Run Tests).

## How Tests Are Triggered

Tests in the Frappe framework can be triggered in several ways:

1. **Manual Execution**: Running test commands as shown above
2. **CI/CD Pipeline**: Automatically running when code is pushed (using GitHub Actions, GitLab CI, etc.)
3. **Pre-commit Hooks**: Running tests before allowing commits
4. **Scheduled Jobs**: Running tests on a schedule to detect regression

The `test_south_african_payroll.py` file doesn't automatically run; it must be triggered through one of these methods.

## Creating End-to-End Testing Scripts

While unit tests focus on specific components, end-to-end tests validate the entire workflow. Here's how to create an end-to-end test script for the employee lifecycle from hiring to payment:

### End-to-End Test Script

Below is a comprehensive script that can be saved as `test_employee_lifecycle.py` in the `tests` directory:

```python
import unittest
import frappe
from frappe.utils import getdate, add_days, add_months
from datetime import date, timedelta

class TestEmployeeLifecycle(unittest.TestCase):
    """
    Test the complete employee lifecycle for South African payroll:
    1. Employee creation (hiring)
    2. Salary structure assignment
    3. Payroll entry creation
    4. Salary slip generation
    5. ETI calculation and verification
    6. Payment processing
    7. IRP5 certificate generation
    """
    
    @classmethod
    def setUpClass(cls):
        # Create test data that will be shared across all tests
        cls.create_test_company()
        cls.create_test_department()
        cls.create_tax_configuration()
        cls.create_salary_components()
        
    @classmethod
    def tearDownClass(cls):
        # Clean up all test data
        cls.clean_up_test_data()

    @classmethod
    def create_test_company(cls):
        if not frappe.db.exists("Company", "_Test SA Company"):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": "_Test SA Company",
                "abbr": "TSA",
                "default_currency": "ZAR",
                "country": "South Africa",
                "create_chart_of_accounts_based_on": "Standard Template",
                "chart_of_accounts": "Standard",
                "domain": "Manufacturing",
                "coida_registration_number": "TEST123456789",
                "default_holiday_list": "_Test Holiday List"
            })
            company.insert()
            
            # Create holiday list
            if not frappe.db.exists("Holiday List", "_Test Holiday List"):
                holiday_list = frappe.get_doc({
                    "doctype": "Holiday List",
                    "holiday_list_name": "_Test Holiday List",
                    "from_date": date(date.today().year, 1, 1),
                    "to_date": date(date.today().year, 12, 31)
                })
                holiday_list.insert()
                
                # Add public holidays
                holiday_list.append("holidays", {
                    "holiday_date": date(date.today().year, 1, 1),
                    "description": "New Year's Day"
                })
                holiday_list.save()
    
    @classmethod
    def create_test_department(cls):
        if not frappe.db.exists("Department", "_Test Department"):
            department = frappe.get_doc({
                "doctype": "Department",
                "department_name": "_Test Department",
                "company": "_Test SA Company",
                "is_group": 0
            })
            department.insert()
    
    @classmethod
    def create_tax_configuration(cls):
        # Create payroll period
        year = date.today().year
        if not frappe.db.exists("Payroll Period", f"_Test Payroll Period {year}"):
            payroll_period = frappe.get_doc({
                "doctype": "Payroll Period",
                "name": f"_Test Payroll Period {year}",
                "company": "_Test SA Company",
                "start_date": date(year, 3, 1),
                "end_date": date(year + 1, 2, 28)
            })
            payroll_period.insert()
            
        # Create income tax slab
        if not frappe.db.exists("Income Tax Slab", f"_Test Tax Slab {year}"):
            tax_slab = frappe.get_doc({
                "doctype": "Income Tax Slab",
                "name": f"_Test Tax Slab {year}",
                "effective_from": date(year, 3, 1),
                "company": "_Test SA Company",
                "currency": "ZAR",
                "slabs": [
                    {
                        "from_amount": 0,
                        "to_amount": 237100,
                        "percent_deduction": 18,
                        "condition": ""
                    },
                    {
                        "from_amount": 237101,
                        "to_amount": 370500,
                        "percent_deduction": 26,
                        "condition": ""
                    }
                ]
            })
            tax_slab.insert()
            
        # Create tax rebates
        if not frappe.db.exists("Tax Rebates Rate", f"_Test Tax Rebates {year}"):
            rebate = frappe.get_doc({
                "doctype": "Tax Rebates Rate",
                "payroll_period": f"_Test Payroll Period {year}",
                "primary": 17235,
                "secondary": 9444,
                "tertiary": 3145
            })
            rebate.insert()
            
        # Create medical tax credits
        if not frappe.db.exists("Medical Tax Credit Rate", f"_Test Medical Credits {year}"):
            medical = frappe.get_doc({
                "doctype": "Medical Tax Credit Rate",
                "payroll_period": f"_Test Payroll Period {year}",
                "no_dependant": 347,
                "one_dependant": 694,
                "two_dependant": 902,
                "additional_dependant": 605
            })
            medical.insert()
            
        # Create ETI slab
        if not frappe.db.exists("ETI Slab", f"_Test ETI Slab {year}"):
            eti_slab = frappe.get_doc({
                "doctype": "ETI Slab",
                "name": f"_Test ETI Slab {year}",
                "start_date": date(year, 3, 1),
                "minimum_age": 18,
                "maximum_age": 29,
                "hours_in_a_month": 160,
                "eti_slabs": [
                    {
                        "from_amount": 0,
                        "to_amount": 2000,
                        "first_qualifying_12_months": "monthly_remuneration * 0.5",
                        "second_qualifying_12_months": "monthly_remuneration * 0.25"
                    },
                    {
                        "from_amount": 2001,
                        "to_amount": 4500,
                        "first_qualifying_12_months": "1000",
                        "second_qualifying_12_months": "500"
                    }
                ]
            })
            eti_slab.insert()
            eti_slab.submit()
    
    @classmethod
    def create_salary_components(cls):
        # Create Basic salary component
        if not frappe.db.exists("Salary Component", "_Test Basic Salary"):
            component = frappe.get_doc({
                "doctype": "Salary Component",
                "salary_component": "_Test Basic Salary",
                "salary_component_abbr": "TBS",
                "type": "Earning",
                "is_tax_applicable": 1,
                "is_payable": 1,
                "custom_allow_for_eti": 1,
                "round_to_the_nearest_integer": 1
            })
            component.insert()
            
        # Create tax component (PAYE)
        if not frappe.db.exists("Salary Component", "_Test PAYE"):
            component = frappe.get_doc({
                "doctype": "Salary Component",
                "salary_component": "_Test PAYE",
                "salary_component_abbr": "TPAYE",
                "type": "Deduction",
                "variable_based_on_taxable_salary": 1,
                "round_to_the_nearest_integer": 1
            })
            component.insert()
            
        # Create UIF component
        if not frappe.db.exists("Salary Component", "_Test UIF"):
            component = frappe.get_doc({
                "doctype": "Salary Component",
                "salary_component": "_Test UIF",
                "salary_component_abbr": "TUIF",
                "type": "Deduction",
                "amount_based_on_formula": 1,
                "formula": "base * 0.01",
                "round_to_the_nearest_integer": 1
            })
            component.insert()
    
    def test_01_create_employee(self):
        """Test employee creation (hiring)"""
        # Create an employee who is eligible for ETI (age 18-29)
        if frappe.db.exists("Employee", "_TST-EMP-00001"):
            frappe.delete_doc("Employee", "_TST-EMP-00001")
            
        employee = frappe.get_doc({
            "doctype": "Employee",
            "employee_name": "John Test",
            "first_name": "John",
            "last_name": "Test",
            "date_of_birth": add_months(getdate(), -(25 * 12)),  # 25 years old
            "date_of_joining": getdate(),  # Today
            "company": "_Test SA Company",
            "gender": "Male",
            "status": "Active",
            "department": "_Test Department",
            "employment_type": "Full-time",
            "custom_employee_type": "Normal",
            "custom_hours_per_month": 160,
            "custom_id_number": "9001015009087",
            "holiday_list": "_Test Holiday List"
        })
        employee.insert()
        
        # Verify employee was created
        self.assertTrue(frappe.db.exists("Employee", employee.name))
        self.assertEqual(employee.status, "Active")
        
        # Store employee for use in subsequent tests
        self.__class__.test_employee = employee.name
        return employee
    
    def test_02_create_salary_structure(self):
        """Test salary structure creation and assignment"""
        # Create salary structure
        if not hasattr(self.__class__, "test_employee"):
            self.test_01_create_employee()
            
        if frappe.db.exists("Salary Structure", "_Test SA Structure"):
            frappe.delete_doc("Salary Structure", "_Test SA Structure")
            
        salary_structure = frappe.get_doc({
            "doctype": "Salary Structure",
            "name": "_Test SA Structure",
            "company": "_Test SA Company",
            "is_active": "Yes",
            "payroll_frequency": "Monthly",
            "salary_component": "_Test Basic Salary",
            "payment_account": frappe.get_value("Account", {"account_name": "Cash", "company": "_Test SA Company"})
        })
        
        # Add earnings and deductions
        salary_structure.append("earnings", {
            "salary_component": "_Test Basic Salary",
            "abbr": "TBS",
            "amount": 10000,
            "formula": "",
            "depends_on_payment_days": 1
        })
        
        salary_structure.append("deductions", {
            "salary_component": "_Test PAYE",
            "abbr": "TPAYE",
            "condition": "",
            "formula": "",
            "variable_based_on_taxable_salary": 1
        })
        
        salary_structure.append("deductions", {
            "salary_component": "_Test UIF",
            "abbr": "TUIF",
            "amount": 0,
            "formula": "base * 0.01",
            "depends_on_payment_days": 1
        })
        
        salary_structure.insert()
        
        # Create salary structure assignment
        if frappe.db.exists("Salary Structure Assignment", {"employee": self.__class__.test_employee}):
            frappe.db.sql("""
                DELETE FROM `tabSalary Structure Assignment`
                WHERE employee = %s
            """, self.__class__.test_employee)
            
        assignment = frappe.get_doc({
            "doctype": "Salary Structure Assignment",
            "employee": self.__class__.test_employee,
            "salary_structure": salary_structure.name,
            "from_date": getdate(),
            "base": 10000,
            "variable": 0,
            "company": "_Test SA Company",
            "currency": "ZAR"
        })
        assignment.insert()
        
        # Verify assignment was created
        self.assertTrue(frappe.db.exists("Salary Structure Assignment", {"employee": self.__class__.test_employee}))
        
        return salary_structure
    
    def test_03_create_payroll_period_and_entry(self):
        """Test payroll entry creation and processing"""
        if not hasattr(self.__class__, "test_employee"):
            self.test_01_create_employee()
            self.test_02_create_salary_structure()
            
        # Create payroll entry
        payroll_entry = frappe.get_doc({
            "doctype": "Payroll Entry",
            "company": "_Test SA Company",
            "payroll_frequency": "Monthly",
            "start_date": getdate().replace(day=1),  # First day of current month
            "end_date": add_days(getdate().replace(day=1), 30),  # Approximately last day
            "payment_account": frappe.get_value("Account", {"account_name": "Cash", "company": "_Test SA Company"}),
            "currency": "ZAR",
            "exchange_rate": 1.0,
            "payroll_payable_account": frappe.get_value("Account", 
                {"account_type": "Payable", "company": "_Test SA Company", "is_group": 0})
        })
        payroll_entry.insert()
        
        # Add employee to payroll entry
        payroll_entry.get_emp_list()
        
        # Verify employee is in payroll entry
        has_employee = False
        for employee in payroll_entry.employees:
            if employee.employee == self.__class__.test_employee:
                has_employee = True
                break
                
        self.assertTrue(has_employee, "Employee not added to payroll entry")
        
        # Create salary slips
        payroll_entry.create_salary_slips()
        
        # Verify salary slip was created
        salary_slip = frappe.get_all("Salary Slip", 
            filters={"employee": self.__class__.test_employee, "docstatus": 0},
            limit=1
        )
        
        self.assertTrue(salary_slip, "Salary slip not created")
        
        # Get the salary slip
        self.__class__.salary_slip = frappe.get_doc("Salary Slip", salary_slip[0].name)
        
        return payroll_entry
    
    def test_04_verify_salary_slip_calculations(self):
        """Test salary slip calculation and ETI"""
        if not hasattr(self.__class__, "salary_slip"):
            self.test_03_create_payroll_period_and_entry()
            
        salary_slip = self.__class__.salary_slip
        
        # Submit the salary slip
        salary_slip.submit()
        
        # Verify salary slip was submitted
        self.assertEqual(salary_slip.docstatus, 1, "Salary slip not submitted")
        
        # Verify ETI calculation
        self.assertTrue(hasattr(salary_slip, "custom_monthly_eti"), "ETI not calculated")
        
        # Employee is 25 years old and should be eligible for ETI
        self.assertGreater(salary_slip.custom_monthly_eti, 0, "ETI amount should be greater than 0")
        
        # Verify tax calculation
        tax_deduction = False
        for deduction in salary_slip.deductions:
            if deduction.salary_component == "_Test PAYE":
                tax_deduction = True
                self.assertTrue(deduction.amount >= 0, "Tax amount invalid")
                
        self.assertTrue(tax_deduction, "Tax component not found in salary slip")
        
        # Verify UIF calculation
        uif_deduction = False
        for deduction in salary_slip.deductions:
            if deduction.salary_component == "_Test UIF":
                uif_deduction = True
                self.assertEqual(deduction.amount, salary_slip.base * 0.01, "UIF calculation incorrect")
                
        self.assertTrue(uif_deduction, "UIF component not found in salary slip")
        
        return salary_slip
    
    def test_05_process_payroll_and_generate_irp5(self):
        """Test payroll processing and IRP5 generation"""
        if not hasattr(self.__class__, "salary_slip"):
            self.test_04_verify_salary_slip_calculations()
            
        # Create an IRP5 certificate for the employee
        irp5 = frappe.get_doc({
            "doctype": "IRP5 Certificate",
            "employee": self.__class__.test_employee,
            "employee_name": "John Test",
            "tax_year": date.today().year,
            "company": "_Test SA Company",
            "period_from": date(date.today().year, 3, 1),
            "period_to": date(date.today().year+1, 2, 28)
        })
        
        # Add the salary slip's income details
        slip = self.__class__.salary_slip
        
        irp5.append("income_details", {
            "income_code": "3601",  # Normal income code
            "description": "Normal Income",
            "amount": slip.gross_pay
        })
        
        # Add the salary slip's deduction details
        for deduction in slip.deductions:
            if deduction.salary_component == "_Test PAYE":
                irp5.append("deduction_details", {
                    "deduction_code": "4102",  # PAYE code
                    "description": "PAYE",
                    "amount": deduction.amount
                })
            elif deduction.salary_component == "_Test UIF":
                irp5.append("deduction_details", {
                    "deduction_code": "4141",  # UIF code
                    "description": "UIF",
                    "amount": deduction.amount
                })
        
        irp5.insert()
        
        # Verify IRP5 was created
        self.assertTrue(frappe.db.exists("IRP5 Certificate", irp5.name))
        
        # Submit the IRP5
        irp5.submit()
        
        # Verify IRP5 was submitted
        self.assertEqual(irp5.docstatus, 1, "IRP5 certificate not submitted")
        
        return irp5
    
    @classmethod
    def clean_up_test_data(cls):
        """Clean up all test data created by this test class"""
        # Cancel and delete all documents in reverse order
        
        # IRP5 certificates
        irp5_certs = frappe.get_all("IRP5 Certificate", 
            filters={"company": "_Test SA Company", "docstatus": 1})
        for cert in irp5_certs:
            doc = frappe.get_doc("IRP5 Certificate", cert.name)
            doc.cancel()
            frappe.delete_doc("IRP5 Certificate", doc.name, force=True)
        
        # Salary slips
        slips = frappe.get_all("Salary Slip", 
            filters={"company": "_Test SA Company", "docstatus": 1})
        for slip in slips:
            doc = frappe.get_doc("Salary Slip", slip.name)
            doc.cancel()
            frappe.delete_doc("Salary Slip", doc.name, force=True)
            
        # Salary structure assignments
        assignments = frappe.get_all("Salary Structure Assignment", 
            filters={"company": "_Test SA Company"})
        for assignment in assignments:
            frappe.delete_doc("Salary Structure Assignment", assignment.name, force=True)
            
        # Salary structures
        structures = frappe.get_all("Salary Structure", 
            filters={"company": "_Test SA Company"})
        for structure in structures:
            frappe.delete_doc("Salary Structure", structure.name, force=True)
            
        # Employees
        if hasattr(cls, "test_employee") and cls.test_employee:
            frappe.delete_doc("Employee", cls.test_employee, force=True)
            
        # ETI slabs (submitted documents need to be cancelled first)
        slabs = frappe.get_all("ETI Slab", 
            filters={"name": f"_Test ETI Slab {date.today().year}", "docstatus": 1})
        for slab in slabs:
            doc = frappe.get_doc("ETI Slab", slab.name)
            doc.cancel()
            frappe.delete_doc("ETI Slab", doc.name, force=True)
            
        # Tax rebates, medical credits, etc.
        for doctype in ["Tax Rebates Rate", "Medical Tax Credit Rate", "Income Tax Slab"]:
            records = frappe.get_all(doctype, 
                filters={"name": ["like", "_Test%"]})
            for record in records:
                frappe.delete_doc(doctype, record.name, force=True)
                
        # Department
        if frappe.db.exists("Department", "_Test Department"):
            frappe.delete_doc("Department", "_Test Department", force=True)
            
        # Holiday list
        if frappe.db.exists("Holiday List", "_Test Holiday List"):
            frappe.delete_doc("Holiday List", "_Test Holiday List", force=True)
            
        # Payroll period
        periods = frappe.get_all("Payroll Period", 
            filters={"company": "_Test SA Company"})
        for period in periods:
            frappe.delete_doc("Payroll Period", period.name, force=True)
            
        # Remove salary components
        for component in ["_Test Basic Salary", "_Test PAYE", "_Test UIF"]:
            if frappe.db.exists("Salary Component", component):
                frappe.delete_doc("Salary Component", component, force=True)
                
        # Finally delete the company
        if frappe.db.exists("Company", "_Test SA Company"):
            frappe.delete_doc("Company", "_Test SA Company", force=True)
```

### Running the End-to-End Test

To run the complete employee lifecycle test:

```bash
bench --site your-site-name run-tests --app kartoza --test kartoza.kartoza.tests.test_employee_lifecycle
```

This will:
1. Create a South African test company with all required configuration
2. Create test salary components
3. Create and hire a test employee
4. Create and assign a salary structure
5. Create a payroll entry and generate salary slips
6. Submit the salary slips and verify calculations including ETI
7. Generate an IRP5 certificate
8. Clean up all test data

## Automating End-to-End Testing

For maximum benefit, you can automate these tests:

### As Part of CI/CD Pipeline

Add the tests to your GitHub Actions or GitLab CI workflow:

```yaml
# .github/workflows/tests.yml
name: Run Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install frappe-bench
          # Additional setup for Frappe/ERPNext
          
      - name: Run Tests
        run: |
          bench --site test-site run-tests --app kartoza --test kartoza.kartoza.tests.test_south_african_payroll
          bench --site test-site run-tests --app kartoza --test kartoza.kartoza.tests.test_employee_lifecycle
```

### As a Scheduled Job

Create a scheduled job that runs the tests periodically to detect regressions:

```bash
bench --site your-site-name add-to-crontab "0 1 * * 0 cd /path/to/frappe-bench && bench --site your-site-name run-tests --app kartoza --test kartoza.kartoza.tests.test_south_african_payroll >> /var/log/payroll_tests.log 2>&1"
```

This will run weekly tests at 1:00 AM on Sundays.

## Best Practices for South African Payroll Testing

1. **Test Realistic Scenarios**: Create test cases that reflect real-world South African payroll scenarios
   - Different age groups for tax rebate testing
   - Different salary levels for ETI thresholds
   - Part-time employees vs. full-time
   
2. **Test Data Isolation**: Ensure test data doesn't interfere with production
   - Always use company names with "_Test" prefix
   - Always clean up data after tests
   
3. **Comprehensive Coverage**: Test all aspects of payroll
   - Tax calculation with rebates and medical credits
   - ETI eligibility and calculations
   - UIF and SDL calculations
   - IRP5 certificate generation
   
4. **Validate Against Known Values**: Compare calculations with values verified manually or from official SARS examples

5. **Test Edge Cases**: Include tests for:
   - Employees turning 65/75 during the tax year (rebate changes)
   - Employees reaching 24 months of ETI claims
   - Employees with incomes at ETI threshold boundaries

## Debugging Test Failures

If tests fail, these approaches help identify the issues:

1. **Logging**: Add detailed logging to your tests:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   logger = logging.getLogger(__name__)
   logger.debug("Calculated ETI amount: %s", eti_amount)
   ```

2. **Run Single Tests**: Run only the failing test:
   ```bash
   bench --site your-site-name run-tests --app kartoza --test kartoza.kartoza.tests.test_employee_lifecycle.TestEmployeeLifecycle.test_04_verify_salary_slip_calculations
   ```

3. **Interactive Debugging**: Add `import pdb; pdb.set_trace()` at critical points in your code to debug interactively.

4. **Transaction Rollback**: If you need to debug without transaction rollback:
   ```bash
   bench --site your-site-name run-tests --app kartoza --test kartoza.kartoza.tests.test_employee_lifecycle --no-auto-rollback
   ```
