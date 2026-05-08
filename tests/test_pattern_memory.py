"""Tests for Clinical Pattern Memory (Phase 5.5)."""
import pytest
from memory.store import ClinicalPatternMemory
from memory.signature import PatternSignature


@pytest.fixture(autouse=True)
def reset_memory():
    """Reset singleton store before and after each test."""
    memory = ClinicalPatternMemory()
    memory._store.clear()
    yield
    memory._store.clear()


# ── Store tests ──────────────────────────────────────────────────────────────

def test_record_and_query_exact_match():
    memory = ClinicalPatternMemory()
    conditions = ["news2_high_risk", "creatinine_rising_trend"]
    memory.record(conditions, "deterioration")
    result = memory.query_similar(conditions)
    assert result is not None
    assert result.total_observations == 1
    assert result.outcome_counts["deterioration"] == 1


def test_record_accumulates_multiple_observations():
    memory = ClinicalPatternMemory()
    conditions = ["creatinine_rising_trend", "metformin_present"]
    memory.record(conditions, "deterioration")
    memory.record(conditions, "deterioration")
    memory.record(conditions, "stable")
    result = memory.query_similar(conditions)
    assert result.total_observations == 3
    assert result.outcome_counts["deterioration"] == 2
    assert result.outcome_counts["stable"] == 1


def test_query_returns_none_if_no_match():
    memory = ClinicalPatternMemory()
    result = memory.query_similar(["nonexistent_condition_xyz_abc"])
    assert result is None


def test_signature_is_order_independent():
    memory = ClinicalPatternMemory()
    conditions_a = ["creatinine_rising_trend", "metformin_present"]
    conditions_b = ["metformin_present", "creatinine_rising_trend"]
    assert memory._make_signature(conditions_a) == memory._make_signature(conditions_b)


def test_singleton_shared_across_instances():
    memory_a = ClinicalPatternMemory()
    memory_b = ClinicalPatternMemory()
    memory_a.record(["test_condition_singleton"], "outcome_a")
    result = memory_b.query_similar(["test_condition_singleton"])
    assert result is not None
    assert result.total_observations == 1


def test_no_patient_data_in_store():
    memory = ClinicalPatternMemory()
    memory.record(["news2_high_risk", "creatinine_rising_trend"], "deterioration")
    for sig, record in memory._store.items():
        # Signature should be a hex hash — no PII-like strings
        assert "patient" not in sig.lower()
        assert "eleanor" not in sig.lower()
        # Conditions must be generic categories, not raw values
        for condition in record.conditions:
            assert "=" not in condition, f"Raw value found in condition: {condition}"
            assert any(c.isalpha() for c in condition), f"Condition has no letters: {condition}"


def test_get_stats_returns_no_pii():
    memory = ClinicalPatternMemory()
    memory.record(["test_condition_stats"], "test_outcome")
    stats = memory.get_stats()
    assert "total_patterns" in stats
    assert "total_observations" in stats
    assert stats["total_patterns"] == 1
    assert stats["total_observations"] == 1
    assert "patient" not in str(stats).lower()


def test_empty_conditions_list_records_nothing():
    memory = ClinicalPatternMemory()
    sig = memory.record([], "some_outcome")
    assert sig == ""
    assert len(memory._store) == 0


def test_query_empty_conditions_returns_none():
    memory = ClinicalPatternMemory()
    result = memory.query_similar([])
    assert result is None


def test_multiple_outcomes_tracked():
    memory = ClinicalPatternMemory()
    cond = ["active_drug_interaction", "news2_medium_risk"]
    memory.record(cond, "deterioration_medium_risk")
    memory.record(cond, "stable")
    memory.record(cond, "deterioration_medium_risk")
    memory.record(cond, "cross_domain_concern")
    result = memory.query_similar(cond)
    assert result.total_observations == 4
    assert result.outcome_counts["deterioration_medium_risk"] == 2
    assert result.outcome_counts["stable"] == 1
    assert result.outcome_counts["cross_domain_concern"] == 1


# ── PatternSignature tests ────────────────────────────────────────────────────

def test_pattern_signature_from_news2_high_risk():
    sig = PatternSignature()
    conditions = sig.from_news2_result(score=8, triggered_rules=["HR 115 bpm — tachycardia (>110)", "SpO₂ 89% — severe hypoxemia (≤91%)"])
    assert "news2_high_risk" in conditions
    assert "elevated_heart_rate" in conditions
    assert "low_oxygen_saturation" in conditions


def test_pattern_signature_from_news2_medium_risk():
    sig = PatternSignature()
    conditions = sig.from_news2_result(score=5, triggered_rules=["RR 22 /min — tachypnea (>20)"])
    assert "news2_medium_risk" in conditions
    assert "elevated_respiratory_rate" in conditions


def test_pattern_signature_from_news2_low_risk():
    sig = PatternSignature()
    conditions = sig.from_news2_result(score=0, triggered_rules=[])
    assert "news2_low_risk" in conditions


