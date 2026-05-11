import logging
from datetime import datetime, timezone

from integrations.fhir_client import FHIRClient, FHIRError
from integrations.llm_client import LLMClient
from models.deterioration import ContextDelta
from sharp import extract_sharp_context, resolve_patient_id, build_sharp_metadata, log_tool_call, log_sharp_absent
from persona.adapter import PersonaAdapter

logger = logging.getLogger(__name__)

fhir = FHIRClient()
llm = LLMClient()
persona = PersonaAdapter(llm)


def _summarize_lab(resource: dict) -> dict:
    code = resource.get("code", {})
    codings = code.get("coding", [{}])
    display = code.get("text") or (codings[0].get("display") if codings else "Unknown")
    value = resource.get("valueQuantity", {}).get("value")
    unit = resource.get("valueQuantity", {}).get("unit", "")
    return {
        "id": resource.get("id", ""),
        "name": display,
        "value": f"{value} {unit}".strip() if value is not None else "N/A",
        "date": resource.get("effectiveDateTime") or resource.get("issued"),
    }


def _summarize_vital(resource: dict) -> dict:
    code = resource.get("code", {})
    codings = code.get("coding", [{}])
    display = code.get("text") or (codings[0].get("display") if codings else "Unknown")
    value = resource.get("valueQuantity", {}).get("value")
    unit = resource.get("valueQuantity", {}).get("unit", "")
    return {
        "id": resource.get("id", ""),
        "name": display,
        "value": f"{value} {unit}".strip() if value is not None else "N/A",
        "date": resource.get("effectiveDateTime"),
    }


def _summarize_medication(resource: dict) -> dict:
    med = resource.get("medicationCodeableConcept", {})
    codings = med.get("coding", [{}])
    display = med.get("text") or (codings[0].get("display") if codings else "Unknown")
    return {
        "id": resource.get("id", ""),
        "name": display,
        "status": resource.get("status", "unknown"),
        "date": resource.get("authoredOn"),
    }


def _summarize_condition(resource: dict) -> dict:
    code = resource.get("code", {})
    codings = code.get("coding", [{}])
    display = code.get("text") or (codings[0].get("display") if codings else "Unknown")
    status = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "unknown")
    return {
        "id": resource.get("id", ""),
        "name": display,
        "status": status,
        "date": resource.get("recordedDate") or resource.get("onsetDateTime"),
    }


async def get_patient_context_delta(patient_id: str, since_hours: int = 48, role: str = None, ctx=None) -> dict:
    """
    Get what has changed in a patient's record over the last N hours.

    Uses FHIR _lastUpdated filter to efficiently fetch only changed resources.
    AI generates a plain-language narrative summary starting with 'In the last X hours, ...'.

    Args:
        patient_id: FHIR Patient resource ID (overridden by SHARP context if present)
        since_hours: Look-back window in hours (default 48)
        ctx: MCP context — carries SHARP headers from Prompt Opinion platform

    Returns:
        ContextDelta with categorized changes and AI narrative
    """
    sharp = extract_sharp_context(ctx, role_hint=role)
    effective_id = resolve_patient_id(patient_id, sharp)

    if sharp.is_present:
        log_tool_call("get_patient_context_delta", sharp.session_id, sharp.role)
    else:
        log_sharp_absent("get_patient_context_delta")

    if not effective_id:
        return {"error": "MISSING_PATIENT_ID", "message": "patient_id required", "retry_suggested": False}

    try:
        changed = await fhir.get_all_since(effective_id, hours=since_hours)
    except FHIRError as e:
        return e.to_dict()
    except Exception as e:
        return {"error": "FHIR_ERROR", "message": str(e), "retry_suggested": True}

    new_labs = [_summarize_lab(r) for r in changed.get("labs", [])]
    new_vitals = [_summarize_vital(r) for r in changed.get("vitals", [])]
    changed_meds = [_summarize_medication(r) for r in changed.get("medications", [])]
    new_conditions = [_summarize_condition(r) for r in changed.get("conditions", [])]

    total = len(new_labs) + len(new_vitals) + len(changed_meds) + len(new_conditions)
    no_changes = total == 0

    changes = {
        "new_labs": new_labs,
        "changed_medications": changed_meds,
        "new_vitals": new_vitals,
        "new_conditions": new_conditions,
    }

    narrative = await llm.explain_context_delta("the patient", since_hours, changes)
    query_ts = datetime.now(timezone.utc).isoformat()

    delta = ContextDelta(
        patient_id=effective_id,
        since_hours=since_hours,
        new_labs=new_labs,
        changed_medications=changed_meds,
        new_vitals=new_vitals,
        new_conditions=new_conditions,
        total_changes=total,
        no_changes=no_changes,
        narrative_summary=narrative,
        ai_generated=narrative is not None,
        query_timestamp=query_ts,
    )

    result = delta.model_dump()
    result["sharp_metadata"] = build_sharp_metadata(sharp)
    effective_role = sharp.role or "physician"
    result = await persona.adapt(result, effective_role)
    return result
