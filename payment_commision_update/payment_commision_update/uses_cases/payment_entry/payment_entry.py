import frappe
from frappe import _
from frappe.utils.background_jobs import get_jobs
from frappe.utils import flt, cint


@frappe.whitelist()
def processing_documents(company):

    try:

        processing_payment_entries(company)

        return "okay"


    except Exception as error:

        frappe.log_error(message=frappe.get_traceback(), title="processing_documents")

        pass

    return "error"


def processing_payment_entries(company):

    # Validar duplicacion de ejecución de proceso
    enqueued_method = 'payment_commision_update.payment_commision_update.uses_cases.payment_entry.payment_entry.create_entries_preview'
    jobs = get_jobs()

    if not jobs or enqueued_method not in jobs[frappe.local.site]:

        frappe.enqueue(enqueued_method, data=company, queue='long', is_async=True, timeout=54000)


def create_entries_preview(data):

    # TODO: Consultar entradas de pagos a procesar

    pe_list = frappe.db.sql_list("""
        select pe.name
        from `tabPayment Entry` as pe
        inner join  `tabSales Taxes and Charges Template` as templ on pe.qp_commission = templ.name
        where pe.party_type = 'Customer' and pe.payment_type = 'Receive' and pe.docstatus = '1'
        and pe.qp_processed = '0' and pe.company = '{0}'
    """.format(data))

    for rec in pe_list:

        create_entry_from_payment(rec)

    return

def create_entry_from_payment(rec):

    try:

        # TODO: evaluar caso de multi currency entre pago y factura
        acum_amount = 0.0

        float_precision = cint(frappe.db.get_default("float_precision")) or 2

        doc = frappe.get_doc("Payment Entry", rec)

        # Buscar factura y validar que tenga una única factura asociada
        if not doc.references:
            frappe.log_error(_("There is no associated reference {0}").format(doc.name),"create_entry_from_payment")
            return
        elif len(doc.references) != 1:
            frappe.log_error(_("Multiple invoices associated with the payment {0}").format(doc.name),"create_entry_from_payment")
            return
        elif doc.references[0].reference_doctype != 'Sales Invoice':
            frappe.log_error(_("There is no associated invoice {0}").format(doc.name),"create_entry_from_payment")
            return
        
        preview = frappe.new_doc("qp_Entries_Preview")

        preview.company = doc.company
        preview.posting_date = doc.posting_date
        preview.payment_entry_name = doc.name

        for doc_ref in doc.references:
            
            doc_invoice = frappe.get_doc("Sales Invoice", doc_ref.reference_name)

            # Calcular proporción
            proportion = flt(doc.paid_amount / doc_invoice.rounded_total)

            payment_tax = frappe.get_doc("Sales Taxes and Charges Template", doc.qp_commission)

            # Recorrer template de impuestos de venta asociada a la factura
            for tax_det in payment_tax.taxes:
                # Determinar seleccion para calcular monto

                tax_factor = flt(abs(tax_det.rate) / 100)

                if tax_det.qp_amount_to_calculate == 'Total before tax':

                    calc_amount = flt(doc_invoice.total * proportion * tax_factor, float_precision)

                elif tax_det.qp_amount_to_calculate == 'Tax':

                    calc_amount = flt(doc_invoice.total_taxes_and_charges * proportion * tax_factor, float_precision)

                elif tax_det.qp_amount_to_calculate == 'Total after tax':

                    calc_amount = flt(doc_invoice.rounded_total * proportion * tax_factor, float_precision)

                elif tax_det.qp_amount_to_calculate == 'Payment Value':

                    calc_amount = flt(doc.paid_amount * proportion * tax_factor, float_precision)

                else:

                    continue

                if calc_amount > 0.00:

                    acum_amount += calc_amount

                    preview.append("accounts", {
                        "account": tax_det.account_head,
                        "cost_center": tax_det.cost_center,
                        "debit": calc_amount,
                        "credit": 0.00,
                        "rate": tax_det.rate,
                        "ref_amount_to_calculate": tax_det.qp_amount_to_calculate
                    })

        if preview.get('accounts', False) and acum_amount > 0.00:
            # Calcular total e intertar contrapartida

            preview.total_debit = acum_amount
            preview.total_credit = acum_amount

            preview.append("accounts", {
                "account": doc.paid_to,
                "cost_center": doc.cost_center,
                "debit": 0.00,
                "credit": acum_amount
            })

        elif preview.get('accounts', False) and not acum_amount > 0.00:

            frappe.throw(_("Amounts to zero - Paymen Entry: {0}".format(doc.name)))

        preview.insert()

        preview.submit()

        frappe.db.commit()

    except Exception as error:

        frappe.db.rollback()

        frappe.log_error(message=frappe.get_traceback(), title="create_entry_from_payment: {0}".format(doc.name))

        pass

    return

def activate_qp_processed(doc_name):

    frappe.db.sql(""" update  `tabPayment Entry` set qp_processed = '1' where name = '{0}'""".format(doc_name))

def deactivate_qp_processed(doc_name):

    frappe.db.sql(""" update  `tabPayment Entry` set qp_processed = '0' where name = '{0}'""".format(doc_name))
