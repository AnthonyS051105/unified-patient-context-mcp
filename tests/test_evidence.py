import pytest
from evidence.scorer import EvidenceScorer, DataSource
from evidence.trail import build_vitals_evidence, build_cross_domain_evidence, build_evidence_trail


@pytest.fixture
def scorer():
    return EvidenceScorer()


def test_high_confidence_complete_recent_data(scorer):
    sources = [
        DataSource("Lab/Creatinine", [1.0, 1.4, 1.8, 2.0, 2.2], recency_hours=6.0, quality="complete"),
        DataSource("Vitals/HR", [80, 85, 90, 88, 92], recency_hours=3.0, quality="complete"),
    ]
    trail = scorer.score(sources)
    assert trail.overall_confidence > 0.8
    assert trail.confidence_label == "high"
    assert trail.recommendation_strength == "strong"


def test_low_confidence_sparse_old_data(scorer):
    sources = [
        DataSource("Lab/Old", [1.0], recency_hours=150.0, quality="estimated"),
    ]
    trail = scorer.score(sources)
    assert trail.overall_confidence < 0.5
    assert trail.confidence_label in ("low", "insufficient")


def test_moderate_confidence_mixed_data(scorer):
    sources = [
        DataSource("Lab/Creatinine", [1.8, 2.0, 2.2], recency_hours=6.0, quality="complete"),
        DataSource("Vitals/UrineOutput", [35, 28], recency_hours=12.0, quality="partial"),
    ]
    trail = scorer.score(sources)
    assert 0.5 <= trail.overall_confidence <= 0.8
    assert trail.confidence_label == "moderate"


def test_empty_sources_returns_insufficient(scorer):
    trail = scorer.score([])
    assert trail.overall_confidence == 0.0
    assert trail.confidence_label == "insufficient"
    assert trail.recommendation_strength == "insufficient"
    assert len(trail.missing_data) > 0


def test_missing_data_detection(scorer):
    # Supply only vitals — egfr, baseline_creatinine etc. should appear in missing_data
    sources = [
        DataSource("Vitals/HeartRate", [80], recency_hours=2.0, quality="complete"),
    ]
    trail = scorer.score(sources)
    gap_names = " ".join(trail.missing_data).lower()
    # At least one standard clinical gap should be detected
    assert any(g in gap_names for g in ["egfr", "baseline creatinine", "urine output"])


def test_transparency_note_not_empty(scorer):
    sources = [
        DataSource("Lab/Creatinine", [1.8], recency_hours=50.0, quality="partial"),
    ]
    trail = scorer.score(sources)
    assert len(trail.transparency_note) > 20


def test_evidence_items_have_correct_structure(scorer):
    sources = [DataSource("Lab/Creatinine", [1.0, 1.5, 1.8], recency_hours=8.0, quality="complete")]
    trail = scorer.score(sources)
    assert len(trail.evidence_items) == 1
    item = trail.evidence_items[0]
    assert item.source == "Lab/Creatinine"
    assert item.data_points == 3
    assert 0.0 <= item.weight <= 1.0
    assert item.quality == "complete"


def test_weight_decreases_with_age(scorer):
    fresh = DataSource("Lab/X", [1.0, 2.0, 3.0], recency_hours=1.0, quality="complete")
    stale = DataSource("Lab/X", [1.0, 2.0, 3.0], recency_hours=120.0, quality="complete")
    fresh_trail = scorer.score([fresh])
    stale_trail = scorer.score([stale])
    assert fresh_trail.overall_confidence > stale_trail.overall_confidence


def test_weight_increases_with_more_data_points(scorer):
    sparse = DataSource("Lab/X", [1.0], recency_hours=6.0, quality="complete")
    rich = DataSource("Lab/X", [1.0, 1.2, 1.4, 1.6, 1.8], recency_hours=6.0, quality="complete")
    sparse_trail = scorer.score([sparse])
    rich_trail = scorer.score([rich])
    assert rich_trail.overall_confidence > sparse_trail.overall_confidence


def test_build_vitals_evidence_with_full_vitals():
    vitals = {
        "heart_rate": 95.0,
        "respiratory_rate": 22.0,
        "oxygen_saturation": 94.0,
        "systolic_bp": 130.0,
        "body_temperature": 37.8,
    }
    trail = build_vitals_evidence(vitals, recency_hours=4.0)
    assert trail.overall_confidence > 0
    assert len(trail.evidence_items) == 5


def test_build_vitals_evidence_empty():
    trail = build_vitals_evidence({}, recency_hours=4.0)
    assert trail is not None
    assert trail.confidence_label in ("low", "insufficient", "moderate")


def test_build_cross_domain_evidence():
    labs = [{"display_name": "Creatinine"}, {"display_name": "BUN"}]
    meds = [{"display_name": "Metformin"}]
    vitals = {"heart_rate": 90.0, "systolic_bp": 125.0}
    trail = build_cross_domain_evidence(labs, meds, vitals)
    assert len(trail.evidence_items) == 3
    source_names = [i.source for i in trail.evidence_items]
    assert "Lab/Results" in source_names
    assert "Medication/Active" in source_names
    assert "Vitals/Signs" in source_names


def test_build_evidence_trail_helper():
    sources = [DataSource("Test/Source", [1, 2, 3], 5.0, "complete")]
    trail = build_evidence_trail(sources)
    assert trail.overall_confidence > 0


def test_quality_ordering(scorer):
    complete = DataSource("Lab/X", [1.0], recency_hours=1.0, quality="complete")
    partial = DataSource("Lab/X", [1.0], recency_hours=1.0, quality="partial")
    estimated = DataSource("Lab/X", [1.0], recency_hours=1.0, quality="estimated")
    c = scorer.score([complete]).overall_confidence
    p = scorer.score([partial]).overall_confidence
    e = scorer.score([estimated]).overall_confidence
    assert c > p > e
