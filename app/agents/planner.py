from typing import Any, Dict, List, Optional
import json
import httpx
from openai import OpenAI
from pydantic import BaseModel, PrivateAttr

class Planner(BaseModel):
    agents: List[Dict[str, Any]]
    planner_prompt: Optional[str] = """
    You are a task planning agent for a financial assistant. Your job is to determine if this query needs:
    1. A simple single-agent response
    2. A complex multi-agent workflow

    For COMPLEX tasks, break the query into subtasks and assign each to the most appropriate agent.

    Available agents:
    {}

    If this is a SIMPLE task, respond with:
    {{
        "task_type": "SIMPLE",
        "primary_agent": "[AGENT_ID]"
    }}

    If this is a COMPLEX task, respond with:
    {{
        "task_type": "COMPLEX",
        "subtasks": [
            {{"id": "subtask1", "description": "...", "agent": "[AGENT_ID]", "depends_on": []}},
            {{"id": "subtask2", "description": "...", "agent": "[AGENT_ID]", "depends_on": ["subtask1"]}}
        ]
    }}
    """

    _client = PrivateAttr(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        # await self._enrich_agents_with_tools()
        self._client = OpenAI()

    # @classmethod
    # async def create(cls, agents: List[Dict[str, Any]]):
    #     instance = cls(agents=agents)
    #     await instance._enrich_agents_with_tools()
    #     instance._client = OpenAI()
    #     return instance

    async def _enrich_agents_with_tools(self):
        for agent in self.agents:
            if "mcp_url" in agent:
                agent["tools"] = await self._get_all_mcp_functions(agent["mcp_url"])
            else:
                agent["tools"] = []
        
    async def _get_all_mcp_functions(self, mcp_url: str):
        all_functions = []
        tools = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{mcp_url}/.well-known/mcp")
                if response.status_code == 200:
                    mcp_schema = response.json()
                    functions = mcp_schema.get("functions", [])
                    all_functions.extend(functions)
        except Exception as e:
            print(f"Error fetching functions from {mcp_url}: {str(e)}")

        for func in all_functions:
            tools.append({
                "name": func["name"],
                "description": func["description"],
                "parameters": func["parameters"]
            })
        return tools

    def _plan_llm_tasks(self, user_message: str):
        # agents_list = "\n".join(
        #     f"- AgentId: {agent['id']}, AgentDescription: {agent['description']}"
        #     for agent in self.agents
        # )
        conversation_history = [
            {"role": "system", "content": self.planner_prompt.format(self.agents, user_message)},
            {"role": "user", "content": user_message}
        ]

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history,
            temperature=0
        )

        try:
            plan = json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            plan = {
                "task_type": "SIMPLE",
                "primary_agent": self.agents[0]["id"]
            }
        return plan
    
    async def process(self, state: Dict[str, Any]):
        new_state = dict(state)
        user_message = next((msg["content"] for msg in reversed(state["messages"]) if msg["role"] == "user"), "")

        # breakpoint()
        await self._enrich_agents_with_tools()

        response = self._plan_llm_tasks(user_message)

        new_state["task_plan"] = response
        new_state["error_count"] = 0

        if response["task_type"] == "COMPLEX":
            new_state["subtasks"] = response["subtasks"]
            new_state["completed_subtasks"] = []
            for subtask in response["subtasks"]:
                if not subtask["depends_on"]:
                    break
        else:
            new_state["current_intent"] = response["primary_agent"]

        if "conversation_history" not in new_state:
            new_state["conversation_history"] = []
        new_state["conversation_history"] = []
        return new_state
