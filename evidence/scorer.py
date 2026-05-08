from dataclasses import dataclass, field
from typing import Literal

from models.advanced import EvidenceItem, EvidenceTrail


@dataclass
class DataSource:
    name: str
    values: list
    recency_hours: float
    quality: Literal["complete", "partial", "estimated"] = "complete"


# Clinical data fields that, if absent, are worth flagging as gaps
_EXPECTED_CLINICAL_FIELDS = {
    "baseline_creatinine",
    "egfr",
    "urine_output",
    "weight",
    "fluid_balance",
}

_QUALITY_SCORES: dict[str, float] = {
    "complete": 1.0,
    "partial": 0.6,
    "estimated": 0.3,
}


class EvidenceScorer:
    def score(self, data_sources: list[DataSource]) -> EvidenceTrail:
        if not data_sources:
            return EvidenceTrail(
                overall_confidence=0.0,
                confidence_label="insufficient",
                evidence_items=[],
                missing_data=["No data sources provided"],
                recommendation_strength="insufficient",
                transparency_note="No data available to assess confidence.",
            )

        items: list[EvidenceItem] = []
        for source in data_sources:
            weight = self._calculate_weight(source)
            items.append(EvidenceItem(
                source=source.name,
                data_points=len(source.values),
                recency_hours=source.recency_hours,
                weight=weight,
                quality=source.quality,
                raw_values=source.values[:10],  # cap at 10 to keep payload small
            ))

        weights = [i.weight for i in items]
        overall = round(sum(weights) / len(weights), 3) if weights else 0.0

        label = self._label(overall)
        strength = self._strength(overall)
        missing = self._find_gaps(data_sources)
        note = self._transparency_note(overall, items, missing)

        return EvidenceTrail(
            overall_confidence=overall,
            confidence_label=label,
            evidence_items=items,
            missing_data=missing,
            recommendation_strength=strength,
            transparency_note=note,
        )

    def score_multi_source(self, unified_context: dict) -> EvidenceTrail:
        """Score evidence across heterogeneous merged context (for orchestrator)."""
        sources: list[DataSource] = []
        for source_id, data in unified_context.items():
            if not isinstance(data, dict):
                continue
            values = list(data.values())[:5]
            quality: Literal["complete", "partial", "estimated"] = (
                "complete" if data.get("available", True) else "estimated"
            )
            sources.append(DataSource(
                name=source_id,
                values=values,
                recency_hours=data.get("recency_hours", 24.0),
                quality=quality,
            ))
        return self.score(sources)

    def _calculate_weight(self, source: DataSource) -> float:
        recency_score = max(0.0, 1.0 - (source.recency_hours / 168.0))  # decay over 1 week
        completeness_score = min(1.0, len(source.values) / 5.0)          # max at 5 data points
        quality_score = _QUALITY_SCORES.get(source.quality, 0.3)
        return round(
            (recency_score * 0.4) + (completeness_score * 0.4) + (quality_score * 0.2),
            3,
        )

    def _label(self, confidence: float) -> Literal["high", "moderate", "low", "insufficient"]:
        if confidence > 0.8:
            return "high"
        if confidence >= 0.5:
            return "moderate"
        if confidence > 0.0:
            return "low"
        return "insufficient"

    def _strength(self, confidence: float) -> Literal["strong", "moderate", "weak", "insufficient"]:
        if confidence > 0.8:
            return "strong"
        if confidence >= 0.5:
            return "moderate"
        if confidence > 0.0:
            return "weak"
        return "insufficient"

    def _find_gaps(self, sources: list[DataSource]) -> list[str]:
        present = {s.name.lower().replace(" ", "_").replace("/", "_") for s in sources}
        gaps: list[str] = []
        for field_name in _EXPECTED_CLINICAL_FIELDS:
            if not any(field_name in p for p in present):
                gaps.append(field_name.replace("_", " "))
        # Flag sources with zero data points
        for s in sources:
            if len(s.values) == 0:
                gaps.append(f"{s.name} — no values recorded")
        return gaps

    def _transparency_note(
        self,
        overall: float,
        items: list[EvidenceItem],
        missing: list[str],
    ) -> str:
        label = self._label(overall)
        low_weight_sources = [i.source for i in items if i.weight < 0.4]
        stale_sources = [i.source for i in items if i.recency_hours > 48]

        reasons: list[str] = []
        if stale_sources:
            reasons.append(f"stale data in {', '.join(stale_sources[:2])}")
        if low_weight_sources:
            reasons.append(f"sparse data in {', '.join(low_weight_sources[:2])}")
        if missing:
            reasons.append(f"missing: {', '.join(missing[:3])}")

        if not reasons:
            return f"Confidence is {label} based on {len(items)} data source(s) with sufficient recency and completeness."

        reason_str = "; ".join(reasons)
        return f"Confidence is {label} because {reason_str}."
