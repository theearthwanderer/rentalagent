from abc import ABC, abstractmethod
from typing import Any, Dict, List, Type
from pydantic import BaseModel

class Tool(ABC):
    name: str = "base_tool"
    description: str = "Base tool description"
    parameters: Type[BaseModel] | None = None

    def to_openai_function_schema(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function schema"""
        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
            }
        }
        if self.parameters:
            schema["function"]["parameters"] = self.parameters.model_json_schema()
        return schema

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass
