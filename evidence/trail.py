from evidence.scorer import EvidenceScorer, DataSource
from models.advanced import EvidenceTrail

_scorer = EvidenceScorer()


def build_evidence_trail(data_sources: list[DataSource]) -> EvidenceTrail:
    return _scorer.score(data_sources)


def build_vitals_evidence(vitals: dict, recency_hours: float) -> EvidenceTrail:
    sources = []
    vital_map = {
        "heart_rate": "Vitals/HeartRate",
        "respiratory_rate": "Vitals/RespiratoryRate",
        "oxygen_saturation": "Vitals/SpO2",
        "systolic_bp": "Vitals/SystolicBP",
        "body_temperature": "Vitals/Temperature",
    }
    for key, label in vital_map.items():
        val = vitals.get(key)
        if val is not None:
            sources.append(DataSource(
                name=label,
                values=[val],
                recency_hours=recency_hours,
                quality="complete",
            ))

    if not sources:
        sources.append(DataSource(
            name="Vitals",
            values=[],
            recency_hours=recency_hours,
            quality="partial",
        ))

    return _scorer.score(sources)


def build_cross_domain_evidence(
    labs: list[dict],
    meds: list[dict],
    vitals: dict,
    lab_recency_hours: float = 24.0,
    med_recency_hours: float = 72.0,
    vital_recency_hours: float = 12.0,
) -> EvidenceTrail:
    sources: list[DataSource] = []

    if labs:
        lab_names = [l.get("display_name", "lab") for l in labs[:5]]
        sources.append(DataSource(
            name="Lab/Results",
            values=lab_names,
            recency_hours=lab_recency_hours,
            quality="complete" if len(labs) >= 2 else "partial",
        ))

    if meds:
        med_names = [m.get("display_name", "med") for m in meds[:5]]
        sources.append(DataSource(
            name="Medication/Active",
            values=med_names,
            recency_hours=med_recency_hours,
            quality="complete",
        ))

    vital_values = [v for v in vitals.values() if isinstance(v, (int, float))]
    if vital_values:
        sources.append(DataSource(
            name="Vitals/Signs",
            values=vital_values[:5],
            recency_hours=vital_recency_hours,
            quality="complete" if len(vital_values) >= 3 else "partial",
        ))

    if not sources:
        sources.append(DataSource("Clinical/Data", [], 999.0, "estimated"))

    return _scorer.score(sources)
