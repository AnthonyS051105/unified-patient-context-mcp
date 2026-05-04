from typing import Optional
from models.deterioration import ClinicalScore


def _score_rr(rr: float) -> int:
    if rr < 9:
        return 2
    if rr <= 14:
        return 0
    if rr <= 20:
        return 1
    if rr <= 29:
        return 2
    return 3


def _score_hr(hr: float) -> int:
    if hr < 40:
        return 2
    if hr <= 50:
        return 1
    if hr <= 100:
        return 0
    if hr <= 110:
        return 1
    if hr <= 129:
        return 2
    return 3


def _score_sbp(sbp: float) -> int:
    if sbp < 70:
        return 3
    if sbp <= 80:
        return 2
    if sbp <= 100:
        return 1
    if sbp <= 199:
        return 0
    return 2


def _score_avpu(avpu: str) -> int:
    mapping = {"A": 0, "V": 1, "P": 2, "U": 3}
    return mapping.get(avpu.upper(), 0)


def _score_temperature(temp: float) -> int:
    if temp < 35.0:
        return 2
    if temp <= 38.4:
        return 0
    return 2


def _risk_level(score: int) -> str:
    if score <= 1:
        return "low"
    if score <= 3:
        return "low-medium"
    if score <= 5:
        return "medium"
    return "high"


def calculate_mews(
    rr: Optional[float] = None,
    hr: Optional[float] = None,
    sbp: Optional[float] = None,
    consciousness: Optional[str] = None,
    temp: Optional[float] = None,
) -> ClinicalScore:
    """Calculate Modified Early Warning Score (MEWS) — 5 parameters."""
    param_scores: dict[str, int] = {}
    missing: list[str] = []
    total = 0

    if rr is not None:
        s = _score_rr(rr)
        param_scores["respiratory_rate"] = s
        total += s
    else:
        missing.append("respiratory_rate")

    if hr is not None:
        s = _score_hr(hr)
        param_scores["heart_rate"] = s
        total += s
    else:
        missing.append("heart_rate")

    if sbp is not None:
        s = _score_sbp(sbp)
        param_scores["systolic_bp"] = s
        total += s
    else:
        missing.append("systolic_bp")

    if consciousness is not None:
        s = _score_avpu(consciousness)
        param_scores["consciousness"] = s
        total += s
    else:
        missing.append("consciousness")

    if temp is not None:
        s = _score_temperature(temp)
        param_scores["temperature"] = s
        total += s
    else:
        missing.append("temperature")

    return ClinicalScore(
        algorithm="MEWS",
        total_score=total,
        risk_level=_risk_level(total),
        parameter_scores=param_scores,
        missing_parameters=missing,
    )
