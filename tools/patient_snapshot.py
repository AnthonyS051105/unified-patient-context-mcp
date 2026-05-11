import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from integrations.fhir_client import FHIRClient, FHIRError
from integrations.llm_client import LLMClient
from models.patient import PatientSnapshot, ActiveProblem, Allergy
from sharp import extract_sharp_context, resolve_patient_id, build_sharp_metadata, log_tool_call, log_sharp_absent
from persona.adapter import PersonaAdapter

logger = logging.getLogger(__name__)

fhir = FHIRClient()
llm = LLMClient()
persona = PersonaAdapter(llm)


def _parse_name(patient_resource: dict) -> str:
    names = patient_resource.get("name", [])
    for n in names:
        if n.get("use") == "official" or not n.get("use"):
            given = " ".join(n.get("given", []))
            family = n.get("family", "")
            full = f"{given} {family}".strip()
            if full:
                return full
    return "Unknown"


def _calc_age(birth_date: str) -> Optional[int]:
    try:
        bdate = datetime.strptime(birth_date[:10], "%Y-%m-%d")
        today = datetime.now(timezone.utc)
        return (today.year - bdate.year
                - ((today.month, today.day) < (bdate.month, bdate.day)))
    except (ValueError, TypeError):
        return None


def _parse_condition(resource: dict) -> ActiveProblem:
    code_obj = resource.get("code", {})
    codings = code_obj.get("coding", [{}])
    code = codings[0].get("code") if codings else None
    code_system = codings[0].get("system") if codings else None
    display = code_obj.get("text") or (codings[0].get("display") if codings else None) or "Unknown condition"

    severity_obj = resource.get("severity", {})
    severity_codings = severity_obj.get("coding", [{}])
    severity = (severity_codings[0].get("display") if severity_codings else None) or severity_obj.get("text")

    clinical_status = (
        resource.get("clinicalStatus", {})
        .get("coding", [{}])[0]
        .get("code", "unknown")
    )

    return ActiveProblem(
        condition_id=resource.get("id", ""),
        display=display,
        code=code,
        code_system=code_system,
        clinical_status=clinical_status,
        severity=severity,
        onset_date=resource.get("onsetDateTime") or resource.get("onsetPeriod", {}).get("start"),
        recorded_date=resource.get("recordedDate"),
    )


def _parse_allergy(resource: dict) -> Allergy:
    subst = resource.get("code", {})
    codings = subst.get("coding", [{}])
    substance = subst.get("text") or (codings[0].get("display") if codings else None) or "Unknown"

    reactions = resource.get("reaction", [])
    reaction_text = None
    severity_text = None
    if reactions:
        manifestations = reactions[0].get("manifestation", [{}])
        mcodings = manifestations[0].get("coding", [{}]) if manifestations else [{}]
        reaction_text = (
            manifestations[0].get("text") or
            (mcodings[0].get("display") if mcodings else None)
        )
        severity_text = reactions[0].get("severity")

    clinical_status = (
        resource.get("clinicalStatus", {})
        .get("coding", [{}])[0]
        .get("code", "active")
    )

    return Allergy(
        substance=substance,
        reaction=reaction_text,
        severity=severity_text,
        status=clinical_status,
    )


async def get_patient_snapshot(patient_id: str, role: Optional[str] = None, ctx=None) -> dict:
    """
    Retrieve a unified snapshot of a patient's current clinical status.

    Fetches Patient demographics, active Conditions, MedicationRequests,
    and AllergyIntolerance from FHIR, then generates an AI summary.

    Args:
        patient_id: FHIR Patient resource ID (overridden by SHARP context if present)
        ctx: MCP context — carries SHARP headers from Prompt Opinion platform

    Returns:
        PatientSnapshot as dict with ai_summary, data_sources, sharp_metadata, and last_updated
    """
    sharp = extract_sharp_context(ctx, role_hint=role)
    effective_id = resolve_patient_id(patient_id, sharp)

    if sharp.is_present:
        log_tool_call("get_patient_snapshot", sharp.session_id, sharp.role)
    else:
        log_sharp_absent("get_patient_snapshot")

    if not effective_id:
        return {
            "error": "MISSING_PATIENT_ID",
            "message": "patient_id is required when SHARP context is not present",
            "retry_suggested": False,
        }

    data_sources: list[str] = []
    errors: list[str] = []

    try:
        patient_resource, conditions_raw, meds_raw, allergies_raw = await asyncio.gather(
            fhir.get_patient(effective_id),
            fhir.get_conditions(effective_id, status="active"),
            fhir.get_medications(effective_id, days=365),
            fhir.get_allergies(effective_id),
            return_exceptions=True,
        )
    except Exception as e:
        return {
            "error": "FHIR_ERROR",
            "message": str(e),
            "suggestion": "Check patient_id and FHIR server availability.",
            "retry_suggested": True,
        }

    if isinstance(patient_resource, FHIRError):
        return patient_resource.to_dict()
    if isinstance(patient_resource, Exception):
        return {"error": "FHIR_ERROR", "message": str(patient_resource), "retry_suggested": True}

    data_sources.append("FHIR/Patient")

    name = _parse_name(patient_resource)
    birth_date = patient_resource.get("birthDate")
    age_years = _calc_age(birth_date) if birth_date else None
    gender = patient_resource.get("gender")

    conditions: list[ActiveProblem] = []
    if not isinstance(conditions_raw, Exception):
        data_sources.append("FHIR/Condition")
        for r in conditions_raw:
            try:
                conditions.append(_parse_condition(r))
            except Exception:
                pass
    else:
        errors.append("Conditions unavailable")

    meds_count = 0
    if not isinstance(meds_raw, Exception):
        data_sources.append("FHIR/MedicationRequest")
        meds_count = len(meds_raw)
    else:
        errors.append("Medications unavailable")

    allergies: list[Allergy] = []
    if not isinstance(allergies_raw, Exception):
        data_sources.append("FHIR/AllergyIntolerance")
        for r in allergies_raw:
            try:
                allergies.append(_parse_allergy(r))
            except Exception:
                pass
    else:
        errors.append("Allergies unavailable")

    condition_names = [c.display for c in conditions]
    ai_summary = await llm.patient_summary(name, condition_names, meds_count)

    snapshot = PatientSnapshot(
        patient_id=effective_id,
        name=name,
        birth_date=birth_date,
        age_years=age_years,
        gender=gender,
        active_conditions=conditions,
        active_medications_count=meds_count,
        allergies=allergies,
        ai_summary=ai_summary,
        ai_generated=ai_summary is not None,
        data_sources=data_sources,
    )

    result = snapshot.model_dump()
    result["sharp_metadata"] = build_sharp_metadata(sharp)
    if errors:
        result["warnings"] = errors
    if sharp.role:
        result = await persona.adapt(result, sharp.role)
    else:
        result["persona_applied"] = "physician"
    return result
