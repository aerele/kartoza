# Copyright (c) 2025, Kartoza and contributors
# For license information, please see license.txt

import unittest
import frappe
from frappe.utils import getdate

class TestVATFunctionality(unittest.TestCase):
    def setUp(self):
        # Create test data
        self._create_test_data()
        
    def tearDown(self):
        # Clean up test data
        self._delete_test_data()
        
    def _create_test_data(self):
        """Create test customer and supplier with VAT numbers"""
        # Create test customer
        if not frappe.db.exists("Customer", "_Test SA Customer"):
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": "_Test SA Customer",
                "customer_type": "Company",
                "customer_group": "_Test Customer Group",
                "territory": "_Test Territory",
                "vat_number": "4123456789",
                "is_vat_registered": 1
            })
            customer.insert(ignore_permissions=True)
            
        # Create test supplier
        if not frappe.db.exists("Supplier", "_Test SA Supplier"):
            supplier = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": "_Test SA Supplier",
                "supplier_group": "_Test Supplier Group",
                "vat_number": "4987654321",
                "is_vat_registered": 1
            })
            supplier.insert(ignore_permissions=True)
    
    def _delete_test_data(self):
        """Delete test data"""
        # Delete test customer
        if frappe.db.exists("Customer", "_Test SA Customer"):
            frappe.delete_doc("Customer", "_Test SA Customer")
            
        # Delete test supplier
        if frappe.db.exists("Supplier", "_Test SA Supplier"):
            frappe.delete_doc("Supplier", "_Test SA Supplier")
    
    def test_vat_number_field_access(self):
        """Test that VAT number field can be accessed in queries"""
        # Search for customer by VAT number
        customers = frappe.get_list("Customer", 
                                    filters={"vat_number": "4123456789"},
                                    fields=["name", "vat_number"])
        
        # Assert that customer was found
        self.assertTrue(len(customers) > 0, "Customer with VAT number not found")
        self.assertEqual(customers[0].vat_number, "4123456789", "VAT number does not match")
        
        # Get values using frappe.db.get_value
        vat_number = frappe.db.get_value("Customer", "_Test SA Customer", "vat_number")
        self.assertEqual(vat_number, "4123456789", "VAT number retrieval failed")
        
        # Test with frappe.db.get_values
        values = frappe.db.get_values("Supplier", 
                                      filters={"name": "_Test SA Supplier"},
                                      fieldname=["vat_number", "is_vat_registered"],
                                      as_dict=True)
        self.assertTrue(len(values) > 0, "Supplier values not found")
        self.assertEqual(values[0].vat_number, "4987654321", "Supplier VAT number does not match")
        
    def test_vat_number_validation(self):
        """Test validation of South African VAT number format"""
        # Test invalid VAT number format
        customer = frappe.get_doc("Customer", "_Test SA Customer")
        customer.vat_number = "123456789"  # Missing 4 prefix
        
        # Should raise validation error
        with self.assertRaises(frappe.ValidationError):
            customer.save()
            
        # Reset to valid number
        customer.reload()
        customer.vat_number = "4123456789"
        customer.save()
        
    def test_vat201_return_creation(self):
        """Test basic VAT201 Return creation and validation"""
        # Create test VAT201 Return
        vat_return = frappe.get_doc({
            "doctype": "VAT201 Return",
            "company": frappe.defaults.get_user_default("Company"),
            "from_date": getdate("2025-01-01"),
            "to_date": getdate("2025-01-31"),
            "vat_period": "202501"
        })
        
        vat_return.insert()
        
        # Test that the document was created
        self.assertTrue(frappe.db.exists("VAT201 Return", vat_return.name))
        
        # Clean up
        frappe.delete_doc("VAT201 Return", vat_return.name)


def run_vat_tests():
    """Run VAT functionality tests"""
    frappe.set_user("Administrator")
    tests = unittest.TestLoader().loadTestsFromTestCase(TestVATFunctionality)
    unittest.TextTestRunner(verbosity=2).run(tests)
