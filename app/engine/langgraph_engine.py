from typing import TypedDict, Optional, List, Dict, Any, Literal
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from openai import OpenAI

from app.agents.base_agent import BaseAgent
from app.agents.batch_agent import BatchAgent
from app.agents.planner import Planner
from app.agents.results_agent import ResultsAgent
from app.agents.supervisor import Supervisor
from app.config.agent_registry import agent_registry

class ChatState(TypedDict, total=False):
    """State of the chat."""
    messages: List[Dict[str, Any]]
    current_intent: str
    intent_history: List[Dict[str, Any]]
    agent_id: Optional[str]

    subtasks: List[Dict[str, Any]]
    completed_subtasks: List[str]
    current_subtask: Optional[Dict[str, Any]]
    task_plan: Optional[Dict[str, Any]]
    conversation_history: Optional[List[Dict[str, Any]]]
    error_count: int

class LangGraphEngine:

    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
        )

        self.agents = self._load_agents()
        self.planner = Planner(agents=self.agents)
        self.supervisor = Supervisor(agents=self.agents)
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(ChatState)

        builder.add_node("planner", self.planner.process)
        builder.add_node("agent_router", self._step_router)
        builder.add_node("task_supervisor", self.supervisor.process)

        builder.add_edge(START, "planner")
        builder.add_edge("planner", "agent_router")
        # builder.add_edge("agent_router", END)
        # builder.add_conditional_edges("agent_router", lambda state: state["current_intent"])

        for agent in self.agents:
            obj = BaseAgent(**agent)
            builder.add_node(agent["id"], obj.process)
            builder.add_edge(agent["id"], "task_supervisor")

        router_map = {
            agent["id"]: agent["id"]
            for agent in self.agents
        }
        router_map["END"] = END

        builder.add_conditional_edges(
            "agent_router",
            lambda state: state.get("agent_id", "END"),
            router_map
        )

        # builder.add_conditional_edges(
        #     "agent_router",
        #     lambda state: END if state.get("current_intent") == "END" else None
        # )

        builder.add_conditional_edges(
            "task_supervisor",
            self._supervisor_condition,
            {
                "COMPLETE": END,
                "CONTINUE": "agent_router"
            }
        )

        return builder.compile()
    
    def _load_agents(self):
        """Load the agents from the registry."""
        agents = []
        for agent in agent_registry:
            if "id" in agent and "description" in agent:
                agents.append(agent)
        return agents

    async def _step_router(self, state: ChatState):
        new_state = dict(state)

        if "task_plan" not in state:
            new_state["agent_id"] = "END"
            return new_state
        
        if new_state["task_plan"]["task_type"] == "SIMPLE":
            primary_agent = new_state["task_plan"].get("primary_agent")
            if primary_agent:
                new_state["agent_id"] = primary_agent
            else:
                new_state["agent_id"] = "END"
        else:
            if not state.get("subtasks"):
                new_state["agent_id"] = "END"
                return new_state

            completed_subtasks = new_state.get("completed_subtasks", [])

            next_subtask = None
            for subtask in new_state["subtasks"]:
                if subtask["id"] not in completed_subtasks:
                    deps_satisfied = all(
                        dep in completed_subtasks for dep in subtask.get("depends_on", [])
                    )
                    if deps_satisfied:
                        next_subtask = subtask
                        break

            if next_subtask:
                agent_id = next_subtask["agent"]
                new_state["current_subtask"] = next_subtask
                new_state["agent_id"] = agent_id

                if agent_id not in [agent["id"] for agent in self.agents]:
                    new_state["agent_id"] = "END"
                    new_state["current_subtask"] = None
            else:
                new_state["agent_id"] = "END"
                new_state["current_subtask"] = None
        return new_state

    # async def _plan_based_router(self, state: ChatState) -> str:
    #     new_state = dict(state)

    #     if "task_plan" in state and state.get("current_intent") == "END":
    #         new_state["agent_id"] = "END"
    #         return new_state
        
    #     if "current_subtask" in state and state["current_subtask"]:
    #         agent_id = state["current_subtask"]["agent"]
    #         if agent_id in [agent["id"] for agent in self.agents]:
    #             new_state["current_intent"] = agent_id
    #             new_state["agent_id"] = agent_id
    #             return new_state
        
    #     if "intent_history" not in state:
    #         new_state["intent_history"] = []

    #     if "current_intent" in state and state["current_intent"]:
    #         new_state["intent_history"].append({
    #             "intent": state["current_intent"],
    #             "message_index": len(state["messages"]) - 1
    #         })

    #     user_message = state["messages"][-1]["content"] if state["messages"] else ""
    #     agents = "\n".join(
    #         f"- AgentId: {agent['id']}, AgentDescription: {agent['description']}"
    #         for agent in self.agents
    #     )

    #     task_context = ""
    #     if "task_plan" in state:
    #         task_context = f"Current task plan: {state['task_plan']}\n"
    #         if "subtasks" in state:
    #             completed = state.get("completed_subtasks", [])
    #             task_context += f"Completed subtasks: {completed}\n"

    #     system_prompt = f"""
    #         You are a routing agent for a financial chatbot. Your job is to determine which agent should handle the user's message.
    #         The options for agents are:
    #         {agents}

    #         {task_context}

    #         The user query: {user_message}
    #         Conversation history: {state["messages"][-5] if len(state["messages"]) > 5 else state["messages"]}

    #         ONLY RESPOND WITH THE AGENT ID that should handle this query.
    #     """

    #     client = OpenAI()
    #     response = client.chat.completions.create(
    #         model="gpt-4o",
    #         messages=[
    #             {"role": "system", "content": system_prompt},
    #             {"role": "user", "content": user_message}
    #         ],
    #         temperature=0
    #     )

    #     agent_id = response.choices[0].message.content.strip()

    #     if agent_id not in [agent["id"] for agent in self.agents]:
    #         new_state["current_intent"] = "END"
    #         new_state["agent_id"] = "END"

    #     new_state["current_intent"] = agent_id
    #     new_state["agent_id"] = agent_id
    #     return new_state
    
    # async def _task_supervisor(self, state: ChatState) -> ChatState:
    #     new_state = dict(state)

    #     if "task_plan" not in state or state["task_plan"]["task_type"] == "SIMPLE":
    #         assistant_message = [msg for msg in state["messages"]
    #                              if msg["role"] == "assistant"]
    #         if assistant_message:
    #             return new_state
    #     else:
    #         if "current_subtask" in state and state["current_subtask"]:
    #             if "completed_subtasks" not in new_state:
    #                 new_state["completed_subtasks"] = []
    #             new_state["completed_subtasks"].append(state["current_subtask"]["id"])

    #             next_subtask = None
    #             for subtask in state["subtasks"]:
    #                 if subtask["id"] not in new_state["completed_subtasks"]:
    #                     deps_satisfied = all(
    #                         dep in new_state["completed_subtasks"]
    #                         for dep in subtask["depends_on"]
    #                     )
    #                     if deps_satisfied:
    #                         next_subtask = subtask
    #                         break
    #             if next_subtask:
    #                 new_state["current_subtask"] = next_subtask
    #                 new_state["current_intent"] = next_subtask["agent"]
    #             else:
    #                 new_state["current_subtask"] = None

    #                 summary_prompt = f"""
    #                     You are a task supervisor agent. Summarize the results of the following subtasks:
                        
    #                     Original query: {state["messages"][-1]["content"] if state["messages"] else ""}

    #                     Task plan: {state["task_plan"]}

    #                     Agent responses:
    #                     {[msg for msg in state["messages"] if msg["role"] == "assistant"]}

    #                     Provide a comprehensive answer that covers all aspects of the user's query.
    #                 """

    #                 client = OpenAI()
    #                 response = client.chat.completions.create(
    #                     model="gpt-4o",
    #                     messages=[{
    #                         "role": "system", 
    #                         "content": summary_prompt
    #                     }],
    #                     temperature=0
    #                 )

    #                 new_state["messages"].append({
    #                     "role": "assistant",
    #                     "content": response.choices[0].message.content.strip()
    #                 })
    #                 new_state["current_intent"] = "END"
    #     return new_state
    
    def _supervisor_condition(self, state: ChatState) -> str:
        if "task_plan" in state and state["task_plan"]["task_type"] == "SIMPLE":
            return "COMPLETE"
        
        if state["agent_id"] == "END":
            return "COMPLETE"

        all_subtasks_completed = (
            "subtasks" in state and
            "completed_subtasks" in state and
            set(state["completed_subtasks"]) == set([task["id"] for task in state["subtasks"]])
            # len(state["completed_subtasks"]) == len(state["subtasks"])
        )

        if all_subtasks_completed:
            return "COMPLETE"
        return "CONTINUE"

    # async def _agent_router(self, state: ChatState) -> str:
    #     """Routes the state to the appropriate agent based on the current intent."""
    #     user_message = state["messages"][-1]["content"] if state["messages"] else ""
    #     agents = "\n".join(
    #         f"- AgentId: {agent["id"]}, AgentDescription: {agent["description"]}"
    #         for index, agent in enumerate(agent_registry)
    #         if "id" in agent and "description" in agent
    #     )
    #     system_prompt = f"""
    #         You are a routing agent for a financial chatbot. Your job is to determine which agent should handle the user's message.
    #         The options for agents are:
    #         {agents}
    #         - AgentId: END, AgentDescription: Finish processing and return the final answer
    #         - AgentId: END, AgentDescription: If the assistant requests additional information

    #         The user query: {user_message}
    #         Conversation history: {state["messages"]}
    #         Based on the user query, ONLY RESPOND WITH THE AGENT ID that should handle it.
    #     """

    #     response = await self.llm.ainvoke([
    #         SystemMessage(content=system_prompt),
    #         HumanMessage(content=user_message)
    #     ])
    #     agent_id = response.content.strip()

    #     new_state = dict(state)
    #     new_state["current_intent"] = agent_id
    #     if agent_id not in [agent["id"] for agent in agent_registry]:
    #         new_state["current_intent"] = "END"
    #     return new_state
    
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
            result = state["messages"].append({
                "role": "assistant",
                "content": f"Error processing the request: {str(e)}"
            })
            pass

        assistant_messages = [msg for msg in result["messages"][original_message_count:]
                              if msg["role"] == "assistant"]
        
        if not assistant_messages:
            response = "No response from assistant."
        else:
            # response = "\n\n".join([msg["content"] for msg in assistant_messages])
            response = assistant_messages[-1]["content"].strip()

        return {
            "response": response
        }
