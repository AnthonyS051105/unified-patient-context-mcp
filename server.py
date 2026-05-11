import os
from mcp.server.fastmcp import FastMCP

from tools.patient_snapshot import get_patient_snapshot
from tools.active_problems import get_active_problems
from tools.medications import get_medication_timeline
from tools.lab_results import get_recent_abnormal_labs
from tools.deterioration import detect_clinical_deterioration_signals
from tools.context_delta import get_patient_context_delta
from tools.cross_domain_insights import synthesize_cross_domain_insights
from tools.ward_alerts import scan_ward_alerts
from tools.orchestrate import orchestrate_context_from_sources
from tools.pattern_insights import get_pattern_insights

mcp = FastMCP(
    name="unified-patient-context",
    instructions=(
        "Nova by NexusHealth — Unified Patient Context MCP Server. "
        "Proactive, Adaptive, Transparent, Pattern-aware, Interoperable healthcare AI layer. "
        "10 clinical tools: patient snapshot, active problems, medication timeline, "
        "abnormal labs, deterioration signals, context delta, cross-domain AI synthesis, "
        "proactive ward alerts (scan_ward_alerts), meta-orchestrator (orchestrate_context_from_sources), "
        "and clinical pattern memory (get_pattern_insights). "
        "Supports SHARP context propagation from Prompt Opinion platform. "
        "Adaptive Clinical Persona (physician/nurse/pharmacist/patient) on every tool. "
        "Confidence-Weighted Evidence Trail on synthesis tools. "
        "Clinical Pattern Memory: anonymous session-scoped pattern accumulation — zero patient data stored."
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
mcp.tool()(scan_ward_alerts)
mcp.tool()(orchestrate_context_from_sources)
mcp.tool()(get_pattern_insights)
