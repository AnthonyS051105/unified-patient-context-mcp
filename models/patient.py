from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Allergy(BaseModel):
    substance: str
    reaction: Optional[str] = None
    severity: Optional[str] = None
    status: str = "active"


class ActiveProblem(BaseModel):
    condition_id: str
    display: str
    code: Optional[str] = None
    code_system: Optional[str] = None
    clinical_status: str
    severity: Optional[str] = None
    onset_date: Optional[str] = None
    recorded_date: Optional[str] = None
    category: Optional[str] = None
    urgency_score: Optional[int] = Field(None, ge=1, le=5, description="1=low, 5=critical — LLM-assigned")
    urgency_reasoning: Optional[str] = None
    ai_generated: bool = False


class PatientSnapshot(BaseModel):
    patient_id: str
    name: str
    birth_date: Optional[str] = None
    age_years: Optional[int] = None
    gender: Optional[str] = None
    active_conditions: list[ActiveProblem] = []
    active_medications_count: int = 0
    allergies: list[Allergy] = []
    ai_summary: Optional[str] = None
    ai_generated: bool = False
    last_updated: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    data_sources: list[str] = []
