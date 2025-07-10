#!/usr/bin/env python3
"""
Enhanced ERPNext MCP Terminal Client
Fast command-line interface for ERPNext reporting with natural language queries

Usage:
    python enhanced_cli_client.py
    python enhanced_cli_client.py --site moo.localhost --port 8100
    python enhanced_cli_client.py --quick "show me today's sales"
"""

import argparse
import asyncio
import json
import os
import readline
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich import print as rprint


class ERPNextMCPTerminal:
    """Enhanced terminal client for ERPNext MCP server with fast reporting"""
    
    def __init__(self, base_url: str = "http://localhost:8100/mcp", site: str = "moo.localhost"):
        self.base_url = base_url
        self.site = site
        self.console = Console()
        self.session_id = f"terminal_{datetime.now().timestamp()}"
        self.history_file = Path.home() / ".erpnext_mcp_history"
        self.favorites_file = Path.home() / ".erpnext_mcp_favorites.json"
        self.cache_file = Path.home() / ".erpnext_mcp_cache.json"
        
        # Load cached data
        self.favorites = self._load_favorites()
        self.cache = self._load_cache()
        
        # Initialize readline for command history
        self._setup_readline()
        
        # Quick report templates
        self.quick_reports = {
            "sales": "Get today's sales summary",
            "customers": "List recent customers", 
            "items": "Show top selling items",
            "orders": "Display pending sales orders",
            "invoices": "Show unpaid invoices",
            "stock": "Check low stock items",
            "users": "List active users",
            "errors": "Show recent error logs"
        }
        
        # Natural language patterns
        self.nl_patterns = {
            r"(sales|revenue|income).*today": "sales_today",
            r"(customer|client).*list": "customer_list", 
            r"(stock|inventory).*low": "low_stock",
            r"(invoice|bill).*unpaid": "unpaid_invoices",
            r"(order|so).*pending": "pending_orders",
            r"(item|product).*top": "top_items",
            r"(user|employee).*active": "active_users",
            r"(error|log).*recent": "recent_errors"
        }

    def _setup_readline(self):
        """Setup readline for command history and completion"""
        try:
            if self.history_file.exists():
                readline.read_history_file(str(self.history_file))
            readline.set_history_length(1000)
            
            # Setup tab completion
            readline.set_completer(self._completer)
            readline.parse_and_bind("tab: complete")
        except Exception:
            pass  # Gracefully handle if readline is not available

    def _completer(self, text: str, state: int) -> Optional[str]:
        """Tab completion for commands"""
        options = list(self.quick_reports.keys()) + ["help", "exit", "clear", "favorites", "cache"]
        matches = [opt for opt in options if opt.startswith(text)]
        return matches[state] if state < len(matches) else None

    def _load_favorites(self) -> Dict[str, str]:
        """Load favorite queries from file"""
        try:
            if self.favorites_file.exists():
                with open(self.favorites_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_favorites(self):
        """Save favorites to file"""
        try:
            with open(self.favorites_file, 'w') as f:
                json.dump(self.favorites, f, indent=2)
        except Exception as e:
            self.console.print(f"[red]Error saving favorites: {e}[/red]")

    def _load_cache(self) -> Dict[str, Any]:
        """Load cached results"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    # Remove expired cache entries (older than 1 hour)
                    current_time = datetime.now().timestamp()
                    return {k: v for k, v in cache.items() 
                           if current_time - v.get('timestamp', 0) < 3600}
        except Exception:
            pass
        return {}

    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            self.console.print(f"[red]Error saving cache: {e}[/red]")

    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call MCP tool with error handling and caching"""
        cache_key = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
        
        # Check cache first
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now().timestamp() - cached['timestamp'] < 300:  # 5 minutes
                return cached['result']

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": self.session_id,
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": arguments
                        }
                    },
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result:
                        # Cache successful results
                        self.cache[cache_key] = {
                            'result': result,
                            'timestamp': datetime.now().timestamp()
                        }
                        self._save_cache()
                        return result
                    else:
                        return {"error": result.get("error", "Unknown error")}
                else:
                    return {"error": f"HTTP {response.status_code}: {response.text}"}
                    
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    async def _execute_quick_report(self, report_type: str) -> None:
        """Execute predefined quick reports"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(f"Generating {report_type} report...", total=None)
            
            if report_type == "sales_today":
                result = await self._call_mcp_tool("execute_sql_query", {
                    "query": """
                        SELECT 
                            COUNT(*) as invoice_count,
                            COALESCE(SUM(grand_total), 0) as total_sales,
                            COALESCE(AVG(grand_total), 0) as avg_invoice_value
                        FROM `tabSales Invoice` 
                        WHERE DATE(creation) = CURDATE() 
                        AND docstatus = 1
                    """
                })
                
            elif report_type == "customer_list":
                result = await self._call_mcp_tool("execute_sql_query", {
                    "query": """
                        SELECT customer_name, territory, customer_type, creation
                        FROM `tabCustomer` 
                        ORDER BY creation DESC 
                        LIMIT 10
                    """
                })
                
            elif report_type == "low_stock":
                result = await self._call_mcp_tool("execute_sql_query", {
                    "query": """
                        SELECT item_code, item_name, actual_qty, reorder_level
                        FROM `tabBin` b
                        JOIN `tabItem` i ON b.item_code = i.name
                        WHERE b.actual_qty <= i.reorder_level
                        AND i.disabled = 0
                        ORDER BY (actual_qty - reorder_level) ASC
                        LIMIT 20
                    """
                })
                
            elif report_type == "unpaid_invoices":
                result = await self._call_mcp_tool("execute_sql_query", {
                    "query": """
                        SELECT name, customer, grand_total, due_date, 
                               DATEDIFF(CURDATE(), due_date) as days_overdue
                        FROM `tabSales Invoice`
                        WHERE status != 'Paid' AND docstatus = 1
                        ORDER BY due_date ASC
                        LIMIT 15
                    """
                })
                
            elif report_type == "pending_orders":
                result = await self._call_mcp_tool("execute_sql_query", {
                    "query": """
                        SELECT name, customer, grand_total, delivery_date, status
                        FROM `tabSales Order`
                        WHERE status IN ('Draft', 'To Deliver and Bill', 'To Bill', 'To Deliver')
                        ORDER BY delivery_date ASC
                        LIMIT 15
                    """
                })
                
            elif report_type == "top_items":
                result = await self._call_mcp_tool("execute_sql_query", {
                    "query": """
                        SELECT i.item_code, i.item_name, 
                               SUM(sii.qty) as total_qty_sold,
                               SUM(sii.amount) as total_revenue
                        FROM `tabSales Invoice Item` sii
                        JOIN `tabSales Invoice` si ON sii.parent = si.name
                        JOIN `tabItem` i ON sii.item_code = i.name
                        WHERE si.docstatus = 1 
                        AND si.posting_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                        GROUP BY sii.item_code
                        ORDER BY total_revenue DESC
                        LIMIT 10
                    """
                })
                
            elif report_type == "active_users":
                result = await self._call_mcp_tool("execute_sql_query", {
                    "query": """
                        SELECT full_name, email, last_login, enabled
                        FROM `tabUser`
                        WHERE enabled = 1 AND user_type = 'System User'
                        ORDER BY last_login DESC
                        LIMIT 15
                    """
                })
                
            else:
                result = {"error": f"Unknown report type: {report_type}"}

        self._display_result(result, report_type)

    def _display_result(self, result: Dict[str, Any], context: str = "") -> None:
        """Display results in a formatted table or panel"""
        if "error" in result:
            self.console.print(f"[red]Error: {result['error']}[/red]")
            return

        try:
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"]
                
                if isinstance(content, list) and len(content) > 0:
                    if isinstance(content[0], dict):
                        # Display as table
                        table = Table(title=f"📊 {context.replace('_', ' ').title()}")
                        
                        # Add columns
                        for key in content[0].keys():
                            table.add_column(key.replace('_', ' ').title(), style="cyan")
                        
                        # Add rows
                        for row in content:
                            table.add_row(*[str(v) for v in row.values()])
                        
                        self.console.print(table)
                    else:
                        # Display as simple list
                        for item in content:
                            self.console.print(f"• {item}")
                else:
                    # Display as text
                    self.console.print(Panel(str(content), title=context.replace('_', ' ').title()))
            else:
                self.console.print(Panel(str(result), title="Result"))
                
        except Exception as e:
            self.console.print(f"[red]Error displaying result: {e}[/red]")

    def _show_help(self) -> None:
        """Show help information"""
        help_text = """
