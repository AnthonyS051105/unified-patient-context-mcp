import pytest
from unittest.mock import AsyncMock, MagicMock
from persona.profiles import RoleProfile, RoleConfig
from persona.adapter import PersonaAdapter
from persona.prompts import PERSONA_PROMPTS


# ─── RoleProfile tests ────────────────────────────────────────────────────────

def test_all_four_roles_defined():
    for role in ("physician", "nurse", "pharmacist", "patient"):
        profile = RoleProfile.get(role)
        assert isinstance(profile, RoleConfig)


def test_physician_has_no_max_length():
    profile = RoleProfile.get("physician")
    assert profile.max_length is None
    assert profile.format == "narrative"
    assert profile.depth == "full"


def test_nurse_has_limited_length():
    profile = RoleProfile.get("nurse")
    assert profile.max_length == 300
    assert profile.format == "bullets"


def test_pharmacist_is_medication_focused():
    profile = RoleProfile.get("pharmacist")
    assert profile.depth == "medication-focused"
    assert "drug_interactions" in profile.priority_fields


def test_patient_is_simplified():
    profile = RoleProfile.get("patient")
    assert profile.terminology == "plain"
    assert profile.depth == "simplified"
    assert profile.format == "simple"


def test_unknown_role_defaults_to_physician():
    profile = RoleProfile.get("unknown_role")
    physician = RoleProfile.get("physician")
    assert profile.format == physician.format
    assert profile.depth == physician.depth


def test_none_role_defaults_to_physician():
    profile = RoleProfile.get(None)
    physician = RoleProfile.get("physician")
    assert profile.format == physician.format


def test_case_insensitive_role_lookup():
    profile_upper = RoleProfile.get("NURSE")
    profile_lower = RoleProfile.get("nurse")
    assert profile_upper.format == profile_lower.format


# ─── PERSONA_PROMPTS tests ────────────────────────────────────────────────────

def test_all_four_prompts_exist():
    for role in ("physician", "nurse", "pharmacist", "patient"):
        assert role in PERSONA_PROMPTS
        assert "{data}" in PERSONA_PROMPTS[role]


def test_nurse_prompt_mentions_escalate():
    assert "ESCALATE" in PERSONA_PROMPTS["nurse"]


def test_pharmacist_prompt_mentions_interactions():
    assert "interaction" in PERSONA_PROMPTS["pharmacist"].lower()


def test_patient_prompt_mentions_reading_level():
    assert "grade" in PERSONA_PROMPTS["patient"].lower()


# ─── PersonaAdapter tests ─────────────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.explain = AsyncMock(return_value="Adapted content from LLM.")
    return llm


@pytest.fixture
def adapter(mock_llm):
    return PersonaAdapter(mock_llm)


@pytest.mark.asyncio
async def test_adapt_adds_persona_applied(adapter):
    result = await adapter.adapt({"patient_id": "p1", "data": "some data"}, role="nurse")
    assert result["persona_applied"] == "nurse"


@pytest.mark.asyncio
async def test_adapt_adds_content_adapted(adapter, mock_llm):
    result = await adapter.adapt({"patient_id": "p1"}, role="physician")
    assert result["content_adapted"] == "Adapted content from LLM."


@pytest.mark.asyncio
async def test_adapt_sets_original_available_true(adapter):
    result = await adapter.adapt({"x": 1}, role="nurse")
    assert result["original_available"] is True


@pytest.mark.asyncio
async def test_adapt_preserves_original_fields(adapter):
    raw = {"patient_id": "p1", "risk_level": "high"}
    result = await adapter.adapt(raw, role="nurse")
    assert result["patient_id"] == "p1"
    assert result["risk_level"] == "high"


@pytest.mark.asyncio
async def test_unknown_role_defaults_to_physician_in_adapter(adapter):
    result = await adapter.adapt({"x": 1}, role="superhero")
    assert result["persona_applied"] == "physician"


@pytest.mark.asyncio
async def test_none_role_defaults_to_physician_in_adapter(adapter):
    result = await adapter.adapt({"x": 1}, role=None)
    assert result["persona_applied"] == "physician"


@pytest.mark.asyncio
async def test_persona_format_matches_role(adapter):
    nurse_result = await adapter.adapt({"x": 1}, role="nurse")
    assert nurse_result["persona_format"] == "bullets"

    pharmacist_result = await adapter.adapt({"x": 1}, role="pharmacist")
    assert pharmacist_result["persona_format"] == "structured"

    patient_result = await adapter.adapt({"x": 1}, role="patient")
    assert patient_result["persona_format"] == "simple"


@pytest.mark.asyncio
async def test_persona_depth_matches_role(adapter):
    result = await adapter.adapt({"x": 1}, role="pharmacist")
    assert result["persona_depth"] == "medication-focused"


@pytest.mark.asyncio
async def test_adapt_strips_sharp_metadata_from_prompt(adapter, mock_llm):
    raw = {
        "patient_id": "p1",
        "sharp_metadata": {"session_id": "secret-123"},
        "clinical_data": "important",
    }
    await adapter.adapt(raw, role="nurse")
    # LLM should have been called; grab the prompt passed to it
    call_args = mock_llm.explain.call_args
    prompt_arg = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
    assert "secret-123" not in prompt_arg


def test_sync_fallback_returns_persona_without_llm_call():
    llm = MagicMock()
    adapter = PersonaAdapter(llm)
    result = adapter.adapt_sync_fallback({"patient_id": "p1"}, role="nurse")
    assert result["persona_applied"] == "nurse"
    assert result["content_adapted"] is None
    llm.explain.assert_not_called()
