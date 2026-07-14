You are working on this repository:

https://github.com/ManotLuijiu/erpnext_mcp_server.git

Your task is to implement a production-oriented DuckDB analytical layer for the existing Frappe/ERPNext MCP Server.

## Primary objective

Add DuckDB as a read-only analytical engine alongside the existing Frappe ORM and MariaDB query tools.

DuckDB must not replace MariaDB.

MariaDB remains the transactional source of truth.

Use Frappe ORM and Frappe APIs for:

- Retrieving permission-sensitive documents
- Creating or updating documents
- Workflow operations
- DocType hooks
- Validation
- Naming series
- Business transactions

Use DuckDB only for:

- Aggregations
- KPI analysis
- General Ledger analysis
- Sales analysis
- Inventory analysis
- Read-only analytical queries

## Important workflow restrictions

Do not run any of the following commands or actions without explicit permission:

- `bench build`
- `bench migrate`
- `bench restart`
- `bench update`
- `npm run build`
- `yarn build`
- database migration commands
- Git commit
- Git push
- pull request creation
- production deployment

You may inspect files, create code, edit code, and add tests.

Do not modify unrelated files.

Do not silently refactor the entire existing MCP server.

Before writing code, inspect the current repository structure and identify:

- The active MCP server entry point
- Existing MCP tool modules
- Existing configuration handling
- Existing test structure
- Existing Python dependency files
- Existing use of `frappe`, `FastMCP`, `Context`, and MCP annotations

Do not assume that the README structure exactly matches the current implementation.

## Existing project behavior to preserve

The project currently provides functionality such as:

- Retrieving Frappe documents
- Querying documents
- Counting documents
- Running ERPNext reports
- Reading files
- Translation-related tools
- Read-only SQL execution
- System information

Do not break or remove existing MCP tools.

DuckDB functionality must be added as a separate analytical layer.

## Required architecture

Create or adapt the repository toward this structure where appropriate:

```text
erpnext_mcp_server/
├── analytics/
│   ├── __init__.py
│   ├── connection.py
│   ├── configuration.py
│   ├── exceptions.py
│   ├── query_guard.py
│   ├── result_formatter.py
│   ├── schema_registry.py
│   └── queries/
│       ├── __init__.py
│       ├── sales.py
│       └── general_ledger.py
├── mcp_tools/
│   ├── __init__.py
│   └── analytics.py
└── tests/
    ├── test_analytics_configuration.py
    ├── test_analytics_query_guard.py
    ├── test_sales_analytics.py
    └── test_general_ledger_analytics.py
```

Adapt this structure to the existing repository conventions instead of forcing duplicate or conflicting packages.

If the repository already has an established tools folder, place the new MCP analytics tools there.

## Initial implementation scope

Implement Phase 1 only:

1. DuckDB connection management
2. DuckDB MySQL extension loading
3. Read-only MariaDB attachment
4. Approved analytics schema registry
5. Sales analytics MCP tool
6. General Ledger analytics MCP tool
7. Analytics health/status MCP tool
8. Analytics schema discovery MCP tool
9. Configuration validation
10. Result limits
11. Query logging
12. Unit tests

Do not implement CDC, Debezium, Parquet snapshots, scheduled synchronization, or a data warehouse in this task.

Design the code so those features can be added later.

## Dependency requirements

Add DuckDB to the correct Python dependency file used by this repository.

Use a supported current DuckDB Python package version compatible with the project’s Python version.

Do not add Pandas unless it already exists in the project or is clearly necessary.

Prefer returning data using:

```python
cursor.fetchall()
cursor.description
```

or DuckDB-native row conversion instead of requiring Pandas.

If SQL parsing is required, use a lightweight and maintained SQL parser only when justified.

For Phase 1, arbitrary user SQL is not required.

## Configuration design

Do not use the main Frappe MariaDB user for DuckDB analytics.

Require a dedicated MariaDB user with `SELECT` privileges only.

Support configuration through environment variables:

```text
MCP_ANALYTICS_ENABLED
MCP_ANALYTICS_DB_HOST
MCP_ANALYTICS_DB_PORT
MCP_ANALYTICS_DB_NAME
MCP_ANALYTICS_DB_USER
MCP_ANALYTICS_DB_PASSWORD
MCP_ANALYTICS_MAX_ROWS
MCP_ANALYTICS_QUERY_TIMEOUT_SECONDS
MCP_ANALYTICS_MEMORY_LIMIT
MCP_ANALYTICS_THREADS
```

Suggested defaults:

```text
MCP_ANALYTICS_ENABLED=false
MCP_ANALYTICS_DB_HOST=127.0.0.1
MCP_ANALYTICS_DB_PORT=3306
MCP_ANALYTICS_MAX_ROWS=500
MCP_ANALYTICS_QUERY_TIMEOUT_SECONDS=30
MCP_ANALYTICS_MEMORY_LIMIT=1GB
MCP_ANALYTICS_THREADS=2
```

