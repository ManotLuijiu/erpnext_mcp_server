# ERPNext MCP Server

**Framework-level MCP Server** for Frappe/ERPNext — works like Doppio CLI, not site-specific.

> Built by AWS Solution Ltd. | Contact: moocoding@gmail.com

## Overview

Unlike typical Frappe apps that install per-site, this MCP server runs at the **bench framework level**:

- One server instance serves all sites on the bench
- Site context switches dynamically via tool calls
- No installation to each site needed

```
┌─────────────────────────────────────────────────────┐
│  MCP Client (Claude, Hermes, etc.)                 │
│  (running on another machine)                        │
└────────────────────┬────────────────────────────────┘
                     │ stdio
┌────────────────────▼────────────────────────────────┐
│  ERPNext MCP Server                                 │
│  (this bench)                                       │
│                                                     │
│  • list_sites     → all bench sites               │
│  • switch_site    → change context                 │
│  • get_document   → query current site             │
│  • execute_sql    → safe SELECT queries            │
│  • bench_command  → read-only bench operations     │
│  • ... + 15 more tools                            │
└─────────────────────────────────────────────────────┘
```

## Prerequisites

- Frappe/ERPNext v15+ installed on a bench
- Python 3.10+ (uses bench's virtual environment)
- MCP client (Claude Code, Hermes Agent, etc.)

## Quick Start

### 1. Verify Python Environment

```bash
cd ~/frappe-bench
./env/bin/python --version  # Should be Python 3.10+
```

### 2. Test Locally

```bash
# Set your default site
export FRAPPE_SITE=your-site.domain.com
export BENCH_PATH=/path/to/your/frappe-bench

# Run the server
./env/bin/python -m erpnext_mcp_server.mcp.server
```

### 3. Configure MCP Client

#### For Claude Code

Add to `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "erpnext": {
      "command": "python",
      "args": ["-m", "erpnext_mcp_server.mcp.server"],
      "env": {
        "FRAPPE_SITE": "your-site.domain.com",
        "BENCH_PATH": "/home/youruser/frappe-bench"
      }
    }
  }
}
```

#### For Hermes Agent

In your Hermes configuration:

```yaml
mcp_servers:
  erpnext:
    command: ssh
    args:
      - user@your-server
      - 'cd /path/to/bench && FRAPPE_SITE=your-site.com ./env/bin/python -m erpnext_mcp_server.mcp.server'
```

#### For Other MCP Clients

The server uses **STDIO transport** (stdin/stdout). Any MCP client that supports stdio will work:

```json
{
  "mcpServers": {
    "erpnext": {
      "command": "/path/to/frappe-bench/env/bin/python",
      "args": ["-m", "erpnext_mcp_server.mcp.server"],
      "env": {
        "FRAPPE_SITE": "your-site.domain.com",
        "BENCH_PATH": "/path/to/frappe-bench"
      }
    }
  }
}
```

## Available Tools

### Site Management

| Tool           | Arguments | Description                  |
| -------------- | --------- | ---------------------------- |
| `list_sites`   | —         | List all sites on this bench |
| `switch_site`  | `site`    | Switch to a different site   |
| `current_site` | —         | Get current site name        |

### Document CRUD

| Tool              | Arguments                       | Description                 |
| ----------------- | ------------------------------- | --------------------------- |
| `get_document`    | `doctype`, `name`               | Get document by ID          |
| `list_documents`  | `doctype`, `filters?`, `limit?` | List documents with filters |
| `create_document` | `doctype`, `data`               | Create new document         |
| `update_document` | `doctype`, `name`, `data`       | Update existing document    |
| `delete_document` | `doctype`, `name`               | Delete/cancel document      |
| `count_documents` | `doctype`, `filters?`           | Count matching documents    |

### Metadata

| Tool               | Arguments | Description           |
| ------------------ | --------- | --------------------- |
| `list_doctypes`    | `module?` | List all DocTypes     |
| `get_doctype_meta` | `doctype` | Get field definitions |

### Database

| Tool             | Arguments         | Description                 |
| ---------------- | ----------------- | --------------------------- |
| `execute_sql`    | `query`, `limit?` | Execute SELECT query (safe) |
| `get_table_info` | `table`           | Get table structure         |

### System Info

| Tool              | Arguments | Description                  |
| ----------------- | --------- | ---------------------------- |
| `get_system_info` | —         | System and DB info           |
| `get_versions`    | —         | Installed app versions       |
| `bench_command`   | `command` | Run read-only bench commands |

### Workflow

| Tool              | Arguments         | Description            |
| ----------------- | ----------------- | ---------------------- |
| `submit_document` | `doctype`, `name` | Submit (docstatus 0→1) |
| `cancel_document` | `doctype`, `name` | Cancel submitted doc   |

### Search

| Tool     | Arguments                     | Description            |
| -------- | ----------------------------- | ---------------------- |
| `search` | `query`, `doctype?`, `limit?` | Search across DocTypes |

### Files

| Tool         | Arguments            | Description                 |
| ------------ | -------------------- | --------------------------- |
| `read_file`  | `path`, `lines?`     | Read file (safe paths only) |
| `list_files` | `path`, `recursive?` | List directory              |

## Usage Examples

### Python Client Test

```python
import subprocess
import json

proc = subprocess.Popen(
    ["./env/bin/python", "-m", "erpnext_mcp_server.mcp.server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    cwd="/path/to/frappe-bench",
    env={"FRAPPE_SITE": "your-site.domain.com"}
)

# Initialize
init_msg = {
    "jsonrpc": "2.0", "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "1.0"}
    }
}
proc.stdin.write((json.dumps(init_msg) + "\n").encode())
proc.stdin.flush()

# List sites
list_msg = {
    "jsonrpc": "2.0", "id": 2,
    "method": "tools/call",
    "params": {"name": "list_sites", "arguments": {}}
}
proc.stdin.write((json.dumps(list_msg) + "\n").encode())
proc.stdin.flush()

proc.stdin.close()
print(proc.stdout.read().decode())
```

### Claude Code Usage

Once configured, simply ask Claude:

```
> List all customers in ERPNext
> Create a new Sales Order for customer ABC
> What is the total outstanding for Invoice INV-001?
```

Claude will use the MCP tools to query ERPNext directly.

## Architecture

```
erpnext_mcp_server/
├── __init__.py
├── hooks.py
├── mcp/
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── server.py            # Main MCP server
│   └── config.py            # Configuration
└── doctype/                 # Settings DocTypes (optional)
```

### Design Principles

1. **Framework Level** — Runs at bench level, not per-site
2. **Lazy Loading** — Frappe imported only when needed
3. **Site Context** — Switches context dynamically per tool call
4. **Security First** — SQL limited to SELECT, files restricted to safe paths

## Security

| Restriction    | Details                                          |
| -------------- | ------------------------------------------------ |
| SQL            | Only SELECT queries allowed                      |
| Files          | Only `sites/`, `apps/`, `logs/`, `config/` paths |
| Bench commands | Read-only operations only                        |
| Site access    | Enforced via Frappe permissions                  |

## Environment Variables

| Variable                | Required | Default                     | Description          |
| ----------------------- | -------- | --------------------------- | -------------------- |
| `FRAPPE_SITE`           | Yes      | —                           | Default site name    |
| `BENCH_PATH`            | No       | `/home/frappe/frappe-bench` | Bench directory      |
| `FRAPPE_STREAM_LOGGING` | No       | `1`                         | Disable file logging |

## Troubleshooting

### "site does not exist" error

```bash
# Verify site exists
ls ~/frappe-bench/sites/  | grep your-site

# Check site config
cat ~/frappe-bench/sites/your-site.domain.com/site_config.json
```

### Connection refused

The server uses **stdio transport**, not HTTP. Ensure your MCP client is connecting via stdin/stdout pipes.

### Permission denied

Ensure the user running the server has:

- Read access to bench directory
- Database access for the site
- Permission to execute bench commands

## License

Proprietary - AWS Solution Ltd.

## Support

- Email: moocoding@gmail.com
- Issues: Open an issue in the repository

---

**Built with Frappe Framework** | **MCP Protocol** | **STDIO Transport**
