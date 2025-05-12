# Standardized MCP Development on Frappe/ERPNext

## ERPNext MCP Server

ERPNext management, file operations, read-only database access, and ERPNext API integration

## The Development to Production Workflow

This guide establishes a standardized approach for developing Model Context Protocol (MCP) servers on Frappe/ERPNext, inspired by the Doppio SPA development workflow.

### Development Mode (Port 8080)

- Live development environment with hot reloading
- Direct debugging and testing
- Clear separation from production

### Production Mode (Port 8100)

- Integrated with NGINX and supervisor
- Secure and scalable
- Follows Frappe's established patterns

## Setting Up the Development Environment

### 1. Install the Framework

Add the MCP development framework to your app's `hooks.py`:

```python
# In your app's hooks.py
commands = [
    "your_app.mcp_dev.commands"
]
```

### 2. Initialize the Development Environment

```bash
# Initialize development environment
bench --site your-site.com mcp-config --app your_app_name

# Configure development port (default: 8080)
bench --site your-site.com mcp-config --dev-port 8080

# Configure production port (default: 8100)
bench --site your-site.com mcp-config --prod-port 8100
```

### 3. Start Development Server

```bash
# Start development server
bench --site your-site.com mcp-dev
```

This will:

- Start your MCP server on port 8080
- Watch for file changes and auto-reload
- Stream logs to the console

## Development to Production Workflow

### 1. Develop on Port 8080

During development:

- Your MCP server runs on port 8080
- Changes to Python files trigger auto-reload
- You can debug and test in real-time

### 2. Build for Production

When ready to deploy:

```bash
# Build for production
bench --site your-site.com mcp-build
```

This will:

- Configure NGINX to serve your MCP server on port 8100 under `/mcp/`
- Set up supervisor to keep your MCP server running
- Prepare all necessary configuration files

### 3. Deploy to Production

```bash
# Deploy to production
bench --site your-site.com mcp-deploy --reload-nginx --restart-supervisor
```

This will:

- Apply the NGINX configuration
- Start the MCP server under supervisor
- Make it available at `https://your-site.com/mcp/`

## Configuration Management

The framework provides a configuration system to manage your MCP development environment:

```bash
# View current configuration
bench --site your-site.com mcp-config

# Update entry point
bench --site your-site.com mcp-config --entry-point "your_app.mcp_server:server"

# Add watched paths
bench --site your-site.com mcp-config --add-watch "apps/your_app/your_app/mcp/*.py"

# Set environment variables
bench --site your-site.com mcp-config --set-env "DEBUG" "true"
```

## Benefits of the Standardized Approach

1. **Development-Production Parity**:

   - Same code runs in both environments
   - No surprises when deploying

2. **Developer Experience**:

   - Hot reloading during development
   - Clear separation of concerns
   - Unified configuration management

3. **Production Robustness**:

   - Proper integration with NGINX
   - Supervisor manages process lifecycle
   - Standard Frappe deployment patterns

4. **Team Collaboration**:
   - Consistent development approach
   - Standard commands and workflows
   - Easy onboarding for new developers

## Best Practices

### 1. Structuring Your MCP Server

Organize your MCP server code with a clean separation of concerns:

```bash
your_app/
├── your_app/
│   ├── mcp_server.py       # Main server entry point
│   ├── mcp/
│   │   ├── __init__.py     # Package initialization
│   │   ├── tools/          # MCP tools implementation
│   │   ├── resources/      # MCP resources implementation
│   │   └── prompts/        # MCP prompts implementation
│   └── mcp_dev.py          # Development framework
```

### 2. Version Control

- Include the development configuration in version control
- Exclude environment-specific settings
- Document required environment variables

### 3. Testing

- Create specific tests for MCP functionality
- Use both unit tests and integration tests
- Test in both development and production modes

### 4. Documentation

- Document your MCP server's capabilities
- Create examples of using your tools and resources
- Include setup instructions for both development and production

## Advanced Topics

### 1. Multiple MCP Servers

For larger applications, you might need multiple MCP servers:

```bash
# Configure multiple entry points
bench --site your-site.com mcp-config --entry-point "your_app.mcp_server_1:server"
bench --site your-site.com mcp-config --dev-port 8081

# Start specific server
bench --site your-site.com mcp-dev --port 8081
```

### 2. Security Considerations

- Use proper authentication in production
- Consider rate limiting for public-facing servers
- Implement proper error handling and logging

### 3. Performance Optimization

- Profile your MCP tools for performance bottlenecks
- Consider caching frequently accessed data
- Use asynchronous operations for I/O-bound tasks

By following this standardized approach, you can develop MCP servers for Frappe/ERPNext that are robust, maintainable, and follow established patterns familiar to Frappe developers.

#### License

mit
