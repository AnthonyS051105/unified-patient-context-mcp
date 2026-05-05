import os
import pytest
from unittest.mock import MagicMock

from sharp.context import SHARPContext, extract_sharp_context
from sharp.middleware import resolve_patient_id, build_sharp_metadata, role_is
from sharp.audit import log_tool_call, log_sharp_absent


class TestExtractSharpContext:
    def test_returns_empty_when_ctx_is_none(self):
        result = extract_sharp_context(None)
        assert isinstance(result, SHARPContext)
        assert result.is_present is False
        assert result.patient_id is None

    def test_returns_empty_when_ctx_has_no_meta(self):
        ctx = MagicMock()
        ctx.request_context.meta = {}
        result = extract_sharp_context(ctx)
        assert result.is_present is False

    def test_extracts_all_fields_from_meta(self):
        ctx = MagicMock()
        ctx.request_context.meta = {
            "sharp_patient_id": "patient-123",
            "sharp_ehr_token": "token-abc",
            "sharp_session_id": "sess-001",
            "sharp_org_id": "org-xyz",
            "sharp_role": "physician",
        }
        result = extract_sharp_context(ctx)
        assert result.patient_id == "patient-123"
        assert result.ehr_token == "token-abc"
        assert result.session_id == "sess-001"
        assert result.org_id == "org-xyz"
        assert result.role == "physician"
        assert result.is_present is True

    def test_graceful_fallback_on_exception(self):
        # Simulate a ctx object where accessing attributes raises an exception
        ctx = MagicMock()
        ctx.request_context = MagicMock()
        ctx.request_context.meta = None
        ctx.meta = None
        result = extract_sharp_context(ctx)
        assert isinstance(result, SHARPContext)
        assert result.is_present is False

    def test_mock_sharp_mode(self, monkeypatch):
        monkeypatch.setenv("MOCK_SHARP", "true")
        monkeypatch.setenv("MOCK_PATIENT_ID", "mock-patient-001")
        monkeypatch.setenv("MOCK_SHARP_ROLE", "nurse")
        result = extract_sharp_context(None)
        assert result.patient_id == "mock-patient-001"
        assert result.role == "nurse"
        assert result.is_present is True

    def test_mock_sharp_false_does_not_inject(self, monkeypatch):
        monkeypatch.setenv("MOCK_SHARP", "false")
        result = extract_sharp_context(None)
        assert result.is_present is False


class TestResolvePatientId:
    def test_sharp_id_takes_priority(self):
        sharp = SHARPContext(patient_id="sharp-patient", is_present=True)
        assert resolve_patient_id("explicit-patient", sharp) == "sharp-patient"

    def test_falls_back_to_explicit_when_no_sharp(self):
        sharp = SHARPContext()
        assert resolve_patient_id("explicit-patient", sharp) == "explicit-patient"

    def test_returns_none_when_both_absent(self):
        sharp = SHARPContext()
        assert resolve_patient_id(None, sharp) is None


class TestBuildSharpMetadata:
    def test_sharp_present_populates_metadata(self):
        sharp = SHARPContext(
            session_id="sess-001",
            org_id="org-xyz",
            role="physician",
            is_present=True,
        )
        meta = build_sharp_metadata(sharp)
        assert meta["sharp_propagated"] is True
        assert meta["role_context"] == "physician"
        assert meta["org_id"] == "org-xyz"
        assert meta["session_id"] == "[REDACTED]"

    def test_sharp_absent_gives_false_propagated(self):
        sharp = SHARPContext()
        meta = build_sharp_metadata(sharp)
        assert meta["sharp_propagated"] is False
        assert meta["session_id"] is None

    def test_ehr_token_never_in_metadata(self):
        sharp = SHARPContext(ehr_token="super-secret-token", is_present=True)
        meta = build_sharp_metadata(sharp)
        assert "ehr_token" not in meta
        assert "super-secret-token" not in str(meta)


class TestRoleIs:
    def test_matches_exact_role(self):
        sharp = SHARPContext(role="physician")
        assert role_is(sharp, "physician") is True

    def test_case_insensitive(self):
        sharp = SHARPContext(role="NURSE")
        assert role_is(sharp, "nurse") is True

    def test_multi_role_check(self):
        sharp = SHARPContext(role="pharmacist")
        assert role_is(sharp, "physician", "pharmacist") is True

    def test_no_match(self):
        sharp = SHARPContext(role="admin")
        assert role_is(sharp, "physician", "nurse") is False

    def test_no_role_returns_false(self):
        sharp = SHARPContext()
        assert role_is(sharp, "physician") is False


class TestAuditLogging:
    def test_log_tool_call_no_exception(self, caplog):
        import logging
        with caplog.at_level(logging.INFO):
            log_tool_call("get_patient_snapshot", "sess-123", "physician")
        assert "get_patient_snapshot" in caplog.text
        assert "physician" in caplog.text
        assert "sess-123" not in caplog.text

    def test_log_sharp_absent_no_exception(self):
        log_sharp_absent("get_patient_snapshot")
