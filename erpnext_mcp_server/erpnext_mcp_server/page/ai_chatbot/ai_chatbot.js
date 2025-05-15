frappe.pages["ai-chatbot"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("ai-chatbot"),
		single_column: true,
	});
};

frappe.pages["ai-chatbot"].on_page_show = function (wrapper) {
	load_desk_page(wrapper);
};

function load_desk_page(wrapper) {
	let $parent = $(wrapper).find(".layout-main-section");
	$parent.empty();

	frappe.require("ai_chatbot.bundle.jsx").then(() => {
		frappe.ai_chatbot = new frappe.ui.AiChatbot({
			wrapper: $parent,
			page: wrapper.page,
		});
	});
}