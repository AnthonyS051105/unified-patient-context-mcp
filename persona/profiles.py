from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class RoleConfig:
    format: Literal["narrative", "bullets", "structured", "simple"]
    depth: Literal["full", "summary", "medication-focused", "simplified"]
    terminology: Literal["medical", "nursing", "pharmacy", "plain"]
    priority_fields: list[str]
    max_length: Optional[int]


class RoleProfile:
    PROFILES: dict[str, RoleConfig] = {
        "physician": RoleConfig(
            format="narrative",
            depth="full",
            terminology="medical",
            priority_fields=["clinical_reasoning", "differential", "raw_values", "evidence"],
            max_length=None,
        ),
        "nurse": RoleConfig(
            format="bullets",
            depth="summary",
            terminology="nursing",
            priority_fields=["monitoring_thresholds", "escalation_triggers", "immediate_actions"],
            max_length=300,
        ),
        "pharmacist": RoleConfig(
            format="structured",
            depth="medication-focused",
            terminology="pharmacy",
            priority_fields=["drug_interactions", "renal_dosing", "contraindications", "alternatives"],
            max_length=400,
        ),
        "patient": RoleConfig(
            format="simple",
            depth="simplified",
            terminology="plain",
            priority_fields=["what_is_happening", "next_steps", "questions_for_doctor"],
            max_length=200,
        ),
    }

    @classmethod
    def get(cls, role: str) -> RoleConfig:
        return cls.PROFILES.get((role or "").lower(), cls.PROFILES["physician"])
