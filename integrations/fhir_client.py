import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "https://hapi.fhir.org/baseR4")

DEFAULT_TIMEOUT = 15.0
DEFAULT_PAGE_SIZE = 50

HEADERS = {
    "Accept": "application/fhir+json",
    "Content-Type": "application/fhir+json",
}


class FHIRError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, retry_suggested: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retry_suggested = retry_suggested

    def to_dict(self) -> dict:
        return {
            "error": "FHIR_ERROR",
            "message": str(self),
            "suggestion": "Check FHIR server availability or retry." if self.retry_suggested else None,
            "retry_suggested": self.retry_suggested,
        }


class FHIRClient:
    def __init__(self, base_url: str = FHIR_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers=HEADERS,
            follow_redirects=True,
        )

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise FHIRError(
                f"FHIR server timed out after {DEFAULT_TIMEOUT}s",
                retry_suggested=True,
            )
        except httpx.HTTPStatusError as e:
            raise FHIRError(
                f"FHIR returned HTTP {e.response.status_code}",
                status_code=e.response.status_code,
                retry_suggested=e.response.status_code >= 500,
            )
        except httpx.RequestError as e:
            raise FHIRError(str(e), retry_suggested=True)

    def _extract_entries(self, bundle: dict) -> list[dict]:
        return [entry["resource"] for entry in bundle.get("entry", []) if "resource" in entry]

    def _date_cutoff(self, days: int) -> str:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _hours_cutoff(self, hours: int) -> str:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    async def get_patient(self, patient_id: str) -> dict:
        return await self._get(f"Patient/{patient_id}")

    async def get_conditions(self, patient_id: str, status: str = "active") -> list[dict]:
        params: dict[str, Any] = {
            "patient": patient_id,
            "_count": DEFAULT_PAGE_SIZE,
        }
        if status:
            params["clinical-status"] = status
        bundle = await self._get("Condition", params)
        return self._extract_entries(bundle)

    async def get_medications(self, patient_id: str, days: int = 90) -> list[dict]:
        bundle = await self._get("MedicationRequest", {
            "patient": patient_id,
            "_count": DEFAULT_PAGE_SIZE,
            "_sort": "-authoredon",
        })
        entries = self._extract_entries(bundle)
        # Filter client-side: HAPI public server doesn't reliably support authoredon date param
        if days:
            cutoff_dt = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_str = cutoff_dt.strftime("%Y-%m-%d")
            entries = [
                e for e in entries
                if e.get("authoredOn", "9999-12-31")[:10] >= cutoff_str
            ]
        return entries

    async def get_observations(
        self,
        patient_id: str,
        category: str,
        days: Optional[int] = None,
        hours: Optional[int] = None,
    ) -> list[dict]:
        params: dict[str, Any] = {
            "patient": patient_id,
            "category": category,
            "_count": DEFAULT_PAGE_SIZE,
            "_sort": "-date",
        }
        if hours is not None:
            params["date"] = f"gt{self._hours_cutoff(hours)}"
        elif days is not None:
            params["date"] = f"gt{self._date_cutoff(days)}"

        bundle = await self._get("Observation", params)
        return self._extract_entries(bundle)

    async def get_allergies(self, patient_id: str) -> list[dict]:
        bundle = await self._get("AllergyIntolerance", {
            "patient": patient_id,
            "_count": DEFAULT_PAGE_SIZE,
        })
        return self._extract_entries(bundle)

    async def get_all_since(self, patient_id: str, hours: int) -> dict[str, list[dict]]:
        cutoff = self._hours_cutoff(hours)
        last_updated_filter = f"gt{cutoff}"

        async def fetch(resource: str, extra: dict) -> list[dict]:
            params = {
                "patient": patient_id,
                "_lastUpdated": last_updated_filter,
                "_count": DEFAULT_PAGE_SIZE,
                **extra,
            }
            try:
                bundle = await self._get(resource, params)
                return self._extract_entries(bundle)
            except FHIRError:
                logger.warning("Failed to fetch %s for [PATIENT_REDACTED]", resource)
                return []

        import asyncio
        labs, vitals, meds, conditions = await asyncio.gather(
            fetch("Observation", {"category": "laboratory"}),
            fetch("Observation", {"category": "vital-signs"}),
            fetch("MedicationRequest", {}),
            fetch("Condition", {}),
        )
        return {
            "labs": labs,
            "vitals": vitals,
            "medications": meds,
            "conditions": conditions,
        }

    async def close(self):
        await self._client.aclose()
