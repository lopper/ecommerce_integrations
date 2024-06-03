// Copyright (c) 2021, Frappe and contributors
// For license information, please see LICENSE

frappe.provide("ecommerce_integrations.zencart.zencart_setting");

frappe.ui.form.on("Zencart Setting", {
	onload: function (frm) {
		frappe.call({
			method: "ecommerce_integrations.utils.naming_series.get_series",
			callback: function (r) {
				$.each(r.message, (key, value) => {
					set_field_options(key, value);
				});
			},
		});
	},

	refresh: function (frm) {

		frm.add_custom_button(__("View Logs"), () => {
			frappe.set_route("List", "Ecommerce Integration Log", {
				integration: "zencart",
			});
		});
		frm.add_custom_button(__("Import Old Olders"), () => {
			// check if the doc has sync_old_orders_checked
			if (!frm.doc.sync_old_orders) {
				frappe.msgprint("Please enable syncing old orders and set the date range to import.");
				return
			}
			// check if 	
			frappe.call({
				method: "ecommerce_integrations.zencart.order.sync_old_orders",
				freeze: true,  // This will freeze the UI
				freeze_message: "Loading, please wait...",  // Optional: Customize the freeze message
				callback: function (r) {
					// show  r.message
					frappe.hide_msgprint();
					frappe.msgprint(r.message);
				},
			});
		});

		frm.add_custom_button(__("Import Recent Olders"), () => {

			// check if 	
			frappe.call({
				method: "ecommerce_integrations.zencart.order.sync_recent_orders",
				freeze: true,  // This will freeze the UI
				freeze_message: "Loading, please wait...",  // Optional: Customize the freeze message
				callback: function (r) {
					// show  r.message
					frappe.hide_msgprint();
					frappe.msgprint(r.message);
				},
			});
		});
		frm.trigger("setup_queries");
	},

	setup_queries: function (frm) {

		frm.set_query("price_list", () => {
			return {
				filters: {
					selling: 1,
				},
			};
		});

		frm.set_query("cost_center", () => {
			return {
				filters: {
					company: frm.doc.company,
					is_group: "No",
				},
			};
		});

		frm.set_query("cash_bank_account", () => {
			return {
				filters: [
					["Account", "account_type", "in", ["Cash", "Bank"]],
					["Account", "root_type", "=", "Asset"],
					["Account", "is_group", "=", 0],
					["Account", "company", "=", frm.doc.company],
				],
			};
		});

		const tax_query = () => {
			return {
				query: "erpnext.controllers.queries.tax_account_query",
				filters: {
					account_type: ["Tax", "Chargeable", "Expense Account"],
					company: frm.doc.company,
				},
			};
		};

		frm.set_query("tax_account", "taxes", tax_query);
		frm.set_query("default_sales_tax_account", tax_query);
		frm.set_query("default_shipping_charges_account", tax_query);
	},
});
