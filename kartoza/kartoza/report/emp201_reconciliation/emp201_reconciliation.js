// Copyright (c) 2025, Aerele and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["EMP201 Reconciliation"] = {
    "filters": [
        {
            "fieldname": "emp201_submission",
            "label": __("EMP201 Submission"),
            "fieldtype": "Link",
            "options": "EMP201 Submission",
            "reqd": 1,
            "description": __("Select the EMP201 Submission to generate the reconciliation report for.")
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default('company')
        }
    ],

    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (column.fieldname === "field_value" && data.fieldname === "status") {
            // Store original data for creating select later
            row.status_data = data; 
            // Initial display can be the value, or we can build select here.
            // For simplicity, let's build it in onload after datatable is rendered.
        }
        return value;
    },

    "onload": function(report) {
        // This onload is for the report view itself, after data is loaded.
        // We need to find the datatable and modify the status row.

        report.page.add_inner_button(__("Save Status"), function() {
            let new_status = $(".report-wrapper .status-select select").val();
            let emp201_submission_id = report.get_filter_value('emp201_submission');

            if (!emp201_submission_id) {
                frappe.msgprint(__("Please select an EMP201 Submission."));
                return;
            }
            if (!new_status) {
                frappe.msgprint(__("No status selected."));
                return;
            }

            frappe.call({
                method: "kartoza.kartoza.report.emp201_reconciliation.emp201_reconciliation.update_emp201_submission_status",
                args: {
                    emp201_submission_id: emp201_submission_id,
                    status: new_status
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({message: __("Status updated successfully."), indicator: "green"});
                        report.refresh(); // Refresh report to show updated status
                    } else {
                        frappe.show_alert({message: __("Failed to update status: ") + (r.message ? r.message.error : _("Unknown error")), indicator: "red"});
                    }
                },
                error: function(r) {
                    frappe.show_alert({message: __("Error calling server to update status."), indicator: "red"});
                }
            });
        });
        
        // The report data is in report.data
        // The datatable instance might be report.datatable
        // We need a slight delay or a more robust way to ensure the datatable is rendered.
        setTimeout(() => {
            if (report.datatable && report.data) {
                report.data.forEach((row_data, index) => {
                    if (row_data.fieldname === "status" && row_data.options) {
                        // Find the cell in the datatable. This is tricky as datatable structure can vary.
                        // Assuming the 'Value' column is the second column (index 1).
                        // And rows in datatable map directly to report.data rows.
                        let row_element = $(report.datatable.get_row_html(index));
                        let cell_to_modify = row_element.find('td[data-col-idx="1"] .value'); // Target .value span

                        if (cell_to_modify.length) {
                            let select_html = `<select class='form-control input-sm'>`;
                            row_data.options.forEach(option => {
                                select_html += `<option value="${option}" ${option === row_data.field_value ? 'selected' : ''}>${option}</option>`;
                            });
                            select_html += `</select>`;
                            
                            // Add a wrapper for easier selection later
                            cell_to_modify.parent().addClass('status-select').html(select_html);
                        }
                    }
                });
            }
        }, 500); // Delay to allow datatable to render. This is not ideal.
                  // A better way would be to hook into a datatable render event if available.
    }
};
