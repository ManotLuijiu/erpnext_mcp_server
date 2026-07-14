# DuckDB Analytics

DuckDB is added as a **read-only analytical layer** that queries MariaDB data for aggregations, KPIs, and analytical reports. It **does not replace MariaDB** — MariaDB remains the transactional source of truth.

## Why DuckDB?

| Use case                           | Database                 |
| ---------------------------------- | ------------------------ |
| Create/update documents            | MariaDB (via Frappe ORM) |
| Workflow operations                | MariaDB (via Frappe ORM) |
| Aggregations, KPIs, GL analysis    | DuckDB                   |
| Sales analysis, inventory analysis | DuckDB                   |

DuckDB runs in-memory with MariaDB attached as a **read-only** foreign table. This keeps the analytical workload off MariaDB and enables fast in-memory aggregation.

## Security Model

DuckDB is strictly read-only. Multiple layers enforce this:

1. **Dedicated MariaDB user** — `SELECT` privileges only (no INSERT, UPDATE, DELETE, etc.)
2. **DuckDB `READ_ONLY` flag** — MariaDB is attached with `READ_ONLY`
3. **Approved datasets only** — only registered tables are exposed
4. **Parameterized queries** — all values use `?` placeholders
5. **Allowlisted identifiers** — table/column/group-by names come from internal maps, never from raw user input
6. **No arbitrary SQL** — Phase 1 has no generic SQL MCP tool
7. **Row limits** — results are capped by configuration

## Installation

### 1. Create a dedicated MariaDB read-only user

Connect to MariaDB as an administrator and run:

```sql
CREATE USER 'erpnext_analytics'@'127.0.0.1'
IDENTIFIED BY 'replace-with-a-strong-password';

GRANT SELECT
ON `your_frappe_database`.*
TO 'erpnext_analytics'@'127.0.0.1';

FLUSH PRIVILEGES;
```

> **Important:** Do NOT grant INSERT, UPDATE, DELETE, CREATE, ALTER, or DROP.

The actual database name comes from your Frappe `site_config.json` (`db_name`).

### 2. Configure environment variables

```bash
# Enable DuckDB analytics
export MCP_ANALYTICS_ENABLED=true

# MariaDB connection
export MCP_ANALYTICS_DB_HOST=127.0.0.1
export MCP_ANALYTICS_DB_PORT=3306
export MCP_ANALYTICS_DB_NAME=your_frappe_database
export MCP_ANALYTICS_DB_USER=erpnext_analytics
export MCP_ANALYTICS_DB_PASSWORD=your_password

# Performance settings (optional)
export MCP_ANALYTICS_MAX_ROWS=500
export MCP_ANALYTICS_QUERY_TIMEOUT_SECONDS=30
export MCP_ANALYTICS_MEMORY_LIMIT=1GB
export MCP_ANALYTICS_THREADS=2
```

### 3. Restart the MCP server

DuckDB and the MySQL scanner extension will be loaded automatically.

## MCP Tools

### `analytics_status`

Returns DuckDB engine status, MariaDB attachment health, and configuration summary.

```json
{
  "enabled": true,
  "engine": "DuckDB",
  "source": "MariaDB",
  "attachment_mode": "read_only",
  "connected": true,
  "duckdb_version": "1.5.4",
  "database_alias": "frappe_db",
  "max_rows": 500
}
```

### `describe_analytics_schema`

Returns metadata for approved datasets. Without arguments, returns all datasets.

```python
# All datasets
describe_analytics_schema()

# One dataset
describe_analytics_schema(dataset="sales_invoice")
```

Returns fields, dimensions, metrics, and default conditions for each dataset.

### `analyze_sales`

Sales analysis from submitted invoices.

```python
analyze_sales(
    company="ACME Corp",
    from_date="2026-01-01",
    to_date="2026-06-30",
    group_by="month",         # customer | customer_group | territory | month | week | year
    metric="net_sales",       # net_sales | gross_sales | invoice_count | qty | avg_net_rate
    limit=100,
)
```

