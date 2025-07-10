#!/bin/bash
# Setup script for Enhanced ERPNext MCP CLI Client

echo "🚀 Setting up Enhanced ERPNext MCP CLI Client..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements_cli.txt

# Make the client executable
echo "🔧 Making client executable..."
chmod +x enhanced_cli_client.py

# Create symlink for easy access (optional)
if [ -w "/usr/local/bin" ]; then
    echo "🔗 Creating symlink in /usr/local/bin..."
    ln -sf "$(pwd)/enhanced_cli_client.py" /usr/local/bin/erpnext-mcp
    echo "✅ You can now run 'erpnext-mcp' from anywhere!"
else
    echo "ℹ️  To use globally, add this to your ~/.bashrc or ~/.zshrc:"
    echo "alias erpnext-mcp='$(pwd)/enhanced_cli_client.py'"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Usage examples:"
echo "  python enhanced_cli_client.py                    # Interactive mode"
echo "  python enhanced_cli_client.py --quick 'sales'    # Quick report"
echo "  python enhanced_cli_client.py --help             # Show all options"
echo ""