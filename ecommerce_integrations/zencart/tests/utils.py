import os
import sys
import unittest
from unittest.mock import patch

import frappe
from erpnext import get_default_cost_center
from pyactiveresource.activeresource import ActiveResource
from pyactiveresource.testing import http_fake

from ecommerce_integrations.zencart.constants import API_VERSION, SETTING_DOCTYPE



class TestCase(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		with patch(
			"ecommerce_integrations.zencart.doctype.zencart_setting.zencart_setting.ZencartSetting._handle_webhooks"
		):
			setting = frappe.get_doc(SETTING_DOCTYPE)

			setting.update(
				{
					"enable_shopify": 1,
					"shopify_url": "frappetest.myshopify.com",
					"password": "supersecret",
					"shared_secret": "supersecret",
					"default_customer": "_Test Customer",
					"customer_group": "_Test Customer Group 1",
					"company": "_Test Company",
					"cost_center": get_default_cost_center("_Test Company"),
					"cash_bank_account": "_Test Bank - _TC",
					"price_list": "_Test Price List",
					"warehouse": "_Test Warehouse - _TC",
					"sales_order_series": "SAL-ORD-.YYYY.-",
					"sync_delivery_note": 1,
					"delivery_note_series": "MAT-DN-.YYYY.-",
					"sync_sales_invoice": 1,
					"sales_invoice_series": "SINV-.YY.-",
					"upload_erpnext_items": 1,
					"update_shopify_item_on_update": 1,
					"update_erpnext_stock_levels_to_shopify": 1,
					"doctype": "Shopify Setting",
					"shopify_warehouse_mapping": [
						{
							"shopify_location_id": "62279942297",
							"shopify_location_name": "WH 1",
							"erpnext_warehouse": "_Test Warehouse 1 - _TC",
						},
						{
							"shopify_location_id": "61724295321",
							"shopify_location_name": "WH 2",
							"erpnext_warehouse": "_Test Warehouse 2 - _TC",
						},
					],
				}
			).save(ignore_permissions=True)

	def setUp(self):
		ActiveResource.site = None
		ActiveResource.headers = None

		shopify.ShopifyResource.clear_session()
		shopify.ShopifyResource.site = f"https://frappetest.myshopify.com/admin/api/{API_VERSION}"
		shopify.ShopifyResource.password = None
		shopify.ShopifyResource.user = None

		http_fake.initialize()
		self.http = http_fake.TestHandler
		self.http.set_response(Exception("Bad request"))
		self.http.site = "https://frappetest.myshopify.com"

	def load_fixture(self, name, format="json"):
		with open(os.path.dirname(__file__) + "/data/%s.%s" % (name, format), "rb") as f:
			return f.read()

	def fake(self, endpoint, **kwargs):
		body = kwargs.pop("body", None) or self.load_fixture(endpoint)
		method = kwargs.pop("method", "GET")
		prefix = kwargs.pop("prefix", f"/admin/api/{API_VERSION}")

		if "extension" in kwargs and not kwargs["extension"]:
			extension = ""
		else:
			extension = ".%s" % (kwargs.pop("extension", "json"))

		url = "https://frappetest.myshopify.com%s/%s%s" % (prefix, endpoint, extension)
		try:
			url = kwargs["url"]
		except KeyError:
			pass

		headers = {}
		if kwargs.pop("has_user_agent", True):
			userAgent = "ShopifyPythonAPI/%s Python/%s" % (shopify.VERSION, sys.version.split(" ", 1)[0])
			headers["User-agent"] = userAgent

		try:
			headers.update(kwargs["headers"])
		except KeyError:
			pass

		code = kwargs.pop("code", 200)

		self.http.respond_to(
			method,
			url,
			headers,
			body=body,
			code=code,
			response_headers=kwargs.pop("response_headers", None),
		)
