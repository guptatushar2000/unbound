from typing import Dict, Any
import json
import httpx
import requests
import copy
from openai import OpenAI

class ResultsAgent:
    def __init__(self):
        self._client = OpenAI()
        self._mcp_service = "results_service"
        self._mcp_url = "http://localhost:8080/mcp"
        # self._mcp_function_to_service = {}
        self._conversation_history = [{
            "role": "system",
            "content": """
                You are an assistant that helps users with retrieving batch results. 
                
                You can:
                1. Retrieve stress batch results (which provide DS2.xlsx)
                2. Retrieve allowance batch results (which provide DS1.xlsx)

                - For complex workflows, you should break them down into steps.
                - Use proper parameters for each type of request."""
            }]
        
    async def _get_all_mcp_functions(self):
        all_functions = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self._mcp_url}/.well-known/mcp")
                if response.status_code == 200:
                    mcp_schema = response.json()
                    functions = mcp_schema.get("functions", [])
                    all_functions.extend(functions)
        except Exception as e:
            print(f"Error fetching functions from {self._mcp_service}: {str(e)}")
        return all_functions

    async def _mcp_to_openai_functions(self):
        openai_functions = []
        mcp_functions = await self._get_all_mcp_functions()
        for func in mcp_functions:
            openai_functions.append({
                "type": "function",
                "function": {
                    "name": func["name"],
                    "description": func["description"],
                    "parameters": func["parameters"]
                }
            })
        return openai_functions
    
    async def _call_mcp_function(self, function_name: str, function_args: Dict[str, Any]):
        function_url = f"{self._mcp_url}/functions/{function_name}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(function_url, json=function_args)
                if response.status_code >= 400:
                    return {"error": f"API error: {response.text}"}
                return response.json()
        except httpx.RequestError as e:
            return {"error": f"Error calling function {function_name}: {str(e)}"}
        
    async def _chat_with_gpt(self, messages: list) -> str:
        functions = await self._mcp_to_openai_functions()

        local_conversation_history = copy.deepcopy(self._conversation_history)

        local_conversation_history.append({
            "role": "user",
            "content": messages
        })

        while True:
            response = self._client.chat.completions.create(
                model="gpt-4o",
                messages=local_conversation_history,
                tools=functions,
                tool_choice="auto",
                temperature=0,
            )

            assistant_message = response.choices[0].message
            has_content = assistant_message.content is not None and len(assistant_message.content.strip()) > 0
            has_tool_calls = hasattr(assistant_message, "tool_calls") and assistant_message.tool_calls

            local_conversation_history.append(assistant_message.model_dump())

            if has_tool_calls:
                function_calls_made = False

                for tool_call in assistant_message.tool_calls:
                    if tool_call.type == "function":
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)

                        function_response = await self._call_mcp_function(function_name, function_args)

                        local_conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(function_response)
                        })

                        function_calls_made = True

                if function_calls_made:
                    continue

            break
        
        final_message = assistant_message.content if has_content else "I've completed the requested operations."
        self._conversation_history = local_conversation_history
        return final_message

    async def process(self, state: Dict[str, Any]):
        # Placeholder for batch processing logic
        new_state = dict(state)
        last_user_message = next((msg["content"] for msg in reversed(state["messages"]) if msg["role"] == "user"), "")
        response = await self._chat_with_gpt(last_user_message)
        new_state["messages"].append({
            "role": "assistant",
            "content": response
        })
        return new_state
