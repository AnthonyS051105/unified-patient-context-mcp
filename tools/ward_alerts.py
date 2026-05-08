import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from integrations.fhir_client import FHIRClient, FHIRError
from integrations.llm_client import LLMClient
from models.advanced import PatientAlert, WardAlertReport
from evidence.trail import build_vitals_evidence
from evidence.scorer import DataSource
from persona.adapter import PersonaAdapter
from sharp import extract_sharp_context, build_sharp_metadata, log_tool_call, log_sharp_absent

logger = logging.getLogger(__name__)

fhir = FHIRClient()
llm = LLMClient()
persona = PersonaAdapter(llm)

ALERT_LEVELS = {"critical": 0, "high": 1, "medium": 2}
NEWS2_THRESHOLDS = {"critical": 7, "high": 5, "medium": 3}

# Demo ward mapping when FHIR location isn't set up
DEMO_WARDS: dict[str, list[str]] = {
    "ICU-A": ["synthea-demo-patient"],
    "Ward-3B": ["synthea-demo-patient"],
}


def _news2_to_alert_level(score: int) -> Optional[str]:
    if score >= 7:
        return "critical"
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return None


def _meets_threshold(alert_level: str, threshold: str) -> bool:
    return ALERT_LEVELS.get(alert_level, 99) <= ALERT_LEVELS.get(threshold, 99)


def _time_since(ts: Optional[str]) -> str:
    if not ts:
        return "unknown"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        total_minutes = int(delta.total_seconds() / 60)
        if total_minutes < 60:
            return f"{total_minutes}m ago"
        hours = total_minutes // 60
        mins = total_minutes % 60
        return f"{hours}h {mins}m ago"
    except Exception:
        return "unknown"


def _extract_patient_name(patient_resource: dict) -> Optional[str]:
    names = patient_resource.get("name", [])
    for name in names:
        if name.get("use") in ("official", "usual") or not name.get("use"):
            given = " ".join(name.get("given", []))
            family = name.get("family", "")
            full = f"{given} {family}".strip()
            if full:
                return full
    return None


async def _fetch_patient_name(patient_id: str) -> Optional[str]:
    try:
        resource = await fhir.get_patient(patient_id)
        return _extract_patient_name(resource)
    except Exception:
        return None


async def _assess_single_patient(patient_id: str, timeout_sec: float = 10.0) -> Optional[dict]:
    """Run deterioration + lab assessment for one patient with timeout."""
    import tools.deterioration as _det_mod
    import tools.lab_results as _lab_mod
    try:
        async with asyncio.timeout(timeout_sec):
            det_result, lab_result = await asyncio.gather(
                _det_mod.detect_clinical_deterioration_signals(
                    patient_id=patient_id, hours_lookback=72, ctx=None
                ),
                _lab_mod.get_recent_abnormal_labs(
                    patient_id=patient_id, days=7, threshold="abnormal", ctx=None
                ),
                return_exceptions=True,
            )
            det = det_result if isinstance(det_result, dict) and not det_result.get("error") else {}
            labs = lab_result if isinstance(lab_result, dict) and not lab_result.get("error") else {}
            if not det and not labs:
                return None
            return {"deterioration": det, "labs": labs}
    except (asyncio.TimeoutError, Exception) as e:
        logger.warning("Patient assessment failed for [PATIENT_REDACTED]: %s", e)
        return None


