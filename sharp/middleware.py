from typing import Optional
from sharp.context import SHARPContext, extract_role_from_text, VALID_ROLES


def resolve_patient_id(explicit_id: Optional[str], sharp: SHARPContext) -> Optional[str]:
    """
    Prioritize patient_id from SHARP context over explicit parameter.
    Also extracts role from patient_id string if sharp.role not yet set
    (handles cases where agent passes role text inside patient_id field).
    """
    # If role still not set, try extracting from the explicit_id string as last resort
    if not sharp.role and explicit_id:
        role_from_id = extract_role_from_text(explicit_id)
        if role_from_id:
            sharp.role = role_from_id

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
