# app/agents/batch_agent.py
from typing import Dict, Any
from app.agents.base_agent import BaseAgent
from app.utils.mcp_tools import batch_tools, MCPToolResponse

class BatchAgent(BaseAgent):
    """Agent for handling batch processing operations"""
    
    def __init__(self, api_manager, context_manager):
        # Define the system prompt template with placeholders for shared context
        system_prompt_template = """
        You are a Financial Batch Processing Agent that helps users manage batch runs for financial risk analysis.
        You have access to the following tools:
        
        {tools}
        
        Current conversation context:
        - User is asking about: {conversation_summary}
        - User's most recent message: {recent_user_messages[0] if recent_user_messages else "No recent messages"}
        {active_run_id if active_run_id else "- No active run ID"}
        
        When a user asks you to perform an action, you should:
        1. Identify which tool to use
        2. Extract necessary parameters from the user's request
        3. Call the appropriate tool with the parameters
        4. Format the response in a user-friendly way
        
        Always use a tool when the user is asking about starting, checking, or managing batch runs.
        Format your tool calls as JSON objects with "tool_name" and "parameters" fields.
        """
        
        super().__init__(
            agent_id="batch_agent",
            api_manager=api_manager,
            context_manager=context_manager,
            system_prompt_template=system_prompt_template,
            tools=batch_tools
        )
    
    async def _process_tool_results(self, state: Dict[str, Any], tool_call: Dict[str, Any], 
                                   tool_response: MCPToolResponse) -> None:
        """Process tool results specific to batch operations"""
        conversation_id = state.get("conversation_id")
        
        # Store relevant information in agent outputs
        if "agent_outputs" not in state:
            state["agent_outputs"] = {}
        if "batch_agent" not in state["agent_outputs"]:
            state["agent_outputs"]["batch_agent"] = {}
        
        # Process specific tool results
        if tool_call["tool_name"] == "start_batch_run" and tool_response.status == "success":
            if tool_response.data and "runId" in tool_response.data:
                run_id = tool_response.data["runId"]
                state["agent_outputs"]["batch_agent"]["runId"] = run_id
                
                # Track run history
                if "run_history" not in state["agent_outputs"]["batch_agent"]:
                    state["agent_outputs"]["batch_agent"]["run_history"] = []
                
                # Add to run history
                state["agent_outputs"]["batch_agent"]["run_history"].append({
                    "runId": run_id,
                    "runType": tool_call["parameters"].get("runType"),
                    "runScenario": tool_call["parameters"].get("runScenario", "Base"),
                    "timestamp": tool_response.data.get("startTime", "unknown")
                })
                
                # Update shared context
                await self.context_manager.update_shared_context(
                    conversation_id,
                    self.agent_id,
                    {
                        "active_run_id": run_id,
                        "run_type": tool_call["parameters"].get("runType"),
                        "run_scenario": tool_call["parameters"].get("runScenario", "Base")
                    }
                )