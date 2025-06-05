// Copyright (c) 2025, Aerele and contributors
// For license information, please see license.txt

frappe.ui.form.on('IRP5 Certificate', {
	refresh: function(frm) {
		// Add custom buttons
		
		// Button to generate certificate data
		if (frm.doc.docstatus === 0) { // Draft state
			frm.add_custom_button(__('Generate Certificate Data'), function() {
				frm.call({
					method: 'generate_certificate_data',
					doc: frm.doc,
					freeze: true,
					freeze_message: __('Generating Certificate Data...'),
					callback: function(r) {
						if (r.message) {
							let counts = r.message;
							frappe.show_alert({
								message: __(`Certificate data generated: ${counts.income_count} income items, ${counts.deduction_count} deduction items`),
								indicator: 'green'
							}, 5);
							frm.refresh();
						}
					}
				});
			}).addClass('btn-primary');
		}
		
		// Button to export certificate as PDF
		if (frm.doc.docstatus === 1) { // Submitted state
			frm.add_custom_button(__('Export IRP5 PDF'), function() {
				frm.call({
					method: 'export_pdf',
					doc: frm.doc,
					freeze: true,
					freeze_message: __('Generating IRP5 PDF...'),
					callback: function(r) {
						if (r.message) {
							let file_url = r.message;
							// Open the file in a new tab/window
							window.open(frappe.urllib.get_full_url(file_url));
						}
					}
				});
			}).addClass('btn-primary');
		}
		
		// Set up filters for related fields
		frm.set_query('employee', function() {
			return {
				filters: {
					'status': 'Active'
				}
			};
		});

		frm.set_query('tax_year', function() {
			return {
				filters: {
					'disabled': 0
				}
			};
		});
		
		// Fetch employee name when employee is selected
		frm.fields_dict['employee'].df.onchange = function() {
			if(frm.doc.employee) {
				frappe.db.get_value('Employee', frm.doc.employee, ['employee_name', 'company'], function(value) {
					frm.set_value('employee_name', value.employee_name);
					if(!frm.doc.company) {
						frm.set_value('company', value.company);
					}
				});
			}
		};
	},
	
	// Update tax year field when dates are changed
	from_date: function(frm) {
		if(frm.doc.from_date && !frm.doc.to_date) {
			// For Interim period: March to August
			if(frm.doc.reconciliation_period === 'Interim') {
				let from_date = frappe.datetime.str_to_obj(frm.doc.from_date);
				let to_date = new Date(from_date.getFullYear(), 7, 31); // August 31
				frm.set_value('to_date', frappe.datetime.obj_to_str(to_date));
			}
			// For Final period: March to February
			else if(frm.doc.reconciliation_period === 'Final') {
				let from_date = frappe.datetime.str_to_obj(frm.doc.from_date);
				let to_year = from_date.getFullYear() + 1;
				// Check for leap year
				let to_day = 28;
				if (to_year % 4 === 0 && (to_year % 100 !== 0 || to_year % 400 === 0)) {
					to_day = 29;
				}
				let to_date = new Date(to_year, 1, to_day); // February 28/29
				frm.set_value('to_date', frappe.datetime.obj_to_str(to_date));
			}
		}
		// set_tax_year(frm); // Removed as tax_year is now a Link field
	},
	
	to_date: function(frm) {
		// set_tax_year(frm); // Removed as tax_year is now a Link field
	},
	
	reconciliation_period: function(frm) {
		// If tax_year is set, trigger its onchange to re-evaluate from_date and to_date
		// based on the new reconciliation_period
		if (frm.doc.tax_year) {
			frm.trigger('tax_year');
		} 
		// If only from_date is set (and no tax_year), try to auto-calculate to_date
		else if (frm.doc.from_date) {
			frm.trigger('from_date');
		}
	},

	tax_year: function(frm) {
		if (frm.doc.tax_year) {
			frappe.model.with_doc("Fiscal Year", frm.doc.tax_year, function() {
				let fiscal_year_doc = frappe.get_doc("Fiscal Year", frm.doc.tax_year);
				let from_date_val = fiscal_year_doc.year_start_date;
				let to_date_val = fiscal_year_doc.year_end_date;

				if (frm.doc.reconciliation_period === 'Interim' && fiscal_year_doc.year_start_date) {
					let year_start_obj = frappe.datetime.str_to_obj(fiscal_year_doc.year_start_date);
					// SARS Interim is March 1 to Aug 31.
					// This logic assumes the fiscal year starts March 1 for Interim to make sense.
					if (year_start_obj.getMonth() + 1 === 3 && year_start_obj.getDate() === 1) {
						from_date_val = fiscal_year_doc.year_start_date;
						let to_date_interim = new Date(year_start_obj.getFullYear(), 7, 31); // Aug 31
						to_date_val = frappe.datetime.obj_to_str(to_date_interim);
					} else {
						// If fiscal year doesn't start March 1, Interim period might be ambiguous from Fiscal Year alone.
						// Keep full fiscal year dates and let validation handle it, or clear them.
						// For now, we'll stick to full fiscal year dates if not a March 1 start.
					}
				}
				// For 'Final', the full fiscal year dates are usually correct for a March-Feb tax year.
				
				frm.set_value('from_date', from_date_val);
				frm.set_value('to_date', to_date_val);
				frm.refresh_fields(['from_date', 'to_date']);
			});
		} else {
			frm.set_value('from_date', null);
			frm.set_value('to_date', null);
			frm.refresh_fields(['from_date', 'to_date']);
		}
	}
});

// IRP5 Income Detail Child Table
frappe.ui.form.on('IRP5 Income Detail', {
	income_details_add: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.tax_year = frm.doc.tax_year;
		row.period = frm.doc.reconciliation_period;
		frm.refresh_field('income_details');
	}
});

// IRP5 Deduction Detail Child Table
frappe.ui.form.on('IRP5 Deduction Detail', {
	deduction_details_add: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		row.tax_year = frm.doc.tax_year;
		row.period = frm.doc.reconciliation_period;
		frm.refresh_field('deduction_details');
	}
});
