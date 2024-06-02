import json
from typing import Literal, Optional
import requests
import frappe
from frappe import _
from frappe.utils import cint, cstr, flt, get_datetime, getdate, nowdate
from datetime import datetime, timedelta


from ecommerce_integrations.zencart.constants import (
	SETTING_DOCTYPE,
	ORDER_ID_FIELD,
	CUSTOMER_ID_FIELD,
	EVENT_MAPPER
)
from ecommerce_integrations.zencart.customer import ZencartCustomer
from ecommerce_integrations.zencart.utils import create_zencart_log

DEFAULT_TAX_FIELDS = {
	"sales_tax": "default_sales_tax_account",
	"shipping": "default_shipping_charges_account",
}


def sync_sales_order(payload, request_id=None):
	order = payload
	#frappe.set_user("Administrator")
	frappe.flags.request_id = request_id
	order_id = cstr(order.get("order_id"))
	if frappe.db.get_value("Sales Order", filters={ORDER_ID_FIELD: order_id}):
		create_zencart_log(status="Invalid", message=f"Sales order {order_id} already exists, not synced")
		return False
	try:		
		zencart_customer = order.get("customer") if order.get("customer") is not None else {}
		zencart_customer["billing_address"] = order.get("billing_address", "")
		zencart_customer["shipping_address"] = order.get("delivery_address", "")
		customer_id = zencart_customer.get("id")
		if customer_id:
			customer = ZencartCustomer(customer_id=customer_id)
			if not customer.is_synced():
				customer.sync_customer(customer=zencart_customer)
			else:
				customer.update_existing_addresses(zencart_customer)

		#don't create items if they don't exist
		#create_items_if_not_exist(order)

		setting = frappe.get_doc(SETTING_DOCTYPE)
		create_order(order, setting)		
	except Exception as e:
		create_zencart_log(status="Error", exception=e, rollback=True)
		return False
	else:
		create_zencart_log(status="Success", message=f"Sales order {order_id} synced")
		return True


def create_order(order, setting, company=None):
	# local import to avoid circular dependencies
	from ecommerce_integrations.zencart.invoice import create_sales_invoice

	so = create_sales_order(order, setting, company)
	if so:
		create_sales_invoice(order, setting, so)

		#if order.get("fulfillments"):
			#create_delivery_note(order, setting, so)


def create_sales_order(zencart_order, setting, company=None):
	customer = None
	if zencart_order.get("customer", {}):
		if customer_id := zencart_order.get("customer", {}).get("id"):
			customer = frappe.db.get_value("Customer", {CUSTOMER_ID_FIELD: customer_id}, "name")

	so = frappe.db.get_value("Sales Order", {ORDER_ID_FIELD: zencart_order.get("order_id")}, "name")
	if not so:
		items = get_order_items(
			zencart_order.get("items"),
			setting,
			getdate(zencart_order.get("date_purchased")))
		if not items:
			message = (
				"Following items exists in the zencart order but relevant records were"
				" not found in the zencart Product master"
			)
			message += "\n" + ", ".join(product_not_exists)

			create_zencart_log(status="Error", exception=message, rollback=True)

			return ""

		taxes = get_order_taxes(zencart_order, setting)
		so = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"naming_series": setting.sales_order_series or "SO-Zencart-",
				"po_no": "ZN-" + zencart_order.get("order_id"),
				ORDER_ID_FIELD: str(zencart_order.get("order_id")),
				"customer": customer,
				"transaction_date": getdate(zencart_order.get("date_purchased")) or nowdate(),
				"delivery_date": getdate(zencart_order.get("date_purchased")) or nowdate(),
				"company": setting.company,
				"ignore_pricing_rule": 1,
				"items": items,
				"taxes": taxes
 			}
		)
		if company:
			so.update({"company": company, "status": "Draft"})
		so.flags.ignore_mandatory = True
		so.flags.zencart_order_json = json.dumps(zencart_order)
		so.save(ignore_permissions=True)
		so.submit()

	else:
		so = frappe.get_doc("Sales Order", so)

	return so

def get_order_taxes(zencart_order, setting):
	# sales tax
	taxes = []
	order_tax_value = zencart_order.get("order_tax")
	if order_tax_value is not None and order_tax_value != '':
		taxes.append(
			{
				"charge_type": "Actual",
				"account_head": get_tax_account_head(charge_type="sales_tax"),
				"tax_amount": float(order_tax_value),
				"included_in_print_rate": 0,
				"cost_center": setting.cost_center,
				"dont_recompute_tax": 1,
			}
		)
	shipping_total_value = zencart_order.get("shipping_total")
	if shipping_total_value is not None and shipping_total_value != '':
		taxes.append(
			{
				"charge_type": "Actual",
				"account_head": get_tax_account_head(charge_type="shipping"),
				"tax_amount": float(shipping_total_value),
				"cost_center": setting.cost_center,
			}
		)
	# shipping charge
	return taxes
