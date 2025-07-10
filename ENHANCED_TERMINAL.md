# Enhanced ERPNext MCP Terminal Client

A fast, interactive command-line interface for ERPNext reporting using the Model Context Protocol (MCP).

## 🚀 Features

### Quick Reports

Pre-built reports accessible with simple commands:

- `sales` - Today's sales summary
- `customers` - Recent customers list  
- `items` - Top selling items (last 30 days)
- `orders` - Pending sales orders
- `invoices` - Unpaid invoices
- `stock` - Low stock items
- `users` - Active users
- `errors` - Recent error logs

### Natural Language Queries

Ask questions in plain English:

- "show me today's sales"
- "list recent customers"
- "check low stock items" 
- "unpaid invoices"

### Intelligent Features

- **Command History**: Use UP/DOWN arrows to navigate previous commands
- **Tab Completion**: Press TAB to auto-complete commands
- **Favorites**: Save frequently used queries
- **Smart Caching**: Results cached for 5 minutes for faster responses
- **Rich Display**: Tables and formatted output using Rich library

## 📦 Installation

### 1. Install Dependencies

```bash
cd /path/to/frappe-bench/apps/erpnext_mcp_server
pip install -r requirements_cli.txt
```

### 2. Setup (Optional)

```bash
chmod +x setup_cli.sh
./setup_cli.sh
```

## 🎯 Usage

### Interactive Mode

```bash
# Direct execution
python enhanced_cli_client.py

# Via bench command (after setup)
bench --site moo.localhost mcp-terminal

# With custom settings
python enhanced_cli_client.py --site mysite.localhost --port 8100
```

### Quick Mode (Single Query)

```bash
# Quick report
python enhanced_cli_client.py --quick "sales"

# Natural language
python enhanced_cli_client.py --quick "show me today's sales"

# Direct SQL (if allowed)
python enhanced_cli_client.py --quick "SELECT COUNT(*) FROM tabCustomer"
```

### Bench Integration

After proper setup, you can use:

```bash
bench --site sitename mcp-terminal
bench --site sitename mcp-terminal --quick "sales"
```

## 🎮 Commands

### Built-in Commands

- `help` - Show help information
- `exit` - Exit the terminal
- `clear` - Clear screen
- `favorites` - Manage favorite queries
- `cache` - Cache management

### Quick Reports

- `sales` - Sales summary for today
- `customers` - Recent 10 customers
- `items` - Top 10 selling items (30 days)
- `orders` - Pending sales orders (15 max)
- `invoices` - Unpaid invoices (15 max)
- `stock` - Items below reorder level (20 max)
- `users` - Active system users (15 max)

### Favorites Management

```bash
# List favorites
favorites list

# Add a favorite
favorites add daily-sales "SELECT COUNT(*) as orders, SUM(grand_total) as revenue FROM `tabSales Order` WHERE DATE(creation) = CURDATE()"

# Run a favorite
favorites run daily-sales

# Remove a favorite
favorites remove daily-sales
```

### Cache Management

```bash
# Check cache status
cache status

# Clear cache
cache clear
```

## 🔧 Configuration

### Environment Variables

- `FRAPPE_SITE_NAME` - Default site name
- `MCP_SERVER_HOST` - MCP server host (default: localhost)
- `MCP_SERVER_PORT` - MCP server port (default: 8100)

### File Locations

- History: `~/.erpnext_mcp_history`
- Favorites: `~/.erpnext_mcp_favorites.json`
- Cache: `~/.erpnext_mcp_cache.json`

## 📊 Example Queries

### Natural Language Examples

```bash
"today's sales"
"recent customers"
"low stock items"
"unpaid invoices"
"pending orders"
"top selling items"
"active users"
```

### Direct SQL Examples (Advanced)

```sql
SELECT customer_name, territory, creation 
FROM `tabCustomer` 
WHERE creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)

SELECT item_code, actual_qty, reorder_level
FROM `tabBin` 
WHERE actual_qty < reorder_level
LIMIT 10
```

## 🛡️ Security

- Only READ operations allowed (SELECT, SHOW, DESCRIBE)
- SQL injection protection with pattern matching
- Blocked dangerous keywords (INSERT, UPDATE, DELETE, etc.)
- Respects ERPNext permissions via MCP server
- Cached results automatically expire

## 🚨 Troubleshooting

### Common Issues

1. **"Connection error"**
   - Ensure MCP server is running on specified port
   - Check host/port settings
   - Verify ERPNext site is accessible

2. **"Permission denied"**
   - Check user permissions in ERPNext
   - Ensure MCP server permissions are configured

3. **"Command not found"**
   - Use `help` to see available commands
   - Check spelling and try tab completion

4. **Slow responses**
   - Results are cached for 5 minutes
   - First query might be slower
   - Use `cache clear` to refresh

### Debug Mode

Run with Python's verbose mode for debugging:

```bash
python -v enhanced_cli_client.py
```

## 🔄 Integration with Existing Tools

### With MCP Server

The terminal connects to your existing ERPNext MCP server and uses the same tools:

- `DatabaseTools` for SQL queries
- `DocumentTools` for DocType operations  
- `SystemTools` for system information

### With Frappe Bench

Integrates seamlessly with bench commands:

```bash
bench --site sitename mcp-terminal
```

## 🎨 Customization

### Adding Custom Reports

Modify the `quick_reports` dictionary in `enhanced_cli_client.py`:

```python
self.quick_reports = {
    "sales": "Get today's sales summary",
    "custom_report": "Your custom report description",
    # ... add more
}
```

### Adding Natural Language Patterns

Add patterns to the `nl_patterns` dictionary:

```python
self.nl_patterns = {
    r"your_pattern": "your_report_type",
    # ... add more
}
```

## 📈 Performance

- **Caching**: Results cached for 5 minutes
- **Connection Pooling**: HTTP connections reused
- **Async Operations**: Non-blocking operations
- **Rich Output**: Efficient terminal rendering

## 🤝 Contributing

To extend the terminal client:

1. Add new report types in `_execute_quick_report()`
2. Add natural language patterns in `nl_patterns`
3. Enhance the display logic in `_display_result()`
4. Add new commands in `_process_input()`

## 📄 License

MIT License - Same as ERPNext MCP Server