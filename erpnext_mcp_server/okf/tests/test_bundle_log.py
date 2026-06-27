"""Tests for bundle.py::generate_log + record_event (OKF spec §7)."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from erpnext_mcp_server.okf.bundle import (
    HISTORY_FILENAME,
    LOG_FILENAME,
    generate_bundle_artifacts,
    generate_index,
    generate_log,
    record_event,
)
from erpnext_mcp_server.okf.writer import write_concept


@pytest.fixture
def sample_bundle(tmp_path):
    """Create a small bundle with 2 concepts for testing."""
    (tmp_path / "doctypes").mkdir()
    write_concept(
        tmp_path / "doctypes" / "sales-invoice.md",
        {"type": "Frappe DocType", "title": "Sales Invoice", "tags": ["billing"]},
        "# Sales Invoice\n\nBody.",
    )
    write_concept(
        tmp_path / "doctypes" / "customer.md",
        {"type": "Frappe DocType", "title": "Customer", "tags": ["crm"]},
        "# Customer\n\nBody.",
    )
    return tmp_path


class TestRecordEvent:
    def test_record_event_creates_history_file(self, sample_bundle):
        event = record_event(
            sample_bundle,
            verb="Update",
            summary="Re-exported 2 DocTypes",
            links=["doctypes/sales-invoice.md", "doctypes/customer.md"],
            details={"count": 2},
        )
        history_path = sample_bundle / HISTORY_FILENAME
        assert history_path.exists()
        history = json.loads(history_path.read_text())
        assert len(history) == 1
        assert history[0]["verb"] == "Update"
        assert history[0]["summary"] == "Re-exported 2 DocTypes"
        assert history[0]["links"] == [
            "doctypes/sales-invoice.md",
            "doctypes/customer.md",
        ]
        assert history[0]["details"] == {"count": 2}
        assert "timestamp" in history[0]

    def test_record_event_appends(self, sample_bundle):
        for i in range(3):
            record_event(sample_bundle, verb="Update", summary=f"event {i}")
        history = json.loads((sample_bundle / HISTORY_FILENAME).read_text())
        assert len(history) == 3
        assert [e["summary"] for e in history] == ["event 0", "event 1", "event 2"]

    def test_record_event_corrupt_history_doesnt_crash(self, tmp_path):
        # Write garbage to history
        (tmp_path / HISTORY_FILENAME).write_text("not valid json{{")
        # Should not raise — returns []
        event = record_event(tmp_path, verb="Update", summary="test")
        assert event["verb"] == "Update"

    def test_record_event_no_details(self, sample_bundle):
        event = record_event(sample_bundle, verb="Creation", summary="Initial bundle")
        assert "details" not in event  # omitted when None
        assert "links" not in event


class TestGenerateLog:
    def test_no_history_no_log(self, sample_bundle):
        """No history file = no log.md (don't create empty log)."""
        result = generate_log(sample_bundle)
        assert result is None
        assert not (sample_bundle / LOG_FILENAME).exists()

    def test_generates_log_after_event(self, sample_bundle):
        record_event(sample_bundle, verb="Initialization", summary="Initial bundle from aws-solution site")
        log_path = generate_log(sample_bundle)
        assert log_path is not None
        assert log_path.exists()
        assert log_path.name == LOG_FILENAME
        content = log_path.read_text()
        assert "# " in content  # has heading
        assert "## " in content  # has date heading
        assert "**Initialization**" in content  # has bold verb
        assert "Initial bundle from aws-solution site" in content

    def test_log_groups_by_date(self, sample_bundle):
        # Manually write history with multiple dates
        history = [
            {"timestamp": "2026-06-27T10:00:00+00:00", "verb": "Update", "summary": "today's update"},
            {"timestamp": "2026-06-26T10:00:00+00:00", "verb": "Creation", "summary": "yesterday's creation"},
        ]
        (sample_bundle / HISTORY_FILENAME).write_text(json.dumps(history))
        log = generate_log(sample_bundle).read_text()

        # Both dates should appear as ## headings
        assert "## 2026-06-27" in log
        assert "## 2026-06-26" in log

        # Newest first (2026-06-27 before 2026-06-26)
        pos_today = log.index("## 2026-06-27")
        pos_yesterday = log.index("## 2026-06-26")
        assert pos_today < pos_yesterday

    def test_log_includes_links(self, sample_bundle):
        record_event(
            sample_bundle,
            verb="Update",
            summary="Re-exported DocType",
            links=["doctypes/sales-invoice.md"],
        )
        log = generate_log(sample_bundle).read_text()
        assert "[`sales-invoice.md`](doctypes/sales-invoice.md)" in log

    def test_log_includes_details(self, sample_bundle):
        record_event(
            sample_bundle,
            verb="Update",
            summary="Bulk export",
            details={"exported": 314, "skipped": 0},
        )
        log = generate_log(sample_bundle).read_text()
        assert "exported=314" in log
        assert "skipped=0" in log

    def test_log_truncates_many_links(self, sample_bundle):
        # 15 links — should truncate to 10 with "and N more"
        links = [f"doctypes/doc-{i}.md" for i in range(15)]
        record_event(sample_bundle, verb="Update", summary="many links", links=links)
        log = generate_log(sample_bundle).read_text()
        assert "and 5 more" in log


class TestGenerateBundleArtifacts:
    def test_generates_both(self, sample_bundle):
        # No history yet — only index.md
        artifacts = generate_bundle_artifacts(sample_bundle)
        assert "index" in artifacts
        assert "log" not in artifacts  # no history yet

        # After recording an event, log.md appears
        record_event(sample_bundle, verb="Update", summary="test")
        artifacts = generate_bundle_artifacts(sample_bundle)
        assert "index" in artifacts
        assert "log" in artifacts

    def test_index_excludes_log_file(self, sample_bundle):
        record_event(sample_bundle, verb="Update", summary="event 1")
        record_event(sample_bundle, verb="Update", summary="event 2")
        generate_bundle_artifacts(sample_bundle)

        # Read index — should NOT list log.md as a concept
        index_content = (sample_bundle / "index.md").read_text()
        assert "log.md" not in index_content
        assert "Sales Invoice" in index_content
        assert "Customer" in index_content

    def test_list_bundles_includes_log_status(self, sample_bundle):
        # Generate index for sample_bundle (no history yet)
        from erpnext_mcp_server.okf.bundle import list_bundles

        generate_bundle_artifacts(sample_bundle)
        bundles = list_bundles(sample_bundle.parent)

        # Find our specific bundle in the list (sibling tests may share tmp_path)
        our_bundle = next((b for b in bundles if b["path"] == str(sample_bundle)), None)
        assert our_bundle is not None, "our bundle should appear in the listing"
        assert our_bundle["has_log"] is False  # no history yet

        # Record event + regenerate
        record_event(sample_bundle, verb="Update", summary="test")
        generate_bundle_artifacts(sample_bundle)
        bundles = list_bundles(sample_bundle.parent)
        our_bundle = next((b for b in bundles if b["path"] == str(sample_bundle)), None)
        assert our_bundle["has_log"] is True
