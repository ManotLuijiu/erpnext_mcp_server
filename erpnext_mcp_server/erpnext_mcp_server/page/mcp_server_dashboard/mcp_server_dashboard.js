frappe.pages['mcp-server-dashboard'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'MCP Server Dashboard',
    single_column: false,
  })

  // Add the page content
  $(frappe.render_template('mcp_server_dashboard', {})).appendTo(page.body)

  // Initialize the dashboard if not already created
  if (!frappe.pages['mcp-server-dashboard'].dashboard) {
    frappe.pages['mcp-server-dashboard'].dashboard = new MCPServerDashboard(
      page,
    )
  }
}

// Single page show handler
frappe.pages['mcp-server-dashboard'].on_page_show = function () {
  // Ensure dashboard instance exists
  if (frappe.pages['mcp-server-dashboard'].dashboard) {
    frappe.pages['mcp-server-dashboard'].dashboard.on_show()
  }
}

// Single page hide handler
frappe.pages['mcp-server-dashboard'].on_page_hide = function () {
  if (frappe.pages['mcp-server-dashboard'].dashboard) {
    frappe.pages['mcp-server-dashboard'].dashboard.on_hide()
  }
}

class MCPServerDashboard {
  constructor(page) {
    this.page = page
    this.status_interval = null
    this.theme_observer = null
    this.setup_theme_support()
    this.setup_actions()
    this.init_dashboard()
    this.start_status_refresh()
  }

  // Called when page is shown
  on_show() {
    // Reapply theme styles and restart refresh if needed
    this.apply_theme_styles()
    if (!this.status_interval) {
      this.start_status_refresh()
    }
    this.refresh_status()
  }

  // Called when page is hidden
  on_hide() {
    // Clean up intervals but keep the dashboard instance
    if (this.status_interval) {
      clearInterval(this.status_interval)
      this.status_interval = null
    }
  }

  setup_theme_support() {
    // Apply theme styles immediately
    this.apply_theme_styles()

    // Watch for theme changes
    this.observe_theme_changes()
  }

