import logging
from typing import Optional

from integrations.fhir_client import FHIRClient, FHIRError
from integrations.llm_client import LLMClient
from models.lab import AbnormalLab, LabTrend

logger = logging.getLogger(__name__)

fhir = FHIRClient()
llm = LLMClient()

CRITICAL_CODES = {"HH", "LL", "AA", "A"}
ABNORMAL_CODES = {"H", "L", "HH", "LL", "A", "AA"}
BORDERLINE_CODES = {"H", "L", "HU", "LU"}

THRESHOLD_MAP = {
    "critical": CRITICAL_CODES,
    "abnormal": ABNORMAL_CODES,
    "borderline": ABNORMAL_CODES | BORDERLINE_CODES,
}


def _parse_observation(resource: dict) -> Optional[dict]:
    code_obj = resource.get("code", {})
    codings = code_obj.get("coding", [{}])
    loinc = None
    for c in codings:
        if "loinc" in c.get("system", "").lower():
            loinc = c.get("code")
            break
    display = code_obj.get("text") or (codings[0].get("display") if codings else None) or "Unknown lab"

    value = resource.get("valueQuantity", {}).get("value")
    unit = resource.get("valueQuantity", {}).get("unit")
    value_string = resource.get("valueString") or resource.get("valueCodeableConcept", {}).get("text")

    ref_ranges = resource.get("referenceRange", [])
    ref_low = ref_high = ref_text = None
    if ref_ranges:
        ref = ref_ranges[0]
        ref_low = ref.get("low", {}).get("value")
        ref_high = ref.get("high", {}).get("value")
        ref_text = ref.get("text")

    interp = resource.get("interpretation", [])
    interp_code = None
    if interp:
        interp_codings = interp[0].get("coding", [{}])
        interp_code = interp_codings[0].get("code") if interp_codings else None

    effective = resource.get("effectiveDateTime") or resource.get("effectivePeriod", {}).get("start")

    return {
        "observation_id": resource.get("id", ""),
        "loinc_code": loinc,
        "display_name": display,
        "value": value,
        "value_string": value_string,
        "unit": unit,
        "reference_low": ref_low,
        "reference_high": ref_high,
        "reference_text": ref_text,
        "interpretation": interp_code,
        "effective_date": effective,
        "status": resource.get("status", "final"),
    }


def _is_abnormal_by_range(obs: dict) -> bool:
    val = obs.get("value")
    if val is None:
        return False
    low = obs.get("reference_low")
    high = obs.get("reference_high")
    if low is not None and val < low:
        return True
    if high is not None and val > high:
        return True
    return False


def _classify_abnormality(obs: dict) -> Optional[str]:
    code = obs.get("interpretation", "")
    if code in ("HH", "LL", "AA"):
        return "critical"
    if code in ("H", "L", "A"):
        if _is_abnormal_by_range(obs):
            val = obs.get("value")
            low = obs.get("reference_low")
            high = obs.get("reference_high")
            if val is not None and high is not None and val > high * 1.5:
                return "critical"
            if val is not None and low is not None and low > 0 and val < low * 0.5:
                return "critical"
        return "abnormal"
    if _is_abnormal_by_range(obs):
        return "borderline"
    return None


def _compute_trend(observations: list[dict]) -> Optional[LabTrend]:
    values = [(o["effective_date"], o["value"]) for o in observations
              if o.get("value") is not None and o.get("effective_date")]
    values.sort(key=lambda x: x[0])
    if len(values) < 2:
        return LabTrend(direction="insufficient_data", data_points=len(values))
    first_val = values[0][1]
    last_val = values[-1][1]
    if first_val == 0:
        pct = None
        direction = "stable"
    else:
        pct = ((last_val - first_val) / abs(first_val)) * 100
        if pct > 10:
            direction = "rising"
        elif pct < -10:
            direction = "falling"
        else:
            direction = "stable"
    return LabTrend(
        direction=direction,
        data_points=len(values),
        first_value=first_val,
        last_value=last_val,
        percent_change=round(pct, 1) if pct is not None else None,
    )


def _ref_range_text(obs: dict) -> str:
    if obs.get("reference_text"):
        return obs["reference_text"]
    low = obs.get("reference_low")
    high = obs.get("reference_high")
    unit = obs.get("unit", "")
    if low is not None and high is not None:
        return f"{low}–{high} {unit}".strip()
    if high is not None:
        return f"<{high} {unit}".strip()
    if low is not None:
        return f">{low} {unit}".strip()
    return "not specified"


async def get_recent_abnormal_labs(
    patient_id: str,
    days: int = 30,
    threshold: str = "abnormal",
) -> dict:
    """
    Retrieve recent abnormal lab results with trend analysis and AI explanations.

    Args:
        patient_id: FHIR Patient resource ID
        days: Number of days to look back (default 30)
        threshold: Severity filter — 'critical', 'abnormal', or 'borderline'

    Returns:
        Dict with list of AbnormalLab results, each with clinical_significance
    """
    if threshold not in THRESHOLD_MAP:
        return {
            "error": "INVALID_PARAMETER",
            "message": f"threshold must be one of: critical, abnormal, borderline",
            "retry_suggested": False,
        }

    try:
        obs_raw = await fhir.get_observations(patient_id, category="laboratory", days=days)
    except FHIRError as e:
        return e.to_dict()
    except Exception as e:
        return {"error": "FHIR_ERROR", "message": str(e), "retry_suggested": True}

    parsed = [o for r in obs_raw if (o := _parse_observation(r)) is not None]

    by_loinc: dict[str, list[dict]] = {}
    for obs in parsed:
        key = obs.get("loinc_code") or obs.get("display_name")
        by_loinc.setdefault(key, []).append(obs)

    abnormals: list[AbnormalLab] = []

    for key, obs_list in by_loinc.items():
        obs_list.sort(key=lambda o: o.get("effective_date") or "", reverse=True)
        latest = obs_list[0]

        level = _classify_abnormality(latest)
        if level is None:
            continue

        if threshold == "critical" and level != "critical":
            continue
        if threshold == "abnormal" and level == "borderline":
            continue

        trend = _compute_trend(obs_list)
        ref_range = _ref_range_text(latest)
        unit = latest.get("unit", "")
        val_str = str(latest["value"]) + f" {unit}".rstrip() if latest.get("value") is not None else (latest.get("value_string") or "N/A")
        trend_str = trend.direction if trend else "unknown"

        explanation = await llm.explain_abnormal_lab(
            latest["display_name"], val_str, ref_range, trend_str
        )

        lab = AbnormalLab(
            observation_id=latest["observation_id"],
            display_name=latest["display_name"],
            loinc_code=latest.get("loinc_code"),
            value=latest.get("value"),
            value_string=latest.get("value_string"),
            unit=unit or None,
            reference_range=ref_range,
            interpretation=latest.get("interpretation") or "out-of-range",
            abnormality_level=level,
            effective_date=latest.get("effective_date"),
            trend=trend,
            clinical_significance=explanation,
            ai_generated=explanation is not None,
        )
        abnormals.append(lab)

    abnormals.sort(key=lambda x: {"critical": 0, "abnormal": 1, "borderline": 2}.get(x.abnormality_level, 3))

    return {
        "patient_id": patient_id,
        "days_queried": days,
        "threshold": threshold,
        "abnormal_labs": [a.model_dump() for a in abnormals],
        "total_count": len(abnormals),
        "has_critical": any(a.abnormality_level == "critical" for a in abnormals),
        "data_sources": ["FHIR/Observation"],
    }
