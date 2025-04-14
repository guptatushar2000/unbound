from typing import TypedDict, Optional, List, Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.base_agent import BaseAgent
from app.agents.batch_agent import BatchAgent
from app.agents.results_agent import ResultsAgent
from app.config.agent_registry import agent_registry

class ChatState(TypedDict, total=False):
    """State of the chat."""
    messages: List[Dict[str, Any]]
    current_intent: str
    intent_history: List[Dict[str, Any]]
    agent_id: Optional[str]

class LangGraphEngine:

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
        )

        self.agents = self._load_agents()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(ChatState)

        builder.add_node("agent_router", self._agent_router)
        builder.add_edge(START, "agent_router")
        builder.add_edge("agent_router", END)
        builder.add_conditional_edges("agent_router", lambda state: state["current_intent"])

        for agent in self.agents:
            obj = BaseAgent(**agent)
            builder.add_node(agent["id"], obj.process)
            builder.add_edge(agent["id"], "agent_router")

        return builder.compile()
    
    def _load_agents(self):
        """Load the agents from the registry."""
        agents = []
        for agent in agent_registry:
            if "id" in agent and "description" in agent:
                agents.append(agent)
        return agents

    async def _agent_router(self, state: ChatState) -> str:
        """Routes the state to the appropriate agent based on the current intent."""
        user_message = state["messages"][-1]["content"] if state["messages"] else ""
        agents = "\n".join(
            f"- AgentId: {agent["id"]}, AgentDescription: {agent["description"]}"
            for index, agent in enumerate(agent_registry)
            if "id" in agent and "description" in agent
        )
        system_prompt = f"""
            You are a routing agent for a financial chatbot. Your job is to determine which agent should handle the user's message.
            The options for agents are:
            {agents}
            - AgentId: END, AgentDescription: Finish processing and return the final answer
            - AgentId: END, AgentDescription: If the assistant requests additional information

            The user query: {user_message}
            Conversation history: {state["messages"]}
            Based on the user query, ONLY RESPOND WITH THE AGENT ID that should handle it.
        """

        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])
        agent_id = response.content.strip()

        new_state = dict(state)
        new_state["current_intent"] = agent_id
        if agent_id not in [agent["id"] for agent in agent_registry]:
            new_state["current_intent"] = "END"
        return new_state
    
    async def process_message(self, message: str):
        state: ChatState = {
            "messages": [
                {
                    "role": "user",
                    "content": message
                }
            ]
        }

        original_message_count = len(state["messages"])

        try:
            result = await self.graph.ainvoke(state)
        except Exception as e:
            pass

        assistant_messages = [msg for msg in result["messages"][original_message_count:]
                              if msg["role"] == "assistant"]
        
        if not assistant_messages:
            response = "No response from assistant."
        else:
            response = "\n\n".join([msg["content"] for msg in assistant_messages])

        return {
            "response": response
        }
