import logging
import os
from typing import Optional

from memory.store import pattern_memory
from memory.signature import pattern_signature
from models.advanced import PatternInsight
from sharp import extract_sharp_context, resolve_patient_id, build_sharp_metadata
from integrations.llm_client import LLMClient

logger = logging.getLogger(__name__)

llm = LLMClient()


async def get_pattern_insights(
    patient_id: str,
    conditions: Optional[list[str]] = None,
    role: str = None,
    ctx=None,
) -> dict:
    """
    Query Clinical Pattern Memory for anonymous session-scoped historical context.

    Returns pattern observations accumulated during the current server session only.
    No patient data is stored — only anonymous SHA-256 hashes of generic clinical conditions.
    Store resets on every server restart (pure in-memory, zero disk writes).

    Args:
        patient_id: FHIR Patient resource ID (used to fetch deterioration data if conditions not provided)
        conditions: Optional list of generic clinical conditions to query (e.g. ["news2_high_risk",
                    "creatinine_rising_trend"]). If not provided, derived from patient's latest
                    deterioration report via Tool 5.
    """
    sharp = extract_sharp_context(ctx, role_hint=role)

    if os.getenv("PATTERN_MEMORY_ENABLED", "true").lower() != "true":
        return PatternInsight(
            pattern_found=False,
            conditions_checked=[],
            contextual_insight="Pattern Memory is disabled on this server.",
            sharp_metadata=build_sharp_metadata(sharp),
        ).model_dump()

    effective_id = resolve_patient_id(patient_id, sharp)

    # If no conditions provided, derive from patient's deterioration data
    effective_conditions = list(conditions) if conditions else []
    if not effective_conditions and effective_id:
        try:
            import tools.deterioration as _det_mod
            det = await _det_mod.detect_clinical_deterioration_signals(effective_id, hours_lookback=72, ctx=ctx)
            if not det.get("error"):
                news2 = (det.get("news2") or {}).get("total_score", 0) or 0
                triggered = det.get("triggered_rules") or []
                effective_conditions = pattern_signature.from_news2_result(
                    score=int(news2),
                    triggered_rules=triggered,
                )
        except Exception as e:
            logger.debug("Could not derive conditions from deterioration: %s", e)

    if not effective_conditions:
        return PatternInsight(
            pattern_found=False,
            conditions_checked=[],
            contextual_insight="No conditions available to query pattern memory.",
            sharp_metadata=build_sharp_metadata(sharp),
        ).model_dump()

    past = pattern_memory.query_similar(effective_conditions)

    if past is None or past.total_observations == 0:
        return PatternInsight(
            pattern_found=False,
            conditions_checked=effective_conditions,
            contextual_insight=(
                "No similar patterns observed in current session yet. "
                "This is the first occurrence of this clinical pattern in this session."
            ),
            sharp_metadata=build_sharp_metadata(sharp),
        ).model_dump()

    total = past.total_observations
    distribution = {k: f"{v / total * 100:.0f}%" for k, v in past.outcome_counts.items()}
    confidence = "moderate" if total >= 5 else "low"

    insight_text = await llm.explain(
        prompt=f"""You are a clinical decision support AI analyzing anonymous session pattern data.

Pattern conditions observed: {past.conditions}
Times seen this session: {total}
Outcome distribution: {distribution}

Write 2-3 sentences explaining this pattern context for a clinician.
RULES:
- NEVER say "diagnose" or "diagnosis"
- ALWAYS note this is session-scoped context only (not a population-level finding)
- ALWAYS note clinician judgment is required
- Keep it factual and hedged; do not overstate significance
- Do not mention specific patient names or IDs""",
        max_tokens=180,
    )

    if not insight_text:
        insight_text = (
            f"This clinical pattern has been observed {total} time(s) this session "
            f"with the following outcomes: {distribution}. "
            "Treat as a weak session-scoped signal requiring clinician judgment."
        )

    return PatternInsight(
        pattern_found=True,
        conditions_checked=effective_conditions,
        signature=past.signature,
        similar_patterns_seen=total,
        outcome_distribution=distribution,
        contextual_insight=insight_text,
        data_scope="current_session_only",
        session_reset_note="Pattern store resets on server restart. No persistent storage of any kind.",
        confidence=confidence,
        confidence_note=f"Based on {total} session observation(s) only — not a validated statistical claim.",
        action_required_by="clinician",
        ai_generated=True,
        sharp_metadata=build_sharp_metadata(sharp),
    ).model_dump()
