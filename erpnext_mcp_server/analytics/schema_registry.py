"""Analytics schema registry module.

Declares the approved logical datasets, physical tables, fields,
and analytical dimensions/metrics available for DuckDB queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Dataset metadata
# ---------------------------------------------------------------------------

ALLOWED_TABLE_NAMES: frozenset[str] = frozenset(
    {
        "tabSales Invoice",
        "tabSales Invoice Item",
        "tabGL Entry",
        "tabCompany",
        "tabCustomer",
        "tabItem",
        "tabAccount",
        "tabCost Center",
    }
)


@dataclass(frozen=True)
class FieldInfo:
    """Describes an approved field in a dataset."""

    name: str
    description: str
    type: str  # e.g., "string", "number", "date", "boolean"
    is_sensitive: bool = False  # blocked for MCP exposure if True


@dataclass(frozen=True)
class DatasetInfo:
    """Describes an approved analytical dataset."""

    dataset: str  # logical key
    table: str  # physical Frappe table
    description: str
    fields: tuple[FieldInfo, ...] = field(default_factory=tuple)
    # Analytical dimensions supported
    dimensions: tuple[str, ...] = field(default_factory=tuple)
    # Analytical metrics supported
    metrics: tuple[str, ...] = field(default_factory=tuple)
    # Default SQL conditions applied to every query
    default_conditions: tuple[str, ...] = field(default_factory=tuple)
    # Blocked fields (sensitive) — not returned in schema discovery
    blocked_fields: frozenset[str] = field(default_factory=frozenset)


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------

_SCHEMA: dict[str, DatasetInfo] = {
    "sales_invoice": DatasetInfo(
        dataset="sales_invoice",
        table="tabSales Invoice",
        description="Submitted sales invoices for a company.",
        fields=(
            FieldInfo("name", "Invoice name (ID)", "string"),
            FieldInfo("company", "Company name", "string"),
            FieldInfo("customer", "Customer name", "string"),
            FieldInfo("customer_name", "Customer full name", "string"),
            FieldInfo("customer_group", "Customer group", "string"),
            FieldInfo("territory", "Territory / region", "string"),
            FieldInfo("posting_date", "Invoice posting date", "date"),
            FieldInfo("due_date", "Payment due date", "date"),
            FieldInfo(
                "docstatus",
                "Document status (0=draft,1=submitted,2=cancelled)",
                "number",
            ),
            FieldInfo(
                "base_net_amount", "Net amount in company base currency", "number"
            ),
            FieldInfo(
                "baseGrossAmount", "Gross amount in company base currency", "number"
            ),
            FieldInfo("base_rounded_total", "Rounded total in base currency", "number"),
            FieldInfo("currency", "Transaction currency", "string"),
            FieldInfo("base_currency", "Company base currency", "string"),
            FieldInfo("status", "Invoice status", "string"),
            FieldInfo("is_return", "Is a sales return", "boolean"),
            FieldInfo("update_stock", "Updates stock", "boolean"),
            FieldInfo("set_posting_time", "Posting time is user-set", "boolean"),
            FieldInfo("selling_price_list", "Selling price list", "string"),
            FieldInfo("taxes_and_charges", "Tax template", "string"),
            FieldInfo("project", "Project name", "string"),
        ),
        dimensions=("customer", "customer_group", "territory", "month", "week", "year"),
        metrics=("net_sales", "gross_sales", "invoice_count", "qty", "avg_net_rate"),
        default_conditions=("docstatus = 1",),
        blocked_fields=frozenset({"customer_signature", "image"}),
    ),
    "sales_invoice_item": DatasetInfo(
        dataset="sales_invoice_item",
        table="tabSales Invoice Item",
        description="Line items of submitted sales invoices.",
        fields=(
            FieldInfo("name", "Item row name", "string"),
            FieldInfo("parent", "Parent invoice name", "string"),
            FieldInfo("parenttype", "Parent doctype", "string"),
            FieldInfo("item_code", "Item code", "string"),
            FieldInfo("item_name", "Item name", "string"),
            FieldInfo("description", "Item description", "string"),
            FieldInfo("item_group", "Item group", "string"),
            FieldInfo("qty", "Quantity", "number"),
            FieldInfo("uom", "Unit of measure", "string"),
            FieldInfo("rate", "Rate in transaction currency", "number"),
            FieldInfo("base_rate", "Rate in company base currency", "number"),
            FieldInfo("amount", "Line amount in transaction currency", "number"),
            FieldInfo("base_amount", "Line amount in base currency", "number"),
            FieldInfo("base_net_amount", "Net line amount in base currency", "number"),
            FieldInfo("net_rate", "Net rate", "number"),
            FieldInfo("stock_qty", "Stock quantity", "number"),
            FieldInfo("stock_uom", "Stock unit of measure", "string"),
            FieldInfo("warehouse", "Warehouse name", "string"),
            FieldInfo("cost_center", "Cost centre", "string"),
            FieldInfo("project", "Project name", "string"),
            FieldInfo("income_account", "Income account", "string"),
            FieldInfo("company", "Company name", "string"),
            FieldInfo("docstatus", "Document status", "number"),
        ),
        dimensions=("item_code", "item_group", "warehouse", "cost_center", "month"),
        metrics=("qty", "net_sales", "gross_sales"),
        default_conditions=("parenttype = 'Sales Invoice'", "docstatus = 1"),
        blocked_fields=frozenset(),
    ),
    "general_ledger": DatasetInfo(
        dataset="general_ledger",
        table="tabGL Entry",
        description="Submitted general ledger entries for a company.",
        fields=(
            FieldInfo("name", "GL Entry name", "string"),
            FieldInfo("posting_date", "Posting date", "date"),
            FieldInfo("company", "Company name", "string"),
            FieldInfo("account", "Account name", "string"),
            FieldInfo("account_currency", "Account currency", "string"),
            FieldInfo("debit", "Debit amount in account currency", "number"),
            FieldInfo("credit", "Credit amount in account currency", "number"),
            FieldInfo(
                "debit_in_account_currency", "Debit in account currency", "number"
            ),
            FieldInfo(
                "credit_in_account_currency", "Credit in account currency", "number"
            ),
            FieldInfo("party_type", "Party type (Customer, Supplier, etc.)", "string"),
            FieldInfo("party", "Party name", "string"),
            FieldInfo("voucher_type", "Voucher doctype name", "string"),
            FieldInfo("voucher_no", "Voucher document name", "string"),
            FieldInfo("cost_center", "Cost centre", "string"),
            FieldInfo("project", "Project name", "string"),
            FieldInfo("against", "Against account", "string"),
            FieldInfo("against_voucher_type", "Against voucher doctype", "string"),
            FieldInfo("against_voucher", "Against voucher name", "string"),
            FieldInfo("user_remark", "User remark / narration", "string"),
            FieldInfo("docstatus", "Document status (1=submitted)", "number"),
            FieldInfo("is_opening", "Is opening entry", "boolean"),
            FieldInfo("is_advance", "Is advance payment", "boolean"),
        ),
        dimensions=("account", "cost_center", "voucher_type", "month", "week", "year"),
        metrics=(),
        default_conditions=("docstatus = 1",),
        blocked_fields=frozenset(),
    ),
    "company": DatasetInfo(
        dataset="company",
        table="tabCompany",
        description="ERPNext company master.",
        fields=(
            FieldInfo("name", "Company name", "string"),
            FieldInfo("abbr", "Company abbreviation", "string"),
            FieldInfo("company_name", "Full company name", "string"),
            FieldInfo("default_currency", "Default currency", "string"),
            FieldInfo("country", "Country of registration", "string"),
        ),
        dimensions=(),
        metrics=(),
        default_conditions=(),
        blocked_fields=frozenset(),
    ),
    "customer": DatasetInfo(
        dataset="customer",
        table="tabCustomer",
        description="ERPNext customer master.",
        fields=(
            FieldInfo("name", "Customer ID", "string"),
            FieldInfo("customer_name", "Customer full name", "string"),
            FieldInfo("customer_type", "Individual or Company", "string"),
            FieldInfo("customer_group", "Customer group", "string"),
            FieldInfo("territory", "Territory", "string"),
            FieldInfo("company_name", "Related company name", "string"),
            FieldInfo("default_currency", "Default currency", "string"),
            FieldInfo("credit_limit", "Credit limit", "number"),
        ),
        dimensions=("customer_group", "territory"),
        metrics=(),
        default_conditions=(),
        blocked_fields=frozenset(),
    ),
    "item": DatasetInfo(
        dataset="item",
        table="tabItem",
        description="ERPNext item master.",
        fields=(
            FieldInfo("name", "Item code", "string"),
            FieldInfo("item_name", "Item name", "string"),
            FieldInfo("item_group", "Item group", "string"),
            FieldInfo("stock_uom", "Stock unit of measure", "string"),
            FieldInfo("item_type", "Item type (Product, Service, etc.)", "string"),
            FieldInfo("is_stock_item", "Is a stock item", "boolean"),
            FieldInfo("disabled", "Item is disabled", "boolean"),
        ),
        dimensions=("item_group",),
        metrics=(),
        default_conditions=(),
        blocked_fields=frozenset(),
    ),
    "account": DatasetInfo(
        dataset="account",
        table="tabAccount",
        description="ERPNext chart of accounts.",
        fields=(
            FieldInfo("name", "Account name", "string"),
            FieldInfo("account_name", "Account display name", "string"),
            FieldInfo("account_number", "Account number", "string"),
            FieldInfo("company", "Company name", "string"),
            FieldInfo("parent_account", "Parent account name", "string"),
            FieldInfo("account_type", "Account type", "string"),
            FieldInfo("is_group", "Is a group account", "boolean"),
            FieldInfo("root_type", "Root type (Asset, Liability, etc.)", "string"),
            FieldInfo("currency", "Account currency", "string"),
        ),
        dimensions=("account_type", "root_type", "company"),
        metrics=(),
        default_conditions=(),
        blocked_fields=frozenset(),
    ),
    "cost_center": DatasetInfo(
        dataset="cost_center",
        table="tabCost Center",
        description="ERPNext cost centre / department hierarchy.",
        fields=(
            FieldInfo("name", "Cost centre name", "string"),
            FieldInfo("cost_center_name", "Cost centre display name", "string"),
            FieldInfo("company", "Company name", "string"),
            FieldInfo("parent_cost_center", "Parent cost centre", "string"),
            FieldInfo("cost_center_type", "Type / department", "string"),
            FieldInfo("is_group", "Is a group cost centre", "boolean"),
        ),
        dimensions=("company",),
        metrics=(),
        default_conditions=(),
        blocked_fields=frozenset(),
    ),
}


class SchemaRegistry:
    """Read-only registry of approved analytical datasets."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._schema = _SCHEMA

    def list_datasets(self) -> list[str]:
        """Return all registered dataset keys."""
        return sorted(self._schema.keys())

    def get_dataset(self, dataset: str) -> DatasetInfo | None:
        """Get metadata for a dataset.

        Args:
            dataset: Logical dataset key.

        Returns:
            DatasetInfo or None if not registered.
        """
        return self._schema.get(dataset)

    def get_field_names(
        self, dataset: str, include_sensitive: bool = False
    ) -> list[str]:
        """Return approved field names for a dataset.

        Args:
            dataset: Logical dataset key.
            include_sensitive: Include blocked/sensitive fields.

        Returns:
            List of field names.
        """
        info = self._schema.get(dataset)
        if info is None:
            return []
        if include_sensitive:
            return [f.name for f in info.fields]
        return [f.name for f in info.fields if f.name not in info.blocked_fields]

    def describe_dataset(self, dataset: str) -> dict[str, Any] | None:
        """Return a human-readable description of a dataset.

        Args:
            dataset: Logical dataset key.

        Returns:
            Dictionary with dataset metadata, or None if not found.
        """
        info = self._schema.get(dataset)
        if info is None:
            return None

        return {
            "dataset": info.dataset,
            "table": info.table,
            "description": info.description,
            "dimensions": list(info.dimensions),
            "metrics": list(info.metrics),
            "default_conditions": list(info.default_conditions),
            "fields": [
                {
                    "name": f.name,
                    "description": f.description,
                    "type": f.type,
                    "available": f.name not in info.blocked_fields,
                }
                for f in info.fields
            ],
        }

    def describe_all(self) -> list[dict[str, Any]]:
        """Return descriptions for all datasets."""
        results: list[dict[str, Any]] = []
        for key in sorted(self._schema.keys()):
            desc = self.describe_dataset(key)
            if desc is not None:
                results.append(desc)
        return results


# Module-level singleton
_registry: SchemaRegistry | None = None


def get_schema_registry() -> SchemaRegistry:
    """Return the global SchemaRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = SchemaRegistry()
    return _registry
