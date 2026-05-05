import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sharp.context import SHARPContext


SAMPLE_LABS = {
    "abnormal_labs": [
        {
            "observation_id": "obs-001",
            "display_name": "Creatinine",
            "value": 2.1,
            "unit": "mg/dL",
            "reference_range": "0.6–1.2 mg/dL",
            "interpretation": "H",
            "abnormality_level": "abnormal",
            "effective_date": "2024-01-10",
            "trend": {"direction": "rising", "data_points": 3, "percent_change": 40.0},
        }
    ],
    "total_count": 1,
    "has_critical": False,
    "sharp_metadata": {"sharp_propagated": False},
}

SAMPLE_MEDS = {
    "medications": [
        {
            "medication_id": "med-001",
            "display_name": "Metformin",
            "generic_name": "metformin",
            "status": "active",
            "authored_on": "2024-01-07",
            "interaction_flags": [],
        }
    ],
    "total_interactions_found": 0,
    "sharp_metadata": {"sharp_propagated": False},
}

SAMPLE_DETERIORATION = {
    "news2": {"total_score": 3, "risk_level": "low-medium"},
    "mews": {"total_score": 2, "risk_level": "low-medium"},
    "risk_level": "low-medium",
    "triggered_rules": ["HR 95 bpm — tachycardia (>90)"],
    "vital_signs_count": 8,
    "latest_vitals": {"heart_rate": 95, "systolic_bp": 118},
    "sharp_metadata": {"sharp_propagated": False},
}

SYNTHESIS_JSON = '{"synthesis_narrative": "Test narrative.", "confidence_level": "moderate", "confidence_reasoning": "Some data.", "data_gaps": [], "cross_domain_patterns": ["Creatinine rise correlates with metformin start"]}'


def _patch_sub_calls():
    """Context manager that patches the three sub-modules used by cross_domain_insights."""
    return (
        patch("tools.lab_results.get_recent_abnormal_labs", new_callable=AsyncMock),
        patch("tools.medications.get_medication_timeline", new_callable=AsyncMock),
        patch("tools.deterioration.detect_clinical_deterioration_signals", new_callable=AsyncMock),
    )


