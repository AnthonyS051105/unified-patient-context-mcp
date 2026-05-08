import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock


MOCK_CORE = {
    "source": "nara_core",
    "available": True,
    "recency_hours": 0.0,
    "snapshot": {"patient_id": "test-p1", "name": "Eleanor Dawson"},
    "news2_score": 6,
    "risk_level": "medium",
}

MOCK_RADIOLOGY = {
    "imaging_findings": "No acute cardiopulmonary process.",
    "last_imaging_date": "2026-05-06",
    "available": True,
    "source": "radiology_mcp",
    "recency_hours": 24.0,
}

MOCK_PHARMACY = {
    "dispensing_records": ["Metformin 500mg — 3 days ago"],
    "available": True,
    "source": "pharmacy_mcp",
    "recency_hours": 72.0,
}


@pytest.mark.asyncio
async def test_orchestrate_with_mock_servers(monkeypatch):
    monkeypatch.setenv("MOCK_EXTERNAL_MCP", "true")

    async def mock_core(pid, ctx):
        return MOCK_CORE

    with patch("tools.orchestrate._get_core_data", side_effect=mock_core), \
         patch("tools.orchestrate.mcp_client") as mock_mcp, \
         patch("tools.orchestrate.llm") as mock_llm:
        mock_mcp.call_tool = AsyncMock(side_effect=[MOCK_RADIOLOGY, MOCK_PHARMACY])
        mock_llm.synthesize = AsyncMock(return_value="Unified clinical synthesis narrative.")

        from tools.orchestrate import orchestrate_context_from_sources
        result = await orchestrate_context_from_sources(
            patient_id="test-p1",
            sources=["nara_core", "radiology_mcp", "pharmacy_mcp"],
        )

    assert result["sources_available"] == 3
    assert result["sources_failed"] == []
    assert "core" in result["unified_context"]
    assert "radiology_mcp" in result["unified_context"]
    assert "pharmacy_mcp" in result["unified_context"]


@pytest.mark.asyncio
async def test_orchestrate_graceful_with_unavailable_server():
    async def mock_core(pid, ctx):
        return MOCK_CORE

    unavailable = {"available": False, "error": "server unreachable", "source": "nonexistent_mcp"}

    with patch("tools.orchestrate._get_core_data", side_effect=mock_core), \
         patch("tools.orchestrate.mcp_client") as mock_mcp, \
         patch("tools.orchestrate.llm") as mock_llm:
        mock_mcp.call_tool = AsyncMock(return_value=unavailable)
        mock_llm.synthesize = AsyncMock(return_value="Partial synthesis.")

        from tools.orchestrate import orchestrate_context_from_sources
        result = await orchestrate_context_from_sources(
            patient_id="test-p1",
            sources=["nara_core", "nonexistent_mcp"],
        )

    assert "nonexistent_mcp" in result["sources_failed"]
    assert result["sources_available"] == 1  # only core succeeded
    # Should still return a result (graceful degradation)
    assert result.get("synthesis") is not None


@pytest.mark.asyncio
async def test_orchestrate_synthesis_not_none():
    async def mock_core(pid, ctx):
        return MOCK_CORE

    with patch("tools.orchestrate._get_core_data", side_effect=mock_core), \
         patch("tools.orchestrate.mcp_client") as mock_mcp, \
         patch("tools.orchestrate.llm") as mock_llm:
        mock_mcp.call_tool = AsyncMock(return_value=MOCK_RADIOLOGY)
        mock_llm.synthesize = AsyncMock(return_value="Cross-source synthesis.")

        from tools.orchestrate import orchestrate_context_from_sources
        result = await orchestrate_context_from_sources(
            patient_id="test-p1",
            sources=["nara_core", "radiology_mcp"],
        )

    assert result.get("synthesis") or result.get("content_adapted")


