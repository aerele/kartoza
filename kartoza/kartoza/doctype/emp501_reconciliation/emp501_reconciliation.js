// Copyright (c) 2025, Aerele and contributors
// For license information, please see license.txt

frappe.ui.form.on('EMP501 Reconciliation', {
    refresh: function(frm) {
        // Add custom buttons based on document status
        if (frm.doc.docstatus === 0) {
            // Draft state
            frm.add_custom_button(__('Fetch EMP201 Submissions'), function() {
                frm.call({
                    doc: frm.doc,
                    method: 'fetch_emp201_submissions',
                    callback: function(r) {
                        if (r.message) {
                            frappe.show_alert({
                                message: __(`${r.message} EMP201 submissions fetched`),
                                indicator: 'green'
                            });
                            frm.refresh();
                        }
                    }
                });
            }, __('Actions'));
        }
        
        if (frm.doc.docstatus === 1) {
            // Submitted state
            if (frm.doc.status === "Prepared") {
                frm.add_custom_button(__('Generate IRP5 Certificates'), function() {
                    frm.call({
                        doc: frm.doc,
                        method: 'generate_irp5_certificates',
                        callback: function(r) {
                            if (r.message) {
                                frappe.show_alert({
                                    message: __(`${r.message} IRP5 certificates generated`),
                                    indicator: 'green'
                                });
                                frm.refresh();
                            }
                        }
                    });
                }, __('Actions'));
                
                frm.add_custom_button(__('Submit to SARS'), function() {
                    frappe.confirm(
                        __('Are you sure you want to submit this EMP501 reconciliation to SARS?'),
                        function() {
                            frm.call({
                                doc: frm.doc,
                                method: 'submit_to_sars',
                                callback: function(r) {
                                    if (r.message) {
                                        frappe.show_alert({
                                            message: __(r.message.message),
                                            indicator: 'green'
                                        });
                                        frm.refresh();
                                    }
                                }
                            });
                        }
                    );
                }).addClass('btn-primary');
            }
            
            // Add button to download CSV for SARS e-Filing
            frm.add_custom_button(__('Download CSV for e-Filing'), function() {
                frappe.call({
                    method: 'kartoza.kartoza.utils.emp501_utils.generate_emp501_csv',
                    args: {
                        emp501: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            window.open(r.message.file_url);
                        }
                    }
                });
            }, __('Actions'));
        }
    },
    
    tax_year: function(frm) {
        // Set from_date and to_date based on tax year and reconciliation period
        if (frm.doc.tax_year && frm.doc.reconciliation_period) {
            frappe.db.get_doc('Fiscal Year', frm.doc.tax_year)
                .then(fiscal_year => {
                    let year_start = fiscal_year.year_start_date;
                    let year_end = fiscal_year.year_end_date;
                    
                    if (frm.doc.reconciliation_period === "Interim") {
                        // Interim period: March to August
                        frm.set_value('from_date', year_start);
                        
                        // Calculate August 31st of the same year
                        let to_date = new Date(year_start);
                        to_date.setMonth(7); // August (0-indexed)
                        to_date.setDate(31);
                        frm.set_value('to_date', frappe.datetime.obj_to_str(to_date));
                    } else if (frm.doc.reconciliation_period === "Final") {
                        // Final period: March to February
                        frm.set_value('from_date', year_start);
                        frm.set_value('to_date', year_end);
                    }
                });
        }
    },
    
    reconciliation_period: function(frm) {
        // Trigger tax_year function to update dates
        frm.trigger('tax_year');
    },
    
    company: function(frm) {
        // Fetch reference numbers from company
        if (frm.doc.company) {
            frappe.db.get_value('Company', frm.doc.company, ['tax_id'])
                .then(r => {
                    if (r.message) {
                        frm.set_value('paye_reference_number', r.message.tax_id);
                        
                        // For SDL and UIF, we'll use the same tax ID with different prefixes
                        // In a real implementation, these would be fetched from company settings
                        let tax_id = r.message.tax_id || '';
                        if (tax_id) {
                            frm.set_value('sdl_reference_number', 'L' + tax_id.replace(/^[A-Z]/, ''));
                            frm.set_value('uif_reference_number', 'U' + tax_id.replace(/^[A-Z]/, ''));
                        }
                    }
                });
        }
    }
});

frappe.ui.form.on('EMP501 EMP201 Reference', {
    emp201_submissions_add: function(frm, cdt, cdn) {
        // When a new row is added, calculate totals
        frm.call('calculate_totals');
    },
    
    emp201_submissions_remove: function(frm) {
        // When a row is removed, calculate totals
        frm.call('calculate_totals');
    }
});
