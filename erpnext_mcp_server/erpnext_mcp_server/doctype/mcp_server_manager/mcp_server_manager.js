frappe.ui.form.on('MCP Server Manager', {
	before_save: function (frm) {
		// Validate required fields
		if (!frm.doc.server_name) {
			frappe.throw(__('Server Name is required'));
			return false;
		}

		if (!frm.doc.server_script_path) {
			frappe.throw(__('Server Script Path is required'));
			return false;
		}

		if (!frm.doc.server_type) {
			frappe.throw(__('Server Type is required'));
			return false;
		}
	},

	validate: function (frm) {
		// Additional validation
		if (frm.doc.server_name && frm.doc.server_name.length < 3) {
			frappe.throw(__('Server Name should be at least 3 characters long'));
		}
	},

	refresh: function (frm) {
		// Auto-refresh status when form is loaded
		frm.trigger('update_server_status');

		// Set up button actions
		frm.fields_dict.start_server.input.onclick = function () {
			frappe.call({
				method: 'start_server',
				doc: frm.doc,
				callback: function (r) {
					console.log('r start_server', r);
					if (r.message) {
						if (r.message.success) {
							frappe.show_alert(r.message.message, 5);
						} else {
							frappe.show_alert(
								{
									message: r.message.message,
									indicator: 'red',
								},
								5
							);
						}
					}
					frm.reload_doc();
				},
			});
		};

		frm.fields_dict.stop_server.input.onclick = function () {
			frappe.call({
				method: 'stop_server',
				doc: frm.doc,
				callback: function (r) {
					console.log('r stop_server', r);
					if (r.message) {
						if (r.message.success) {
							frappe.show_alert(r.message.message, 5);
						} else {
							frappe.show_alert(
								{
									message: r.message.message,
									indicator: 'red',
								},
								5
							);
						}
					}
					frm.reload_doc();
				},
			});
		};

		frm.fields_dict.restart_server.input.onclick = function () {
			frappe.call({
				method: 'restart_server',
				doc: frm.doc,
				callback: function (r) {
					console.log('r restart_server', r);
					if (r.message) {
						if (r.message.success) {
							frappe.show_alert(r.message.message, 5);
						} else {
							frappe.show_alert(
								{
									message: r.message.message,
									indicator: 'red',
								},
								5
							);
						}
					}
					frm.reload_doc();
				},
			});
		};

		frm.fields_dict.view_logs.input.onclick = function () {
			frappe.call({
				method: 'view_logs',
				doc: frm.doc,
				callback: function (r) {
					console.log('r view_logs', r);
					if (r.message) {
						if (r.message.success) {
							frappe.show_alert(r.message.message, 5);
						} else {
							frappe.show_alert(
								{
									message: r.message.message,
									indicator: 'red',
								},
								5
							);
						}
					}
					frm.reload_doc();
				},
			});
		};

		// Style status field based on value
		if (frm.doc.server_status) {
			let status_field = frm.get_field('server_status');
			if (frm.doc.server_status === 'Running') {
				status_field.$wrapper.css('color', 'green');
			} else if (frm.doc.server_status === 'Error') {
				status_field.$wrapper.css('color', 'red');
			} else {
				status_field.$wrapper.css('color', 'orange');
			}
		}
	},

	update_server_status: function (frm) {
		// Auto-refresh status every 5 seconds if server is running
		if (frm.doc.server_status === 'Running') {
			setTimeout(function () {
				frappe.call({
					method: 'update_server_status',
					doc: frm.doc,
					callback: function (r) {
						console.log('r update_server_status', r);
						frm.reload_doc();
						frm.trigger('update_server_status');
					},
				});
			}, 5000);
		}
	},
});
