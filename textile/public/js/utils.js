frappe.provide("textile");

textile.print_process_components = {
	"coating_item": "Coating",
	"softener_item": "Softener",
	"sublimation_paper_item": "Sublimation Paper",
	"protection_paper_item": "Protection Paper",
}

$.extend(textile, {
	get_items_from_print_order: function (frm, method, filters) {
		let query_filters = {
			docstatus: 1,
			status: ["!=", "Closed"],
			items_created: 1,
			company: frm.doc.company,
			customer: frm.doc.customer || undefined,
		}
		if (filters) {
			Object.assign(query_filters, filters);
		}

		erpnext.utils.map_current_doc({
			method: method,
			source_doctype: "Print Order",
			target: frm,
			setters: [
				{
					fieldtype: 'Link',
					label: __('Customer'),
					options: 'Customer',
					fieldname: 'customer',
					default: frm.doc.customer || undefined,
				},
				{
					fieldtype: 'Link',
					label: __('Fabric Item'),
					options: 'Item',
					fieldname: 'fabric_item',
					get_query: () => {
						return erpnext.queries.item({ print_item_type: 'Fabric' });
					},
				},
				{
					fieldtype: 'Link',
					label: __('Process Item'),
					options: 'Item',
					fieldname: 'process_item',
					get_query: () => {
						return erpnext.queries.item({ print_item_type: 'Print Process' });
					},
				},
			],
			columns: ['customer_name', 'fabric_item_name', 'process_item_name', 'transaction_date'],
			get_query_filters: query_filters,
		});
	},
});