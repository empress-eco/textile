# Copyright (c) 2023, ParaLogic and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _, STANDARD_USERS
from frappe.utils import cint, cstr, getdate, get_datetime, add_days, validate_email_address
from textile.fabric_printing.report.fabric_printing_summary.fabric_printing_summary import FabricPrintingSummary
from textile.utils import get_rotated_image


class TextileEmailDigest(Document):
	def validate(self):
		self.validate_mandatory()

	def validate_mandatory(self):
		if not cint(self.enabled):
			return

		if not self.recipient_list:
			frappe.throw(_("Recipient is mandatory"))
		if not self.email_template:
			frappe.throw(_("Email Template is mandatory"))

		for email in [rec for rec in cstr(self.recipient_list).split() if rec]:
			validate_email_address(email, True)

	@frappe.whitelist()
	def get_users(self):
		user_list = frappe.db.sql("""
			SELECT name, enabled FROM `tabUser`
			WHERE name NOT IN ({standard_users})
			and user_type != "Website User"
			order by enabled desc, name asc
		""".format(
			standard_users=", ".join(frappe.db.escape(user) for user in STANDARD_USERS)
		), as_dict=1)

		recipient_list = [rec for rec in cstr(self.recipient_list).split() if rec]

		for d in user_list:
			d["checked"] = d["name"] in recipient_list

		return user_list

	@frappe.whitelist()
	def send(self, is_background=False):
		context = self.get_context()

		if not self.email_template:
			frappe.throw(_("Email Template is not set."))

		if is_background and self.do_not_send_if_no_transaction and not context.get("daily_by_material"):
			return

		recipients = self.get_recipients()

		email_template = frappe.get_cached_doc("Email Template", self.email_template)
		formatted_template = email_template.get_formatted_email(context)

		if recipients:
			frappe.sendmail(
				recipients=recipients,
				subject=formatted_template['subject'],
				message=formatted_template['message'],
			)

	def get_context(self):
		context = frappe._dict({})

		filters = {
			"to_date": add_days(getdate(), -1)
		}
		filters["from_date"] = filters["to_date"].replace(day=1)
		context["monthly_by_material"], context["monthly_totals"] = FabricPrintingSummary(filters).get_data_for_digest()

		filters["from_date"] = filters["to_date"]
		context["daily_by_material"], context["daily_totals"] = FabricPrintingSummary(filters).get_data_for_digest()

		if context.daily_totals.most_produced_item:
			item_details = frappe.db.get_value("Item", context.daily_totals.most_produced_item, ["image", "fabric_item", "fabric_item_name"], as_dict=1)
			context.daily_totals["most_produced_item_fabric"] = item_details.fabric_item
			context.daily_totals["most_produced_item_fabric_name"] = item_details.fabric_item_name
			context.daily_totals["most_produced_item_image"] = item_details.image
			context.daily_totals["most_produced_item_image_rotated"] = get_rotated_image(item_details.image, get_path=True) if item_details.image else None

		return context

	def get_recipients(self):
		return [rec.strip() for rec in cstr(self.recipient_list).split() if rec]


@frappe.whitelist()
def send_textile_email_digest():
	now_dt = get_datetime()
	digest_doc = frappe.get_single("Textile Email Digest")

	if not cint(digest_doc.enabled):
		return
	if not digest_doc.email_template:
		return

	if cint(digest_doc.send_at_hour_of_the_day) > now_dt.hour:
		return

	digest_last_sent_date = frappe.db.get_global("textile_email_digest_last_sent_date")
	if digest_last_sent_date and getdate(digest_last_sent_date) >= now_dt.date():
		return

	digest_doc.send(is_background=True)

	frappe.db.set_global("textile_email_digest_last_sent_date", now_dt.date())