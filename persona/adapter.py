import json
import logging
from typing import Optional

from persona.profiles import RoleProfile
from persona.prompts import PERSONA_PROMPTS

logger = logging.getLogger(__name__)


class PersonaAdapter:
    def __init__(self, llm_client):
        self.llm = llm_client

    async def adapt(self, raw_output: dict, role: Optional[str]) -> dict:
        """
        Transform raw tool output for the given clinical role.
        Returns the original output enriched with persona-adapted content.
        """
        effective_role = (role or "").lower()
        if effective_role not in RoleProfile.PROFILES:
            effective_role = "physician"

        profile = RoleProfile.get(effective_role)
        prompt_template = PERSONA_PROMPTS.get(effective_role, PERSONA_PROMPTS["physician"])

        # Serialize relevant data for the prompt — strip sharp_metadata and evidence internals
        data_for_prompt = {
            k: v for k, v in raw_output.items()
            if k not in ("sharp_metadata", "disclaimer", "evidence_trail")
        }
        try:
            data_str = json.dumps(data_for_prompt, indent=2, default=str)[:3000]
        except Exception:
            data_str = str(data_for_prompt)[:3000]

        prompt = prompt_template.format(data=data_str)
        max_tokens = profile.max_length or 600

        adapted_content = await self.llm.explain(prompt, max_tokens=max_tokens)

        return {
            **raw_output,
            "content_adapted": adapted_content,
            "persona_applied": effective_role,
            "persona_format": profile.format,
            "persona_depth": profile.depth,
            "original_available": True,
        }

    def adapt_sync_fallback(self, raw_output: dict, role: Optional[str]) -> dict:
        """Synchronous fallback when LLM is unavailable — returns role metadata without adapting content."""
        effective_role = (role or "").lower()
        if effective_role not in RoleProfile.PROFILES:
            effective_role = "physician"
        profile = RoleProfile.get(effective_role)
        return {
            **raw_output,
            "content_adapted": None,
            "persona_applied": effective_role,
            "persona_format": profile.format,
            "persona_depth": profile.depth,
            "original_available": True,
        }
