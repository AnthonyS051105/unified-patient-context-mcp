import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Google Gemini via AI Studio — 1500 req/day free tier
# Get API key: https://aistudio.google.com/apikey
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

DEFAULT_TIMEOUT = 20.0


class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")

    async def explain(self, prompt: str, max_tokens: int = 200) -> Optional[str]:
        if not self._api_key:
            logger.warning("GEMINI_API_KEY not set — skipping LLM explanation")
            return None
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    GEMINI_API_URL,
                    params={"key": self._api_key},
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "maxOutputTokens": max(max_tokens, 100),
                            "temperature": 0.2,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except httpx.TimeoutException:
            logger.warning("Gemini request timed out")
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Gemini rate limit hit — skipping LLM explanation")
            else:
                logger.warning("Gemini returned HTTP %s", e.response.status_code)
            return None
        except (KeyError, IndexError) as e:
            logger.warning("Gemini response parse error: %s", e)
            return None
        except Exception as e:
            logger.warning("Gemini error: %s", e)
            return None

    async def synthesize(self, prompt: str) -> Optional[str]:
        """For Tool 7 — larger context, longer response, JSON output."""
        return await self.explain(prompt, max_tokens=600)

    async def patient_summary(
        self, name: str, conditions: list[str], medications_count: int
    ) -> Optional[str]:
        cond_text = ", ".join(conditions[:5]) if conditions else "no recorded conditions"
        prompt = (
            f"Write a single concise sentence (max 30 words) summarizing this patient's clinical status "
            f"for a healthcare professional. Do not diagnose or prescribe. "
            f"Patient: {name}. Active conditions: {cond_text}. Active medications: {medications_count}."
        )
        return await self.explain(prompt, max_tokens=80)

    async def prioritize_problems(
        self, conditions: list[str], role_hint: str = ""
    ) -> Optional[str]:
        if not conditions:
            return None
        cond_text = "\n".join(f"- {c}" for c in conditions[:10])
        prompt = (
            f"You are assisting a clinician. Rate the following conditions by clinical urgency "
            f"(1=low, 5=critical).{role_hint} "
            f"Respond ONLY as JSON list: "
            f'[{{"condition": "...", "urgency": N, "reason": "..."}}]. '
            f"Do not diagnose. Conditions:\n{cond_text}"
        )
        return await self.explain(prompt, max_tokens=400)

    async def explain_interaction(
        self,
        drug_a: str,
        drug_b: str,
        description: str,
        detailed: bool = False,
    ) -> Optional[str]:
        detail_str = (
            "Provide a detailed pharmacist-level explanation including mechanism and clinical management."
            if detailed
            else "Explain in 1-2 plain sentences for a clinician."
        )
        prompt = (
            f"{detail_str} Why is the interaction between '{drug_a}' and '{drug_b}' clinically important? "
            f"Base your answer only on: {description[:300]}. Do not diagnose or prescribe."
        )
        return await self.explain(prompt, max_tokens=150 if detailed else 120)

    async def explain_abnormal_lab(
        self, lab_name: str, value: str, reference: str, trend: str
    ) -> Optional[str]:
        prompt = (
            f"In 1-2 plain sentences, explain the clinical significance of an abnormal lab result "
            f"for a clinician. Lab: {lab_name}. Value: {value}. Reference range: {reference}. "
            f"Trend: {trend}. Do not diagnose. State only what this finding may indicate and why monitoring matters."
        )
        return await self.explain(prompt, max_tokens=120)

    async def explain_deterioration(
        self,
        news2_score: int,
        mews_score: int,
        risk_level: str,
        triggered_rules: list[str],
        role: str = "clinician",
    ) -> Optional[str]:
        rules_text = "; ".join(triggered_rules) if triggered_rules else "no specific rules triggered"
        role_instruction = (
            "Use actionable language suitable for a nurse (what to watch for, what to report)."
            if role.lower() == "nurse"
            else "Use clinical terminology appropriate for a physician or clinician."
        )
        prompt = (
            f"A rule-based clinical scoring system has flagged these findings for clinician review. "
            f"NEWS2 score: {news2_score} ({risk_level} risk). MEWS score: {mews_score}. "
            f"Triggered rules: {rules_text}. "
            f"{role_instruction} "
            f"Write 2-3 plain sentences explaining what these findings mean. "
            f"Do NOT diagnose, predict, or prescribe. Use language like 'may indicate' or 'warrants attention'. "
            f"End with: 'Clinical assessment required.'"
        )
        return await self.explain(prompt, max_tokens=180)

    async def explain_context_delta(
        self, patient_name: str, hours: int, changes: dict
    ) -> Optional[str]:
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
            f"Summarize the following clinical changes in the last {hours} hours in 1-2 plain sentences "
            f"for a clinician: {changes_text}. "
            f"Start with 'In the last {hours} hours, ...'. Do not diagnose."
        )
        return await self.explain(prompt, max_tokens=100)
