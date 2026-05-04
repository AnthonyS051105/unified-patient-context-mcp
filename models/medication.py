from typing import Optional
from pydantic import BaseModel, Field


class InteractionFlag(BaseModel):
    drug_a: str
    drug_b: str
    severity: str  # "major" | "moderate" | "minor"
    description: str
    source: str = "OpenFDA"
    ai_explanation: Optional[str] = None
    ai_generated: bool = False


class MedicationEntry(BaseModel):
    medication_id: str
    display_name: str
    generic_name: Optional[str] = None
    brand_name: Optional[str] = None
    dosage: Optional[str] = None
    route: Optional[str] = None
    frequency: Optional[str] = None
    status: str  # "active" | "completed" | "stopped"
    authored_on: Optional[str] = None
    prescriber: Optional[str] = None
    is_duplicate_merged: bool = False
    merged_from: list[str] = Field(default_factory=list)
    interaction_flags: list[InteractionFlag] = Field(default_factory=list)


class MedicationTimeline(BaseModel):
    patient_id: str
    days_queried: int
    medications: list[MedicationEntry] = []
    total_interactions_found: int = 0
    has_major_interactions: bool = False
    deduplication_applied: bool = True
    data_sources: list[str] = ["FHIR/MedicationRequest", "OpenFDA"]