Do not log database passwords or full connection strings.

Implement a typed configuration object, preferably using a Python dataclass.

Example conceptual interface:

```python
@dataclass(frozen=True)
class AnalyticsConfiguration:
    enabled: bool
    host: str
    port: int
    database: str
    user: str
    password: str
    max_rows: int
    query_timeout_seconds: int
    memory_limit: str
    threads: int
```

Validate:

- Required values when analytics is enabled
- Port range
- Positive row limits
- Positive timeout
- Positive thread count
- Non-empty database name
- Non-empty username
- Non-empty password

Raise specific configuration exceptions.

## DuckDB connection manager

Implement a reusable DuckDB analytics connection manager.

Requirements:

- Use an in-memory DuckDB connection for Phase 1
- Load the DuckDB MySQL extension
- Attach MariaDB using `TYPE mysql`
- Force `READ_ONLY`
- Use a stable alias such as `frappe_db`
- Apply DuckDB memory and thread settings
- Avoid sharing one unsafe connection across concurrent threads
- Support explicit connection closing
- Avoid exposing credentials in exceptions
- Be testable without a real MariaDB instance

Recommended conceptual API:

```python
class DuckDBAnalyticsConnection:
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        ...

    def close(self) -> None:
        ...

    def health_check(self) -> dict[str, object]:
        ...
```

A thread-local connection is acceptable.

A connection-per-request design is also acceptable if lifecycle and performance are handled correctly.

Do not install extensions on every individual query if it can be avoided safely.

Handle environments where extension installation is unavailable.

Return a clear configuration or connection error instead of crashing the MCP server.

## Security requirements

DuckDB must be strictly read-only.

Use multiple layers:

1. Dedicated MariaDB `SELECT`-only user
2. DuckDB attachment using `READ_ONLY`
3. No generic write MCP tools
4. No arbitrary SQL execution in Phase 1
5. Approved table and field registry
6. Parameterized query values
7. Controlled SQL identifiers
8. Maximum row limits
9. Query timeout or interruption strategy
10. Audit logging without secrets

Never execute SQL identifiers supplied directly by the LLM.

For values, always use query parameters.

For dimensions such as `group_by`, map approved literal values to predefined SQL expressions.

Example:

```python
GROUP_BY_EXPRESSIONS = {
    "customer": "customer",
    "customer_group": "customer_group",
    "territory": "territory",
    "month": "DATE_TRUNC('month', posting_date)",
}
```

Never do this:

```python
query = f"GROUP BY {user_supplied_value}"
```

unless the value has first been resolved through an internal allowlisted mapping.

## Approved initial ERPNext tables

Register these initial tables:

```text
tabSales Invoice
tabSales Invoice Item
tabGL Entry
tabCompany
tabCustomer
tabItem
tabAccount
tabCost Center
```

Create a schema registry describing:

- Logical dataset name
- Physical Frappe table
- Description
- Approved fields
- Sensitive or blocked fields
- Default conditions
- Supported analytical dimensions
- Supported metrics

Do not expose all MariaDB tables.

Example logical datasets:

```text
sales_invoice
sales_invoice_item
general_ledger
company
customer
item
account
cost_center
```

The schema registry should be usable by both MCP schema discovery and internal validation.

## Required MCP tool 1: analytics status

Implement a tool similar to:

```python
get_analytics_status()
```

It should return:

```json
{
  "enabled": true,
  "engine": "DuckDB",
  "source": "MariaDB",
  "attachment_mode": "read_only",
  "connected": true,
  "duckdb_version": "...",
  "database_alias": "frappe_db",
  "max_rows": 500
}
```

Do not return credentials, host passwords, or the raw connection string.

If disabled, return a clear result:

```json
{
  "enabled": false,
  "connected": false,
  "message": "DuckDB analytics is disabled"
}
```

Use the MCP read-only annotation.

## Required MCP tool 2: analytics schema discovery

Implement:

```python
describe_analytics_schema(
    dataset: str | None = None,
)
```

Without a dataset, return all approved logical datasets.

With a dataset, return its approved:

- Description
- Fields
- Dimensions
- Metrics
- Required filters
- Default conditions

Do not expose blocked or sensitive fields unless clearly marked as unavailable.

Use this tool to help an LLM understand the analytical semantic layer without accessing raw database metadata.

## Required MCP tool 3: sales analytics

Implement a controlled tool similar to:

