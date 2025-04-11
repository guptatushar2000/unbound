# app/utils/mcp_tools.py
from typing import Dict, List, Any, Optional, Union, Literal
from pydantic import BaseModel, Field

# Common MCP types
class MCPToolParameter(BaseModel):
    name: str
    description: str
    type: str = "string"
    required: bool = True
    enum: Optional[List[str]] = None

class MCPTool(BaseModel):
    name: str
    description: str
    parameters: List[MCPToolParameter]

class MCPToolCall(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]

class MCPToolResponse(BaseModel):
    status: Literal["success", "error"]
    data: Any = None
    error: Optional[str] = None

# Batch service tools
batch_tools = [
    MCPTool(
        name="start_batch_run",
        description="Start a new batch run with the specified parameters",
        parameters=[
            MCPToolParameter(
                name="runType",
                description="Type of the run (CCAR, RiskApetite, or Stress)",
                required=True,
                enum=["CCAR", "RiskApetite", "Stress"]
            ),
            MCPToolParameter(
                name="runScenario",
                description="Scenario for the run",
                required=False
            ),
            MCPToolParameter(
                name="cobDate",
                description="Month end or Qtr end COB date for the run (format: YYYYMMDD)",
                required=False
            ),
            MCPToolParameter(
                name="runGroup",
                description="Group for the run",
                required=False
            )
        ]
    ),
    MCPTool(
        name="get_run_status",
        description="Get the status of a run",
        parameters=[
            MCPToolParameter(
                name="runId",
                description="ID of the run to check",
                required=True
            )
        ]
    ),
    MCPTool(
        name="kill_run",
        description="Kill a running batch job",
        parameters=[
            MCPToolParameter(
                name="runId",
                description="ID of the run to kill",
                required=True
            )
        ]
    ),
    MCPTool(
        name="get_run_log",
        description="Get the log of a run",
        parameters=[
            MCPToolParameter(
                name="runId",
                description="ID of the run to get logs for",
                required=True
            )
        ]
    )
]

# Results service tools
results_tools = [
    MCPTool(
        name="get_stress_results",
        description="Get stress test results and provide download link to DS2.xlsx",
        parameters=[
            MCPToolParameter(
                name="runtype",
                description="Type of the run",
                required=True
            ),
            MCPToolParameter(
                name="cob",
                description="Cut-off date for the run (format: YYYYMMDD)",
                required=True
            ),
            MCPToolParameter(
                name="scenario",
                description="Scenario for the run",
                required=True
            )
        ]
    ),
    MCPTool(
        name="get_allowance_results",
        description="Get allowance results and provide download link to DS1.xlsx",
        parameters=[
            MCPToolParameter(
                name="runtype",
                description="Type of the run",
                required=True
            ),
            MCPToolParameter(
                name="cob",
                description="Cut-off date for the run (format: YYYYMMDD)",
                required=True
            ),
            MCPToolParameter(
                name="scenario",
                description="Scenario for the run",
                required=True
            )
        ]
    )
]