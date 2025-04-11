# app/core/api_manager.py
import httpx
import json
import asyncio
from typing import Dict, Any, Optional, Union
from app.core.config import settings
from app.utils.mcp_tools import MCPToolResponse

class APIManager:
    """Manages connections to external REST services"""
    
    def __init__(self):
        """Initialize the API manager with configuration"""
        self.batch_service_url = settings.services.BATCH_SERVICE_URL
        self.results_service_url = settings.services.RESULTS_SERVICE_URL
        self.timeout = 30.0  # Default timeout in seconds
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> MCPToolResponse:
        """Execute a tool using Multi-Agent Communication Protocol"""
        try:
            # Map tool name to the appropriate method
            if tool_name == "start_batch_run":
                result = await self.start_batch_run(**parameters)
                return MCPToolResponse(status="success", data=result)
            
            elif tool_name == "get_run_status":
                result = await self.get_run_status(**parameters)
                return MCPToolResponse(status="success", data=result)
            
            elif tool_name == "kill_run":
                result = await self.kill_run(**parameters)
                return MCPToolResponse(status="success", data=result)
            
            elif tool_name == "get_run_log":
                result = await self.get_run_log(**parameters)
                return MCPToolResponse(status="success", data=result)
            
            elif tool_name == "get_stress_results":
                result = await self.get_stress_results(**parameters)
                return MCPToolResponse(status="success", data=result)
            
            elif tool_name == "get_allowance_results":
                result = await self.get_allowance_results(**parameters)
                return MCPToolResponse(status="success", data=result)
            
            else:
                return MCPToolResponse(
                    status="error", 
                    error=f"Unknown tool: {tool_name}"
                )
        
        except Exception as e:
            return MCPToolResponse(
                status="error",
                error=f"Error executing {tool_name}: {str(e)}"
            )
    
    # Batch Service API methods
    async def start_batch_run(self, runType, runScenario="Base", cobDate="20243112", runGroup="default_group"):
        """Start a batch run"""
        url = f"{self.batch_service_url}/runs"
        payload = {
            "runType": runType,
            "runScenario": runScenario,
            "cobDate": cobDate,
            "runGroup": runGroup
        }
        
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error starting batch run: {str(e)}")
    
    async def get_run_status(self, runId):
        """Get the status of a batch run"""
        url = f"{self.batch_service_url}/runs/{runId}"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error getting run status: {str(e)}")
    
    async def kill_run(self, runId):
        """Kill a batch run"""
        url = f"{self.batch_service_url}/runs/{runId}"
        
        try:
            response = await self.client.delete(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error killing run: {str(e)}")
    
    async def get_run_log(self, runId):
        """Get the log for a batch run"""
        url = f"{self.batch_service_url}/runs/{runId}/log"
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Error getting run log: {str(e)}")
    
    # Results Service API methods
    async def get_stress_results(self, runtype, cob, scenario):
        """Get stress test results"""
        url = f"{self.results_service_url}/stressResults"
        params = {
            "runtype": runtype,
            "cob": cob,
            "scenario": scenario
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error getting stress results: {str(e)}")
    
    async def get_allowance_results(self, runtype, cob, scenario):
        """Get allowance results"""
        url = f"{self.results_service_url}/allowanceResults"
        params = {
            "runtype": runtype,
            "cob": cob,
            "scenario": scenario
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error getting allowance results: {str(e)}")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()