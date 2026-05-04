from typing import Optional
from pydantic import BaseModel


class LabResult(BaseModel):
    observation_id: str
    loinc_code: Optional[str] = None
    display_name: str
    value: Optional[float] = None
    value_string: Optional[str] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    interpretation: Optional[str] = None  # "H" | "HH" | "L" | "LL" | "N" | "A"
    effective_date: Optional[str] = None
    status: str = "final"


class LabTrend(BaseModel):
    direction: str  # "rising" | "falling" | "stable" | "insufficient_data"
    data_points: int
    first_value: Optional[float] = None
    last_value: Optional[float] = None
    percent_change: Optional[float] = None


class AbnormalLab(BaseModel):
    observation_id: str
    display_name: str
    loinc_code: Optional[str] = None
    value: Optional[float] = None
    value_string: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    interpretation: str
    abnormality_level: str  # "critical" | "abnormal" | "borderline"
    effective_date: Optional[str] = None
    trend: Optional[LabTrend] = None
    clinical_significance: Optional[str] = None
    ai_generated: bool = False
