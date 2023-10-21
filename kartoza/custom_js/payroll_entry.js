frappe.ui.form.on('Payroll Entry', {
	refresh:function(frm){
		if (frm.doc.docstatus == 1) {
			// if (frm.custom_buttons) frm.clear_custom_buttons();
			if (frm.doc.salary_slips_submitted || (frm.doc.__onload && frm.doc.__onload.submitted_ss)) {
				frm.remove_custom_button("Make Bank Entry")
				frm.add_custom_button(__("Make Bank Entry"), function () {
					let account_map = {}
					let field_list = []
					frm.doc.employees.forEach(row => {
						if(row.custom_payroll_payable_bank_account){
							if(row.custom_payroll_payable_bank_account in account_map)
								account_map[row.custom_payroll_payable_bank_account].push({"employee":row.employee, "employee_name":row.employee_name, "is_bank_entry_created":row.custom_is_bank_entry_creaeted})
							else
								account_map[row.custom_payroll_payable_bank_account] = [{"employee":row.employee, "employee_name":row.employee_name, "is_bank_entry_created":row.custom_is_bank_entry_creaeted}]
						}
					});
					for(let account in account_map){
						let is_read_only = 0
						if (account_map[account].length == account_map[account].filter(function(item){
							return item.is_bank_entry_created;
						  }).length){
							is_read_only = 1
						  }
						field_list.push({
							label: account,
							fieldname: account,
							fieldtype: 'Check',
							read_only: is_read_only,
							change: ()=>{
								$(".employee-list").empty()
								for(let account in account_map){
									if(d.get_value(account)){
										$(".employee-list").append(`
												<tr style="width:100%;"><td style="border-bottom: 1px solid #d4d4d4;width:100%;"><b>Employees paid with <a href="/app/bank-account/${account}">${account}</a></b></td></tr>
											`)
										account_map[account].forEach(row => {
											$(".employee-list").append(`
												<tr style="width:100%;"><td style="border-bottom: 1px solid #d4d4d4;width:100%;"><a href="/app/employee/${row.employee}" target="_blank" >${row.employee}: ${row.employee_name}</a></td></tr>
											`)
										})
									}
								}
							}
						})
					}
					field_list.push({fieldtype:"Section Break"})
					field_list.push({
						fieldname: "employee_list",
						fieldtype: "Text",
						default: "<table class='employee-list' style='width:100%;'></table>",
						read_only: 1
					})
					let d = new frappe.ui.Dialog({
						title: 'Enter details',
						fields: field_list,
						size: 'small', // small, large, extra-large
						primary_action_label: 'Create Bank Entry',
						primary_action(values) {
							cur_frm.doc.selected_payment_account = values
							frappe.call({
								doc: cur_frm.doc,
								method: "make_payment_entry",
								callback: function () {
									frappe.set_route(
										'List', 'Journal Entry', {
											"Journal Entry Account.reference_name": frm.doc.name
										}
									);
								},
								freeze: true,
								freeze_message: __("Creating Payment Entries......")
							});
							console.log(values);
							d.hide();
						}
					});

					d.show();
				}).addClass("btn-primary");
			}
		}
	}
})