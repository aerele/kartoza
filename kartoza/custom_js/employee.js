frappe.ui.form.on("Employee", {
	"onload":function(frm){
		frm.set_query('payroll_payable_account', function(doc) {
			return {
				filters: {
					"is_company_account": 1,
					"account": ["!=", null]
				}
			};
		});
	}
})