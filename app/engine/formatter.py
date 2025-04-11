# app/engine/formatter.py
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import settings

class OutputFormatter:
    """Formats and enhances agent responses for consistency"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.model.MODEL_NAME,
            temperature=settings.model.MODEL_TEMPERATURE,
            openai_api_key=settings.api.OPENAI_API_KEY
        )
    
    async def format_output(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Format the final response with consistent style and voice"""
        # Only generate a response if no agent has responded yet
        latest_message = state["messages"][-1] if state["messages"] else None
        
        if not latest_message or latest_message["role"] != "assistant":
            # Create a context-aware prompt for the formatter
            system_prompt = """
            You are the consistent voice of a financial chatbot system. Your job is to:
            
            1. Maintain a consistent, professional tone across all responses
            2. Ensure clarity and completeness in all communications
            3. Add a personalized touch where appropriate
            
            If the user's request couldn't be processed by our specialized agents, provide a helpful response.
            Always be concise, helpful, and friendly while maintaining a consistent voice.
            """
            
            # Get conversation history for context
            history_text = "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in state["messages"][-5:]  # Last 5 messages for context
            ])
            
            # Generate response using GPT-4o
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Conversation history:\n{history_text}\n\nHow should I respond to the user's last message?")
            ])
            
            # Update state with the response
            new_state = dict(state)
            new_state["messages"].append({
                "role": "assistant",
                "content": response.content,
                "agent_id": "formatter"
            })
            
            return new_state
        
        # If an agent already responded but it was a multi-part workflow
        elif latest_message and latest_message["role"] == "assistant":
            # Check if we need to add any cross-agent contextual information
            intent = state.get("current_intent")
            
            # If we just finished a batch run, and previous intent was about results
            if intent == "BATCH" and "batch_agent" in state.get("agent_outputs", {}) and "runId" in state["agent_outputs"]["batch_agent"]:
                # Get run ID
                run_id = state["agent_outputs"]["batch_agent"]["runId"]
                
                # Check previous messages for results intent
                previous_intents = [item.get("intent") for item in state.get("intent_history", [])]
                if "RESULTS" in previous_intents[-3:]:  # Check last 3 intents
                    # Add helpful cross-context information
                    new_state = dict(state)
                    new_state["messages"].append({
                        "role": "assistant",
                        "content": f"Now that your run (ID: {run_id}) has been started, you can check its status anytime. Once it completes, you can retrieve the results by asking me for stress test results or allowance results.",
                        "agent_id": "formatter"
                    })
                    return new_state
        
        # Otherwise just pass through the state
        return state