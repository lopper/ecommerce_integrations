from typing import List

import frappe
from frappe import _, _dict

from ecommerce_integrations.ecommerce_integrations.doctype.ecommerce_integration_log.ecommerce_integration_log import (
	create_log,
)
from ecommerce_integrations.zencart.constants import (
	MODULE_NAME,
	OLD_SETTINGS_DOCTYPE,
	SETTING_DOCTYPE,
)


def create_zencart_log(**kwargs):
	return create_log(module_def=MODULE_NAME, **kwargs)