```python
analyze_sales(
    company: str,
    from_date: str,
    to_date: str,
    group_by: Literal[
        "customer",
        "customer_group",
        "territory",
        "month",
    ] = "month",
    metric: Literal[
        "net_sales",
        "gross_sales",
        "invoice_count",
    ] = "net_sales",
    limit: int = 100,
)
```

Required behavior:

- Query `tabSales Invoice`
- Require `company`
- Require date range
- Include only submitted invoices using `docstatus = 1`
- Use `posting_date`
- Bound the requested limit between 1 and the configured maximum
- Use parameterized values
- Order by the selected metric descending
- Return structured metadata and data rows
- Return query duration
- Return row count
- Do not return the raw database password or connection string
- Do not expose arbitrary SQL through the MCP result

Suggested result:

```json
{
  "analysis": "sales",
  "company": "Example Company",
  "from_date": "2026-01-01",
  "to_date": "2026-06-30",
  "group_by": "month",
  "metric": "net_sales",
  "row_count": 6,
  "duration_ms": 24,
  "data": [
    {
      "dimension": "2026-01-01",
      "invoice_count": 120,
      "net_sales": 1500000.0,
      "gross_sales": 1605000.0
    }
  ]
}
```

Validate that:

- `from_date <= to_date`
- Company is not empty
- Grouping is allowlisted
- Metric is allowlisted
- Limit is valid

## Required MCP tool 4: General Ledger analytics

Implement a controlled tool similar to:

```python
analyze_general_ledger(
    company: str,
    from_date: str,
    to_date: str,
    group_by: Literal[
        "account",
        "cost_center",
        "voucher_type",
        "month",
    ] = "account",
    account: str | None = None,
    cost_center: str | None = None,
    limit: int = 100,
)
```

Required behavior:

- Query `tabGL Entry`
- Require `company`
- Require date range
- Include only submitted entries using `docstatus = 1`
- Exclude cancelled entries where relevant
- Use parameterized optional account and cost center filters
- Calculate:
  - Total debit
  - Total credit
  - Net balance
  - Entry count

- Use company currency fields when appropriate
- Bound the result limit
- Order by absolute net balance descending when possible
- Return metadata, duration, and rows

Suggested result:

```json
{
  "analysis": "general_ledger",
  "company": "Example Company",
  "from_date": "2026-01-01",
  "to_date": "2026-06-30",
  "group_by": "account",
  "row_count": 50,
  "duration_ms": 31,
  "data": [
    {
      "dimension": "Sales - EC",
      "entry_count": 250,
      "total_debit": 0.0,
      "total_credit": 3500000.0,
      "net_balance": -3500000.0
    }
  ]
}
```

Be careful with the accounting meaning of debit minus credit.

Do not label the value as profit or loss.

Use a neutral name such as `net_balance`.

## Query execution abstraction

Do not duplicate query execution logic across tools.

Create an internal executor such as:

```python
class AnalyticsQueryExecutor:
    def execute(
        self,
        query: str,
        parameters: Sequence[object],
        max_rows: int,
    ) -> AnalyticsQueryResult:
        ...
```

Suggested result model:

```python
@dataclass(frozen=True)
class AnalyticsQueryResult:
    columns: list[str]
    rows: list[dict[str, object]]
    row_count: int
    duration_ms: int
    truncated: bool
```

Responsibilities:

- Execute query
- Measure duration
- Apply row cap
- Convert DuckDB values into JSON-compatible values
- Convert dates and timestamps to ISO 8601 strings
- Convert Decimal values safely
- Detect truncation
- Log query type and duration
- Never log credentials
- Raise specific analytics exceptions

## Timeout handling

Implement the safest practical timeout mechanism supported by the current architecture.

Possible approaches include:

- Running the query in a controlled worker and interrupting the DuckDB connection
- Using a connection interruption strategy
- Applying conservative query designs and row limits
- Documenting limitations where hard cancellation is not reliable

Do not falsely claim timeout enforcement if it is only advisory.

If a fully reliable hard timeout is not practical in this phase, implement:

- Execution duration measurement
- Conservative approved queries
- Maximum rows
- Limited dimensions
- Limited metrics
- Clear documentation of the limitation

## Logging

Log:

- Tool name
- Logical dataset
- Company
- Date range
- Grouping
- Metric
- Row count
- Query duration
- Success or failure

Do not log:

- Database password
- Raw environment variables
- Full connection string
- Sensitive row values
- Entire SQL results

Use the project’s existing logging convention if one exists.

Otherwise use Python logging with a dedicated logger:

```python
logger = logging.getLogger("erpnext_mcp_server.analytics")
```

## Error design

Create specific exceptions such as:

```python
class AnalyticsError(Exception):
    pass

class AnalyticsDisabledError(AnalyticsError):
    pass

class AnalyticsConfigurationError(AnalyticsError):
    pass

class AnalyticsConnectionError(AnalyticsError):
    pass

class AnalyticsValidationError(AnalyticsError):
    pass

class AnalyticsQueryError(AnalyticsError):
    pass
```

