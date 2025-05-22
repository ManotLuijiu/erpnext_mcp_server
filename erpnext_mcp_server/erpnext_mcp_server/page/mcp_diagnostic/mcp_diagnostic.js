frappe.pages['mcp-diagnostic'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('MCP Diagnostic'),
    single_column: true,
  });

  // Add diagnostic button
  var $btnContainer = $('<div class="diagnostic-buttons">').appendTo(page.main);

  // Test simple subprocess
  $('<button class="btn btn-primary m-2">')
    .text('Test Subprocess')
    .appendTo($btnContainer)
    .on('click', function () {
      frappe.call({
        method: 'erpnext_mcp_server.api.diagnostic.test_subprocess',
        callback: function (r) {
          show_result('Subprocess Test', r.message);
        },
      });
    });

  // Test realtime
  $('<button class="btn btn-primary m-2">')
    .text('Test Realtime')
    .appendTo($btnContainer)
    .on('click', function () {
      // Set up listener
      frappe.realtime.on('diagnostic_response', function (data) {
        show_result('Realtime Test', data);
        // Remove listener
        frappe.realtime.off('diagnostic_response');
      });

      // Trigger event
      frappe.call({
        method: 'erpnext_mcp_server.api.diagnostic.test_realtime',
        callback: function (r) {
          // Success response from the call (not the realtime)
          console.log('Test realtime call successful', r);
        },
      });
    });

  // Results container
  var $results = $('<div class="results-container mt-4">').appendTo(page.main);

  function show_result(title, result) {
    var $result = $('<div class="result-item card p-3 mb-3">').appendTo(
      $results
    );
    $('<h5>').text(title).appendTo($result);

    if (typeof result === 'object') {
      // Pretty print object
      $('<pre>')
        .text(JSON.stringify(result, null, 2))
        .appendTo($result);
    } else {
      // Simple text
      $('<div>').text(result).appendTo($result);
    }
  }
};

frappe.pages['mcp-diagnostic'].on_page_show = function (wrapper) {
  load_desk_page(wrapper);
};

function load_desk_page(wrapper) {
  let $parent = $(wrapper).find('.layout-main-section');
  $parent.empty();

  frappe.require('mcp_diagnostic.bundle.jsx').then(() => {
    frappe.mcp_diagnostic = new frappe.ui.McpDiagnostic({
      wrapper: $parent,
      page: wrapper.page,
    });
  });
}