  apply_theme_styles() {
    // Remove existing theme styles
    $('#mcp-dashboard-theme-styles').remove()

    // Detect current theme
    const isDarkTheme =
      document.documentElement.getAttribute('data-theme') === 'dark'

    // Create dynamic styles
    const theme_styles = `
      <style id="mcp-dashboard-theme-styles">
        /* Theme aware variables */
        .mcp-server-dashboard {
          background-color: ${isDarkTheme ? 'var(--bg-color)' : '#f5f5f5'};
          color: ${isDarkTheme ? 'var(--text-color)' : '#333'};
          min-height: calc(100vh - 60px);
          padding: 20px;
        }
        
        .mcp-server-dashboard .card {
          background: ${isDarkTheme ? 'var(--card-bg)' : '#ffffff'};
          border: 1px solid ${isDarkTheme ? 'var(--border-color)' : '#d1d8dd'};
          border-radius: 8px;
          margin-bottom: 20px;
          box-shadow: 0 1px 3px ${isDarkTheme ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.1)'};
          transition: all 0.3s ease;
        }
        
        .mcp-server-dashboard .card:hover {
          box-shadow: 0 4px 8px ${isDarkTheme ? 'rgba(0,0,0,0.4)' : 'rgba(0,0,0,0.15)'};
        }
        
        .mcp-server-dashboard .card-header {
          background: ${isDarkTheme ? 'var(--subtle-accent)' : '#f8f9fa'};
          border-bottom: 1px solid ${isDarkTheme ? 'var(--border-color)' : '#e0e6ed'};
          padding: 15px 20px;
        }
        
        .mcp-server-dashboard .card-title {
          color: ${isDarkTheme ? 'var(--text-color)' : '#333'};
          font-weight: 600;
          font-size: 16px;
          margin: 0;
        }
        
        .mcp-server-dashboard .card-body {
          padding: 20px;
        }
        
        .mcp-server-dashboard label {
          font-weight: 600;
          color: ${isDarkTheme ? 'var(--text-muted)' : '#6c757d'};
          font-size: 13px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .mcp-server-dashboard .form-group {
          margin-bottom: 15px;
        }
        
        .mcp-server-dashboard .form-group > div {
          color: ${isDarkTheme ? 'var(--text-color)' : '#212529'};
          font-size: 15px;
          margin-top: 5px;
        }
        
        /* Status display */
        .status-display {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .indicator {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          display: inline-block;
          margin-right: 0;
        }
        
        #mcp-status-text {
          font-weight: 600;
          color: ${isDarkTheme ? 'var(--text-color)' : '#333'};
        }
        
        /* Error section */
        .mcp-error-section .card-header {
          background: ${isDarkTheme ? '#2a1a1a' : '#fff5f5'};
          border-color: ${isDarkTheme ? '#4a2020' : '#f8d7da'};
        }
        
        .mcp-error-section .card {
          border-color: ${isDarkTheme ? '#4a2020' : '#f8d7da'};
        }
        
        #mcp-error-log {
          background: ${isDarkTheme ? '#1a1a1a' : '#f8f9fa'};
          color: ${isDarkTheme ? '#ff9999' : '#721c24'};
          border: 1px solid ${isDarkTheme ? '#333' : '#e9ecef'};
          border-radius: 4px;
          padding: 10px;
          font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
          font-size: 13px;
          line-height: 1.5;
          max-height: 200px;
          overflow-y: auto;
          white-space: pre-wrap;
        }
        
        /* Action buttons styling */
        .page-actions .btn {
          border-radius: 4px;
          padding: 6px 12px;
          font-size: 13px;
          font-weight: 500;
          transition: all 0.3s ease;
        }
        
        .page-actions .btn-default {
          background: ${isDarkTheme ? 'var(--btn-bg)' : '#ffffff'};
          border: 1px solid ${isDarkTheme ? 'var(--border-color)' : '#d1d8dd'};
          color: ${isDarkTheme ? 'var(--text-color)' : '#333'};
        }
        
        .page-actions .btn-default:hover {
          background: ${isDarkTheme ? 'var(--subtle-accent)' : '#f8f9fa'};
          border-color: ${isDarkTheme ? 'var(--primary-color)' : '#007bff'};
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
          .mcp-server-dashboard {
            padding: 10px;
          }
          
          .mcp-server-dashboard .card {
            margin-bottom: 15px;
          }
        }
        
        /* Indicators */
        .indicator-green {
          background-color: #28a745;
          box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.4);
        }
        
        .indicator-red {
          background-color: #dc3545;
          box-shadow: 0 0 0 0 rgba(220, 53, 69, 0.4);
        }
        
        .indicator-orange {
          background-color: #fd7e14;
          box-shadow: 0 0 0 0 rgba(253, 126, 20, 0.4);
        }
        
        .indicator-blue {
          background-color: #007bff;
          box-shadow: 0 0 0 0 rgba(0, 123, 255, 0.4);
        }
        
        /* Add pulse animation for active status */
        .indicator-green,
        .indicator-blue {
          animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
          0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(0, 123, 255, 0.7);
          }
          
          70% {
            transform: scale(1);
            box-shadow: 0 0 0 6px rgba(0, 123, 255, 0);
          }
          
          100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(0, 123, 255, 0);
          }
        }
        
        /* Dark mode pulse animation */
        .indicator-green.dark {
          animation: pulse-green 2s infinite;
        }
        
        @keyframes pulse-green {
          0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7);
          }
          
          70% {
            transform: scale(1);
            box-shadow: 0 0 0 6px rgba(40, 167, 69, 0);
          }
          
          100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(40, 167, 69, 0);
          }
        }
        
        /* List styles */
        .mcp-server-dashboard ul {
          padding-left: 20px;
          color: ${isDarkTheme ? 'var(--text-color)' : '#444'};
        }
        
        .mcp-server-dashboard ul li {
          margin-bottom: 8px;
          line-height: 1.6;
        }
        
        /* Pre tag styling */
        .mcp-server-dashboard pre {
          background: ${isDarkTheme ? '#1a1a1a' : '#f8f9fa'};
          border: 1px solid ${isDarkTheme ? '#333' : '#e9ecef'};
          border-radius: 4px;
          padding: 10px;
          margin: 0;
        }
      </style>
    `

    // Add styles to head
    $('head').append(theme_styles)
  }

