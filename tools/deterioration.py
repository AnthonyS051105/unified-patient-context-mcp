import logging
import os
from typing import Optional

from integrations.fhir_client import FHIRClient, FHIRError
from integrations.llm_client import LLMClient
from engine.news2 import calculate_news2
from engine.mews import calculate_mews
from models.deterioration import DeteriorationReport, VitalSign
from sharp import extract_sharp_context, resolve_patient_id, build_sharp_metadata, role_is, log_tool_call, log_sharp_absent
from evidence.trail import build_vitals_evidence
from persona.adapter import PersonaAdapter
from memory.store import pattern_memory
from memory.signature import pattern_signature

logger = logging.getLogger(__name__)

fhir = FHIRClient()
llm = LLMClient()
persona = PersonaAdapter(llm)

VITAL_SIGNS_LOINC = {
    "8867-4": "heart_rate",
    "9279-1": "respiratory_rate",
    "59408-5": "oxygen_saturation",
    "8480-6": "systolic_bp",
    "8462-4": "diastolic_bp",
    "8310-5": "body_temperature",
    "67775-7": "consciousness_avpu",
    "9269-2": "gcs_total",
    "55284-4": "blood_pressure",
    "8478-0": "mean_arterial_pressure",
}

AVPU_FROM_GCS = {
    range(15, 16): "A",
    range(13, 15): "V",
    range(9, 13): "P",
    range(3, 9): "U",
}


def _gcs_to_avpu(gcs: float) -> str:
    for r, code in AVPU_FROM_GCS.items():
        if int(gcs) in r:
            return code
    return "U"


def _parse_vital(resource: dict) -> Optional[tuple[str, float, VitalSign]]:
    code_obj = resource.get("code", {})
    codings = code_obj.get("coding", [])
    display = code_obj.get("text") or (codings[0].get("display") if codings else "unknown")

    loinc_code = None
    vital_key = None
    for c in codings:
        code = c.get("code", "")
        if code in VITAL_SIGNS_LOINC:
            loinc_code = code
            vital_key = VITAL_SIGNS_LOINC[code]
            break

    if not vital_key:
        return None

    value = resource.get("valueQuantity", {}).get("value")
    unit = resource.get("valueQuantity", {}).get("unit")

    if value is None:
        for comp in resource.get("component", []):
            comp_code = comp.get("code", {}).get("coding", [{}])[0].get("code", "")
            if comp_code == "8480-6":
                value = comp.get("valueQuantity", {}).get("value")
                unit = comp.get("valueQuantity", {}).get("unit")
                vital_key = "systolic_bp"
                loinc_code = "8480-6"
                break

    if value is None:
        return None

    effective = resource.get("effectiveDateTime") or resource.get("effectivePeriod", {}).get("start", "")

    return vital_key, value, VitalSign(
        loinc_code=loinc_code or "",
        display_name=display,
        value=value,
        unit=unit,
        effective_date=effective,
    )


def _build_triggered_rules(vitals: dict, news2_score: int, mews_score: int) -> list[str]:
    rules = []
    hr = vitals.get("heart_rate")
    rr = vitals.get("respiratory_rate")
    spo2 = vitals.get("oxygen_saturation")
    sbp = vitals.get("systolic_bp")
    temp = vitals.get("body_temperature")
    avpu = vitals.get("consciousness_str")

    if hr is not None:
        if hr <= 40 or hr >= 131:
            rules.append(f"HR {hr:.0f} bpm — extreme value")
        elif hr >= 111:
            rules.append(f"HR {hr:.0f} bpm — tachycardia (>110)")
        elif hr <= 50:
            rules.append(f"HR {hr:.0f} bpm — bradycardia (<50)")
    if rr is not None:
        if rr >= 25:
            rules.append(f"RR {rr:.0f} /min — severe tachypnea (≥25)")
        elif rr >= 21:
            rules.append(f"RR {rr:.0f} /min — tachypnea (>20)")
        elif rr <= 8:
            rules.append(f"RR {rr:.0f} /min — bradypnea (≤8)")
    if spo2 is not None:
        if spo2 <= 91:
            rules.append(f"SpO₂ {spo2:.0f}% — severe hypoxemia (≤91%)")
        elif spo2 <= 95:
            rules.append(f"SpO₂ {spo2:.0f}% — hypoxemia (≤95%)")
    if sbp is not None:
        if sbp <= 90:
            rules.append(f"SBP {sbp:.0f} mmHg — hypotension (≤90)")
        elif sbp >= 220:
            rules.append(f"SBP {sbp:.0f} mmHg — hypertensive crisis (≥220)")
    if temp is not None:
        if temp <= 35.0:
            rules.append(f"Temp {temp:.1f}°C — hypothermia (≤35.0°C)")
        elif temp >= 39.1:
            rules.append(f"Temp {temp:.1f}°C — high fever (≥39.1°C)")
    if avpu and avpu.upper() != "A":
        rules.append(f"Consciousness: {avpu.upper()} — altered mental status")

    if news2_score >= 7:
        rules.append(f"NEWS2 score {news2_score} — HIGH RISK: emergency response indicated")
    elif news2_score >= 5:
        rules.append(f"NEWS2 score {news2_score} — MEDIUM RISK: urgent clinical review needed")

    return rules


