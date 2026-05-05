from typing import Optional
from sharp.context import SHARPContext


def resolve_patient_id(explicit_id: Optional[str], sharp: SHARPContext) -> Optional[str]:
    """
    Prioritize patient_id from SHARP context over explicit parameter.
    When running on Prompt Opinion, the agent never needs to pass patient_id manually.
    """
    return sharp.patient_id or explicit_id


def build_sharp_metadata(sharp: SHARPContext) -> dict:
    """
    Build the sharp_metadata dict to include in every tool response.
    Never includes ehr_token or patient_id.
    """
    return {
        "session_id": "[REDACTED]" if sharp.session_id else None,
        "org_id": sharp.org_id,
        "role_context": sharp.role,
        "sharp_propagated": sharp.is_present,
    }


def role_is(sharp: SHARPContext, *roles: str) -> bool:
    if not sharp.role:
        return False
    return sharp.role.lower() in {r.lower() for r in roles}
