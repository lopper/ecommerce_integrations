import frappe

from ecommerce_integrations.zencart.constants import SETTING_DOCTYPE
from ecommerce_integrations.zencart.doctype.zencart_setting.zencart_setting import (
	setup_custom_fields,
)


def execute():
	frappe.reload_doc("zencart", "doctype", "zencart_setting")

	settings = frappe.get_doc(SETTING_DOCTYPE)
	if settings.is_enabled():
		setup_custom_fields()
