frappe.ui.form.on("Payroll Entry", {
	// v16 calls this hook from its standard refresh handler.
	add_bank_entry_button: function (frm) {
		if (frm.doc.docstatus == 1) {
			if (frm.doc.salary_slips_submitted || (frm.doc.__onload && frm.doc.__onload.submitted_ss)) {
				frm.remove_custom_button(__("Make Bank Entry"));
				frm
					.add_custom_button(__("Make Bank Entry"), function () {
						let field_list = [];
						const account_map = {};

						frm.doc.employees.forEach((row) => {
							if (row.custom_payroll_payable_bank_account) {
								if (row.custom_payroll_payable_bank_account in account_map)
									account_map[row.custom_payroll_payable_bank_account].push({
										employee: row.employee,
										employee_name: row.employee_name,
										account_currency: row.custom_bank_account_currency,
										is_bank_entry_created: row.custom_is_bank_entry_creaeted,
										is_company_contribution_created: row.custom_is_company_contribution_created,
									});
								else
									account_map[row.custom_payroll_payable_bank_account] = [
										{
											employee: row.employee,
											employee_name: row.employee_name,
											account_currency: row.custom_bank_account_currency,
											is_bank_entry_created: row.custom_is_bank_entry_creaeted,
											is_company_contribution_created: row.custom_is_company_contribution_created,
										},
									];
							}
						});
						let company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;
						for (let account in account_map) {
							let is_read_only = 0;
							if (
								account_map[account].length ==
								account_map[account].filter(
									(item) => item.is_bank_entry_created && item.is_company_contribution_created
								).length
							) {
								is_read_only = 1;
							}
							field_list.push({
								label: account,
								fieldname: account,
								fieldtype: "Check",
								read_only: is_read_only,
								change: () => {
									d.fields_dict.employee_list.$wrapper.find(".employee-list").empty();
									for (let account in account_map) {
										if (d.get_value(account)) {
											d.fields_dict.employee_list.$wrapper.find(".employee-list").append(`
												<div class="col-sm-12" style="border-bottom: 1px solid #d4d4d4;"><b>Employees paid with <a href="/desk/bank-account/${encodeURIComponent(
													account
												)}">${frappe.utils.escape_html(account)}</a></b></div>
											`);
											account_map[account].forEach((row) => {
												let is_disabled = false;
												if (!(row.is_bank_entry_created || row.is_company_contribution_created)) {
													is_disabled = true;
												}

												d.fields_dict.employee_list.$wrapper.find(".employee-list").append(`
													<div class="col-sm-6" style="border-bottom: 1px solid #d4d4d4;"><input type="checkbox" class="employee-checkbox" account="${frappe.utils.escape_html(
														account
													)}" employee="${frappe.utils.escape_html(row.employee)}" checked ${
													!is_disabled ? "disabled" : ""
												}><a href="/desk/employee/${encodeURIComponent(
													row.employee
												)}" target="_blank" >${frappe.utils.escape_html(
													row.employee
												)}: ${frappe.utils.escape_html(row.employee_name)}</a></div>
												`);
											});
										}
									}
								},
							});
							field_list.push({
								fieldtype: "Column Break",
							});
							field_list.push({
								label: "Payment Date" + " <small>(" + account + ")</small>",
								fieldname: account + "_date",
								fieldtype: "Date",
								read_only: is_read_only,
								change: () => {
									frappe.call({
										method: "erpnext.setup.utils.get_exchange_rate",
										args: {
											from_currency: account_map[account][0].account_currency,
											to_currency: company_currency,
											transaction_date: d.get_value(account + "_date"),
										},
										callback: function (r, rt) {
											d.set_value(account + "_ex_rate", r.message);
										},
									});
								},
							});
							field_list.push({
								fieldtype: "Column Break",
							});
							field_list.push({
								label: "Exchange Rate" + " <small>(" + account + ")</small>",
								fieldname: account + "_ex_rate",
								fieldtype: "Float",
								precision: 9,
								read_only:
									is_read_only || company_currency == account_map[account][0].account_currency
										? 1
										: 0,
							});
							field_list.push({ fieldtype: "Section Break" });
						}
						field_list.push({
							fieldname: "employee_list",
							// v16 escapes markup in read-only Text controls.
							fieldtype: "HTML",
							options:
								'<div class="container" style="margin:0px;width:100%;"><div class="row employee-list"></div></div>',
							read_only: 1,
						});
						const d = new frappe.ui.Dialog({
							title: "Enter details",
							fields: field_list,
							size: "extra-large", // small, large, extra-large
							primary_action_label: "Create Bank Entry",
							primary_action(values) {
								let account_emp_map = {};
								d.fields_dict.employee_list.$wrapper
									.find(".employee-checkbox:checkbox:checked")
									.each((i, e) => {
										const acc = $(e).attr("account");
										const emp = $(e).attr("employee");
										account_emp_map[acc] ||= { employees: [] };
										if (!account_emp_map[acc].employees.includes(emp)) {
											account_emp_map[acc].employees.push(emp);
										}
									});
								if (!Object.keys(account_emp_map).length) {
									frappe.throw(__("Select at least one employee."));
								}
								for (const account in account_emp_map) {
									if (!values[account + "_date"]) {
										frappe.throw(`Posting date for ${account} is mandatory`);
									}

									if (!(values[account + "_ex_rate"] > 0)) {
										frappe.throw("Exchange rate must be greater than zero");
									}

									account_emp_map[account]["currency"] = account_map[account][0].account_currency;
									account_emp_map[account]["posting_date"] = values[account + "_date"];
									account_emp_map[account]["exchange_rate"] = values[account + "_ex_rate"];
								}
								frm.doc.selected_payment_account = account_emp_map;
								frappe.call({
									doc: frm.doc,
									method: "make_payment_entry",
									callback: function (r) {
										if (r.exc) return;
										d.hide();
										frm.reload_doc();
										frappe.set_route("List", "Journal Entry", {
											"Journal Entry Account.reference_name": frm.doc.name,
										});
									},
									freeze: true,
									freeze_message: __("Creating Payment Entries......"),
								});
							},
						});

						d.show();
					})
					.addClass("btn-primary");
			}
		}
	},
});
