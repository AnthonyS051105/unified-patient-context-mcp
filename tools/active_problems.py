import json
import logging

from integrations.fhir_client import FHIRClient, FHIRError
from integrations.llm_client import LLMClient
from models.patient import ActiveProblem

logger = logging.getLogger(__name__)

fhir = FHIRClient()
llm = LLMClient()


def _parse_condition(resource: dict) -> ActiveProblem:
    code_obj = resource.get("code", {})
    codings = code_obj.get("coding", [{}])
    code = codings[0].get("code") if codings else None
    code_system = codings[0].get("system") if codings else None
    display = (
        code_obj.get("text")
        or (codings[0].get("display") if codings else None)
        or "Unknown condition"
    )

    severity_obj = resource.get("severity", {})
    severity_codings = severity_obj.get("coding", [{}])
    severity = (severity_codings[0].get("display") if severity_codings else None) or severity_obj.get("text")

    clinical_status = (
        resource.get("clinicalStatus", {})
        .get("coding", [{}])[0]
        .get("code", "unknown")
    )

    categories = resource.get("category", [])
    category_text = None
    if categories:
        cat_codings = categories[0].get("coding", [{}])
        category_text = categories[0].get("text") or (cat_codings[0].get("display") if cat_codings else None)

    return ActiveProblem(
        condition_id=resource.get("id", ""),
        display=display,
        code=code,
        code_system=code_system,
        clinical_status=clinical_status,
        severity=severity,
        onset_date=resource.get("onsetDateTime") or resource.get("onsetPeriod", {}).get("start"),
        recorded_date=resource.get("recordedDate"),
        category=category_text,
    )


async def get_active_problems(patient_id: str, include_resolved: bool = False) -> dict:
    """
    Get a prioritized list of a patient's clinical problems.

    Fetches Condition resources from FHIR and uses AI to assign urgency scores.

    Args:
        patient_id: FHIR Patient resource ID
        include_resolved: If True, include resolved/inactive conditions

    Returns:
        Dict with 'problems' list and AI urgency prioritization
    """
    try:
        status = None if include_resolved else "active"
        conditions_raw = await fhir.get_conditions(patient_id, status=status)
    except FHIRError as e:
        return e.to_dict()
    except Exception as e:
        return {"error": "FHIR_ERROR", "message": str(e), "retry_suggested": True}

    problems: list[ActiveProblem] = []
    for r in conditions_raw:
        try:
            problems.append(_parse_condition(r))
        except Exception:
            pass

    condition_names = [p.display for p in problems]
    urgency_json = await llm.prioritize_problems(condition_names)

    urgency_map: dict[str, dict] = {}
    if urgency_json:
        try:
            parsed = json.loads(urgency_json)
            for item in parsed:
                cond_name = item.get("condition", "").lower()
                urgency_map[cond_name] = item
        except (json.JSONDecodeError, TypeError):
            pass

    for problem in problems:
        key = problem.display.lower()
        if key in urgency_map:
            problem.urgency_score = urgency_map[key].get("urgency")
            problem.urgency_reasoning = urgency_map[key].get("reason")
            problem.ai_generated = True

    problems.sort(key=lambda p: -(p.urgency_score or 0))

    return {
        "patient_id": patient_id,
        "problems": [p.model_dump() for p in problems],
        "total_count": len(problems),
        "include_resolved": include_resolved,
        "ai_prioritized": bool(urgency_json),
        "ai_generated": bool(urgency_json),
        "data_sources": ["FHIR/Condition"],
    }
