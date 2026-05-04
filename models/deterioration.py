from typing import Optional
from pydantic import BaseModel, Field


class VitalSign(BaseModel):
    loinc_code: str
    display_name: str
    value: float
    unit: Optional[str] = None
    effective_date: str


class ClinicalScore(BaseModel):
    algorithm: str  # "NEWS2" | "MEWS"
    total_score: int
    risk_level: str  # "low" | "low-medium" | "medium" | "high"
    parameter_scores: dict[str, int] = Field(default_factory=dict)
    missing_parameters: list[str] = Field(default_factory=list)


class DeteriorationReport(BaseModel):
    patient_id: str
    news2: Optional[ClinicalScore] = None
    mews: Optional[ClinicalScore] = None
    triggered_rules: list[str] = Field(default_factory=list)
    risk_level: str = "unknown"  # overall, worst of NEWS2/MEWS
    recommendation: str = "Clinical assessment required"
    clinical_narrative: Optional[str] = None
    confidence: str = "rule-based"
    action_required_by: str = "clinician"
    ai_generated: bool = False
    data_window_hours: int = 72
    vital_signs_count: int = 0
    latest_vitals_timestamp: Optional[str] = None


class ContextDelta(BaseModel):
    patient_id: str
    since_hours: int
    new_labs: list[dict] = Field(default_factory=list)
    changed_medications: list[dict] = Field(default_factory=list)
    new_vitals: list[dict] = Field(default_factory=list)
    new_conditions: list[dict] = Field(default_factory=list)
    total_changes: int = 0
    no_changes: bool = False
    narrative_summary: Optional[str] = None
    ai_generated: bool = False
    query_timestamp: str = ""
