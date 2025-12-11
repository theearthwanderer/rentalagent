import json
import structlog
from typing import List, Dict, Any
from app.state.models import RentalSession, ConversationMessage
from app.tools.search import SearchListingsTool
from app.tools.listings import GetListingDetailsTool
from app.core.config import settings
from openai import AsyncOpenAI

logger = structlog.get_logger()

class RentalAgent:
    def __init__(self):
        self.tools = {
            "search_listings": SearchListingsTool(),
            "get_listing_details": GetListingDetailsTool()
        }
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o" # or gpt-4-turbo

    async def run_turn(self, session: RentalSession, user_message: str | None = None) -> Dict[str, Any]:
        """
        Run a turn of the conversation.
        If user_message is provided, it's added to history.
        Recursively handles tool calls.
        """
        if user_message:
            session.conversation_history.append(ConversationMessage(role="user", content=user_message))
        
        # Build messages for LLM
        messages = self._build_ops_messages(session)
        
        # Define Tools
        tools_schema = [t.to_openai_function_schema() for t in self.tools.values()]
        
        logger.info("Calling LLM", model=self.model)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools_schema,
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        # Update history with Assistant message
        session.conversation_history.append(ConversationMessage(
            role="assistant",
            content=message.content,
            tool_calls=[tc.model_dump() for tc in message.tool_calls] if message.tool_calls else None
        ))
        
        # Handle Tool Calls
        if message.tool_calls:
            logger.info("Processing tool calls", count=len(message.tool_calls))
            tool_results = []
            
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                
                tool_instance = self.tools.get(function_name)
                if tool_instance:
                    logger.info(f"Executing tool: {function_name}", args=arguments)
                    raw_result = await tool_instance.execute(**arguments)
                    
                    # Sanitize result (convert datetimes to strings) for both LLM and Frontend
                    result_str = json.dumps(raw_result, default=str)
                    result = json.loads(result_str)
                    
                    # Special handling for search_listings to save tokens
                    if function_name == "search_listings":
                        # Create a summary for the LLM
                        count = len(result)
                        top_ids = [r.get('id') for r in result[:3]]
                        summary = f"Found {count} listings. Top 3 IDs: {top_ids}. Full results sent to UI."
                        # Summarized history for LLM
                        history_content = json.dumps({"summary": summary, "top_results": result[:5]}, default=str)
                    else:
                        # Standard handling for other tools
                        history_content = json.dumps(result, default=str)

                    # Store result in history (Optimized)
                    session.conversation_history.append(ConversationMessage(
                        role="tool",
                        content=history_content,
                        tool_call_id=tool_call.id,
                        name=function_name
                    ))
                    
                    # For the frontend, pass the FULL result
                    tool_results.append({
                        "name": function_name,
                        "result": result # Send full list to UI (including all 50 items)
                    })
                else:
                    logger.error(f"Tool not found: {function_name}")
            
            # Recursive call with tool results
            final_response = await self.run_turn(session, user_message=None)
            
            # Merge tool info for frontend display
            if "tool_results" not in final_response:
                final_response["tool_results"] = []
            final_response["tool_results"].extend(tool_results)
            
            # Also merge current turn's tool calls
            tool_calls_data = [
                {"name": tc.function.name, "arguments": json.loads(tc.function.arguments)} 
                for tc in message.tool_calls
            ]
            if "tool_calls" not in final_response:
                final_response["tool_calls"] = []
            final_response["tool_calls"].extend(tool_calls_data)
            
            return final_response

        else:
            # Final text response
            return {
                "role": "assistant",
                "content": message.content
            }

    def _build_ops_messages(self, session: RentalSession) -> List[Dict[str, Any]]:
        system_prompt = """You are Havena, an advanced AI Rental Agent.
        
        CAPABILITIES:
        1. Search: You can search by price, beds, baths, location, and specific amenities (pets, parking, laundry, AC).
        2. Vibe: You can filter by 'vibe score' (0-5) or semantic queries like "quiet", "sunny", "safe".
        3. Details: You can retrieve full details for a specific listing using 'get_listing_details'.
        
        BEHAVIOR:
        - STATEFUL SEARCH: If the user says "make it cheaper" or "add parking", you must CALL search_listings AGAIN with the new filters merged with the previous ones.
        - TOKEN EFFICIENCY: The search tool returns a summary to you. Trust that the full list is shown to the user in the UI.
        - COMPARISON: If asked to compare, fetch details for the relevant listings and give a side-by-side analysis.
        - COMMUTE: You can discuss transport scores and nearby transit if available in the description/metadata.
        
        When replying, be concise, helpful, and professional.
        """
        
        msgs = [{"role": "system", "content": system_prompt}]
        
        for m in session.conversation_history:
            msg_dict = {"role": m.role}
            if m.content:
                msg_dict["content"] = m.content
            if m.tool_calls:
                msg_dict["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                msg_dict["tool_call_id"] = m.tool_call_id
            # 'name' is not strictly required for tool role in some API versions but good to have
            if m.role == "tool" and m.name:
                pass 
            msgs.append(msg_dict)
            
        return msgs
