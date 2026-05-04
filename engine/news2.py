from typing import Optional
from models.deterioration import ClinicalScore


def _score_rr(rr: float) -> int:
    if rr <= 8:
        return 3
    if rr <= 11:
        return 1
    if rr <= 20:
        return 0
    if rr <= 24:
        return 2
    return 3


def _score_spo2(spo2: float, copd: bool = False) -> int:
    if copd:
        if spo2 <= 83:
            return 3
        if spo2 <= 85:
            return 2
        if spo2 <= 87:
            return 1
        if spo2 <= 92:
            return 0
        if spo2 <= 94:
            return 1  # Scale 2: target 88-92
        if spo2 <= 96:
            return 2
        return 3
    # Scale 1 (standard)
    if spo2 <= 91:
        return 3
    if spo2 <= 93:
        return 2
    if spo2 <= 95:
        return 1
    return 0


def _score_sbp(sbp: float) -> int:
    if sbp <= 90:
        return 3
    if sbp <= 100:
        return 2
    if sbp <= 110:
        return 1
    if sbp <= 219:
        return 0
    return 3


def _score_hr(hr: float) -> int:
    if hr <= 40:
        return 3
    if hr <= 50:
        return 1
    if hr <= 90:
        return 0
    if hr <= 110:
        return 1
    if hr <= 130:
        return 2
    return 3


def _score_consciousness(avpu: str) -> int:
    return 0 if avpu.upper() == "A" else 3


def _score_temperature(temp: float) -> int:
    if temp <= 35.0:
        return 3
    if temp <= 36.0:
        return 1
    if temp <= 38.0:
        return 0
    if temp <= 39.0:
        return 1
    return 2


def _risk_level(score: int) -> str:
    if score == 0:
        return "low"
    if score <= 4:
        return "low-medium"
    if score <= 6:
        return "medium"
    return "high"


def calculate_news2(
    rr: Optional[float] = None,
    spo2: Optional[float] = None,
    sbp: Optional[float] = None,
    hr: Optional[float] = None,
    temp: Optional[float] = None,
    consciousness: Optional[str] = None,
    on_supplemental_o2: bool = False,
    copd: bool = False,
) -> ClinicalScore:
    """
    Calculate NEWS2 score per Royal College of Physicians 2017 guideline.
    Supplemental O2 adds 2 points.
    """
    param_scores: dict[str, int] = {}
    missing: list[str] = []
    total = 0

    if rr is not None:
        s = _score_rr(rr)
        param_scores["respiratory_rate"] = s
        total += s
    else:
        missing.append("respiratory_rate")

    if spo2 is not None:
        s = _score_spo2(spo2, copd=copd)
        param_scores["spo2"] = s
        total += s
    else:
        missing.append("spo2")

    if on_supplemental_o2:
        param_scores["supplemental_o2"] = 2
        total += 2

    if sbp is not None:
        s = _score_sbp(sbp)
        param_scores["systolic_bp"] = s
        total += s
    else:
        missing.append("systolic_bp")

    if hr is not None:
        s = _score_hr(hr)
        param_scores["heart_rate"] = s
        total += s
    else:
        missing.append("heart_rate")

    if consciousness is not None:
        s = _score_consciousness(consciousness)
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
        algorithm="NEWS2",
        total_score=total,
        risk_level=_risk_level(total),
        parameter_scores=param_scores,
        missing_parameters=missing,
    )
