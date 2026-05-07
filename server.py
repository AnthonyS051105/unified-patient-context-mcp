import os
from mcp.server.fastmcp import FastMCP

from tools.patient_snapshot import get_patient_snapshot
from tools.active_problems import get_active_problems
from tools.medications import get_medication_timeline
from tools.lab_results import get_recent_abnormal_labs
from tools.deterioration import detect_clinical_deterioration_signals
from tools.context_delta import get_patient_context_delta
from tools.cross_domain_insights import synthesize_cross_domain_insights

mcp = FastMCP(
    name="unified-patient-context",
    instructions=(
        "Unified Patient Context MCP Server — aggregates FHIR patient data, lab results, "
        "medications, and vital signs into a single clinical context for healthcare AI agents. "
        "Supports SHARP context propagation from Prompt Opinion platform. "
        "7 clinical tools: patient snapshot, active problems, medication timeline, "
        "abnormal labs, deterioration signals, context delta, and cross-domain AI synthesis."
    ),
    host=os.getenv("FASTMCP_HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", os.getenv("FASTMCP_PORT", "8000"))),
)

mcp.tool()(get_patient_snapshot)
mcp.tool()(get_active_problems)
mcp.tool()(get_medication_timeline)
mcp.tool()(get_recent_abnormal_labs)
mcp.tool()(detect_clinical_deterioration_signals)
mcp.tool()(get_patient_context_delta)
mcp.tool()(synthesize_cross_domain_insights)
