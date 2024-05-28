
import json
import unittest
import os
from .utils import TestCase
import frappe
from json import loads
from frappe import _
from frappe.utils import cint, cstr, flt, get_datetime, getdate, nowdate
from ecommerce_integrations.zencart.order import sync_old_orders, sync_sales_order, create_sales_order,query_zencart_sales_orders,sync_recent_orders
from ecommerce_integrations.zencart.constants import (
	SETTING_DOCTYPE
)


class TestOrder(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.setting = frappe.get_doc(SETTING_DOCTYPE)

	def load_fixture(self, name, format="json"):
		with open(os.path.dirname(__file__) + "/data/%s.%s" % (name, format), "rb") as f:
			return f.read()

	def test_sync_sales_order(self):
		single_order = loads(self.load_fixture("single_order"))
		sync_sales_order(single_order)
		pass

	def test_query_sales_orders(self):
		zencart_setting = frappe.get_cached_doc(SETTING_DOCTYPE)
		url = zencart_setting.zencart_url

		orders = query_zencart_sales_orders(
				zencart_setting.zencart_url,
				zencart_setting.password,
				zencart_setting.old_orders_from, 
				zencart_setting.old_orders_to)
		pass

	def test_sync_old_orders(self):
		#sync_old_orders()
		sync_recent_orders()