import asyncio
import logging
from itertools import combinations

from integrations.fhir_client import FHIRClient, FHIRError
from integrations.openfda_client import OpenFDAClient
from integrations.llm_client import LLMClient
from engine.deduplicator import deduplicate_medications
from models.medication import MedicationEntry, MedicationTimeline

logger = logging.getLogger(__name__)

fhir = FHIRClient()
openfda = OpenFDAClient()
llm = LLMClient()


def _parse_medication(resource: dict) -> dict:
    med_obj = resource.get("medicationCodeableConcept", {})
    codings = med_obj.get("coding", [{}])
    display_name = (
        med_obj.get("text")
        or (codings[0].get("display") if codings else None)
        or "Unknown medication"
    )
    code = codings[0].get("code") if codings else None

    dosage_list = resource.get("dosageInstruction", [])
    dosage_text = None
    route_text = None
    frequency_text = None
    if dosage_list:
        d = dosage_list[0]
        dosage_text = d.get("text")
        route_obj = d.get("route", {})
        route_codings = route_obj.get("coding", [{}])
        route_text = route_obj.get("text") or (route_codings[0].get("display") if route_codings else None)
        timing = d.get("timing", {})
        repeat = timing.get("repeat", {})
        if repeat.get("frequency") and repeat.get("period"):
            frequency_text = f"{repeat['frequency']} per {repeat['period']} {repeat.get('periodUnit', '')}"

    status = resource.get("status", "unknown")
    authored_on = resource.get("authoredOn")

    requester = resource.get("requester", {})
    prescriber = requester.get("display")

    return {
        "medication_id": resource.get("id", ""),
        "display_name": display_name,
        "generic_name": None,
        "brand_name": None,
        "dosage": dosage_text,
        "route": route_text,
        "frequency": frequency_text,
        "status": status,
        "authored_on": authored_on,
        "prescriber": prescriber,
        "rxnorm_code": code,
    }


async def get_medication_timeline(patient_id: str, days: int = 90) -> dict:
    """
    Get medication history with drug interaction flags.

    Fetches MedicationRequests from FHIR, deduplicates brand/generic names,
    and checks each drug pair against OpenFDA for interactions.

    Args:
        patient_id: FHIR Patient resource ID
        days: Number of days to look back (default 90)

    Returns:
        MedicationTimeline with interaction_flags and AI explanations
    """
    try:
        meds_raw = await fhir.get_medications(patient_id, days=days)
    except FHIRError as e:
        return e.to_dict()
    except Exception as e:
        return {"error": "FHIR_ERROR", "message": str(e), "retry_suggested": True}

    parsed_meds = [_parse_medication(r) for r in meds_raw]
    deduped = deduplicate_medications(parsed_meds)

    generic_names = [m.get("generic_name") or m.get("display_name") for m in deduped]
    pairs = list(combinations(generic_names, 2))

    interaction_results = []
    if pairs:
        tasks = [openfda.check_interaction(a, b) for a, b in pairs[:20]]
        interaction_results = await asyncio.gather(*tasks, return_exceptions=True)

    interaction_by_drug: dict[str, list] = {name: [] for name in generic_names}
    total_interactions = 0
    has_major = False

    for i, (drug_a, drug_b) in enumerate(pairs[:20]):
        result = interaction_results[i] if i < len(interaction_results) else None
        if result and not isinstance(result, Exception):
            total_interactions += 1
            if result.severity == "major":
                has_major = True

            explanation = await llm.explain_interaction(
                drug_a, drug_b, result.description
            )
            result.ai_explanation = explanation
            result.ai_generated = explanation is not None

            interaction_by_drug[drug_a].append(result)
            interaction_by_drug[drug_b].append(result)

    medication_entries: list[MedicationEntry] = []
    for med in deduped:
        name = med.get("generic_name") or med.get("display_name")
        entry = MedicationEntry(
            medication_id=med["medication_id"],
            display_name=med["display_name"],
            generic_name=med.get("generic_name"),
            brand_name=med.get("brand_name"),
            dosage=med.get("dosage"),
            route=med.get("route"),
            frequency=med.get("frequency"),
            status=med.get("status", "unknown"),
            authored_on=med.get("authored_on"),
            prescriber=med.get("prescriber"),
            is_duplicate_merged=med.get("is_duplicate_merged", False),
            merged_from=med.get("merged_from", []),
            interaction_flags=interaction_by_drug.get(name, []),
        )
        medication_entries.append(entry)

    timeline = MedicationTimeline(
        patient_id=patient_id,
        days_queried=days,
        medications=medication_entries,
        total_interactions_found=total_interactions,
        has_major_interactions=has_major,
        deduplication_applied=True,
        data_sources=["FHIR/MedicationRequest", "OpenFDA"],
    )
    return timeline.model_dump()
