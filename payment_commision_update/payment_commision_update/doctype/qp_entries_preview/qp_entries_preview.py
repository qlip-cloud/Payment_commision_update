# Copyright (c) 2023, Mentum Group and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from payment_commision_update.payment_commision_update.uses_cases.payment_entry.payment_entry import activate_qp_processed
from payment_commision_update.payment_commision_update.uses_cases.payment_entry.payment_entry import deactivate_qp_processed

class qp_Entries_Preview(Document):

	def on_submit(self):

		self.create_fournal_entry()

		activate_qp_processed(self.payment_entry_name)

	def create_fournal_entry(self):

		if self.get('accounts', False):

			jv = frappe.new_doc("Journal Entry")
			jv.company = self.company
			jv.posting_date = self.posting_date

			for acc in self.accounts:
				jv.append("accounts", {
					"account": acc.account,
					"cost_center": acc.cost_center,
					"debit_in_account_currency": acc.debit,
					"credit_in_account_currency": acc.credit
				})

			jv.insert()
			jv.submit()

			frappe.db.sql(""" update  `tabqp_Entries_Preview` set journal_entry_name = '{0}' where name = '{1}'""".format(jv.name, self.name))
	
	def on_cancel(self):

		if self.journal_entry_name:

			je = frappe.get_doc("Journal Entry", self.journal_entry_name)
			je.cancel()

		deactivate_qp_processed(self.payment_entry_name)

	def on_trash(self):
		
		frappe.throw(_("Records not allowed to be deleted"))
