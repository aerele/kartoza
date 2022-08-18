// Copyright (c) 2022, Aerele and contributors
// For license information, please see license.txt

frappe.ui.form.on('Employee Benefit Claim', {
	kilometer: function(frm){
		frappe.call({
			method: 'frappe.client.get_value',
			args: {
				'doctype': 'HR Settings',
				'filters': {'name': 'HR Settings'},
				'fieldname': [
								'amount_per_kilometer'
								]
			},
			async:false,
			callback: function(r){
					if(r.message){
						frm.set_value("claimed_amount",frm.doc.kilometer * r.message["amount_per_kilometer"]);
					}
			} 
		})
	}
});
