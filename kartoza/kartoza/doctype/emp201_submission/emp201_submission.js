// Copyright (c) 2024, Aerele and contributors
// For license information, please see license.txt

frappe.ui.form.on("EMP201 Submission", {
    refresh: function(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Fetch EMP201 Data"), function() {
                frm.call({
                    doc: frm.doc,
                    method: "fetch_emp201_data",
                    callback: function(r) {
                        if (r.message) {
                            frm.refresh_fields();
                            frappe.msgprint(__("EMP201 data fetched successfully."));
                        }
                    },
                    freeze: true,
                    freeze_message: __("Fetching EMP201 Data...")
                });
            }).addClass("btn-primary");
        }
    },

    company: function(frm) {
        // Clear dependent fields if company changes
        frm.set_value("fiscal_year", "");
        frm.set_value("month", "");
        frm.set_value("submission_period_start_date", null);
        frm.set_value("submission_period_end_date", null);
        // Clear calculated fields
        clear_calculated_fields(frm);
    },

    fiscal_year: function(frm) {
        if (frm.doc.fiscal_year && frm.doc.month) {
            call_set_submission_period_dates(frm);
        } else {
            frm.set_value("submission_period_start_date", null);
            frm.set_value("submission_period_end_date", null);
        }
        clear_calculated_fields(frm);
    },

    month: function(frm) {
        if (frm.doc.fiscal_year && frm.doc.month) {
            call_set_submission_period_dates(frm);
        } else {
            frm.set_value("submission_period_start_date", null);
            frm.set_value("submission_period_end_date", null);
        }
        clear_calculated_fields(frm);
    }
});

function call_set_submission_period_dates(frm) {
    if (frm.doc.fiscal_year && frm.doc.month) {
        frappe.call({
            method: "frappe.client.set_value",
            args: {
                doctype: frm.doc.doctype,
                name: frm.doc.name,
                fieldname: "submission_period_start_date", // This will trigger validate in backend
                value: null // Temporarily set to null to ensure validate runs if dates don't change
            },
            callback: function() {
                 frm.call({
                    doc: frm.doc,
                    method: "set_submission_period_dates", // Call the backend method
                    callback: function(r) {
                        if (r.docs && r.docs.length > 0) {
                             frm.refresh_field("submission_period_start_date");
                             frm.refresh_field("submission_period_end_date");
                        }
                    }
                });
            }
        });
    }
}

function clear_calculated_fields(frm) {
    frm.set_value("gross_paye_before_eti", 0);
    frm.set_value("eti_carried_forward_from_previous", 0);
    frm.set_value("eti_generated_current_month", 0);
    frm.set_value("total_eti_available", 0);
    frm.set_value("eti_utilized_current_month", 0);
    frm.set_value("net_paye_payable", 0);
    frm.set_value("eti_to_be_carried_forward", 0);
    frm.set_value("uif_payable", 0);
    frm.set_value("sdl_payable", 0);
}
