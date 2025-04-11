# app/engine/langgraph_engine.py
from typing import TypedDict, List, Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import uuid
import time

from app.core.config import settings
from app.core.db import StateManager
from app.agents.batch_agent import BatchAgent
from app.agents.results_agent import ResultsAgent
from app.utils.context_manager import SharedContextManager
from app.engine.entity_extractor import EntityExtractor
from app.engine.formatter import OutputFormatter

class ChatState(TypedDict, total=False):
    """Type definition for chat state"""
    conversation_id: str
    user_id: str
    user_groups: List[str]
    messages: List[Dict[str, Any]]
    current_intent: Optional[str]
    entities: Dict[str, Any]
    agent_outputs: Dict[str, Any]
    intent_history: List[Dict[str, str]]

class LangGraphEngine:
    """Main engine powering the chatbot using LangGraph"""
    
    def __init__(self, state_manager: StateManager, api_manager):
        """Initialize the LangGraph engine"""
        self.state_manager = state_manager
        self.api_manager = api_manager
        
        # Create shared context manager
        self.context_manager = SharedContextManager()
        
        # Initialize entity extractor
        self.entity_extractor = EntityExtractor()
        
        # Initialize output formatter
        self.output_formatter = OutputFormatter()
        
        # Initialize intent classifier
        self.llm = ChatOpenAI(
            model=settings.model.MODEL_NAME, 
            temperature=settings.model.MODEL_TEMPERATURE,
            openai_api_key=settings.api.OPENAI_API_KEY
        )
        
        # Initialize specialized agents
        self.batch_agent = BatchAgent(api_manager, self.context_manager)
        self.results_agent = ResultsAgent(api_manager, self.context_manager)
        
        # Build and compile the graph
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        # Create a graph with our ChatState schema
        builder = StateGraph(ChatState)
        
        # Add nodes for each stage of processing
        builder.add_node("intent_classifier", self._intent_classifier)
        builder.add_node("entity_extractor", self._entity_extractor)
        builder.add_node("batch_agent", self.batch_agent.process)
        builder.add_node("results_agent", self.results_agent.process)
        builder.add_node("output_formatter", self.output_formatter.format_output)
        
        # Add conditional edges from START to intent classifier
        builder.add_edge(START, "intent_classifier")
        
        # Intent classifier to entity extractor
        builder.add_edge("intent_classifier", "entity_extractor")
        
        # Add conditional edges from entity extractor to agents
        builder.add_conditional_edges(
            "entity_extractor",
            self._route_to_agent,
            {
                "batch": "batch_agent",
                "results": "results_agent",
                "unknown": "output_formatter"
            }
        )
        
        # All agents go to output formatter
        builder.add_edge("batch_agent", "output_formatter")
        builder.add_edge("results_agent", "output_formatter")
        
        # Output formatter goes to END
        builder.add_edge("output_formatter", END)
        
        # Compile the graph
        return builder.compile()
    
    async def _intent_classifier(self, state: ChatState) -> ChatState:
        """Classify the user's intent using GPT-4o"""
        # Extract the latest user message
        user_message = state["messages"][-1]["content"] if state["messages"] else ""
        
        # Create a prompt for intent classification
        system_prompt = """
        You are an intent classifier for a financial chatbot. Your job is to determine if the user's message is related to:
        
        1. Batch processing (starting runs, checking status, logs, etc.)
        2. Results retrieval (getting stress test results, allowance results, etc.)
        3. Something else (general questions, greetings, etc.)
        
        Respond with only one word: "BATCH", "RESULTS", or "UNKNOWN".
        """
        
        # Get classification from GPT-4o
        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        
        # Extract the intent
        intent = response.content.strip().upper()
        if intent not in ["BATCH", "RESULTS", "UNKNOWN"]:
            # Default to UNKNOWN if response is not one of the expected values
            intent = "UNKNOWN"
        
        # Update state
        new_state = dict(state)
        new_state["current_intent"] = intent
        
        return new_state
    
    async def _entity_extractor(self, state: ChatState) -> ChatState:
        """Extract entities from the user's message"""
        user_message = state["messages"][-1]["content"] if state["messages"] else ""
        intent = state.get("current_intent", "UNKNOWN")
        
        # Extract entities
        entities = await self.entity_extractor.extract_entities(intent, user_message)
        
        # Update state
        new_state = dict(state)
        new_state["entities"] = entities
        
        return new_state
    
    def _route_to_agent(self, state: ChatState) -> Literal["batch", "results", "unknown"]:
        """Route to appropriate agent based on classified intent"""
        intent = state.get("current_intent", "UNKNOWN")
        
        if intent == "BATCH":
            return "batch"
        elif intent == "RESULTS":
            return "results"
        else:
            return "unknown"
    
    async def process_message(self, user_id: str, message: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a message from the user"""
        # Get or create conversation
        if conversation_id:
            state = self.state_manager.get_conversation_state(conversation_id)
            if not state:
                conversation_id = self.state_manager.create_conversation(user_id)
                state = self.state_manager.get_conversation_state(conversation_id)
        else:
            conversation_id = self.state_manager.create_conversation(user_id)
            state = self.state_manager.get_conversation_state(conversation_id)
        
        # Ensure conversation_id is in the state
        state["conversation_id"] = conversation_id
        
        # Get user groups
        user_groups = settings.USER_GROUPS.get(user_id, ["basic-users"])
        state["user_groups"] = user_groups
        
        # Track intent history
        if "intent_history" not in state:
            state["intent_history"] = []
        if "current_intent" in state:
            state["intent_history"].append({"intent": state["current_intent"]})
            # Keep only last 10 intents
            state["intent_history"] = state["intent_history"][-10:]
        
        # Add message to state
        if "messages" not in state:
            state["messages"] = []
            
        state["messages"].append({
            "role": "user",
            "content": message
        })
        
        # Run the graph
        try:
            result = await self.graph.ainvoke(state)
        except Exception as e:
            pass
        
        # Save updated state
        self.state_manager.save_conversation_state(conversation_id, result)
        
        # Extract assistant's responses (might be multiple from different components)
        assistant_messages = [msg for msg in result["messages"] 
                            if msg["role"] == "assistant" and 
                            result["messages"].index(msg) > state["messages"].index(state["messages"][-1])]
        
        if not assistant_messages:
            response = "I'm not sure how to respond to that."
        else:
            # Combine responses if there are multiple (unusual but possible)
            response = "\n\n".join([msg["content"] for msg in assistant_messages])
        
        return {
            "conversation_id": conversation_id,
            "response": response
        }