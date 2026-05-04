import pytest
from unittest.mock import AsyncMock, patch

from engine.deduplicator import deduplicate_medications


class TestDeduplicator:
    def test_no_duplicates(self):
        meds = [
            {"medication_id": "1", "display_name": "Metformin"},
            {"medication_id": "2", "display_name": "Lisinopril"},
        ]
        result = deduplicate_medications(meds)
        assert len(result) == 2
        assert all(not r["is_duplicate_merged"] for r in result)

    def test_brand_generic_merged(self):
        meds = [
            {"medication_id": "1", "display_name": "Glucophage"},
            {"medication_id": "2", "display_name": "Metformin"},
        ]
        result = deduplicate_medications(meds)
        assert len(result) == 1
        assert result[0]["is_duplicate_merged"] is True

    def test_lipitor_to_atorvastatin(self):
        meds = [
            {"medication_id": "1", "display_name": "Lipitor"},
            {"medication_id": "2", "display_name": "Atorvastatin"},
        ]
        result = deduplicate_medications(meds)
        assert len(result) == 1
        assert result[0]["generic_name"] == "atorvastatin"

    def test_empty_list(self):
        assert deduplicate_medications([]) == []

    def test_unknown_drugs_not_merged(self):
        meds = [
            {"medication_id": "1", "display_name": "DrugA"},
            {"medication_id": "2", "display_name": "DrugB"},
        ]
        result = deduplicate_medications(meds)
        assert len(result) == 2


class TestPatientSnapshotParsing:
    def test_name_parsing(self):
        from tools.patient_snapshot import _parse_name
        resource = {
            "name": [
                {"use": "official", "family": "Smith", "given": ["John", "Paul"]}
            ]
        }
        assert _parse_name(resource) == "John Paul Smith"

    def test_name_fallback(self):
        from tools.patient_snapshot import _parse_name
        assert _parse_name({}) == "Unknown"

    def test_age_calculation(self):
        from tools.patient_snapshot import _calc_age
        age = _calc_age("1990-01-01")
        assert isinstance(age, int)
        assert 30 < age < 50

    def test_parse_condition(self):
        from tools.patient_snapshot import _parse_condition
        resource = {
            "id": "c001",
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "code": {
                "coding": [{"code": "I10", "system": "http://hl7.org/fhir/sid/icd-10", "display": "Hypertension"}],
                "text": "Essential Hypertension",
            },
            "onsetDateTime": "2020-03-01",
        }
        cond = _parse_condition(resource)
        assert cond.display == "Essential Hypertension"
        assert cond.clinical_status == "active"
        assert cond.code == "I10"

    def test_parse_allergy(self):
        from tools.patient_snapshot import _parse_allergy
        resource = {
            "id": "a001",
            "code": {"coding": [{"display": "Penicillin"}]},
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "reaction": [{"manifestation": [{"coding": [{"display": "Rash"}]}], "severity": "moderate"}],
        }
        allergy = _parse_allergy(resource)
        assert allergy.substance == "Penicillin"
        assert allergy.severity == "moderate"


class TestLabResultsParsing:
    def test_abnormality_classification_critical(self):
        from tools.lab_results import _classify_abnormality
        obs = {"interpretation": "HH", "value": 200, "reference_low": 70, "reference_high": 100}
        assert _classify_abnormality(obs) == "critical"

    def test_abnormality_classification_borderline(self):
        from tools.lab_results import _classify_abnormality
        obs = {"interpretation": None, "value": 105, "reference_low": 70, "reference_high": 100}
        assert _classify_abnormality(obs) == "borderline"

    def test_trend_rising(self):
        from tools.lab_results import _compute_trend
        obs = [
            {"value": 5.0, "effective_date": "2024-01-01"},
            {"value": 8.0, "effective_date": "2024-01-02"},
        ]
        trend = _compute_trend(obs)
        assert trend.direction == "rising"

    def test_trend_falling(self):
        from tools.lab_results import _compute_trend
        obs = [
            {"value": 10.0, "effective_date": "2024-01-01"},
            {"value": 6.0, "effective_date": "2024-01-02"},
        ]
        trend = _compute_trend(obs)
        assert trend.direction == "falling"

    def test_trend_insufficient_data(self):
        from tools.lab_results import _compute_trend
        obs = [{"value": 5.0, "effective_date": "2024-01-01"}]
        trend = _compute_trend(obs)
        assert trend.direction == "insufficient_data"
