// Copyright (c) 2022, Aerele and contributors
// For license information, please see license.txt

frappe.ui.form.on("Employee Benefit", {
  // refresh: function(frm) {
  // }
});

frappe.ui.form.on("Medical Tax Credit Rate", {
  year: function(frm, cdt, cdn){
	let row = locals[cdt][cdn];
	if(row.year == 0)
	frappe.throw("Year cannot be 0")
	if(parseString(row.year).length != 4)
	frappe.throw("Year must be 4 digit")
  }
});