# app/agents/base_agent.py
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import re
import json
import time

from app.core.config import settings
from app.utils.mcp_tools import MCPTool, MCPToolResponse

class BaseAgent:
    """Base class for all agents providing shared functionality"""
    
    def __init__(self, agent_id: str, api_manager, context_manager, system_prompt_template: str, tools: List[MCPTool]):
        self.agent_id = agent_id
        self.api_manager = api_manager
        self.context_manager = context_manager
        self.system_prompt_template = system_prompt_template
        self.tools = tools
        
        # Initialize GPT-4o model
        self.llm = ChatOpenAI(
            model=settings.model.MODEL_NAME,
            temperature=settings.model.MODEL_TEMPERATURE,
            openai_api_key=settings.api.OPENAI_API_KEY
        )
    
    def _create_system_prompt(self, shared_context: Dict[str, Any]) -> str:
        """Create system prompt with tool definitions and context"""
        tools_description = "\n\n".join([
            f"Tool: {tool.name}\n"
            f"Description: {tool.description}\n"
            f"Parameters: {', '.join([f'{p.name} ({p.type}{'' if p.required else ', optional'})' for p in tool.parameters])}\n"
            for tool in self.tools
        ])
        
        # Process active_run_id specially
        active_run_id = shared_context.get('active_run_id')
        if active_run_id:
            shared_context['active_run_id'] = f"- Active run ID: {active_run_id}"
        
        # Process recent_run_types specially
        recent_run_types = shared_context.get('recent_run_types')
        if recent_run_types and len(recent_run_types) > 0:
            shared_context['recent_run_types'] = f"- Recently discussed run types: {', '.join(recent_run_types)}"
        
        # Make sure all required keys exist with defaults
        required_keys = ['conversation_summary', 'recent_user_messages']
        for key in required_keys:
            if key not in shared_context or shared_context[key] is None:
                if key == 'recent_user_messages':
                    shared_context[key] = []
                else:
                    shared_context[key] = ""
        
        # Fill in the template
        try:
            system_prompt = self.system_prompt_template.format(
                tools=tools_description,
                **shared_context
            )
            return system_prompt
        except KeyError as e:
            # Fall back to a simpler prompt if formatting fails
            print(f"Warning: Error formatting system prompt: {e}")
            return f"""You are a Financial Assistant. You have access to tools: {tools_description}"""
    
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process user query using MCP and GPT-4o"""
        # Get shared context
        conversation_id = state.get("conversation_id")
        shared_context = await self.context_manager.get_shared_context(conversation_id, self.agent_id)
        
        # Extract the conversation history
        messages = self._extract_conversation_history(state)
        
        # Create system prompt with context
        system_prompt = self._create_system_prompt(shared_context)
        
        # Add system message at the beginning
        messages.insert(0, SystemMessage(content=system_prompt))
        
        # Get response from GPT-4o
        ai_response = await self.llm.ainvoke(messages)
        ai_content = ai_response.content
        
        # Check if the model's response contains a tool call
        tool_call = self._extract_tool_call(ai_content)
        response_text = ""
        
        if tool_call:
            # Execute the tool call
            tool_response = await self.api_manager.execute_tool(
                tool_call["tool_name"], 
                tool_call["parameters"]
            )
            
            # Process tool-specific results and update shared context
            await self._process_tool_results(state, tool_call, tool_response)
            
            # Generate a response based on the tool result
            context_with_result = messages + [
                AIMessage(content=ai_content),
                SystemMessage(content=f"Tool response: {tool_response.model_dump_json()}\n\nNow, provide a helpful response to the user based on this tool output. Format any structured data for readability.")
            ]
            
            final_response = await self.llm.ainvoke(context_with_result)
            response_text = final_response.content
        else:
            # If no tool call was made, just use the AI's response
            response_text = ai_content
        
        # Update state with the response
        return self._update_state(state, response_text)
    
    async def _process_tool_results(self, state: Dict[str, Any], tool_call: Dict[str, Any], 
                                   tool_response: MCPToolResponse) -> None:
        """Process tool results and update shared context"""
        # Override in subclasses to handle specific tool results
        pass
    
    def _extract_conversation_history(self, state: Dict[str, Any]) -> List:
        """Extract conversation history in LangChain message format"""
        history = []
        
        for msg in state.get("messages", []):
            if msg["role"] == "user":
                history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant" and msg.get("agent_id") == self.agent_id:
                history.append(AIMessage(content=msg["content"]))
        
        # If there are no messages from this agent yet, just include the latest user message
        if not any(isinstance(msg, AIMessage) for msg in history):
            latest_user_msg = next((msg for msg in reversed(state.get("messages", [])) 
                                    if msg["role"] == "user"), None)
            if latest_user_msg:
                history = [HumanMessage(content=latest_user_msg["content"])]
        
        return history
    
    def _extract_tool_call(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract tool call from GPT-4o response (simple JSON extraction)"""
        # Try to find JSON object in the response
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if not json_match:
            json_match = re.search(r'{[\s\S]*"tool_name"[\s\S]*}', content)
        
        if json_match:
            try:
                tool_call_text = json_match.group(1) if "```json" in content else json_match.group(0)
                tool_call = json.loads(tool_call_text)
                
                # Check if this is a valid MCP tool call
                if "tool_name" in tool_call and "parameters" in tool_call:
                    return tool_call
            except Exception as e:
                print(f"Error parsing tool call: {str(e)}")
        
        return None
    
    def _update_state(self, state: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Update the state with a new message"""
        new_state = dict(state)
        
        # Ensure agent_outputs exists
        if "agent_outputs" not in new_state:
            new_state["agent_outputs"] = {}
        
        # Ensure agent-specific outputs exist
        if self.agent_id not in new_state["agent_outputs"]:
            new_state["agent_outputs"][self.agent_id] = {}
        
        # Add to messages
        if "messages" not in new_state:
            new_state["messages"] = []
            
        new_state["messages"].append({
            "role": "assistant",
            "content": message,
            "agent_id": self.agent_id
        })
        
        return new_state