def get_order_items(order_items, setting, delivery_date):
	items = []
	for zencart_item in order_items:
		items.append(
			{
				"item_code": zencart_item.get("name"),
				"item_name": zencart_item.get("name"),
				"rate": zencart_item.get("price"),
				"delivery_date": delivery_date,
				"qty": zencart_item.get("quantity"),
				"stock_uom": zencart_item.get("uom") or "Each",
				"warehouse": setting.warehouse
			}
		)


	return items




def consolidate_order_taxes(taxes):
	tax_account_wise_data = {}
	for tax in taxes:
		account_head = tax["account_head"]
		tax_account_wise_data.setdefault(
			account_head,
			{
				"charge_type": "Actual",
				"account_head": account_head,
				"description": tax.get("description"),
				"cost_center": tax.get("cost_center"),
				"included_in_print_rate": 0,
				"dont_recompute_tax": 1,
				"tax_amount": 0,
				"item_wise_tax_detail": {},
			},
		)
		tax_account_wise_data[account_head]["tax_amount"] += flt(tax.get("tax_amount"))
		if tax.get("item_wise_tax_detail"):
			tax_account_wise_data[account_head]["item_wise_tax_detail"].update(tax["item_wise_tax_detail"])

	return tax_account_wise_data.values()



def get_tax_account_description(tax):
	tax_title = tax.get("title")

	tax_description = frappe.db.get_value(
		"Zencart Tax Account", {"parent": SETTING_DOCTYPE, "zencart_tax": tax_title}, "tax_description",
	)

	return tax_description


def get_tax_account_head(charge_type: Optional[Literal["shipping", "sales_tax"]] = None):
	
	tax_account = frappe.db.get_single_value(SETTING_DOCTYPE, DEFAULT_TAX_FIELDS[charge_type])

	if not tax_account:
		frappe.throw(_("Tax Account not specified for Zencart Tax {0}").format(tax.get("title")))

	return tax_account

def get_sales_order(order_id):
	"""Get ERPNext sales order using zencart order id."""
	sales_order = frappe.db.get_value("Sales Order", filters={ORDER_ID_FIELD: order_id})
	if sales_order:
		return frappe.get_doc("Sales Order", sales_order)

@frappe.whitelist()
def sync_recent_orders():
	zencart_setting = frappe.get_cached_doc(SETTING_DOCTYPE)
	if not cint(zencart_setting.enable_zencart):
		return

	zencart_setting = frappe.get_cached_doc(SETTING_DOCTYPE)
	
	now = datetime.now()
	past_time = now - timedelta(hours=4)
	orders = query_zencart_sales_orders(
			zencart_setting.zencart_url,
			zencart_setting.password,
			past_time, 
			now)
	successfulImports = 0
	skippedImports = 0
	for order in orders:
		if frappe.db.get_value("Sales Order", filters={ORDER_ID_FIELD: cstr(order.get("order_id"))}):
			print(f"Order {order.get('id')} already exists, not synced")
			skippedImports += 1
		else:
			log = create_zencart_log(
				method=EVENT_MAPPER["orders/create"], request_data=json.dumps(order), make_new=True
			)
			sync_sales_order(order, request_id=log.name)
			successfulImports += 1

	zencart_setting = frappe.get_doc(SETTING_DOCTYPE)
	zencart_setting.last_sync_date = now
	zencart_setting.save()
	return f"Success, imported {successfulImports} recent orders and skipped {skippedImports}."

@frappe.whitelist()
def sync_old_orders():
	zencart_setting = frappe.get_cached_doc(SETTING_DOCTYPE)
	if not cint(zencart_setting.sync_old_orders):
		return
	
	orders = query_zencart_sales_orders(
			zencart_setting.zencart_url,
			zencart_setting.password,
			zencart_setting.old_orders_from, 
			zencart_setting.old_orders_to)

	successfulImports = 0
	skippedImports = 0
	for order in orders:
		if frappe.db.get_value("Sales Order", filters={ORDER_ID_FIELD: cstr(order.get("order_id"))}):
			print(f"Order {order.get('order_id')} already exists, not synced")
			skippedImports += 1
		else:
			log = create_zencart_log(
				method=EVENT_MAPPER["orders/create"], request_data=json.dumps(order), make_new=True
			)
			sync_sales_order(order, request_id=log.name)
			successfulImports += 1

	zencart_setting = frappe.get_doc(SETTING_DOCTYPE)
	zencart_setting.sync_old_orders = 0
	zencart_setting.save()
	return f"Success, imported {successfulImports} recent orders and skipped {skippedImports}."


def query_zencart_sales_orders(url, api_key, start_date, end_date):
	start_date = get_datetime(start_date).astimezone()
	start_date = start_date.strftime('%Y-%m-%d')
	end_date = get_datetime(end_date).astimezone()
	end_date = end_date.strftime('%Y-%m-%d')

	params = {
		'start_date': start_date,
		'end_date': end_date
	}
	headers = {
		'Authorization': api_key,
		"User-Agent": "ErpNext",
		'Content-Type': 'application/json',
		'Accept': 'application/json'
    }
	try:
		response = requests.get(url, params=params, headers=headers)
		response.raise_for_status()  # Raise an exception for bad status codes
		return response.json()
	except requests.exceptions.RequestException as e:
		print(f"Error: {e}")
		return None
	return response