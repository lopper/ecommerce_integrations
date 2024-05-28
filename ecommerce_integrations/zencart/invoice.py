import frappe
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from frappe.utils import cint, cstr, getdate, nowdate

from ecommerce_integrations.zencart.constants import (
	ORDER_ID_FIELD,
	SETTING_DOCTYPE,
)
from ecommerce_integrations.zencart.utils import create_zencart_log


def prepare_sales_invoice(payload, request_id=None):
	from ecommerce_integrations.zencart.order import get_sales_order

	order = payload

	frappe.set_user("Administrator")
	setting = frappe.get_doc(SETTING_DOCTYPE)
	frappe.flags.request_id = request_id

	try:
		sales_order = get_sales_order(cstr(order["id"]))
		if sales_order:
			create_sales_invoice(order, setting, sales_order)
			create_zencart_log(status="Success")
		else:
			create_zencart_log(status="Invalid", message="Sales Order not found for syncing sales invoice.")
	except Exception as e:
		create_zencart_log(status="Error", exception=e, rollback=True)


def create_sales_invoice(zencart_order, setting, so):
	if (
		not frappe.db.get_value("Sales Invoice", {ORDER_ID_FIELD: zencart_order.get("order_id")}, "name")
		and so.docstatus == 1
		and not so.per_billed
	):
		posting_date = getdate(zencart_order.get("date_purchased")) or nowdate()
		sales_invoice = make_sales_invoice(so.name, ignore_permissions=True)
		sales_invoice.set(ORDER_ID_FIELD, str(zencart_order.get("order_id")))
		sales_invoice.set_posting_time = 1
		sales_invoice.posting_date = posting_date
		sales_invoice.due_date = posting_date
		sales_invoice.naming_series =   setting.sales_invoice_series or "SI-Zencart-"
		#sales_invoice.naming_series = setting.sales_invoice_series or "SI-Zencart-"
		sales_invoice.flags.ignore_mandatory = True
		sales_invoice.insert(ignore_mandatory=True)
		sales_invoice.submit()
		if sales_invoice.grand_total > 0:
			make_payament_entry_against_sales_invoice(sales_invoice, setting, posting_date)



def set_cost_center(items, cost_center):
	for item in items:
		item.cost_center = cost_center


def make_payament_entry_against_sales_invoice(doc, setting, posting_date=None):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	payment_entry = get_payment_entry(doc.doctype, doc.name, bank_account=setting.cash_bank_account)
	payment_entry.flags.ignore_mandatory = True
	payment_entry.reference_no = doc.name
	payment_entry.posting_date = posting_date or nowdate()
	payment_entry.reference_date = posting_date or nowdate()
	payment_entry.insert(ignore_permissions=True)
	payment_entry.submit()