async def scan_ward_alerts(
    ward_id: str,
    threshold: str = "high",
    max_patients: int = 20,
    ctx=None,
) -> dict:
    """
    Proactively scan all patients in a ward and return prioritized clinical alerts.

    Runs parallel deterioration assessments for every patient in the ward,
    ranks by NEWS2 risk score, and returns only patients meeting the threshold.
    No need to ask about each patient individually — Nara monitors the whole ward.

    Args:
        ward_id: FHIR Location ID or demo ward name (e.g. "ICU-A", "Ward-3B")
        threshold: Minimum alert level to include — "critical" | "high" | "medium" (default: "high")
        max_patients: Maximum patients to scan in parallel (default: 20)
        ctx: MCP context — carries SHARP headers from Prompt Opinion platform

    Returns:
        WardAlertReport with prioritized patient alerts, evidence trails, and persona-adapted summary.
    """
    sharp = extract_sharp_context(ctx)
    if sharp.is_present:
        log_tool_call("scan_ward_alerts", sharp.session_id, sharp.role)
    else:
        log_sharp_absent("scan_ward_alerts")

    scan_ts = datetime.now(timezone.utc).isoformat()
    effective_role = sharp.role or "nurse"

    # Resolve ward → patient list
    mock_mode = os.getenv("MOCK_WARD_PATIENTS", "").lower() == "true"
    patients: list[dict] = []

    if mock_mode or ward_id in DEMO_WARDS:
        # Demo mode: use static ward mapping
        demo_ids = DEMO_WARDS.get(ward_id, DEMO_WARDS.get("ICU-A", ["synthea-demo-patient"]))
        for pid in demo_ids[:max_patients]:
            patients.append({"id": pid, "resourceType": "Patient"})
    else:
        try:
            patients = await fhir.get_patients_by_location(ward_id, max_count=max_patients)
        except Exception as e:
            logger.warning("Ward patient fetch failed: %s", e)
            patients = []

    patients = patients[:max_patients]

    if not patients:
        return WardAlertReport(
            ward_id=ward_id,
            scan_timestamp=scan_ts,
            patients_scanned=0,
            alerts=[],
            no_alerts_found=True,
            summary_narrative="No patients found in this ward or ward data is unavailable.",
            persona_applied=effective_role,
            sharp_metadata=build_sharp_metadata(sharp),
        ).model_dump()

    # Parallel assessment + name fetch
    patient_ids = [p.get("id") for p in patients if p.get("id")]
    assess_tasks = [_assess_single_patient(pid) for pid in patient_ids]
    name_tasks = [_fetch_patient_name(pid) for pid in patient_ids]
    results, patient_names = await asyncio.gather(
        asyncio.gather(*assess_tasks, return_exceptions=True),
        asyncio.gather(*name_tasks, return_exceptions=True),
    )
    patient_name_map = {
        pid: (name if isinstance(name, str) else None)
        for pid, name in zip(patient_ids, patient_names)
    }

    # Build alerts
    alerts: list[PatientAlert] = []
    for pid, assessment in zip(patient_ids, results):
        if isinstance(assessment, Exception) or assessment is None:
            continue

        det_result = assessment.get("deterioration") or {}
        lab_result = assessment.get("labs") or {}

        news2 = (det_result.get("news2") or {}).get("total_score", 0)
        mews = (det_result.get("mews") or {}).get("total_score", 0)
        overall_risk = det_result.get("risk_level", "low")
        triggered = det_result.get("triggered_rules", [])
        latest_ts = det_result.get("latest_vitals_timestamp")

        # Lab-based alert escalation
        abnormal_labs = lab_result.get("abnormal_labs") or []
        critical_labs = [l for l in abnormal_labs if l.get("abnormality_level") == "critical"]
        abnormal_only = [l for l in abnormal_labs if l.get("abnormality_level") == "abnormal"]

        news2_level = _news2_to_alert_level(news2)

        # Determine alert level: NEWS2 OR lab-based, take highest severity
        if critical_labs:
            lab_alert_level = "high"  # critical labs = high alert even with low NEWS2
        elif len(abnormal_only) >= 2:
            lab_alert_level = "medium"
        else:
            lab_alert_level = None

        # Pick the more severe of the two
        candidates = [l for l in [news2_level, lab_alert_level] if l is not None]
        if not candidates:
            continue
        alert_level = min(candidates, key=lambda l: ALERT_LEVELS.get(l, 99))

        if not _meets_threshold(alert_level, threshold):
            continue

        # Build secondary signals from labs
        lab_signals = [
            f"{l['display_name']} {l.get('value', '')} {l.get('unit', '')} ({l['abnormality_level']})".strip()
            for l in (critical_labs + abnormal_only)[:3]
        ]
        secondary = (triggered + lab_signals)[:4]

        # Build primary signal description
        if critical_labs and news2 == 0:
            primary_signal = f"{len(critical_labs)} critical lab(s): {critical_labs[0]['display_name']}"
        else:
            primary_signal = f"NEWS2={news2}, risk={overall_risk}"
            if critical_labs:
                primary_signal += f" + {len(critical_labs)} critical lab(s)"

        # Build evidence trail from vitals
        latest_vitals = det_result.get("latest_vitals") or {}
        evidence = build_vitals_evidence(latest_vitals, recency_hours=6.0)

        action_map = {
            "critical": "Immediate emergency response required",
            "high": "Urgent clinical review required within 30 minutes",
            "medium": "Increase monitoring frequency",
        }

        alerts.append(PatientAlert(
            patient_id=pid,
            patient_name=patient_name_map.get(pid),
            alert_level=alert_level,
            news2_score=news2,
            mews_score=mews,
            primary_signal=primary_signal,
            secondary_signals=secondary,
            recommended_action=action_map.get(alert_level, "Clinical assessment required"),
            time_since_last_assessment=_time_since(latest_ts),
            evidence_trail=evidence,
        ))

    # Sort by severity then NEWS2 score
    alerts.sort(key=lambda a: (ALERT_LEVELS.get(a.alert_level, 99), -a.news2_score))

    if not alerts:
        summary = f"No patients in {ward_id} met the '{threshold}' threshold. All patients appear stable."
        return WardAlertReport(
            ward_id=ward_id,
            scan_timestamp=scan_ts,
            patients_scanned=len(patient_ids),
            alerts=[],
            no_alerts_found=True,
            summary_narrative=summary,
            persona_applied=effective_role,
            sharp_metadata=build_sharp_metadata(sharp),
        ).model_dump()

    # LLM-generated summary
    alert_summary_lines = [
        f"Patient {a.patient_name or a.patient_id}: {a.alert_level} ({a.primary_signal})"
        for a in alerts[:5]
    ]
    summary_prompt = (
        f"A ward scan of '{ward_id}' found {len(alerts)} patient(s) requiring attention "
        f"(threshold: {threshold}).\nAlerts:\n" + "\n".join(alert_summary_lines) + "\n"
        f"Write a 2-3 sentence summary for a {effective_role}. Use actionable language. "
        f"Do not diagnose."
    )
    summary_narrative = await llm.explain(summary_prompt, max_tokens=200)
    if not summary_narrative:
        summary_narrative = (
            f"{len(alerts)} of {len(patient_ids)} patients in {ward_id} require attention "
            f"(threshold: {threshold}). Most urgent: {alerts[0].primary_signal}."
        )

    report = WardAlertReport(
        ward_id=ward_id,
        scan_timestamp=scan_ts,
        patients_scanned=len(patient_ids),
        alerts=alerts,
        no_alerts_found=False,
        summary_narrative=summary_narrative,
        persona_applied=effective_role,
        sharp_metadata=build_sharp_metadata(sharp),
    )

    result = report.model_dump()
    # Apply persona to summary only (not individual alerts)
    if sharp.role:
        summary_wrapper = {"summary_narrative": summary_narrative, "alerts_count": len(alerts)}
        adapted = await persona.adapt(summary_wrapper, sharp.role)
        result["summary_narrative"] = adapted.get("content_adapted") or summary_narrative
        result["persona_applied"] = sharp.role

    return result
