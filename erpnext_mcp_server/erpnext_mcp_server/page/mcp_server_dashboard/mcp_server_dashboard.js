frappe.pages['mcp-server-dashboard'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'MCP Server Dashboard',
    single_column: false,
  })

  // Add the page content
  $(frappe.render_template('mcp_server_dashboard', {})).appendTo(page.body)

  // Initialize the dashboard
  new MCPServerDashboard(page)
}

class MCPServerDashboard {
  constructor(page) {
    this.page = page
    this.setup_actions()
    this.init_dashboard()
    this.start_status_refresh()
  }

  setup_actions() {
    const me = this

    // Add actions to the page
    this.page.add_inner_button(__('Start MCP Server'), function () {
      me.start_mcp_server()
    })
    this.page.add_inner_button(__('Stop MCP Server'), function () {
      me.stop_mcp_server()
    })
    this.page.add_inner_button(__('Restart MCP Server'), function () {
      me.refresh_status()
    })
    this.page.add_inner_button(__('Settings'), function () {
      frappe.set_route('List', 'MCP Server Settings')
    })
  }

  init_dashboard() {
    this.refresh_status()
  }

  start_status_refresh() {
    // Refresh status every 10 seconds
    const me = this
    setInterval(function () {
      me.refresh_status()
    }, 10000)
  }

  refresh_status() {
    const me = this
    frappe.call({
      method: 'erpnext_mcp_server.api.mcp_server.get_mcp_server_status',
      callback: function (r) {
        if (r.message) {
          me.update_status_display(r.message)
        } else {
          frappe.msgprint(__('Failed to restart MCP server'))
        }
      },
    })
  }

  update_status_display(data) {
    // Update status indicator
    const status_indicator = $('#mcp-status-indicator')
    const status_text = $('#mcp-status-text')
    const process_id = $('#mcp-process-id')
    const last_start = $('#mcp-last-start')
    const last_stop = $('#mcp-last-stop')
    const transport = $('#mcp-transport')
    const error_log = $('#mcp-error-log')

    // Clear existing classes and set new one
    status_indicator.removeClass(
      'indicator-green indicator-red indicator-orange indicator-blue',
    )

    if (data.status === 'Running') {
      status_indicator.addClass('indicator-green')
      status_text.text('Running')
    } else if (data.status === 'Starting') {
      status_indicator.addClass('indicator-blue')
      status_text.text('Starting')
    } else if (data.status === 'Error') {
      status_indicator.addClass('indicator-red')
      status_text.text('Error')
    } else {
      status_indicator.addClass('indicator-orange')
      status_text.text('Stopped')
    }

    // Update other fields
    process_id.text(data.process_id || 'N/A')
    last_start.text(data.last_start_time || 'N/A')
    last_stop.text(data.last_stop_time || 'N/A')
    transport.text(data.transport || 'stdio')

    if (data.last_error) {
      error_log.text(data.last_error)
      $('.mcp-error-section').show()
    } else {
      error_log.text('No errors reported.')
      $('.mcp-error-section').hide()
    }
  }

  start_mcp_server() {
    const me = this
    frappe.call({
      method: 'erpnext_mcp_server.api.mcp_server.start_mcp_server',
      callback: function (r) {
        if (r.message) {
          if (r.message.status === 'success') {
            frappe.show_alert(
              {
                message: __('MCP server started successfully'),
                indicator: 'green',
              },
              5,
            )
            me.refresh_status()
          } else {
            frappe.show_alert(
              {
                message: __(r.message.message || 'Failed to start MCP Server'),
                indicator: 'red',
              },
              5,
            )
          }
          me.update_status_display(r.message)
        } else {
          frappe.msgprint(__('Failed to start MCP server'))
        }
      },
    })
  }

  stop_server() {
    const me = this
    frappe.confirm(
      __('Are you sure you want to stop the MCP Server?'),
      function () {
        // Yes
        frappe.call({
          method:
            'erpnext_mcp_server.erpnext_mcp_server.api.mcp_server.stop_server',
          callback: function (r) {
            if (r.message) {
              if (r.message.status === 'success') {
                frappe.show_alert(
                  {
                    message: __('MCP Server stopped successfully'),
                    indicator: 'green',
                  },
                  5,
                )
                me.refresh_status()
              } else {
                frappe.show_alert(
                  {
                    message: __(
                      r.message.message || 'Failed to stop MCP Server',
                    ),
                    indicator: 'red',
                  },
                  5,
                )
              }
            }
          },
        })
      },
      function () {
        // No - do nothing
      },
    )
  }
}