async def detect_clinical_deterioration_signals(
    patient_id: str,
    hours_lookback: int = 72,
    role: str = None,
    ctx=None,
) -> dict:
    """
    Detect clinical deterioration signals using NEWS2 and MEWS scoring algorithms.

    Rule engine decides risk level. AI generates the narrative explanation — no diagnosis.
    Output always includes confidence='rule-based' and action_required_by='clinician'.

    Args:
        patient_id: FHIR Patient resource ID (overridden by SHARP context if present)
        hours_lookback: Hours of vital sign history to analyze (default 72)
        ctx: MCP context — carries SHARP headers from Prompt Opinion platform

    Returns:
        DeteriorationReport with NEWS2/MEWS scores, triggered rules, and clinical narrative.
    """
    sharp = extract_sharp_context(ctx, role_hint=role)
    effective_id = resolve_patient_id(patient_id, sharp)

    if sharp.is_present:
        log_tool_call("detect_clinical_deterioration_signals", sharp.session_id, sharp.role)
    else:
        log_sharp_absent("detect_clinical_deterioration_signals")

    if not effective_id:
        return {"error": "MISSING_PATIENT_ID", "message": "patient_id required", "retry_suggested": False}

    try:
        obs_raw = await fhir.get_observations(effective_id, category="vital-signs", hours=hours_lookback)
    except FHIRError as e:
        return e.to_dict()
    except Exception as e:
        return {"error": "FHIR_ERROR", "message": str(e), "retry_suggested": True}

    vital_signs: list[VitalSign] = []
    latest_vitals: dict[str, float] = {}
    latest_ts: Optional[str] = None

    for resource in obs_raw:
        parsed = _parse_vital(resource)
        if parsed is None:
            continue
        vital_key, value, vs = parsed
        vital_signs.append(vs)
        if vital_key not in latest_vitals:
            latest_vitals[vital_key] = value
            if latest_ts is None:
                latest_ts = vs.effective_date

    if "consciousness_avpu" not in latest_vitals and "gcs_total" in latest_vitals:
        latest_vitals["consciousness_str"] = _gcs_to_avpu(latest_vitals["gcs_total"])
    else:
        latest_vitals["consciousness_str"] = latest_vitals.get("consciousness_str", "A")

    news2 = calculate_news2(
        rr=latest_vitals.get("respiratory_rate"),
        spo2=latest_vitals.get("oxygen_saturation"),
        sbp=latest_vitals.get("systolic_bp"),
        hr=latest_vitals.get("heart_rate"),
        temp=latest_vitals.get("body_temperature"),
        consciousness=latest_vitals.get("consciousness_str", "A"),
    )

    mews = calculate_mews(
        rr=latest_vitals.get("respiratory_rate"),
        hr=latest_vitals.get("heart_rate"),
        sbp=latest_vitals.get("systolic_bp"),
        consciousness=latest_vitals.get("consciousness_str", "A"),
        temp=latest_vitals.get("body_temperature"),
    )

    triggered_rules = _build_triggered_rules(latest_vitals, news2.total_score, mews.total_score)

    risk_levels = {"low": 0, "low-medium": 1, "medium": 2, "high": 3}
    overall_risk = max(news2.risk_level, mews.risk_level, key=lambda r: risk_levels.get(r, 0))

    recommendation_map = {
        "low": "Continue routine monitoring",
        "low-medium": "Increase monitoring frequency",
        "medium": "Urgent clinical review required",
        "high": "Immediate emergency response required",
    }

    # Nurse-facing language: more actionable. Physician: more technical.
    role_context = sharp.role or "clinician"
    clinical_narrative = await llm.explain_deterioration(
        news2.total_score, mews.total_score, overall_risk, triggered_rules,
        role=role_context,
    )

    report = DeteriorationReport(
        patient_id=effective_id,
        news2=news2,
        mews=mews,
        triggered_rules=triggered_rules,
        risk_level=overall_risk,
        recommendation=recommendation_map.get(overall_risk, "Clinical assessment required"),
        clinical_narrative=clinical_narrative,
        confidence="rule-based",
        action_required_by="clinician",
        ai_generated=clinical_narrative is not None,
        data_window_hours=hours_lookback,
        vital_signs_count=len(vital_signs),
        latest_vitals_timestamp=latest_ts,
    )

    # Build evidence trail from available vital signs
    vital_recency = 6.0  # approximate recency for most recent vitals
    evidence = build_vitals_evidence(
        {k: v for k, v in latest_vitals.items() if k != "consciousness_str"},
        recency_hours=vital_recency,
    )

    result = report.model_dump()
    result["latest_vitals"] = {k: v for k, v in latest_vitals.items() if k != "consciousness_str"}
    result["evidence_trail"] = evidence.model_dump()
    result["sharp_metadata"] = build_sharp_metadata(sharp)

    # Auto-record pattern to Clinical Pattern Memory (non-blocking, never errors main flow)
    if os.getenv("PATTERN_MEMORY_ENABLED", "true").lower() == "true":
        try:
            conditions = pattern_signature.from_news2_result(
                score=news2.total_score,
                triggered_rules=triggered_rules,
            )
            if conditions:
                if news2.total_score >= 7:
                    outcome = "deterioration_high_risk"
                elif news2.total_score >= 5:
                    outcome = "deterioration_medium_risk"
                else:
                    outcome = "stable"
                pattern_memory.record(conditions, outcome)
                result["pattern_recorded"] = True
                result["pattern_conditions"] = conditions
        except Exception:
            pass  # Pattern recording must never block or crash main flow

    if sharp.role:
        result = await persona.adapt(result, sharp.role)
    else:
        result["persona_applied"] = "physician"
    return result
