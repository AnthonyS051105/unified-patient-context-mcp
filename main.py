import os
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

from server import mcp  # noqa: E402 — must import after env loaded

if __name__ == "__main__":
    # FastMCP reads settings via FASTMCP_ prefix env vars
    # Railway injects PORT; mirror it to FASTMCP_PORT and bind to 0.0.0.0
    os.environ.setdefault("FASTMCP_HOST", "0.0.0.0")
    os.environ.setdefault("FASTMCP_PORT", os.getenv("PORT", "8000"))

    mcp.run(transport="streamable-http")
