from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

from app.agents.batch_agent import BatchAgent
from app.agents.results_agent import ResultsAgent

class ChatState(TypedDict, total=False):
    """State of the chat."""
    messages: List[Dict[str, Any]]

class LangGraphEngine:

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
        )

        self.batch_agent = BatchAgent()
        self.results_agent = ResultsAgent()

        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(ChatState)

        # builder.add_node("batch_agent", self.batch_agent.process)
        builder.add_node("results_agent", self.results_agent.process)

        # builder.add_edge(START, "batch_agent")
        # builder.add_edge("batch_agent", END)

        builder.add_edge(START, "results_agent")
        builder.add_edge("results_agent", END)

        return builder.compile()
    
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
