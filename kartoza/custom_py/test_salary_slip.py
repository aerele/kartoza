# Run only on a throwaway site that has kartoza installed (run-tests commits test records), e.g.:
#   bench --site <test-site> run-tests --module kartoza.custom_py.test_salary_slip
import ast
import inspect
import textwrap
from unittest.mock import PropertyMock, patch

import frappe
from frappe.tests import IntegrationTestCase
from hrms.payroll.doctype.salary_slip.salary_slip import SalarySlip

from kartoza.custom_py.salary_slip import CustomSalarySlip

TAX_COMPONENT = "_Test Kartoza PAYE"
MODULE = "kartoza.custom_py.salary_slip"


class TestCustomSalarySlipTax(IntegrationTestCase):
	def make_slip(self, payment_days=30, total_working_days=30, depends_on_payment_days=1):
		slip = frappe.new_doc("Salary Slip")
		self.assertIsInstance(slip, CustomSalarySlip)
		slip.payment_days = payment_days
		slip.total_working_days = total_working_days
		slip.append(
			"deductions",
			{"salary_component": TAX_COMPONENT, "depends_on_payment_days": depends_on_payment_days},
		)
		return slip

	def run_variable_tax(self, slip, has_additional_salary_tax_component=False):
		"""Run calculate_variable_tax with annual tax 12000, 2000 already paid, 10 periods left."""
		slip.remaining_sub_periods = 10
		slip.total_taxable_earnings_without_full_tax_addl_components = 100000
		slip.current_additional_earnings_with_full_tax = 0
		slip.is_forex_employee = 0
		slip.tax_slab = frappe._dict(foreign_tax_threshold=0)
		slip._component_based_variable_tax = {TAX_COMPONENT: {}}
		payroll_period = frappe._dict(start_date="2026-03-01", end_date="2027-02-28")
		with (
			patch.object(CustomSalarySlip, "payroll_period", new_callable=PropertyMock, return_value=payroll_period),
			patch.object(CustomSalarySlip, "get_tax_paid_in_period", return_value=2000),
			patch.object(CustomSalarySlip, "get_tax_rebate", return_value=0),
			patch.object(CustomSalarySlip, "get_medical_aid", return_value=0),
			patch.object(CustomSalarySlip, "get_data_for_eval", return_value=({}, {})),
			patch(f"{MODULE}.calculate_tax_by_tax_slab", return_value=(12000, None)),
		):
			slip.calculate_variable_tax(TAX_COMPONENT, has_additional_salary_tax_component)
		return slip._component_based_variable_tax[TAX_COMPONENT]

	def test_share_is_payment_days_ratio_when_tax_row_depends_on_payment_days(self):
		slip = self.make_slip(payment_days=16, total_working_days=30)
		self.assertAlmostEqual(slip.get_tax_payment_days_share(TAX_COMPONENT, False), 16 / 30)

	def test_share_uses_fractional_working_days(self):
		# half-day holidays make total_working_days fractional; a full month must still be share 1
		slip = self.make_slip(payment_days=21.5, total_working_days=21.5)
		self.assertEqual(slip.get_tax_payment_days_share(TAX_COMPONENT, False), 1)

	def test_share_is_one_when_tax_row_ignores_payment_days(self):
		slip = self.make_slip(payment_days=16, total_working_days=30, depends_on_payment_days=0)
		self.assertEqual(slip.get_tax_payment_days_share(TAX_COMPONENT, False), 1)

	def test_share_is_one_for_additional_salary_tax_component(self):
		slip = self.make_slip(payment_days=16, total_working_days=30)
		self.assertEqual(slip.get_tax_payment_days_share(TAX_COMPONENT, True), 1)

	def test_share_is_one_without_working_days(self):
		slip = self.make_slip(payment_days=0, total_working_days=0)
		self.assertEqual(slip.get_tax_payment_days_share(TAX_COMPONENT, False), 1)

	def test_share_falls_back_to_salary_component_when_row_is_from_additional_salary(self):
		slip = self.make_slip(payment_days=16, total_working_days=30, depends_on_payment_days=0)
		slip.deductions[0].additional_salary = "_Test Additional Salary"
		master = frappe._dict(depends_on_payment_days=1)
		with patch(f"{MODULE}.get_salary_component_data", return_value=master):
			self.assertAlmostEqual(slip.get_tax_payment_days_share(TAX_COMPONENT, False), 16 / 30)

	def test_split_remaining_tax(self):
		slip = self.make_slip()
		slip.total_structured_tax_amount, slip.previous_total_paid_taxes = 12000, 2000
		self.assertEqual(slip.split_remaining_tax(10), 1000)
		self.assertEqual(slip.split_remaining_tax(0), 0)
		self.assertEqual(slip.split_remaining_tax(-0.5), 0)

	def test_full_month_tax_is_unchanged(self):
		tax = self.run_variable_tax(self.make_slip(payment_days=30, total_working_days=30))
		self.assertAlmostEqual(tax["current_tax_amount"], 10000 / 10)
		self.assertAlmostEqual(tax["current_tax_amount_for_payment_days"], 10000 / 10)

	def test_partial_month_counts_as_its_payment_days_share(self):
		tax = self.run_variable_tax(self.make_slip(payment_days=15, total_working_days=30))
		expected = 10000 / (10 - 1 + 0.5)
		self.assertAlmostEqual(tax["current_tax_amount"], expected)
		self.assertAlmostEqual(tax["current_tax_amount_for_payment_days"], expected * 0.5)

	def test_partial_month_unprorated_when_tax_row_ignores_payment_days(self):
		slip = self.make_slip(payment_days=15, total_working_days=30, depends_on_payment_days=0)
		tax = self.run_variable_tax(slip)
		self.assertAlmostEqual(tax["current_tax_amount"], 10000 / 10)
		self.assertAlmostEqual(tax["current_tax_amount_for_payment_days"], 10000 / 10)

	def test_additional_salary_tax_reports_the_deducted_amount(self):
		slip = self.make_slip(payment_days=15, total_working_days=30)
		slip.additional_salary_amount = 500
		tax = self.run_variable_tax(slip, has_additional_salary_tax_component=True)
		self.assertEqual(tax["current_tax_amount_for_payment_days"], 500)

	def test_writes_every_key_upstream_calculate_variable_tax_writes(self):
		# HRMS reads these keys elsewhere (e.g. get_income_tax_deducted_till_date). kartoza replaces
		# calculate_variable_tax entirely, so a key added upstream must be added here too.
		tax = self.run_variable_tax(self.make_slip())
		self.assertLessEqual(get_upstream_variable_tax_keys(), set(tax))


def get_upstream_variable_tax_keys() -> set[str]:
	source = textwrap.dedent(inspect.getsource(SalarySlip.calculate_variable_tax))
	keys = set()
	for node in ast.walk(ast.parse(source)):
		is_update_call = (
			isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "update"
		)
		if is_update_call and node.args and isinstance(node.args[0], ast.Dict):
			keys |= {k.value for k in node.args[0].keys if isinstance(k, ast.Constant)}
	assert keys, "could not find the _component_based_variable_tax update in upstream calculate_variable_tax"
	return keys
