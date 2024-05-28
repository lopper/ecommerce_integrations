# Copyright (c) 2021, Frappe and contributors
# For license information, please see LICENSE

from typing import Dict, List

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import get_datetime

from ecommerce_integrations.controllers.setting import (
	ERPNextWarehouse,
	IntegrationWarehouse,
	SettingController,
)
from ecommerce_integrations.zencart.constants import (
	CUSTOMER_ID_FIELD,
	ORDER_ID_FIELD

)

class ZencartSetting(SettingController):
	def is_enabled(self) -> bool:
		return bool(self.enable_zencart)

	def validate(self):
		
		self._initalize_default_values()

		if self.is_enabled():
			setup_custom_fields()

	def on_update(self):
		pass


	def _initalize_default_values(self):
		if not self.last_inventory_sync:
			self.last_inventory_sync = get_datetime("1970-01-01")

def setup_custom_fields():
	custom_fields = {

		"Customer": [
			dict(
				fieldname=CUSTOMER_ID_FIELD,
				label="Zencart Customer Id",
				fieldtype="Data",
				insert_after="series",
				read_only=1,
				print_hide=1,
			)
		],
		"Sales Order": [
			dict(
				fieldname=ORDER_ID_FIELD,
				label="Zencart Order Id",
				fieldtype="Data",
				insert_after="series",
				read_only=1,
				print_hide=1,
			)
		],
		
		"Sales Invoice": [
			dict(
				fieldname=ORDER_ID_FIELD,
				label="Zencart Order Id",
				fieldtype="Data",
				insert_after="series",
				read_only=1,
				print_hide=1,
			)
		],
	}

	create_custom_fields(custom_fields)
