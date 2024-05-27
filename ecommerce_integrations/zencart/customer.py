from typing import Any, Dict, Optional

import frappe
from frappe import _
from frappe.utils import cstr, validate_phone_number

from ecommerce_integrations.controllers.customer import EcommerceCustomer
from ecommerce_integrations.zencart.constants import (
	CUSTOMER_ID_FIELD,
	MODULE_NAME,
	SETTING_DOCTYPE,
)


class ZencartCustomer(EcommerceCustomer):
	def __init__(self, customer_id: str):
		self.setting = frappe.get_doc(SETTING_DOCTYPE)
		super().__init__(customer_id, CUSTOMER_ID_FIELD, MODULE_NAME)

	def sync_customer(self, customer: Dict[str, Any]) -> None:
		"""Create Customer in ERPNext using zencart's Customer dict."""

		customer_name = customer.get("company")
		if len(customer_name.strip()) == 0:
			customer_name = customer.get("name")

		customer_group = self.setting.customer_group
		super().sync_customer(customer_name, customer_group)

		billing_address = customer.get("billing_address", {})
		shipping_address = customer.get("delivery_address", {})

		if billing_address:
			self.create_customer_address(
				customer_name, billing_address, address_type="Billing", email=customer.get("email")
			)
		if shipping_address:
			self.create_customer_address(
				customer_name, shipping_address, address_type="Shipping", email=customer.get("email")
			)

		self.create_customer_contact(customer)

	def create_customer_address(
		self,
		customer_name,
		zencart_address: Dict[str, Any],
		address_type: str = "Billing",
		email: Optional[str] = None,
	) -> None:
		"""Create customer address(es) using Customer dict provided by zencart."""
		address_fields = _map_address_fields(zencart_address, customer_name, address_type, email)
		super().create_customer_address(address_fields)

	def update_existing_addresses(self, customer):
		billing_address = customer.get("billing_address", {}) or customer.get("default_address")
		shipping_address = customer.get("shipping_address", {})

		customer_name = cstr(customer.get("first_name")) + " " + cstr(customer.get("last_name"))
		email = customer.get("email")

		if billing_address:
			self._update_existing_address(customer_name, billing_address, "Billing", email)
		if shipping_address:
			self._update_existing_address(customer_name, shipping_address, "Shipping", email)

	def _update_existing_address(
		self,
		customer_name,
		zencart_address: Dict[str, Any],
		address_type: str = "Billing",
		email: Optional[str] = None,
	) -> None:
		old_address = self.get_customer_address_doc(address_type)

		if not old_address:
			self.create_customer_address(customer_name, zencart_address, address_type, email)
		else:
			exclude_in_update = ["address_title", "address_type"]
			new_values = _map_address_fields(zencart_address, customer_name, address_type, email)

			old_address.update({k: v for k, v in new_values.items() if k not in exclude_in_update})
			old_address.flags.ignore_mandatory = True
			old_address.save()

	def create_customer_contact(self, zencart_customer: Dict[str, Any]) -> None:

		if not (zencart_customer.get("name") and zencart_customer.get("id")):
			return

		contact_fields = {
			"status": "Passive",
			"first_name": zencart_customer.get("name")
			"company_name": zencart_customer.get("company")
			#"last_name": zencart_customer.get("last_name"),
		}

		phone_no = zencart_customer.get("telephone") 

		if validate_phone_number(phone_no, throw=False):
			contact_fields["phone_nos"] = [{"phone": phone_no, "is_primary_phone": True}]

		super().create_customer_contact(contact_fields)


def _map_address_fields(zencart_address, customer_name, address_type):
	""" returns dict with zencart address fields mapped to equivalent ERPNext fields"""
	address_fields = {
		"address_title": zencart_address.get("name") or customer_name,
		"address_type": address_type,
		"address_line1": zencart_address.get("street_address")
		#"address_line2": zencart_address.get("address2"),
		"city": zencart_address.get("city"),
		"county" : zencart_address.get("suburb"),
		"state": zencart_address.get("state"),
		"pincode": zencart_address.get("postcode"),
		"country": zencart_address.get("country"),
	}


	return address_fields
