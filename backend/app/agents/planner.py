import json
import structlog
from typing import List, Dict, Any
from app.state.models import RentalSession, ConversationMessage
from app.tools.search import SearchListingsTool
from app.core.config import settings
from openai import AsyncOpenAI

logger = structlog.get_logger()

class RentalAgent:
    def __init__(self):
        self.tools = {
            "search_listings": SearchListingsTool()
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
                    result = await tool_instance.execute(**arguments)
                    
                    # Store result in history
                    # We serialize for the LLM history (string)
                    result_str = json.dumps(result, default=str)
                    session.conversation_history.append(ConversationMessage(
                        role="tool",
                        content=result_str,
                        tool_call_id=tool_call.id,
                        name=function_name
                    ))
                    
                    # For the frontend, we want structured data but JSON safe (no datetimes)
                    # We can reuse the stringified version or re-parse it to ensure valid JSON types
                    tool_results.append({
                        "name": function_name,
                        "result": json.loads(result_str)
                    })
                else:
                    logger.error(f"Tool not found: {function_name}")
            
            # Recursive call with tool results
            # We return a merged response so the frontend knows what happened
            # Optionally we can just recurse and return the final text, 
            # but usually we want to stream tool calls to frontend too.
            # detailed agent loop. 
            
            # Recurse
            final_response = await self.run_turn(session, user_message=None)
            
            # Merge tool info for frontend awareness if needed, 
            # but for now assume final_response contains the text we need.
            # We might want to inject `tool_results` into the return dict for frontend display
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
        system_prompt = """You are a helpful and knowledgeable Rental Agent. 
        Your goal is to help users find rental properties that match their needs.
        
        You have access to a tool 'search_listings' to find properties.
        ALWAYS use the search tool when the user asks for listings or specific criteria.
        
        When replying:
        1. Be friendly and professional.
        2. If you find listings, summarize the top 3-4 most relevant ones in your text response, highlighting why they match.
        3. If no listings match, ask clarifying questions to adjust parameters.
        4. Ask about budget, location, and bedroom count if not provided.
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
