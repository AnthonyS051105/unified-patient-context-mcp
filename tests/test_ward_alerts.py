import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def _make_det_result(news2: int, mews: int = 3, risk: str = "high") -> dict:
    """Build a minimal detect_clinical_deterioration_signals-style result."""
    return {
        "patient_id": "test-patient",
        "news2": {"total_score": news2, "risk_level": risk},
        "mews": {"total_score": mews, "risk_level": risk},
        "triggered_rules": [f"NEWS2 score {news2} — HIGH RISK"],
        "risk_level": risk,
        "vital_signs_count": 5,
        "latest_vitals_timestamp": "2026-05-07T10:00:00Z",
        "latest_vitals": {"heart_rate": 110, "respiratory_rate": 24},
        "evidence_trail": None,
    }


@pytest.mark.asyncio
async def test_scan_empty_ward_returns_no_alerts():
    with patch("tools.ward_alerts.fhir") as mock_fhir:
        mock_fhir.get_patients_by_location = AsyncMock(return_value=[])
        from tools.ward_alerts import scan_ward_alerts
        result = await scan_ward_alerts("EMPTY-WARD", threshold="high")
        assert result["no_alerts_found"] is True
        assert result["patients_scanned"] == 0
        assert result["alerts"] == []


@pytest.mark.asyncio
async def test_scan_returns_prioritized_alerts():
    patients = [
        {"id": "p1", "resourceType": "Patient"},
        {"id": "p2", "resourceType": "Patient"},
        {"id": "p3", "resourceType": "Patient"},
    ]
    det_results = {
        "p1": _make_det_result(news2=9, risk="high"),
        "p2": _make_det_result(news2=4, risk="low-medium"),
        "p3": _make_det_result(news2=7, risk="high"),
    }

    async def mock_assess(patient_id, timeout_sec=5.0):
        return det_results.get(patient_id)

    with patch("tools.ward_alerts.fhir") as mock_fhir, \
         patch("tools.ward_alerts._assess_single_patient", side_effect=mock_assess), \
         patch("tools.ward_alerts.llm") as mock_llm:
        mock_fhir.get_patients_by_location = AsyncMock(return_value=patients)
        mock_llm.explain = AsyncMock(return_value="2 patients need attention.")

        from tools.ward_alerts import scan_ward_alerts
        result = await scan_ward_alerts("TEST-WARD", threshold="high")

    # p2 (NEWS2=4) should be below threshold=high (need >=5)
    assert len(result["alerts"]) == 2
    # Most critical first
    scores = [a["news2_score"] for a in result["alerts"]]
    assert scores[0] >= scores[1]


@pytest.mark.asyncio
async def test_scan_critical_threshold_filters_correctly():
    patients = [{"id": "p1"}, {"id": "p2"}]
    det_results = {
        "p1": _make_det_result(news2=8, risk="high"),   # critical (>=7)
        "p2": _make_det_result(news2=5, risk="medium"),  # high but not critical
    }

    async def mock_assess(patient_id, timeout_sec=5.0):
        return det_results.get(patient_id)

    with patch("tools.ward_alerts.fhir") as mock_fhir, \
         patch("tools.ward_alerts._assess_single_patient", side_effect=mock_assess), \
         patch("tools.ward_alerts.llm") as mock_llm:
        mock_fhir.get_patients_by_location = AsyncMock(return_value=patients)
        mock_llm.explain = AsyncMock(return_value="Critical patient needs attention.")

        from tools.ward_alerts import scan_ward_alerts
        result = await scan_ward_alerts("TEST-WARD", threshold="critical")

    # Only p1 should be in alerts (NEWS2>=7 = critical)
    assert len(result["alerts"]) == 1
    assert result["alerts"][0]["patient_id"] == "p1"


@pytest.mark.asyncio
async def test_each_alert_has_evidence_trail():
    patients = [{"id": "p1"}]
    det_results = {"p1": _make_det_result(news2=7)}

    async def mock_assess(patient_id, timeout_sec=5.0):
        return det_results.get(patient_id)

    with patch("tools.ward_alerts.fhir") as mock_fhir, \
         patch("tools.ward_alerts._assess_single_patient", side_effect=mock_assess), \
         patch("tools.ward_alerts.llm") as mock_llm:
        mock_fhir.get_patients_by_location = AsyncMock(return_value=patients)
        mock_llm.explain = AsyncMock(return_value="Patient needs urgent review.")

        from tools.ward_alerts import scan_ward_alerts
        result = await scan_ward_alerts("TEST-WARD", threshold="medium")

    assert len(result["alerts"]) == 1
    alert = result["alerts"][0]
    assert alert["evidence_trail"] is not None
    assert "overall_confidence" in alert["evidence_trail"]


