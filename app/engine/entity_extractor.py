# app/engine/entity_extractor.py
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re

from app.core.config import settings

class EntityExtractor:
    """Extracts entities from user messages based on intent"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.model.MODEL_NAME,
            temperature=0.0,  # Use low temperature for deterministic extraction
            openai_api_key=settings.api.OPENAI_API_KEY
        )
    
    async def extract_entities(self, intent: str, message: str) -> Dict[str, Any]:
        """Extract entities from a user message based on intent"""
        # Create a prompt for entity extraction based on intent
        system_prompt = f"""
        You are an entity extraction system for a financial chatbot. The user's message has been classified as {intent}.
        
        Based on this intent, extract the following entities in JSON format:
        
        For BATCH intent:
        - run_type: The type of run (CCAR, RiskApetite, Stress), if mentioned
        - run_scenario: The scenario for the run, if mentioned
        - run_id: Any run ID mentioned in the message
        - action: The specific action (start, status, kill, log), if clear
        
        For RESULTS intent:
        - result_type: The type of results (stress, allowance), if mentioned
        - run_type: The type of run (CCAR, RiskApetite, Stress), if mentioned
        - cob_date: Any date mentioned in format YYYYMMDD
        - scenario: The scenario mentioned
        
        Return your response as a JSON object with the relevant fields. If an entity is not present, exclude it.
        """
        
        # Get entity extraction from GPT-4o
        response = await self.llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=message)
        ])
        
        # Try to extract JSON from the response
        entities = {}
        json_match = re.search(r'{.*}', response.content, re.DOTALL)
        if json_match:
            try:
                entities = json.loads(json_match.group(0))
            except:
                # If JSON parsing fails, just continue with empty entities
                pass
        
        return entities