class TestCrossDomainInsights:
    @pytest.mark.asyncio
    async def test_returns_disclaimer_always(self):
        from tools.cross_domain_insights import synthesize_cross_domain_insights

        with (
            patch("tools.lab_results.get_recent_abnormal_labs", new_callable=AsyncMock) as mock_labs,
            patch("tools.medications.get_medication_timeline", new_callable=AsyncMock) as mock_meds,
            patch("tools.deterioration.detect_clinical_deterioration_signals", new_callable=AsyncMock) as mock_det,
            patch.object(__import__("tools.cross_domain_insights", fromlist=["llm"]), "llm") as mock_llm,
        ):
            mock_labs.return_value = SAMPLE_LABS
            mock_meds.return_value = SAMPLE_MEDS
            mock_det.return_value = SAMPLE_DETERIORATION
            mock_llm.synthesize = AsyncMock(return_value=SYNTHESIS_JSON)

            result = await synthesize_cross_domain_insights(
                "patient-001",
                "Is the elevated creatinine related to the new medication?",
            )

        assert "disclaimer" in result
        assert result["action_required_by"] == "clinician"
        assert result["ai_generated"] is True

    @pytest.mark.asyncio
    async def test_returns_sharp_metadata(self):
        from tools.cross_domain_insights import synthesize_cross_domain_insights
        import tools.cross_domain_insights as _mod

        with (
            patch("tools.lab_results.get_recent_abnormal_labs", new_callable=AsyncMock) as mock_labs,
            patch("tools.medications.get_medication_timeline", new_callable=AsyncMock) as mock_meds,
            patch("tools.deterioration.detect_clinical_deterioration_signals", new_callable=AsyncMock) as mock_det,
            patch.object(_mod, "llm") as mock_llm,
        ):
            mock_labs.return_value = SAMPLE_LABS
            mock_meds.return_value = SAMPLE_MEDS
            mock_det.return_value = SAMPLE_DETERIORATION
            mock_llm.synthesize = AsyncMock(return_value=SYNTHESIS_JSON)

            result = await synthesize_cross_domain_insights("patient-001", "Is patient safe for discharge?")

        assert "sharp_metadata" in result
        assert result["sharp_metadata"]["sharp_propagated"] is False

    @pytest.mark.asyncio
    async def test_supporting_data_counts(self):
        from tools.cross_domain_insights import synthesize_cross_domain_insights
        import tools.cross_domain_insights as _mod

        with (
            patch("tools.lab_results.get_recent_abnormal_labs", new_callable=AsyncMock) as mock_labs,
            patch("tools.medications.get_medication_timeline", new_callable=AsyncMock) as mock_meds,
            patch("tools.deterioration.detect_clinical_deterioration_signals", new_callable=AsyncMock) as mock_det,
            patch.object(_mod, "llm") as mock_llm,
        ):
            mock_labs.return_value = SAMPLE_LABS
            mock_meds.return_value = SAMPLE_MEDS
            mock_det.return_value = SAMPLE_DETERIORATION
            mock_llm.synthesize = AsyncMock(return_value=SYNTHESIS_JSON)

            result = await synthesize_cross_domain_insights("patient-001", "What is driving the elevated creatinine?")

        sd = result["supporting_data"]
        assert sd["labs_referenced"] == 1
        assert sd["medications_referenced"] == 1
        assert sd["vitals_referenced"] == 8

    @pytest.mark.asyncio
    async def test_missing_patient_id_returns_error(self):
        from tools.cross_domain_insights import synthesize_cross_domain_insights
        result = await synthesize_cross_domain_insights("", "Any question?")
        assert result.get("error") == "MISSING_PATIENT_ID"

    @pytest.mark.asyncio
    async def test_missing_clinical_question_returns_error(self):
        from tools.cross_domain_insights import synthesize_cross_domain_insights
        result = await synthesize_cross_domain_insights("patient-001", "")
        assert result.get("error") == "MISSING_CLINICAL_QUESTION"

    @pytest.mark.asyncio
    async def test_sub_call_failure_graceful(self):
        from tools.cross_domain_insights import synthesize_cross_domain_insights
        import tools.cross_domain_insights as _mod

        with (
            patch("tools.lab_results.get_recent_abnormal_labs", new_callable=AsyncMock) as mock_labs,
            patch("tools.medications.get_medication_timeline", new_callable=AsyncMock) as mock_meds,
            patch("tools.deterioration.detect_clinical_deterioration_signals", new_callable=AsyncMock) as mock_det,
            patch.object(_mod, "llm") as mock_llm,
        ):
            mock_labs.return_value = {"error": "FHIR_ERROR", "message": "timeout"}
            mock_meds.return_value = SAMPLE_MEDS
            mock_det.return_value = SAMPLE_DETERIORATION
            mock_llm.synthesize = AsyncMock(
                return_value='{"synthesis_narrative": "Test.", "confidence_level": "low", '
                             '"confidence_reasoning": ".", "data_gaps": [], "cross_domain_patterns": []}'
            )

            result = await synthesize_cross_domain_insights("patient-001", "Is patient safe for discharge?")

        assert result.get("error") is None
        assert "Lab results unavailable" in result.get("data_gaps", [])

    @pytest.mark.asyncio
    async def test_cross_domain_patterns_in_response(self):
        from tools.cross_domain_insights import synthesize_cross_domain_insights
        import tools.cross_domain_insights as _mod

        with (
            patch("tools.lab_results.get_recent_abnormal_labs", new_callable=AsyncMock) as mock_labs,
            patch("tools.medications.get_medication_timeline", new_callable=AsyncMock) as mock_meds,
            patch("tools.deterioration.detect_clinical_deterioration_signals", new_callable=AsyncMock) as mock_det,
            patch.object(_mod, "llm") as mock_llm,
        ):
            mock_labs.return_value = SAMPLE_LABS
            mock_meds.return_value = SAMPLE_MEDS
            mock_det.return_value = SAMPLE_DETERIORATION
            mock_llm.synthesize = AsyncMock(return_value=SYNTHESIS_JSON)

            result = await synthesize_cross_domain_insights("patient-001", "Should we be concerned about the heart rate trend?")

        assert "cross_domain_patterns" in result
        assert isinstance(result["cross_domain_patterns"], list)


class TestPromptFormatters:
    def test_format_labs_empty(self):
        from tools.cross_domain_insights import _format_labs_for_prompt
        assert "No recent abnormal labs" in _format_labs_for_prompt([])

    def test_format_labs_with_data(self):
        from tools.cross_domain_insights import _format_labs_for_prompt
        labs = [{"display_name": "Creatinine", "value": 2.1, "unit": "mg/dL",
                 "reference_range": "0.6–1.2", "abnormality_level": "abnormal",
                 "trend": {"direction": "rising"}}]
        text = _format_labs_for_prompt(labs)
        assert "Creatinine" in text
        assert "rising" in text

    def test_format_meds_empty(self):
        from tools.cross_domain_insights import _format_meds_for_prompt
        assert "No recent medications" in _format_meds_for_prompt([])

    def test_format_vitals_with_deterioration(self):
        from tools.cross_domain_insights import _format_vitals_for_prompt
        text = _format_vitals_for_prompt(SAMPLE_DETERIORATION)
        assert "NEWS2" in text
        assert "low-medium" in text
