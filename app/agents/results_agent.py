# app/agents/results_agent.py
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.utils.mcp_tools import results_tools, MCPToolResponse

class ResultsAgent(BaseAgent):
    """Agent for handling result retrieval operations"""
    
    def __init__(self, api_manager, context_manager):
        # Define the system prompt template with placeholders for shared context
        system_prompt_template = """
        You are a Financial Results Agent that helps users retrieve and analyze results from financial risk analysis runs.
        You have access to the following tools:
        
        {tools}
        
        Current conversation context:
        - User is asking about: {conversation_summary}
        - User's most recent message: {recent_user_messages[0] if recent_user_messages else "No recent messages"}
        {active_run_id if active_run_id else "- No active run ID from previous runs"}
        {recent_run_types if recent_run_types else "- No recent run types mentioned"}
        
        When a user asks you to retrieve results, you should:
        1. Identify which result type they need (stress test or allowance)
        2. Extract necessary parameters from the user's request
        3. Call the appropriate tool with the parameters
        4. Format the response in a user-friendly way
        
        Always use a tool when the user is asking for results.
        Format your tool calls as JSON objects with "tool_name" and "parameters" fields.
        If parameters are missing, look for context from the conversation or ask the user.
        """
        
        super().__init__(
            agent_id="results_agent",
            api_manager=api_manager,
            context_manager=context_manager,
            system_prompt_template=system_prompt_template,
            tools=results_tools
        )
    
    async def _process_tool_results(self, state: Dict[str, Any], tool_call: Dict[str, Any], 
                                   tool_response: MCPToolResponse) -> None:
        """Process tool results specific to results operations"""
        conversation_id = state.get("conversation_id")
        
        # Store relevant information in agent outputs
        if "agent_outputs" not in state:
            state["agent_outputs"] = {}
        if "results_agent" not in state["agent_outputs"]:
            state["agent_outputs"]["results_agent"] = {}
        
        # Process specific tool results
        if tool_response.status == "success" and tool_response.data and "downloadId" in tool_response.data:
            download_id = tool_response.data["downloadId"]
            download_link = tool_response.data.get("link")
            
            if tool_call["tool_name"] == "get_stress_results":
                state["agent_outputs"]["results_agent"]["stressDownloadId"] = download_id
                
                # Update shared context
                await self.context_manager.update_shared_context(
                    conversation_id,
                    self.agent_id,
                    {
                        "stress_download_id": download_id,
                        "stress_download_link": download_link,
                        "results_type": "stress",
                        "run_type": tool_call["parameters"].get("runtype"),
                        "scenario": tool_call["parameters"].get("scenario")
                    }
                )
                
            elif tool_call["tool_name"] == "get_allowance_results":
                state["agent_outputs"]["results_agent"]["allowanceDownloadId"] = download_id
                
                # Update shared context
                await self.context_manager.update_shared_context(
                    conversation_id,
                    self.agent_id,
                    {
                        "allowance_download_id": download_id,
                        "allowance_download_link": download_link,
                        "results_type": "allowance",
                        "run_type": tool_call["parameters"].get("runtype"),
                        "scenario": tool_call["parameters"].get("scenario")
                    }
                )