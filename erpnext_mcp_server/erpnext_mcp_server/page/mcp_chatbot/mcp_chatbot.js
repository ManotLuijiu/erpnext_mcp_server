frappe.pages["mcp-chatbot"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("mcp-chatbot"),
		single_column: true,
	});
};

frappe.pages["mcp-chatbot"].on_page_show = function (wrapper) {
	load_desk_page(wrapper);
};

function load_desk_page(wrapper) {
	let $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();

	frappe.require("mcp_chatbot.bundle.js").then(() => {
		frappe.mcp_chatbot = new frappe.ui.McpChatbot({
			wrapper: $parent,
			page: wrapper.page,
		});
	});
}