Example result:

```json
{
  "analysis": "sales",
  "company": "ACME Corp",
  "from_date": "2026-01-01",
  "to_date": "2026-06-30",
  "group_by": "month",
  "metric": "net_sales",
  "row_count": 6,
  "duration_ms": 24.5,
  "truncated": false,
  "data": [
    {
      "dimension": "2026-01-01T00:00:00",
      "metric_value": 1500000.0,
      "invoice_count": 120
    }
  ]
}
```

### `analyze_general_ledger`

GL analysis from submitted entries.

```python
analyze_general_ledger(
    company="ACME Corp",
    from_date="2026-01-01",
    to_date="2026-06-30",
    group_by="account",       # account | cost_center | voucher_type | month | week | year
    account="Sales - EC",     # optional filter
    cost_center="Main CC",    # optional filter
    limit=100,
)
```

Example result:

```json
{
  "analysis": "general_ledger",
  "company": "ACME Corp",
  "from_date": "2026-01-01",
  "to_date": "2026-06-30",
  "group_by": "account",
  "row_count": 50,
  "duration_ms": 31.2,
  "truncated": false,
  "data": [
    {
      "dimension": "Sales - EC",
      "total_debit": 0.0,
      "total_credit": 3500000.0,
      "net_balance": -3500000.0,
      "entry_count": 250
    }
  ]
}
```

> Note: `net_balance = total_debit - total_credit`. A negative balance indicates net credit; it is not labelled as profit or loss.

## Approved Datasets

| Dataset              | Physical Table          |
| -------------------- | ----------------------- |
| `sales_invoice`      | `tabSales Invoice`      |
| `sales_invoice_item` | `tabSales Invoice Item` |
| `general_ledger`     | `tabGL Entry`           |
| `company`            | `tabCompany`            |
| `customer`           | `tabCustomer`           |
| `item`               | `tabItem`               |
| `account`            | `tabAccount`            |
| `cost_center`        | `tabCost Center`        |

## Environment Variables Reference

| Variable                              | Default     | Description                     |
| ------------------------------------- | ----------- | ------------------------------- |
| `MCP_ANALYTICS_ENABLED`               | `false`     | Enable/disable DuckDB analytics |
| `MCP_ANALYTICS_DB_HOST`               | `127.0.0.1` | MariaDB host                    |
| `MCP_ANALYTICS_DB_PORT`               | `3306`      | MariaDB port                    |
| `MCP_ANALYTICS_DB_NAME`               | —           | MariaDB database name           |
| `MCP_ANALYTICS_DB_USER`               | —           | MariaDB username                |
| `MCP_ANALYTICS_DB_PASSWORD`           | —           | MariaDB password                |
| `MCP_ANALYTICS_MAX_ROWS`              | `500`       | Max rows per query (1–10000)    |
| `MCP_ANALYTICS_QUERY_TIMEOUT_SECONDS` | `30`        | Query timeout (1–300s)          |
| `MCP_ANALYTICS_MEMORY_LIMIT`          | `1GB`       | DuckDB memory limit             |
| `MCP_ANALYTICS_THREADS`               | `2`         | DuckDB threads (1–32)           |

## Current Limitations

- **In-memory only** — data is not persisted between server restarts
- **No CDC** — data is queried live from MariaDB on each request
- **No Parquet snapshots** — snapshots planned for Phase 2
- **No scheduled sync** — real-time only
- **No arbitrary SQL** — Phase 1 has no generic SQL tool
- **Timeout is advisory** — DuckDB does not support reliable hard-cancel of individual queries; duration is measured and logged

## Future Architecture (Phase 2+)

- CDC capture via MariaDB binlog
- Debezium integration
- Parquet file snapshots
- DuckDB-based data warehouse
- Pre-aggregated KPI tables
- Grafana dashboards via DuckDB
