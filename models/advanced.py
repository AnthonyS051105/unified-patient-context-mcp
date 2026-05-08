from typing import Literal, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str
    data_points: int
    recency_hours: float
    weight: float
    quality: Literal["complete", "partial", "estimated"]
    raw_values: list = Field(default_factory=list)


class EvidenceTrail(BaseModel):
    overall_confidence: float
    confidence_label: Literal["high", "moderate", "low", "insufficient"]
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    recommendation_strength: Literal["strong", "moderate", "weak", "insufficient"]
    transparency_note: str


class PatientAlert(BaseModel):
    patient_id: str
    patient_name: Optional[str] = None
    alert_level: Literal["critical", "high", "medium"]
    news2_score: int = 0
    mews_score: int = 0
    primary_signal: str
    secondary_signals: list[str] = Field(default_factory=list)
    recommended_action: str
    time_since_last_assessment: str = "unknown"
    evidence_trail: Optional[EvidenceTrail] = None


class WardAlertReport(BaseModel):
    ward_id: str
    scan_timestamp: str
    patients_scanned: int
    alerts: list[PatientAlert] = Field(default_factory=list)
    no_alerts_found: bool = False
    summary_narrative: str
    persona_applied: str
    sharp_metadata: dict = Field(default_factory=dict)


class ExternalSourceResult(BaseModel):
    source_id: str
    available: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class OrchestratedContext(BaseModel):
    patient_id: str
    sources_queried: list[str] = Field(default_factory=list)
    sources_available: int = 0
    sources_failed: list[str] = Field(default_factory=list)
    unified_context: dict = Field(default_factory=dict)
    synthesis: Optional[str] = None
    evidence_trail: Optional[EvidenceTrail] = None
    persona_applied: str = "physician"
    sharp_metadata: dict = Field(default_factory=dict)
    action_required_by: str = "clinician"
    ai_generated: bool = True