def test_pattern_signature_no_numeric_raw_values():
    sig = PatternSignature()
    conditions = sig.from_news2_result(score=7, triggered_rules=["RR 25 /min — severe tachypnea (≥25)"])
    for condition in conditions:
        assert ">" not in condition, f"Operator found in condition: {condition}"
        assert "=" not in condition, f"Assignment found in condition: {condition}"


def test_pattern_signature_from_synthesis_context_with_labs():
    sig = PatternSignature()
    # Simulate lab dicts (as returned by tools)
    labs = [
        {"display_name": "Creatinine", "trend": {"direction": "rising"}},
        {"display_name": "Hemoglobin", "trend": {"direction": "falling"}},
    ]
    conditions = sig.from_synthesis_context(labs=labs, meds=[], vitals_summary={})
    assert "creatinine_rising_trend" in conditions
    assert "abnormal_hemoglobin" in conditions


def test_pattern_signature_from_synthesis_context_with_meds():
    sig = PatternSignature()
    meds = [
        {"display_name": "Metformin 500mg", "interaction_flags": []},
        {"display_name": "Warfarin 5mg", "interaction_flags": [{"severity": "major"}]},
    ]
    conditions = sig.from_synthesis_context(labs=[], meds=meds, vitals_summary={})
    assert "metformin_present" in conditions
    assert "anticoagulant_present" in conditions
    assert "active_drug_interaction" in conditions


def test_pattern_signature_deduplicates():
    sig = PatternSignature()
    # Both rules normalize to the same label
    conditions = sig.from_news2_result(
        score=7,
        triggered_rules=["HR 115 bpm — tachycardia (>110)", "HR 125 bpm — tachycardia (>110)"],
    )
    # Should not have duplicates
    assert conditions.count("elevated_heart_rate") == 1


# ── Tool integration tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_pattern_insights_not_found_when_empty():
    from tools.pattern_insights import get_pattern_insights
    result = await get_pattern_insights(
        patient_id="test-patient-xyz",
        conditions=["very_rare_condition_xyz_9999"],
    )
    assert result["pattern_found"] is False
    assert result["action_required_by"] == "clinician"
    assert result["data_scope"] == "current_session_only"


@pytest.mark.asyncio
async def test_get_pattern_insights_returns_context_after_recording():
    from memory.store import pattern_memory
    from tools.pattern_insights import get_pattern_insights

    pattern_memory.record(["creatinine_rising_trend", "metformin_present"], "deterioration")
    pattern_memory.record(["creatinine_rising_trend", "metformin_present"], "deterioration")

    result = await get_pattern_insights(
        patient_id="test-patient",
        conditions=["creatinine_rising_trend", "metformin_present"],
    )
    assert result["pattern_found"] is True
    assert result["similar_patterns_seen"] == 2
    assert result["action_required_by"] == "clinician"
    assert result["data_scope"] == "current_session_only"
    assert result["ai_generated"] is True
    assert "session_reset_note" in result


@pytest.mark.asyncio
async def test_get_pattern_insights_confidence_low_below_5():
    from memory.store import pattern_memory
    from tools.pattern_insights import get_pattern_insights

    pattern_memory.record(["news2_high_risk"], "deterioration_high_risk")
    pattern_memory.record(["news2_high_risk"], "stable")

    result = await get_pattern_insights(
        patient_id="test-patient",
        conditions=["news2_high_risk"],
    )
    assert result["pattern_found"] is True
    assert result["confidence"] == "low"  # < 5 observations


@pytest.mark.asyncio
async def test_get_pattern_insights_confidence_moderate_at_5_or_more():
    from memory.store import pattern_memory
    from tools.pattern_insights import get_pattern_insights

    cond = ["elevated_heart_rate", "news2_medium_risk"]
    for _ in range(5):
        pattern_memory.record(cond, "deterioration_medium_risk")

    result = await get_pattern_insights(patient_id="test-patient", conditions=cond)
    assert result["confidence"] == "moderate"


@pytest.mark.asyncio
async def test_get_pattern_insights_empty_conditions_returns_no_match():
    from tools.pattern_insights import get_pattern_insights

    # No conditions passed, no FHIR data (will fail gracefully)
    result = await get_pattern_insights(patient_id="", conditions=[])
    assert result["pattern_found"] is False


@pytest.mark.asyncio
async def test_get_pattern_insights_always_has_disclaimer_fields():
    from memory.store import pattern_memory
    from tools.pattern_insights import get_pattern_insights

    pattern_memory.record(["test_condition_disclaimer"], "outcome")
    result = await get_pattern_insights(
        patient_id="test-patient",
        conditions=["test_condition_disclaimer"],
    )
    assert "session_reset_note" in result
    assert "confidence_note" in result
    assert result["action_required_by"] == "clinician"
    assert "persistent" in result["session_reset_note"].lower()
