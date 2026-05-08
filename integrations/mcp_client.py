import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Mock server data for demo mode (MOCK_EXTERNAL_MCP=true)
_MOCK_SERVERS: dict[str, dict] = {
    "radiology_mcp": {
        "get_patient_data": lambda pid: {
            "imaging_findings": "No acute cardiopulmonary process on CXR. Mild cardiomegaly noted.",
            "last_imaging_date": "2026-05-06",
            "modality": "Chest X-Ray",
            "available": True,
            "source": "radiology_mcp",
            "recency_hours": 24.0,
        }
    },
    "pharmacy_mcp": {
        "get_patient_data": lambda pid: {
            "dispensing_records": [
                "Metformin 500mg — dispensed 3 days ago",
                "Lisinopril 10mg — dispensed 7 days ago",
            ],
            "refill_due": "2026-05-20",
            "last_dispensed": "Metformin 500mg",
            "available": True,
            "source": "pharmacy_mcp",
            "recency_hours": 72.0,
        }
    },
}


class MCPClient:
    """MCP-to-MCP HTTP client for Meta-Orchestrator."""

    async def call_tool(
        self, server_id: str, tool_name: str, params: dict
    ) -> dict:
        """
        Call a tool on an external MCP server.
        Uses mock data if MOCK_EXTERNAL_MCP=true or server URL not configured.
        Always returns gracefully — never raises.
        """
        mock_mode = os.getenv("MOCK_EXTERNAL_MCP", "true").lower() == "true"

        if mock_mode:
            return self._call_mock(server_id, tool_name, params)

        server_url = os.getenv(f"MCP_URL_{server_id.upper()}", "")
        if not server_url:
            logger.info("No URL configured for %s, using mock", server_id)
            return self._call_mock(server_id, tool_name, params)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{server_url}/tools/{tool_name}",
                    json=params,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                return {**data, "available": True, "source": server_id}
        except httpx.TimeoutException:
            logger.warning("MCP server %s timed out", server_id)
            return {"available": False, "error": "timeout", "source": server_id}
        except Exception as e:
            logger.warning("MCP server %s error: %s", server_id, e)
            return {"available": False, "error": str(e), "source": server_id}

    def _call_mock(self, server_id: str, tool_name: str, params: dict) -> dict:
        mock = _MOCK_SERVERS.get(server_id, {})
        handler = mock.get(tool_name)
        if handler:
            patient_id = params.get("patient_id", "unknown")
            return handler(patient_id)
        return {"available": False, "error": f"Mock for {server_id}/{tool_name} not found", "source": server_id}