[bold cyan]ERPNext MCP Terminal - Quick Commands[/bold cyan]

[bold yellow]Quick Reports:[/bold yellow]
• sales       - Today's sales summary
• customers   - Recent customers list  
• items       - Top selling items
• orders      - Pending sales orders
• invoices    - Unpaid invoices
• stock       - Low stock items
• users       - Active users
• errors      - Recent error logs

[bold yellow]Commands:[/bold yellow]
• help        - Show this help
• favorites   - Manage favorite queries
• cache       - Cache management
• clear       - Clear screen
• exit        - Exit terminal

[bold yellow]Natural Language:[/bold yellow]
You can also type natural language queries like:
• "show me today's sales"
• "list recent customers"  
• "check low stock items"
• "unpaid invoices"

[bold yellow]Advanced:[/bold yellow]
• Use TAB for command completion
• Use UP/DOWN arrows for history
• Add queries to favorites with: fav add <name> <query>
        """
        self.console.print(Panel(help_text, title="Help"))

    def _manage_favorites(self, args: List[str]) -> None:
        """Manage favorite queries"""
        if not args or args[0] == "list":
            if self.favorites:
                table = Table(title="📌 Favorite Queries")
                table.add_column("Name", style="cyan")
                table.add_column("Query", style="green")
                
                for name, query in self.favorites.items():
                    table.add_row(name, query[:60] + "..." if len(query) > 60 else query)
                
                self.console.print(table)
            else:
                self.console.print("[yellow]No favorites saved[/yellow]")
                
        elif args[0] == "add" and len(args) >= 3:
            name = args[1]
            query = " ".join(args[2:])
            self.favorites[name] = query
            self._save_favorites()
            self.console.print(f"[green]Added favorite: {name}[/green]")
            
        elif args[0] == "remove" and len(args) >= 2:
            name = args[1]
            if name in self.favorites:
                del self.favorites[name]
                self._save_favorites()
                self.console.print(f"[green]Removed favorite: {name}[/green]")
            else:
                self.console.print(f"[red]Favorite not found: {name}[/red]")
                
        elif args[0] == "run" and len(args) >= 2:
            name = args[1]
            if name in self.favorites:
                self.console.print(f"[cyan]Running favorite: {name}[/cyan]")
                asyncio.create_task(self._process_input(self.favorites[name]))
            else:
                self.console.print(f"[red]Favorite not found: {name}[/red]")
        else:
            self.console.print("[yellow]Usage: favorites [list|add <name> <query>|remove <name>|run <name>][/yellow]")

    def _manage_cache(self, args: List[str]) -> None:
        """Manage cache"""
        if not args or args[0] == "status":
            self.console.print(f"[cyan]Cache entries: {len(self.cache)}[/cyan]")
            self.console.print(f"[cyan]Cache file: {self.cache_file}[/cyan]")
        elif args[0] == "clear":
            self.cache.clear()
            self._save_cache()
            self.console.print("[green]Cache cleared[/green]")
        else:
            self.console.print("[yellow]Usage: cache [status|clear][/yellow]")

    async def _process_input(self, user_input: str) -> None:
        """Process user input and route to appropriate handler"""
        user_input = user_input.strip()
        
        if not user_input:
            return
            
        # Save to history
        try:
            readline.add_history(user_input)
            readline.write_history_file(str(self.history_file))
        except Exception:
            pass

        parts = user_input.split()
        command = parts[0].lower()
        args = parts[1:]

        # Handle built-in commands
        if command == "help":
            self._show_help()
        elif command == "exit":
            return False
        elif command == "clear":
            os.system('clear' if os.name == 'posix' else 'cls')
        elif command == "favorites" or command == "fav":
            self._manage_favorites(args)
        elif command == "cache":
            self._manage_cache(args)
        elif command in self.quick_reports:
            await self._execute_quick_report(command)
        elif command in self.favorites:
            await self._process_input(self.favorites[command])
        else:
            # Try natural language processing
            import re
            matched = False
            for pattern, report_type in self.nl_patterns.items():
                if re.search(pattern, user_input.lower()):
                    await self._execute_quick_report(report_type)
                    matched = True
                    break
            
            if not matched:
                # Try as direct SQL query (if it looks like one)
                if any(keyword in user_input.upper() for keyword in ["SELECT", "SHOW", "DESCRIBE"]):
                    result = await self._call_mcp_tool("execute_sql_query", {"query": user_input})
                    self._display_result(result, "Custom Query")
                else:
                    self.console.print(f"[red]Unknown command: {command}[/red]")
                    self.console.print("[yellow]Type 'help' for available commands[/yellow]")
        
        return True

    async def run_interactive(self) -> None:
        """Run interactive terminal session"""
        self.console.print(Panel(
            "[bold cyan]ERPNext MCP Terminal[/bold cyan]\n"
            f"Connected to: {self.base_url}\n"
            f"Site: {self.site}\n\n"
            "Type 'help' for commands or use natural language queries",
            title="🚀 Welcome"
        ))

        try:
            while True:
                try:
                    user_input = Prompt.ask("\n[bold green]erpnext>[/bold green]", console=self.console)
                    
                    if user_input.lower() in ['exit', 'quit', 'bye']:
                        break
                        
                    result = await self._process_input(user_input)
                    if result is False:
                        break
                        
                except KeyboardInterrupt:
                    if Confirm.ask("\n[yellow]Exit ERPNext MCP Terminal?[/yellow]"):
                        break
                    continue
                except EOFError:
                    break
                    
        except Exception as e:
            self.console.print(f"[red]Fatal error: {e}[/red]")
        
        self.console.print("\n[cyan]Goodbye! 👋[/cyan]")

    async def run_quick(self, query: str) -> None:
        """Run a single query and exit"""
        self.console.print(f"[cyan]Running: {query}[/cyan]")
        await self._process_input(query)


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enhanced ERPNext MCP Terminal Client")
    parser.add_argument("--site", default="moo.localhost", help="ERPNext site name")
    parser.add_argument("--port", type=int, default=8100, help="MCP server port")
    parser.add_argument("--host", default="localhost", help="MCP server host")
    parser.add_argument("--quick", help="Run a single query and exit")
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}/mcp"
    terminal = ERPNextMCPTerminal(base_url, args.site)
    
    if args.quick:
        await terminal.run_quick(args.quick)
    else:
        await terminal.run_interactive()


if __name__ == "__main__":
    asyncio.run(main())