MCP tools should catch these and return safe structured errors.

Example:

```json
{
  "error": {
    "code": "ANALYTICS_DISABLED",
    "message": "DuckDB analytics is disabled"
  }
}
```

Do not expose stack traces, passwords, or internal database connection details to MCP clients.

Unexpected exceptions should still be logged internally.

## MCP integration

Register the new tools with the active FastMCP server.

Use the correct annotation type already used by the project.

For all analytics tools, declare that they are read-only.

Do not create another independent MCP server unless the current architecture explicitly requires it.

Avoid circular imports between the server module and tool modules.

A registration pattern is acceptable:

```python
def register_analytics_tools(server: FastMCP) -> None:
    ...
```

Use the existing project style where possible.

## Tests

Add tests that do not require a running MariaDB database.

Use dependency injection or mocks for DuckDB connections.

Test at least:

### Configuration tests

- Analytics disabled by default
- Required variables when enabled
- Invalid port
- Invalid max rows
- Invalid timeout
- Invalid thread count
- Password is not included in exception messages

### Query mapping tests

- Valid sales groupings
- Invalid sales grouping rejected
- Valid metric mapping
- Limit bounded to configured maximum
- Date range validation
- Empty company rejected
- Optional GL filters parameterized

### Query safety tests

- No arbitrary SQL parameter is exposed through Phase 1 tools
- Grouping values are resolved through allowlisted mappings
- Table names come only from the internal schema registry
- Values remain parameterized
- No write query is generated
- Attachment is configured read-only

### Result formatting tests

- Dates become ISO strings
- Datetimes become ISO strings
- Decimal values become JSON-compatible
- Column names map correctly
- Row truncation is reported

### MCP tool tests

- Disabled analytics returns a safe error
- Connection error returns a safe error
- Sales analysis returns expected metadata
- GL analysis returns expected metadata
- Schema discovery returns only approved datasets
- Status tool does not expose credentials

Do not write tests that depend on external network access.

## Documentation

Update the README or add:

```text
docs/duckdb_analytics.md
```

Document:

1. Purpose of DuckDB in this project
2. Why DuckDB does not replace MariaDB
3. Installation
4. Environment variables
5. Creating a dedicated MariaDB read-only user
6. Security model
7. Available MCP tools
8. Example MCP requests
9. Current limitations
10. Future snapshot/Parquet architecture

Include an example MariaDB user setup:

```sql
CREATE USER 'erpnext_analytics'@'127.0.0.1'
IDENTIFIED BY 'replace-with-a-strong-password';

GRANT SELECT
ON `your_frappe_database`.*
TO 'erpnext_analytics'@'127.0.0.1';

FLUSH PRIVILEGES;
```

Explain that the actual database name must be taken from the Frappe site configuration.

Warn users not to grant:

- INSERT
- UPDATE
- DELETE
- CREATE
- ALTER
- DROP

Document that DuckDB must attach MariaDB with `READ_ONLY`.

## Code quality requirements

- Use Python type hints
- Avoid `Any` where a more precise type is practical
- Prefer dataclasses and typed literals
- Keep functions focused
- Avoid global mutable state
- Avoid duplicated SQL fragments
- Use parameterized query values
- Use internal mappings for SQL identifiers
- Add docstrings to public classes and functions
- Follow the repository’s formatter and lint conventions
- Preserve compatibility with the project’s supported Python version
- Avoid unnecessary dependencies
- Do not use Pandas unless already required
- Do not mix transactional writes into analytics code

## Required final response

After implementing, provide:

1. Summary of the architecture implemented
2. List of files created
3. List of files modified
4. Explanation of each MCP tool
5. Security controls implemented
6. Tests added
7. Tests actually run
8. Test results
9. Commands not run because permission was not provided
10. Known limitations
11. Recommended next phase

Do not claim that tests passed unless you actually ran them.

Do not run build, migration, restart, commit, push, or deployment commands without explicit permission.

## Acceptance criteria

The task is complete when:

- Existing MCP tools remain functional
- DuckDB analytics can be disabled cleanly
- Analytics configuration is validated
- MariaDB attachment is read-only
- No generic arbitrary DuckDB SQL MCP tool exists
- Sales analytics is implemented
- General Ledger analytics is implemented
- Analytics schema discovery is implemented
- Analytics status is implemented
- Queries use parameterized values
- SQL identifiers come from internal allowlists
- Results are JSON-compatible
- Result limits are enforced
- Errors do not expose credentials
- Tests cover validation, security, query mapping, and formatting
- Documentation explains setup and limitations
- No build, migration, commit, push, or deployment was performed