@pytest.mark.asyncio
async def test_orchestrate_evidence_trail_present():
    async def mock_core(pid, ctx):
        return MOCK_CORE

    with patch("tools.orchestrate._get_core_data", side_effect=mock_core), \
         patch("tools.orchestrate.mcp_client") as mock_mcp, \
         patch("tools.orchestrate.llm") as mock_llm:
        mock_mcp.call_tool = AsyncMock(return_value=MOCK_RADIOLOGY)
        mock_llm.synthesize = AsyncMock(return_value="Synthesis with evidence.")

        from tools.orchestrate import orchestrate_context_from_sources
        result = await orchestrate_context_from_sources(
            patient_id="test-p1",
            sources=["nara_core", "radiology_mcp"],
        )

    assert result.get("evidence_trail") is not None
    trail = result["evidence_trail"]
    assert "overall_confidence" in trail
    assert "evidence_items" in trail


@pytest.mark.asyncio
async def test_orchestrate_missing_patient_id_returns_error():
    from tools.orchestrate import orchestrate_context_from_sources
    result = await orchestrate_context_from_sources(
        patient_id="",
        sources=["nara_core"],
    )
    assert result.get("error") == "MISSING_PATIENT_ID"


@pytest.mark.asyncio
async def test_orchestrate_applies_persona():
    async def mock_core(pid, ctx):
        return MOCK_CORE

    class MockCtx:
        class request_context:
            meta = {"sharp_role": "pharmacist", "sharp_patient_id": "test-p1", "sharp_session_id": "s1"}

    with patch("tools.orchestrate._get_core_data", side_effect=mock_core), \
         patch("tools.orchestrate.mcp_client") as mock_mcp, \
         patch("tools.orchestrate.llm") as mock_llm:
        mock_mcp.call_tool = AsyncMock(return_value=MOCK_PHARMACY)
        mock_llm.synthesize = AsyncMock(return_value="Pharmacy-focused synthesis.")
        mock_llm.explain = AsyncMock(return_value="Pharmacist persona output.")

        from tools.orchestrate import orchestrate_context_from_sources
        result = await orchestrate_context_from_sources(
            patient_id="test-p1",
            sources=["nara_core", "pharmacy_mcp"],
            ctx=MockCtx(),
        )

    assert result["persona_applied"] == "pharmacist"


@pytest.mark.asyncio
async def test_orchestrate_includes_sources_queried():
    async def mock_core(pid, ctx):
        return MOCK_CORE

    with patch("tools.orchestrate._get_core_data", side_effect=mock_core), \
         patch("tools.orchestrate.mcp_client") as mock_mcp, \
         patch("tools.orchestrate.llm") as mock_llm:
        mock_mcp.call_tool = AsyncMock(return_value=MOCK_RADIOLOGY)
        mock_llm.synthesize = AsyncMock(return_value="Synthesis.")

        from tools.orchestrate import orchestrate_context_from_sources
        result = await orchestrate_context_from_sources(
            patient_id="test-p1",
            sources=["nara_core", "radiology_mcp"],
        )

    assert "nara_core" in result["sources_queried"]
    assert "radiology_mcp" in result["sources_queried"]


# ─── MCPClient tests ──────────────────────────────────────────────────────────

def test_mcp_client_mock_radiology(monkeypatch):
    monkeypatch.setenv("MOCK_EXTERNAL_MCP", "true")
    from integrations.mcp_client import MCPClient
    import asyncio
    client = MCPClient()
    result = asyncio.get_event_loop().run_until_complete(
        client.call_tool("radiology_mcp", "get_patient_data", {"patient_id": "p1"})
    )
    assert result["available"] is True
    assert "imaging_findings" in result


def test_mcp_client_mock_pharmacy(monkeypatch):
    monkeypatch.setenv("MOCK_EXTERNAL_MCP", "true")
    from integrations.mcp_client import MCPClient
    import asyncio
    client = MCPClient()
    result = asyncio.get_event_loop().run_until_complete(
        client.call_tool("pharmacy_mcp", "get_patient_data", {"patient_id": "p1"})
    )
    assert result["available"] is True
    assert "dispensing_records" in result


def test_mcp_client_unknown_server_returns_unavailable(monkeypatch):
    monkeypatch.setenv("MOCK_EXTERNAL_MCP", "true")
    from integrations.mcp_client import MCPClient
    import asyncio
    client = MCPClient()
    result = asyncio.get_event_loop().run_until_complete(
        client.call_tool("unknown_server", "get_patient_data", {"patient_id": "p1"})
    )
    assert result["available"] is False
