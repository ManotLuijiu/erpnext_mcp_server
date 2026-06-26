"""Tests for redaction.py — pure Python, no Frappe dep."""

import pytest

from erpnext_mcp_server.okf.redaction import (
    is_secret_field,
    redact_value,
    redact_field_definition,
    REDACTED_PLACEHOLDER,
)


# ---- is_secret_field ----

class TestIsSecretField:
    @pytest.mark.parametrize("name", [
        "password", "PASSWORD", "Password",
        "passwd", "PASSWD",
        "secret", "SECRET", "client_secret",
        "token", "TOKEN", "access_token", "refresh_token",
        "api_key", "api_secret", "apikey", "apisecret",
        "oauth", "OAuth", "OAUTH_TOKEN",
        "private_key", "PRIVATE_KEY",
        "session_key", "encryption_key", "ssh_key",
        "webhook_secret", "signing_key",
        "my_password_field", "user_api_key",
        "field_password_value", "client_oauth_token",
    ])
    def test_detects_secret_names(self, name):
        assert is_secret_field(name) is True, f"should detect: {name}"

    @pytest.mark.parametrize("name", [
        "email", "first_name", "company",
        "description", "subject", "body",
        "posting_date", "grand_total", "docstatus",
        "user", "owner", "modified_by",
        "title", "name",
    ])
    def test_does_not_flag_normal_fields(self, name):
        assert is_secret_field(name) is False, f"false positive: {name}"

    def test_handles_non_string(self):
        assert is_secret_field(None) is False
        assert is_secret_field(123) is False


# ---- redact_value ----

class TestRedactValue:
    def test_redacts_aws_key(self):
        assert redact_value("AKIAIOSFODNN7EXAMPLE") == REDACTED_PLACEHOLDER

    def test_redacts_github_pat(self):
        assert redact_value("ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij") == REDACTED_PLACEHOLDER

    def test_redacts_openai_key(self):
        assert redact_value("sk-abcdefghijklmnopqrstuvwxyz1234567890") == REDACTED_PLACEHOLDER

    def test_redacts_anthropic_key(self):
        assert redact_value("sk-ant-api03-abcdefghijklmnopqrstuvwxyz") == REDACTED_PLACEHOLDER

    def test_redacts_jwt(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        assert redact_value(jwt) == REDACTED_PLACEHOLDER

    def test_redacts_pem_block(self):
        pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAK..."
        assert redact_value(pem) == REDACTED_PLACEHOLDER

    def test_does_not_redact_normal_text(self):
        assert redact_value("Hello world") == "Hello world"
        assert redact_value("Sales Invoice #12345") == "Sales Invoice #12345"

    def test_redacts_in_dict(self):
        result = redact_value({
            "api_key": "sk-abcdefghijklmnopqrstuvwxyz1234567890",
            "company": "Acme Corp",
        })
        assert result["api_key"] == REDACTED_PLACEHOLDER
        assert result["company"] == "Acme Corp"

    def test_redacts_in_list(self):
        result = redact_value([
            "sk-abcdefghijklmnopqrstuvwxyz1234567890",
            "normal text",
        ])
        assert result[0] == REDACTED_PLACEHOLDER
        assert result[1] == "normal text"

    def test_handles_non_string_types(self):
        assert redact_value(123) == 123
        assert redact_value(None) is None
        assert redact_value(True) is True


# ---- redact_field_definition ----

class TestRedactFieldDefinition:
    def test_redacts_password_field_name(self):
        result = redact_field_definition("api_key", "Data", "sk-test123")
        assert result["_redacted"] is True
        assert result["options"] == REDACTED_PLACEHOLDER

    def test_redacts_password_fieldtype(self):
        result = redact_field_definition("user_pwd", "Password")
        assert result["_redacted"] is True
        # When fieldtype is "Password", options are always redacted (to placeholder)
        assert result["options"] == REDACTED_PLACEHOLDER

    def test_keeps_normal_field(self):
        result = redact_field_definition("email", "Data", "user@example.com")
        assert "_redacted" not in result
        assert result["options"] == "user@example.com"

    def test_includes_fieldname_and_type(self):
        result = redact_field_definition("amount", "Currency", "THB")
        assert result["fieldname"] == "amount"
        assert result["fieldtype"] == "Currency"
