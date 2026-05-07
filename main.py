import os
import logging

from dotenv import load_dotenv

load_dotenv()

# Must be set BEFORE importing FastMCP — Settings reads env vars at import time
# Railway injects PORT; FastMCP reads FASTMCP_HOST and FASTMCP_PORT
os.environ.setdefault("FASTMCP_HOST", "0.0.0.0")
os.environ.setdefault("FASTMCP_PORT", os.getenv("PORT", "8000"))

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

from server import mcp  # noqa: E402 — must import after env vars set

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
