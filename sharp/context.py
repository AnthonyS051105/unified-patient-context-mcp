import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SHARPContext:
    patient_id: Optional[str] = None
    ehr_token: Optional[str] = None
    session_id: Optional[str] = None
    org_id: Optional[str] = None
    role: Optional[str] = None
    is_present: bool = False


def extract_sharp_context(ctx=None) -> SHARPContext:
    """
    Extract SHARP context from MCP request context.

    SHARP headers are propagated automatically by the Prompt Opinion platform.
    When testing locally (MCP Inspector), context will be empty — this is normal.
    If MOCK_SHARP=true, returns a simulated context for local dev/testing.
    """
    if os.getenv("MOCK_SHARP", "false").lower() == "true":
        return SHARPContext(
            patient_id=os.getenv("MOCK_PATIENT_ID", "synthea-001"),
            role=os.getenv("MOCK_SHARP_ROLE", "physician"),
            session_id="dev-session-001",
            org_id="test-org",
            is_present=True,
        )

    try:
        meta: dict = {}
        if ctx is not None:
            if hasattr(ctx, "request_context") and ctx.request_context is not None:
                meta = ctx.request_context.meta or {}
            elif hasattr(ctx, "meta") and ctx.meta is not None:
                meta = ctx.meta or {}

        patient_id = meta.get("sharp_patient_id")
        return SHARPContext(
            patient_id=patient_id,
            ehr_token=meta.get("sharp_ehr_token"),
            session_id=meta.get("sharp_session_id"),
            org_id=meta.get("sharp_org_id"),
            role=meta.get("sharp_role"),
            is_present=bool(patient_id),
        )
    except Exception:
        return SHARPContext()
