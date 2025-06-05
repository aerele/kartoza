// Copyright (c) 2024, Aerele and contributors
// For license information, please see license.txt

frappe.ui.form.on("EMP201 Submission", {
    refresh: function(frm) {
        // Populate the custom HTML field with the full document name
        if (frm.doc.name && frm.fields_dict.name_display_html) {
            let name_html = `
                <div style="
                    padding: var(--padding-sm) 0; 
                    font-size: var(--text-base); 
                    font-weight: 500;
                    color: var(--text-color);
                    word-break: break-all; 
                    user-select: text;
                    line-height: 1.5;
                ">
                    ${frm.doc.name}
                </div>`;
            frm.set_df_property("name_display_html", "options", name_html);
        }

        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__("Fetch EMP201 Data"), function() {
                console.log("EMP201 JS: Before Fetch Data - frm.is_new():", frm.is_new(), "frm.doc.name:", frm.doc.name);
                frm.call({
                    doc: frm.doc,
                    method: "fetch_emp201_data",
                    callback: function(r) {
                        console.log("EMP201 JS: After Fetch Data - frm.is_new():", frm.is_new(), "frm.doc.name:", frm.doc.name, "Response message:", r.message);
                        if (r.message) { // r.message is the updated doc from the server
                            // First, sync the entire document. This updates frm.doc.
                            frappe.model.sync(r.message);
                            
                            // Then, explicitly use frm.set_value for each calculated field.
                            // This ensures both frm.doc is updated for these fields AND their UI display is refreshed.
                            const calculated_fields = [
                                "gross_paye_before_eti", "eti_carried_forward_from_previous",
                                "eti_generated_current_month", "total_eti_available",
                                "eti_utilized_current_month", "net_paye_payable",
                                "eti_to_be_carried_forward", "uif_payable", "sdl_payable"
                            ];
                            calculated_fields.forEach(function(field) {
                                if (r.message.hasOwnProperty(field)) {
                                    frm.set_value(field, r.message[field]);
                                }
                            });
                            
                            // Finally, refresh the overall form state (e.g., save status, title if name changed).
                            // This will also re-render other fields if their values in frm.doc were changed by frappe.model.sync.
                            frm.refresh(); 

                            frappe.msgprint(__("EMP201 data fetched successfully."));
                        } else if (r.exc) {
                            frappe.msgprint({
                                title: __('Error'),
                                indicator: 'red',
                                message: __('Error fetching EMP201 data. Please check logs.')
                            });
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
    if (frm.doc.fiscal_year && frm.doc.month && frm.doc.company) {
        // Directly call the server method to calculate and get dates.
        // The server method now returns the dates.
        frm.call({
            doc: frm.doc, // Pass current client-side doc data. Server method will use these.
            method: "set_submission_period_dates",
            callback: function(r) {
                if (r.message && r.message.submission_period_start_date && r.message.submission_period_end_date) {
                    // Update client-side fields with the dates returned from the server.
                    // This will mark the form as dirty, which is fine.
                    // These values will be part of the document when it's next saved.
                    frm.set_value("submission_period_start_date", r.message.submission_period_start_date);
                    frm.set_value("submission_period_end_date", r.message.submission_period_end_date);
                } else {
                    // If server didn't return dates (e.g., fiscal year not found), clear them.
                    frm.set_value("submission_period_start_date", null);
                    frm.set_value("submission_period_end_date", null);
                    // Optionally, show an error if r.exc or some other error indicator is present
                    if (r.exc) {
                        frappe.msgprint({
                            title: __('Error Calculating Dates'),
                            indicator: 'orange',
                            message: __('Could not calculate submission period dates. Please ensure Fiscal Year and Month are valid and try saving.')
                        });
                    }
                }
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