  observe_theme_changes() {
    // Disconnect existing observer if any
    if (this.theme_observer) {
      this.theme_observer.disconnect()
    }

    // Use MutationObserver to detect theme changes
    this.theme_observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (
          mutation.type === 'attributes' &&
          mutation.attributeName === 'data-theme'
        ) {
          this.apply_theme_styles()
        }
      }
    })

    this.theme_observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    })
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
      me.restart_mcp_server()
    })
    this.page.add_inner_button(__('Settings'), function () {
      frappe.set_route('List', 'MCP Server Settings')
    })
    this.page.add_inner_button(__('Server Logs'), function () {
      me.show_server_logs()
    })
  }

  init_dashboard() {
    this.refresh_status()
  }

  start_status_refresh() {
    // Clear any existing interval
    if (this.status_interval) {
      clearInterval(this.status_interval)
    }

    // Refresh status every 10 seconds
    const me = this
    this.status_interval = setInterval(function () {
      me.refresh_status()
    }, 10000)
  }

  // refresh_status() {
  //   const me = this
  //   frappe.call({
  //     method: 'erpnext_mcp_server.api.mcp_server.get_mcp_server_status',
  //     callback: function (r) {
  //       if (r.message) {
  //         me.update_status_display(r.message)
  //       } else {
  //         console.error('Failed to get MCP server status')
  //       }
  //     },
  //     error: function (r) {
  //       console.error('Error getting MCP server status:', r)
  //       // Show error indicator
  //       me.update_status_display({
  //         status: 'Error',
  //         is_running: false,
  //         last_error: 'Failed to get server status',
  //       })
  //     },
  //   })
  // }

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
      'indicator-green indicator-red indicator-orange indicator-blue dark',
    )

    const isDarkTheme =
      document.documentElement.getAttribute('data-theme') === 'dark'

    // Use the status directly from data object, with fallback logic
    const status = data.status || (data.is_running ? 'Running' : 'Stopped')

    if (status === 'Running') {
      status_indicator.addClass(`indicator-green${isDarkTheme ? ' dark' : ''}`)
      status_text.text('Running').css('color', '#28a745')
    } else if (status === 'Starting') {
      status_indicator.addClass('indicator-blue')
      status_text.text('Starting').css('color', '#007bff')
    } else if (status === 'Error') {
      status_indicator.addClass('indicator-red')
      status_text.text('Error').css('color', '#dc3545')
    } else {
      status_indicator.addClass('indicator-orange')
      status_text.text('Stopped').css('color', '#fd7e14')
    }

    // Update other fields
    process_id.text(data.process_id || 'N/A')
    last_start.text(data.last_start_time || 'N/A')
    last_stop.text(data.last_stop_time || 'N/A')
    transport.text(data.transport || 'stdio')

    if (data.last_error) {
      error_log.text(data.last_error)
      $('.mcp-error-section').slideDown()
    } else {
      error_log.text('No errors reported.')
      $('.mcp-error-section').slideUp()
    }
  }

  start_mcp_server() {
    const me = this

    // Show loading indicator
    frappe.show_alert(
      {
        message: __('Starting MCP server...'),
        indicator: 'blue',
      },
      3,
    )

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
      error: function (r) {
        console.error('Error starting MCP server:', r)
        frappe.show_alert(
          {
            message: __('Failed to start MCP server'),
            indicator: 'red',
          },
          5,
        )
      },
    })
  }

  stop_mcp_server() {
    const me = this

    frappe.confirm(
      __('Are you sure you want to stop the MCP Server?'),
      function () {
        // Yes
        frappe.call({
          method: 'erpnext_mcp_server.api.mcp_server.stop_mcp_server',
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
          error: function (r) {
            frappe.show_alert(
              {
                message: __('Failed to stop MCP server'),
                indicator: 'red',
              },
              5,
            )
            console.error('Error stopping MCP server:', r)
          },
        })
      },
      function () {
        // No - do nothing
      },
    )
  }

  restart_mcp_server() {
    const me = this

    frappe.confirm(
      __('Are you sure you want to restart the MCP Server?'),
      function () {
        me.stop_mcp_server()
        setTimeout(() => {
          me.start_mcp_server()
        }, 2000)
      },
    )
  }

  show_server_logs() {
    const me = this

    // Create a dialog to show server logs
    const dialog = new frappe.ui.Dialog({
      title: __('MCP Server Logs'),
      size: 'extra-large',
      fields: [
        {
          fieldtype: 'Code',
          fieldname: 'logs',
          label: __('Logs'),
          options: 'Text',
          default: __('Loading logs...'),
          read_only: 1,
        },
      ],
      primary_action_label: __('Refresh'),
      primary_action: function () {
        me.refresh_logs(dialog)
      },
    })

    dialog.show()

    // Load initial logs
    this.refresh_logs(dialog)
  }

  refresh_logs(dialog) {
    frappe.call({
      method: 'erpnext_mcp_server.api.mcp_server.get_mcp_server_logs',
      callback: function (r) {
        if (r.message) {
          dialog.set_value('logs', r.message)
        } else {
          dialog.set_value('logs', __('No logs available'))
        }
      },
      error: function (r) {
        console.error('Error loading logs:', r)
        dialog.set_value('logs', __('Error loading logs'))
      },
    })
  }

  // Cleanup when dashboard is destroyed
  destroy() {
    // Clear intervals
    if (this.status_interval) {
      clearInterval(this.status_interval)
      this.status_interval = null
    }

    // Disconnect observers
    if (this.theme_observer) {
      this.theme_observer.disconnect()
      this.theme_observer = null
    }

    // Remove styles
    $('#mcp-dashboard-theme-styles').remove()
  }
}
