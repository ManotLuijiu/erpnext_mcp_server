# Setting Up MCP Server with Your Frappe Installation

This guide provides step-by-step instructions for setting up the MCP server for ERPNext to work with your specific Frappe configuration.

## Prerequisites

- Frappe/ERPNext installed and running
- Supervisor installed
- NGINX installed and configured
- Python 3.10 or higher

## Installation Steps

### 1. Install ERPNext MCP Server

```bash
# Go to your bench directory
cd frappe-bench

# Get the app
bench get-app https://github.com/ManotLuijiu/erpnext_mcp_server

# Install the app on your site
bench --site your-site.com install-app erpnext_mcp_server
```

### 2. Configure NGINX

```bash
# Setup NGINX configuration for MCP server (default port: 8100)
bench --site your-site.com setup-mcp-nginx

# Or specify a custom port
bench --site your-site.com setup-mcp-nginx --port 8100

# Test NGINX configuration
sudo nginx -t

# If test passes, reload NGINX
sudo service nginx reload
```

### 3. Configure Supervisor

```bash
# Setup supervisor configuration for MCP server
bench --site your-site.com setup-mcp-supervisor

# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Start the MCP server
sudo supervisorctl start mcp-your-site.com
```

### 4. Configure Translation Tools

```bash
# Go to Desk > Translation Tools Settings
# Enable MCP integration
# Set MCP URL to: https://your-site.com/mcp/
# Save and test connection
```

## Testing

You can test if the MCP server is working by:

1. Open your browser and navigate to `https://your-site.com/mcp/`

   - You should see a "Bad Request" error (which is normal, as we're not sending a valid MCP request)

2. Test from Translation Tools:
   - Go to your chatbot interface
   - Try a data query like "Show me Sales Invoice information"

## Troubleshooting

### Checking Logs

```bash
# Check MCP server logs
tail -f frappe-bench/logs/mcp-your-site.com.log

# Check MCP server error logs
tail -f frappe-bench/logs/mcp-your-site.com.error.log

# Check NGINX access logs
tail -f /var/log/nginx/access.log

# Check NGINX error logs
tail -f /var/log/nginx/error.log
```

### Common Issues

1. **Port Already in Use**

   ```bash
   # Check which process is using the port
   sudo netstat -tlpn | grep 8100

   # Choose a different port
   bench --site your-site.com setup-mcp-nginx --port 8101
   bench --site your-site.com setup-mcp-supervisor --port 8101
   ```

2. **Permission Issues**

   ```bash
   # Make sure logs directory is writable
   sudo chown -R frappe:frappe frappe-bench/logs
   ```

3. **Supervisor Not Starting**

   ```bash
   # Check supervisor status
   sudo supervisorctl status

   # Check if ENV_BENCH_CMD is set in supervisor environment
   sudo supervisorctl status
   ```

## Maintenance

### Updating the Configuration

If you need to change the port or other settings:

```bash
# Update NGINX configuration
bench --site your-site.com setup-mcp-nginx --port 8101

# Update supervisor configuration
bench --site your-site.com setup-mcp-supervisor --port 8101

# Reload NGINX
sudo service nginx reload

# Restart supervisor
sudo supervisorctl restart mcp-your-site.com
```

### Starting/Stopping the Server

```bash
# Start the MCP server
sudo supervisorctl start mcp-your-site.com

# Stop the MCP server
sudo supervisorctl stop mcp-your-site.com

# Restart the MCP server
sudo supervisorctl restart mcp-your-site.com
```

## How It Works

The setup process:

1. Directly modifies your `nginx.conf` to add the MCP server location block
2. Adds a new program section to your `supervisor.conf` for the MCP server
3. Stores configuration in `common_site_config.json` for persistence
4. Creates log files in your `frappe-bench/logs` directory

This approach follows your specific Frappe configuration structure and ensures the MCP server is properly integrated with your production environment.
