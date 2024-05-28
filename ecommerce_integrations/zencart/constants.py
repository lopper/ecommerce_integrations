# Copyright (c) 2021, Frappe and contributors
# For license information, please see LICENSE


MODULE_NAME = "zencart"
SETTING_DOCTYPE = "Zencart Setting"

API_VERSION = "2025-05"

WEBHOOK_EVENTS = [

]

EVENT_MAPPER = {
	"orders/create": "ecommerce_integrations.zencart.order.sync_sales_order"
}


# custom fields

CUSTOMER_ID_FIELD = "zencart_customer_id"
ORDER_ID_FIELD = "zencart_order_id"

# ERPNext already defines the default UOMs from Shopify but names are different
