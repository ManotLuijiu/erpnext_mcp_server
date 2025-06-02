"""
Database Tools for ERPNext MCP Server
Handles safe database operations with security restrictions
"""

import json
import re
from typing import Any, Dict, List, Union

import frappe
from frappe import _


class DatabaseTools:
    """Tools for safe database operations."""

    def __init__(self, config=None) -> None:
        print(f"config DatabaseTools {config}")
        # Only allow SELECT statements for security
        self.allowed_sql_patterns = [
            r"^\s*SELECT\s+",
            r"^\s*WITH\s+.*SELECT\s+",  # Allow CTEs
            r"^\s*SHOW\s+",
            r"^\s*DESCRIBE\s+",
            r"^\s*DESC\s+",
            r"^\s*EXPLAIN\s+",
        ]

        # Dangerous keywords to block
        self.blocked_keywords = [
            "INSERT",
            "UPDATE",
            "DELETE",
            "DROP",
            "CREATE",
            "ALTER",
            "TRUNCATE",
            "REPLACE",
            "MERGE",
            "CALL",
            "EXEC",
            "EXECUTE",
            "LOAD",
            "OUTFILE",
            "DUMPFILE",
            "INTO",
            "BULK",
        ]

    def _is_safe_query(self, query: str) -> tuple[bool, str]:
        """Check if SQL query is safe to execute."""
        query_upper = query.upper().strip()

        # Check for blocked keywords
        for keyword in self.blocked_keywords:
            if keyword in query_upper:
                return False, f"Blocked keyword detected: {keyword}"

        # Check if query matches allowed patterns
        for pattern in self.allowed_sql_patterns:
            if re.match(pattern, query_upper, re.IGNORECASE):
                return True, "Query is safe"

        return (
            False,
            "Query does not match allowed patterns (only SELECT, SHOW, DESCRIBE, EXPLAIN allowed)",
        )

    async def execute_sql(self, query: str, limit: int = 100) -> str:
        """Execute a safe SQL query with results formatting."""
        try:
            # Security check
            is_safe, message = self._is_safe_query(query)
            if not is_safe:
                return f"❌ Security Error: {message}"

            # Add limit if not present in SELECT queries
            query_upper = query.upper().strip()
            if query_upper.startswith("SELECT") and "LIMIT" not in query_upper:
                query = f"{query.rstrip(';')} LIMIT {limit}"

            # Execute query
            result = frappe.db.sql(query, as_dict=True)

            if not result:
                return "📊 Query executed successfully - No results returned"

            # Format results
            output = [
                "📊 SQL Query Results",
                "=" * 30,
                f"Query: {query}",
                f"Rows returned: {len(result)}",  # type: ignore
                "",
            ]

            if len(result) > 0:  # type: ignore
                # Get column names
                columns = list(result[0].keys())  # type: ignore

                # Create table header
                header = " | ".join([col.ljust(15)[:15] for col in columns])
                separator = "-" * len(header)

                output.extend([header, separator])

                # Add data rows
                for row in result:
                    row_data = []
                    for col in columns:
                        value = str(row.get(col, ""))[:15]  # type: ignore
                        row_data.append(value.ljust(15))
                    output.append(" | ".join(row_data))

                # Add summary
                output.extend(
                    ["", f"📈 Summary: {len(result)} rows, {len(columns)} columns"]  # type: ignore
                )

                # If too many rows, suggest using LIMIT
                if len(result) >= limit:  # type: ignore
                    output.append(
                        f"⚠️  Results limited to {limit} rows. Use LIMIT clause for specific count."
                    )

            return "\n".join(output)

        except Exception as e:
            return f"❌ SQL Error: {str(e)}"

    async def get_table_info(self, table_name: str) -> str:
        """Get information about a database table."""
        try:
            # Security: Only allow tables that start with tab
            if not table_name.startswith("tab"):
                table_name = f"tab{table_name}"

            # Check if table exists
            tables = frappe.db.sql(f"SHOW TABLES LIKE '{table_name}'", as_dict=True)
            if not tables:
                return f"❌ Table not found: {table_name}"

            # Get table structure
            structure = frappe.db.sql(f"DESCRIBE `{table_name}`", as_dict=True)

            # Get row count
            count_result = frappe.db.sql(
                f"SELECT COUNT(*) as count FROM `{table_name}`", as_dict=True
            )
            row_count = count_result[0]["count"] if count_result else 0  # type: ignore

            # Format output
            output = [
                f"📋 Table Information: {table_name}",
                "=" * (len(table_name) + 22),
                f"Total Rows: {row_count:,}",
                "",
                "Column Structure:",
                "-" * 50,
            ]

            for col in structure:
                field_info = f"{col['Field'].ljust(25)} {col['Type'].ljust(20)}"  # type: ignore
                if col["Null"] == "NO":  # type: ignore
                    field_info += " NOT NULL"
                if col["Key"]:  # type: ignore
                    field_info += f" ({col['Key']})"  # type: ignore
                if col["Default"]:  # type: ignore
                    field_info += f" DEFAULT: {col['Default']}"  # type: ignore

                output.append(field_info)

            return "\n".join(output)

        except Exception as e:
            return f"❌ Error getting table info: {str(e)}"

    async def get_database_stats(self) -> str:
        """Get database statistics and information."""
        try:
            output = ["📊 Database Statistics", "=" * 30, ""]

            # Get database name
            db_name = frappe.conf.db_name
            output.append(f"Database: {db_name}")

            # Get table count
            tables = frappe.db.sql("SHOW TABLES", as_dict=True)
            table_count = len(tables)  # type: ignore
            output.append(f"Total Tables: {table_count}")

            # Get ERPNext specific stats
            doctypes = frappe.db.sql(
                "SELECT COUNT(*) as count FROM `tabDocType`", as_dict=True
            )
            doctype_count = doctypes[0]["count"] if doctypes else 0  # type: ignore
            output.append(f"Document Types: {doctype_count}")

            # Get user count
            users = frappe.db.sql(
                "SELECT COUNT(*) as count FROM `tabUser` WHERE enabled=1", as_dict=True
            )
            user_count = users[0]["count"] if users else 0  # type: ignore
            output.append(f"Active Users: {user_count}")

            # Get recent activity
            recent_docs = frappe.db.sql(
                """
                SELECT doctype, COUNT(*) as count 
                FROM `tabVersion` 
                WHERE creation >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY doctype 
                ORDER BY count DESC 
                LIMIT 5
            """,
                as_dict=True,
            )

            if recent_docs:
                output.extend(["", "📈 Most Active DocTypes (Last 7 days):", "-" * 40])
                for doc in recent_docs:
                    output.append(f"  {doc['doctype']}: {doc['count']} changes")  # type: ignore

            return "\n".join(output)

        except Exception as e:
            return f"❌ Error getting database stats: {str(e)}"