@pytest.mark.asyncio
async def test_scan_respects_max_patients_limit():
    patients = [{"id": f"p{i}"} for i in range(10)]

    async def mock_assess(patient_id, timeout_sec=5.0):
        return _make_det_result(news2=6)

    with patch("tools.ward_alerts.fhir") as mock_fhir, \
         patch("tools.ward_alerts._assess_single_patient", side_effect=mock_assess), \
         patch("tools.ward_alerts.llm") as mock_llm:
        mock_fhir.get_patients_by_location = AsyncMock(return_value=patients)
        mock_llm.explain = AsyncMock(return_value="Summary.")

        from tools.ward_alerts import scan_ward_alerts
        result = await scan_ward_alerts("TEST-WARD", threshold="medium", max_patients=5)

    # At most 5 patients scanned
    assert result["patients_scanned"] <= 5


@pytest.mark.asyncio
async def test_scan_applies_persona_to_summary():
    patients = [{"id": "p1"}]
    det_results = {"p1": _make_det_result(news2=7)}

    async def mock_assess(patient_id, timeout_sec=5.0):
        return det_results.get(patient_id)

    class MockCtx:
        class request_context:
            meta = {"sharp_role": "nurse", "sharp_patient_id": "p1", "sharp_session_id": "s1"}

    with patch("tools.ward_alerts.fhir") as mock_fhir, \
         patch("tools.ward_alerts._assess_single_patient", side_effect=mock_assess), \
         patch("tools.ward_alerts.llm") as mock_llm:
        mock_fhir.get_patients_by_location = AsyncMock(return_value=patients)
        mock_llm.explain = AsyncMock(return_value="Nurse-friendly summary.")

        from tools.ward_alerts import scan_ward_alerts
        result = await scan_ward_alerts("TEST-WARD", threshold="medium", ctx=MockCtx())

    assert result["persona_applied"] == "nurse"


@pytest.mark.asyncio
async def test_scan_handles_patient_assessment_failure_gracefully():
    patients = [{"id": "p1"}, {"id": "p2"}]

    async def mock_assess(patient_id, timeout_sec=5.0):
        if patient_id == "p1":
            raise Exception("Assessment failed")
        return _make_det_result(news2=7)

    with patch("tools.ward_alerts.fhir") as mock_fhir, \
         patch("tools.ward_alerts._assess_single_patient", side_effect=mock_assess), \
         patch("tools.ward_alerts.llm") as mock_llm:
        mock_fhir.get_patients_by_location = AsyncMock(return_value=patients)
        mock_llm.explain = AsyncMock(return_value="Summary.")

        from tools.ward_alerts import scan_ward_alerts
        # Should not raise even if one patient fails
        result = await scan_ward_alerts("TEST-WARD", threshold="high")

    assert "alerts" in result
    # p2 should still be in results
    assert any(a["patient_id"] == "p2" for a in result["alerts"])


@pytest.mark.asyncio
async def test_scan_demo_ward_uses_known_patients():
    """ICU-A is in DEMO_WARDS and should return synthea-demo-patient."""

    async def mock_assess(patient_id, timeout_sec=5.0):
        return _make_det_result(news2=7)

    with patch("tools.ward_alerts._assess_single_patient", side_effect=mock_assess), \
         patch("tools.ward_alerts.llm") as mock_llm:
        mock_llm.explain = AsyncMock(return_value="ICU summary.")

        from tools.ward_alerts import scan_ward_alerts
        result = await scan_ward_alerts("ICU-A", threshold="medium")

    assert result["ward_id"] == "ICU-A"
    assert result["patients_scanned"] >= 1


def test_news2_to_alert_level_mapping():
    from tools.ward_alerts import _news2_to_alert_level
    assert _news2_to_alert_level(9) == "critical"
    assert _news2_to_alert_level(7) == "critical"
    assert _news2_to_alert_level(6) == "high"
    assert _news2_to_alert_level(5) == "high"
    assert _news2_to_alert_level(4) == "medium"
    assert _news2_to_alert_level(3) == "medium"
    assert _news2_to_alert_level(2) is None


def test_meets_threshold():
    from tools.ward_alerts import _meets_threshold
    assert _meets_threshold("critical", "critical") is True
    assert _meets_threshold("critical", "high") is True
    assert _meets_threshold("critical", "medium") is True
    assert _meets_threshold("high", "critical") is False
    assert _meets_threshold("high", "high") is True
    assert _meets_threshold("medium", "high") is False
