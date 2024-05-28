
import json
import unittest
import os
from .utils import TestCase
import frappe
from json import loads
from frappe import _
from frappe.utils import cint, cstr, flt, get_datetime, getdate, nowdate
from ecommerce_integrations.zencart.customer import ZencartCustomer

from ecommerce_integrations.zencart.constants import (
	SETTING_DOCTYPE
)


class TestCustomer(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.setting = frappe.get_doc(SETTING_DOCTYPE)

	def load_fixture(self, name, format="json"):
		with open(os.path.dirname(__file__) + "/data/%s.%s" % (name, format), "rb") as f:
			return f.read()


	def test_sync_customer(self):
		customer = loads(self.load_fixture("single_customer"))
		#if customer_id:
		zencart_customer = ZencartCustomer(customer_id=customer["id"])
		if not zencart_customer.is_synced():
			zencart_customer.sync_customer(customer=customer)
		else:
			zencart_customer.update_existing_addresses(customer)
		pass
