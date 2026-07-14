"""Tests for analytics schema registry module."""

from erpnext_mcp_server.analytics.query_guard import DATASET_TABLE_MAP
from erpnext_mcp_server.analytics.schema_registry import (
    ALLOWED_TABLE_NAMES,
    SchemaRegistry,
    get_schema_registry,
)


class TestSchemaRegistry:
    """Tests for SchemaRegistry class."""

    def test_list_datasets(self):
        """list_datasets returns all dataset keys."""
        r = SchemaRegistry()
        datasets = r.list_datasets()
        assert "sales_invoice" in datasets
        assert "general_ledger" in datasets
        assert len(datasets) >= 8

    def test_get_dataset(self):
        """get_dataset returns DatasetInfo for valid key."""
        r = SchemaRegistry()
        info = r.get_dataset("sales_invoice")
        assert info is not None
        assert info.table == "tabSales Invoice"

    def test_get_dataset_nonexistent(self):
        """get_dataset returns None for unknown key."""
        r = SchemaRegistry()
        assert r.get_dataset("nonexistent") is None

    def test_get_field_names(self):
        """get_field_names returns field names."""
        r = SchemaRegistry()
        fields = r.get_field_names("sales_invoice")
        assert "company" in fields
        assert "customer" in fields
        assert "posting_date" in fields

    def test_get_field_names_excludes_blocked(self):
        """Blocked fields are excluded by default."""
        r = SchemaRegistry()
        fields = r.get_field_names("sales_invoice")
        # customer_signature and image should be blocked
        assert "customer_signature" not in fields

    def test_get_field_names_include_sensitive(self):
        """include_sensitive does not add fields not in the approved list."""
        r = SchemaRegistry()
        # customer_signature is in blocked_fields but not in the approved fields list,
        # so it never appears regardless of include_sensitive flag.
        # This is correct: we only expose pre-approved fields.
        fields = r.get_field_names("sales_invoice", include_sensitive=True)
        assert "customer_signature" not in fields  # not in approved fields
        # Regular fields are always present when include_sensitive=True
        assert "company" in fields
        assert "posting_date" in fields

    def test_describe_dataset(self):
        """describe_dataset returns complete metadata."""
        r = SchemaRegistry()
        desc = r.describe_dataset("sales_invoice")
        assert desc is not None
        assert desc["dataset"] == "sales_invoice"
        assert desc["table"] == "tabSales Invoice"
        assert "dimensions" in desc
        assert "metrics" in desc
        assert "fields" in desc
        assert "month" in desc["dimensions"]
        assert "net_sales" in desc["metrics"]

    def test_describe_dataset_nonexistent(self):
        """describe_dataset returns None for unknown dataset."""
        r = SchemaRegistry()
        assert r.describe_dataset("malicious") is None

    def test_describe_all(self):
        """describe_all returns all datasets."""
        r = SchemaRegistry()
        all_datasets = r.describe_all()
        assert len(all_datasets) >= 8
        # Check structure of each
        for desc in all_datasets:
            assert "dataset" in desc
            assert "table" in desc
            assert "fields" in desc

    def test_all_datasets_have_required_fields(self):
        """All datasets have required metadata."""
        r = SchemaRegistry()
        for key in r.list_datasets():
            desc = r.describe_dataset(key)
            assert desc is not None
            assert desc["dataset"] == key
            assert desc["table"] in ALLOWED_TABLE_NAMES

    def test_general_ledger_dataset(self):
        """general_ledger dataset has correct structure."""
        r = SchemaRegistry()
        desc = r.describe_dataset("general_ledger")
        assert desc is not None
        assert desc["table"] == "tabGL Entry"
        assert "debit" in [f["name"] for f in desc["fields"]]
        assert "credit" in [f["name"] for f in desc["fields"]]
        assert "posting_date" in [f["name"] for f in desc["fields"]]

    def test_dataset_table_map_consistency(self):
        """DATASET_TABLE_MAP keys match registered datasets."""
        r = SchemaRegistry()
        for key in DATASET_TABLE_MAP:
            info = r.get_dataset(key)
            assert info is not None
            assert info.table == DATASET_TABLE_MAP[key]


class TestSchemaRegistrySingleton:
    """Tests for the module-level singleton."""

    def test_get_schema_registry_returns_instance(self):
        """get_schema_registry returns a SchemaRegistry."""
        r = get_schema_registry()
        assert isinstance(r, SchemaRegistry)

    def test_get_schema_registry_same_instance(self):
        """get_schema_registry returns the same instance on repeated calls."""
        r1 = get_schema_registry()
        r2 = get_schema_registry()
        assert r1 is r2
