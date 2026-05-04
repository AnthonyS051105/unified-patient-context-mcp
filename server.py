from mcp.server.fastmcp import FastMCP

from tools.patient_snapshot import get_patient_snapshot
from tools.active_problems import get_active_problems
from tools.medications import get_medication_timeline
from tools.lab_results import get_recent_abnormal_labs
from tools.deterioration import detect_clinical_deterioration_signals
from tools.context_delta import get_patient_context_delta

mcp = FastMCP(
    name="unified-patient-context",
    instructions=(
        "Aggregates patient data from FHIR and clinical databases into unified context "
        "for healthcare AI agents. Provides 6 clinical tools covering patient snapshots, "
        "active problems, medication timelines, abnormal labs, deterioration signals, "
        "and context deltas."
    ),
)

mcp.tool()(get_patient_snapshot)
mcp.tool()(get_active_problems)
mcp.tool()(get_medication_timeline)
mcp.tool()(get_recent_abnormal_labs)
mcp.tool()(detect_clinical_deterioration_signals)
mcp.tool()(get_patient_context_delta)
