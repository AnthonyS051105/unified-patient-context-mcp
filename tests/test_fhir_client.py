import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.fhir_client import FHIRClient, FHIRError


SAMPLE_PATIENT = {
    "resourceType": "Patient",
    "id": "test-patient-001",
    "name": [{"use": "official", "family": "Doe", "given": ["John"]}],
    "birthDate": "1980-01-15",
    "gender": "male",
}

SAMPLE_BUNDLE = {
    "resourceType": "Bundle",
    "total": 1,
    "entry": [{"resource": SAMPLE_PATIENT}],
}

EMPTY_BUNDLE = {
    "resourceType": "Bundle",
    "total": 0,
    "entry": [],
}


@pytest.fixture
def fhir_client():
    return FHIRClient(base_url="https://mock-fhir.test/baseR4")


class TestFHIRClientParsing:
    def test_extract_entries_normal(self, fhir_client):
        entries = fhir_client._extract_entries(SAMPLE_BUNDLE)
        assert len(entries) == 1
        assert entries[0]["id"] == "test-patient-001"

    def test_extract_entries_empty(self, fhir_client):
        entries = fhir_client._extract_entries(EMPTY_BUNDLE)
        assert entries == []

    def test_extract_entries_missing_resource(self, fhir_client):
        bundle = {"entry": [{"fullUrl": "http://foo"}]}
        entries = fhir_client._extract_entries(bundle)
        assert entries == []

    def test_date_cutoff_format(self, fhir_client):
        cutoff = fhir_client._date_cutoff(30)
        assert "T" in cutoff
        assert cutoff.endswith("Z")

    def test_hours_cutoff_format(self, fhir_client):
        cutoff = fhir_client._hours_cutoff(72)
        assert "T" in cutoff
        assert cutoff.endswith("Z")


class TestFHIRClientHTTP:
    @pytest.mark.asyncio
    async def test_get_patient_success(self, fhir_client):
        mock_response = MagicMock()
        mock_response.json.return_value = SAMPLE_PATIENT
        mock_response.raise_for_status = MagicMock()

        with patch.object(fhir_client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await fhir_client.get_patient("test-patient-001")
            assert result["id"] == "test-patient-001"

    @pytest.mark.asyncio
    async def test_get_patient_timeout_raises_fhir_error(self, fhir_client):
        with patch.object(fhir_client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("timeout")
            with pytest.raises(FHIRError) as exc_info:
                await fhir_client.get_patient("test-patient-001")
            assert exc_info.value.retry_suggested is True

    @pytest.mark.asyncio
    async def test_get_conditions_returns_list(self, fhir_client):
        condition = {
            "resourceType": "Condition",
            "id": "cond-001",
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "code": {"text": "Hypertension"},
        }
        bundle = {"resourceType": "Bundle", "entry": [{"resource": condition}]}
        mock_response = MagicMock()
        mock_response.json.return_value = bundle
        mock_response.raise_for_status = MagicMock()

        with patch.object(fhir_client._client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await fhir_client.get_conditions("test-patient-001")
            assert len(result) == 1
            assert result[0]["id"] == "cond-001"

    @pytest.mark.asyncio
    async def test_fhir_error_to_dict(self, fhir_client):
        err = FHIRError("Server error", status_code=500, retry_suggested=True)
        d = err.to_dict()
        assert d["retry_suggested"] is True
        assert "message" in d
