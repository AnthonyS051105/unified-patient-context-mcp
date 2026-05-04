import os
import logging
from typing import Optional

import httpx

from models.medication import InteractionFlag

logger = logging.getLogger(__name__)

OPENFDA_BASE_URL = os.getenv("OPENFDA_BASE_URL", "https://api.fda.gov/drug")
DEFAULT_TIMEOUT = 10.0


class OpenFDAClient:
    def __init__(self, base_url: str = OPENFDA_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True)

    async def _get(self, endpoint: str, params: dict) -> Optional[dict]:
        url = f"{self.base_url}/{endpoint}"
        try:
            response = await self._client.get(url, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            logger.warning("OpenFDA timeout for endpoint %s", endpoint)
            return None
        except httpx.HTTPStatusError as e:
            logger.warning("OpenFDA HTTP %s for %s", e.response.status_code, endpoint)
            return None
        except httpx.RequestError as e:
            logger.warning("OpenFDA request error: %s", e)
            return None

    async def get_drug_info(self, drug_name: str) -> Optional[dict]:
        result = await self._get("label.json", {
            "search": f'openfda.generic_name:"{drug_name}"',
            "limit": 1,
        })
        if result and result.get("results"):
            return result["results"][0]
        result = await self._get("label.json", {
            "search": f'openfda.brand_name:"{drug_name}"',
            "limit": 1,
        })
        if result and result.get("results"):
            return result["results"][0]
        return None

    async def check_interaction(self, drug_a: str, drug_b: str) -> Optional[InteractionFlag]:
        """
        Check for interaction between two drugs using OpenFDA label data.
        Searches warnings and drug_interactions field of drug_a's label for mentions of drug_b.
        """
        drug_info = await self.get_drug_info(drug_a)
        if not drug_info:
            return None

        drug_b_lower = drug_b.lower()
        interaction_text = self._find_interaction_text(drug_info, drug_b_lower)
        if not interaction_text:
            drug_info_b = await self.get_drug_info(drug_b)
            if drug_info_b:
                interaction_text = self._find_interaction_text(drug_info_b, drug_a.lower())

        if not interaction_text:
            return None

        severity = self._estimate_severity(interaction_text)
        return InteractionFlag(
            drug_a=drug_a,
            drug_b=drug_b,
            severity=severity,
            description=interaction_text[:500],
            source="OpenFDA/label",
        )

    def _find_interaction_text(self, drug_info: dict, target_drug: str) -> Optional[str]:
        fields_to_check = [
            "drug_interactions",
            "warnings",
            "warnings_and_cautions",
            "precautions",
            "contraindications",
        ]
        for field in fields_to_check:
            texts = drug_info.get(field, [])
            for text in texts:
                if target_drug in text.lower():
                    return text
        return None

    def _estimate_severity(self, text: str) -> str:
        text_lower = text.lower()
        major_keywords = [
            "contraindicated", "avoid", "do not use", "fatal", "life-threatening",
            "serious", "severe", "hemorrhage", "bleeding",
        ]
        moderate_keywords = [
            "caution", "monitor", "reduce dose", "adjust", "closely",
            "increase", "decrease", "may affect",
        ]
        if any(kw in text_lower for kw in major_keywords):
            return "major"
        if any(kw in text_lower for kw in moderate_keywords):
            return "moderate"
        return "minor"

    async def close(self):
        await self._client.aclose()
