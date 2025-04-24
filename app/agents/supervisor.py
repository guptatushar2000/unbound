import json
from typing import Any, Dict, List, Optional
from openai import OpenAI
from pydantic import BaseModel, PrivateAttr

class Supervisor(BaseModel):
    agents: List[Dict[str, Any]]
    supervisor_prompt: Optional[str] = """
    You are a Supervisor AI agent responsible for evaluating whether a given LLM agent's response is correct based on the original query that the user asked from that agent and the tools that were available to the agent.

    [CAUSE] User Query: {query}

    [EFFECT] Response from Agent: {response}

    Tools available to Agent: {agents}

    [CONTEXT] You can the following conversation for more context: {conversation_history}

    Your task is to determine whether the response is valid or not.
    Respond strictly in the following format:
    {{
        "is_valid": true/false,
        "needs_feedback": [TRUE IF AGENT REQUESTS SOME INFORMATION FROM USER OR RAISES SOME ERROR ELSE FALSE],
        "is_job_done": [TRUE IF AGENT COMPLETED THE USER REQUESTED TASK ELSE FALSE],
        "keywords": {{DICTIONARY OF KEY DETAILS LIKE RUN ID, STATUS, ETC.}}
    }}

    Understand the difference between "is_valid" and "is_job_done" through the following examples:
    - User Query: "Check the status of run ID 12345"
    - Agent Response: "The status of run ID 12345 is 'running'."
        -- is_valid: true
        -- is_job_done: false

    ASSUME THAT AGENTS ARE HONEST AND DO NOT LIE. YOU NEED NOT VALIDATE FACTUAL ACCURACY OF THE RESPONSE.

     - Example of a valid query and response:
     [CAUSE] User Query: "Trigger a batch run for CCAR"
     [EFFECT] Response from Agent: "I have started the batch run for CCAR. The run ID is 12345."

     [CAUSE] User Query: "Trigger a test run"
     [EFFECT] Response from Agent: "The test run has been completed successfully. The run ID is 67890."

     [CAUSE] User Query: "What is the status of run ID 12345?"
     [EFFECT] Response from Agent: "The status of run ID 12345 is 'completed'."
    """

    _client = PrivateAttr(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        self._client = OpenAI()

    def _validate_response(self, response: str, subtask: Dict[str, Any], conversation_history: List[Dict[str, str]]):
        response = self._client.responses.create(
            model="o4-mini-2025-04-16",
            reasoning={"effort": "medium"},
            input=[{
                "role": "user",
                "content": self.supervisor_prompt.format(
                    response=response, 
                    query=subtask["description"], 
                    agents=self.agents,
                    conversation_history=conversation_history)
            }]
        )

        try:
            status = json.loads(response.output_text.strip())
        except Exception as e:
            status = json.loads({"is_valid": False, "feedback": f"Error parsing response: {str(e)}"})
        return status

    def process(self, state: Dict[str, Any]):
        new_state = dict(state)

        agent_response = next((msg["content"] for msg in reversed(state["messages"]) if msg["role"] == "assistant"), "")
        
        if "task_plan" not in new_state or not new_state.get("subtasks") or new_state["task_plan"]["task_type"] == "SIMPLE":
            return new_state
        
        current_subtask = new_state["current_subtask"]
        conversation_history = new_state.get("conversation_history", [])
        status = self._validate_response(agent_response, current_subtask, conversation_history)

        if not status["is_valid"] or status["needs_feedback"]:
            new_state["agent_id"] = "END"
            return new_state
        
        new_state["conversation_history"].append({
            "user_query": current_subtask["description"],
            "assistant_response": agent_response,
            "keywords": status["keywords"]
        })

        if not status["is_job_done"]:
            return new_state
        
        if "completed_subtasks" not in new_state:
            new_state["completed_subtasks"] = []

        subtask_id = new_state["current_subtask"]["id"]
        if subtask_id not in new_state["completed_subtasks"]:
            new_state["completed_subtasks"].append(subtask_id)

        if len(new_state["completed_subtasks"]) == len(new_state["subtasks"]):
            new_state["agent_id"] = "END"
            return new_state
        
        return new_state
