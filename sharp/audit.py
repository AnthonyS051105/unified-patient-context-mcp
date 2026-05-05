import logging
from typing import Optional

logger = logging.getLogger(__name__)


def log_tool_call(tool_name: str, session_id: Optional[str], role: Optional[str]) -> None:
    """
    Zero-PII audit log for tool calls via SHARP context.
    Never logs patient_id, ehr_token, or clinical data.
    """
    if session_id:
        logger.info(
            "SHARP tool call | tool=%s | session=[REDACTED] | role=%s",
            tool_name,
            role or "unknown",
        )
    else:
        logger.debug("Local tool call | tool=%s (no SHARP session)", tool_name)


def log_sharp_absent(tool_name: str) -> None:
    logger.debug("SHARP context absent for tool=%s — using explicit parameters", tool_name)
