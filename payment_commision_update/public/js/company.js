frappe.ui.form.on("Company", "refresh", function(frm) {
    frm.add_custom_button(__("Entries for taxes"), () => {
        frappe.confirm(__("This action will create Preview List. Are you certain?"), function() {
            frappe.call({
                method: "payment_commision_update.payment_commision_update.uses_cases.payment_entry.payment_entry.processing_documents",
                args: {
                    company: frm.doc.name
                },
                freeze: true,
                callback: () => {
                    frappe.msgprint({
                        title: __("Sync Started"),
                        message: __("The process has started in the background."),
                        alert: 1
                    });
                    frappe.set_route("List", "qp_Entries_Preview",{"docstatus": '1'});
                }
            });
        });
    });
    });
