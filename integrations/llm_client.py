import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 200
DEFAULT_TIMEOUT = 15.0


class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

    async def explain(self, prompt: str, max_tokens: int = MAX_TOKENS) -> Optional[str]:
        if not self._api_key:
            logger.warning("ANTHROPIC_API_KEY not set — skipping LLM explanation")
            return None
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    ANTHROPIC_API_URL,
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": MODEL,
                        "max_tokens": max_tokens,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["content"][0]["text"]
        except httpx.TimeoutException:
            logger.warning("LLM request timed out")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning("LLM returned HTTP %s", e.response.status_code)
            return None
        except Exception as e:
            logger.warning("LLM error: %s", e)
            return None

    async def patient_summary(self, name: str, conditions: list[str], medications_count: int) -> Optional[str]:
        cond_text = ", ".join(conditions[:5]) if conditions else "no recorded conditions"
        prompt = (
            f"Write a single concise sentence (max 30 words) summarizing this patient's clinical status "
            f"for a healthcare professional. Do not diagnose or prescribe. "
            f"Patient: {name}. Active conditions: {cond_text}. Active medications: {medications_count}."
        )
        return await self.explain(prompt, max_tokens=80)

    async def prioritize_problems(self, conditions: list[str]) -> Optional[str]:
        if not conditions:
            return None
        cond_text = "\n".join(f"- {c}" for c in conditions[:10])
        prompt = (
            f"You are assisting a clinician. Rate the following conditions by clinical urgency (1=low, 5=critical). "
            f"Respond ONLY as JSON list: [{{'condition': '...', 'urgency': N, 'reason': '...'}}]. "
            f"Do not diagnose. Conditions:\n{cond_text}"
        )
        return await self.explain(prompt, max_tokens=400)

    async def explain_interaction(self, drug_a: str, drug_b: str, description: str) -> Optional[str]:
        prompt = (
            f"Explain in 1-2 plain sentences for a clinician (not a patient) why the interaction between "
            f"'{drug_a}' and '{drug_b}' is clinically important. "
            f"Base your answer only on this information: {description[:300]}. "
            f"Do not diagnose or prescribe."
        )
        return await self.explain(prompt, max_tokens=120)

    async def explain_abnormal_lab(self, lab_name: str, value: str, reference: str, trend: str) -> Optional[str]:
        prompt = (
            f"In 1-2 plain sentences, explain the clinical significance of an abnormal lab result for a clinician. "
            f"Lab: {lab_name}. Value: {value}. Reference range: {reference}. Trend: {trend}. "
            f"Do not diagnose. State only what this finding may indicate and why monitoring matters."
        )
        return await self.explain(prompt, max_tokens=120)

    async def explain_deterioration(
        self,
        news2_score: int,
        mews_score: int,
        risk_level: str,
        triggered_rules: list[str],
    ) -> Optional[str]:
        rules_text = "; ".join(triggered_rules) if triggered_rules else "no specific rules triggered"
        prompt = (
            f"A rule-based clinical scoring system has flagged the following findings for clinician review. "
            f"NEWS2 score: {news2_score} ({risk_level} risk). MEWS score: {mews_score}. "
            f"Triggered rules: {rules_text}. "
            f"Write 2-3 plain sentences explaining what these findings mean to a clinician. "
            f"Do NOT diagnose, predict, or prescribe. Use language like 'may indicate' or 'warrants attention'. "
            f"End with: 'Clinical assessment required.'"
        )
        return await self.explain(prompt, max_tokens=180)

    async def explain_context_delta(self, patient_name: str, hours: int, changes: dict) -> Optional[str]:
        parts = []
        if changes.get("new_labs"):
            parts.append(f"{len(changes['new_labs'])} new lab result(s)")
        if changes.get("changed_medications"):
            parts.append(f"{len(changes['changed_medications'])} medication change(s)")
        if changes.get("new_vitals"):
            parts.append(f"{len(changes['new_vitals'])} new vital sign(s)")
        if changes.get("new_conditions"):
            parts.append(f"{len(changes['new_conditions'])} new condition(s)")

        if not parts:
            return f"In the last {hours} hours, no clinical changes were recorded for this patient."

        changes_text = ", ".join(parts)
        prompt = (
            f"Summarize the following clinical changes for patient {patient_name} in the last {hours} hours, "
            f"in 1-2 plain sentences for a clinician: {changes_text}. "
            f"Start with 'In the last {hours} hours, ...'. Do not diagnose."
        )
        return await self.explain(prompt, max_tokens=100)
