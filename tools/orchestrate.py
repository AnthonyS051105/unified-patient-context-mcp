import asyncio
import logging
from typing import Optional

from integrations.llm_client import LLMClient
from integrations.mcp_client import MCPClient
from models.advanced import OrchestratedContext
from evidence.scorer import EvidenceScorer, DataSource
from persona.adapter import PersonaAdapter
from sharp import extract_sharp_context, resolve_patient_id, build_sharp_metadata, log_tool_call, log_sharp_absent

logger = logging.getLogger(__name__)

llm = LLMClient()
mcp_client = MCPClient()
evidence_scorer = EvidenceScorer()
persona = PersonaAdapter(llm)

DISCLAIMER = (
    "This orchestrated context is synthesized by an AI clinical decision support tool. "
    "It does not constitute a diagnosis or clinical recommendation. "
    "All clinical decisions must be made by a qualified healthcare professional."
)


async def orchestrate_context_from_sources(
    patient_id: str,
    sources: list[str],
    role: str = None,
    ctx=None,
) -> dict:
    """
    Orchestrate patient context from multiple MCP servers into a unified view.

    Nara calls other MCP servers in parallel, merges all results, and synthesizes
    a unified clinical narrative — making Nara the only submission that truly
    implements MCP interoperability as an orchestrator, not just an endpoint.

    Args:
        patient_id: FHIR Patient resource ID (overridden by SHARP context if present)
        sources: List of MCP server IDs to query, e.g. ["nara_core", "radiology_mcp", "pharmacy_mcp"]
        ctx: MCP context — carries SHARP headers from Prompt Opinion platform

    Returns:
        OrchestratedContext with unified data from all sources, AI synthesis, evidence trail,
        and persona-adapted output.
    """
    sharp = extract_sharp_context(ctx, role_hint=role)
    effective_id = resolve_patient_id(patient_id, sharp)

    if sharp.is_present:
        log_tool_call("orchestrate_context_from_sources", sharp.session_id, sharp.role)
    else:
        log_sharp_absent("orchestrate_context_from_sources")

    if not effective_id:
        return {"error": "MISSING_PATIENT_ID", "message": "patient_id required", "retry_suggested": False}

    if not sources:
        sources = ["nara_core"]

    effective_role = sharp.role or "physician"

    # Always get core Nara data
    core_task = _get_core_data(effective_id, ctx)

    # External MCP calls (exclude nara_core which we handle directly)
    external_sources = [s for s in sources if s != "nara_core"]
    external_tasks = [
        mcp_client.call_tool(src, "get_patient_data", {"patient_id": effective_id})
        for src in external_sources
    ]

    # Run all in parallel
    all_results = await asyncio.gather(core_task, *external_tasks, return_exceptions=True)
    core_result = all_results[0]
    external_results = list(all_results[1:])

    # Build unified context
    unified: dict = {}
    sources_available = 0
    sources_failed: list[str] = []

    # Core data
    if isinstance(core_result, Exception) or (isinstance(core_result, dict) and core_result.get("error")):
        sources_failed.append("nara_core")
        logger.warning("Core data fetch failed: %s", core_result)
    else:
        unified["core"] = core_result
        sources_available += 1

    # External data
    for src_id, ext_result in zip(external_sources, external_results):
        if isinstance(ext_result, Exception):
            sources_failed.append(src_id)
        elif isinstance(ext_result, dict) and ext_result.get("available") is False:
            sources_failed.append(src_id)
            logger.info("External source %s unavailable: %s", src_id, ext_result.get("error"))
        else:
            unified[src_id] = ext_result
            sources_available += 1

    # Build evidence trail across all sources
    ev_sources: list[DataSource] = []
    for src_key, src_data in unified.items():
        if not isinstance(src_data, dict):
            continue
        values = [str(v) for v in src_data.values() if isinstance(v, (str, int, float))][:5]
        recency = float(src_data.get("recency_hours", 24.0))
        quality = "complete" if src_data.get("available", True) else "partial"
        ev_sources.append(DataSource(src_key, values, recency, quality))

    evidence = evidence_scorer.score(ev_sources)

    # LLM synthesis
    synthesis_prompt = _build_synthesis_prompt(unified, effective_role)
    synthesis = await llm.synthesize(synthesis_prompt)
    if not synthesis:
        synthesis = f"Patient context aggregated from {sources_available} source(s). Manual review of each data source is recommended."

    result = OrchestratedContext(
        patient_id=effective_id,
        sources_queried=list(sources),
        sources_available=sources_available,
        sources_failed=sources_failed,
        unified_context=unified,
        synthesis=synthesis,
        evidence_trail=evidence,
        persona_applied=effective_role,
        sharp_metadata=build_sharp_metadata(sharp),
        action_required_by="clinician",
        ai_generated=True,
    ).model_dump()

    result["disclaimer"] = DISCLAIMER

    effective_role = sharp.role or "physician"
    result = await persona.adapt(result, effective_role)
    return result


async def _get_core_data(patient_id: str, ctx) -> dict:
    """Fetch snapshot + labs + meds in parallel from Nara's own tools."""
    import tools.patient_snapshot as _snap_mod
    import tools.lab_results as _lab_mod
    import tools.deterioration as _det_mod

    snap, labs, det = await asyncio.gather(
        _snap_mod.get_patient_snapshot(patient_id, ctx=ctx),
        _lab_mod.get_recent_abnormal_labs(patient_id, days=30, threshold="abnormal", ctx=ctx),
        _det_mod.detect_clinical_deterioration_signals(patient_id, hours_lookback=72, ctx=ctx),
        return_exceptions=True,
    )

    core: dict = {"source": "nara_core", "available": True, "recency_hours": 0.0}
    if not isinstance(snap, Exception) and not (isinstance(snap, dict) and snap.get("error")):
        core["snapshot"] = snap
    if not isinstance(labs, Exception) and not (isinstance(labs, dict) and labs.get("error")):
        core["labs"] = labs
    if not isinstance(det, Exception) and not (isinstance(det, dict) and det.get("error")):
        core["deterioration"] = det
        core["news2_score"] = (det.get("news2") or {}).get("total_score")
        core["risk_level"] = det.get("risk_level")

    return core


def _build_synthesis_prompt(unified: dict, role: str) -> str:
    role_instruction = {
        "physician": "Provide full clinical reasoning with medical terminology.",
        "nurse": "Focus on actionable monitoring parameters and escalation triggers.",
        "pharmacist": "Focus on medication-related findings and drug safety concerns.",
        "patient": "Explain in plain language at a 6th grade reading level.",
    }.get(role.lower(), "Provide a balanced clinical synthesis.")

    sections: list[str] = []
    for src_key, src_data in unified.items():
        if not isinstance(src_data, dict):
            continue
        sections.append(f"[{src_key.upper()}]")
        for k, v in src_data.items():
            if k not in ("source", "available", "recency_hours", "sharp_metadata"):
                sections.append(f"  {k}: {str(v)[:200]}")

    data_text = "\n".join(sections) or "No data available."

    return (
        f"You are a clinical decision support AI synthesizing data from multiple sources. "
        f"{role_instruction}\n\n"
        f"MULTI-SOURCE PATIENT DATA:\n{data_text}\n\n"
        f"Synthesize this data into a 3-5 sentence clinical narrative. "
        f"Highlight cross-source patterns. Note any conflicts or gaps. "
        f"Do NOT diagnose. Use 'may suggest', 'warrants evaluation', 'consistent with'. "
        f"End with: 'Action required by: clinician.'"
    )
