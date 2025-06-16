from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """
    Protocol for a callable tool.
    """

    name: str
    description: str
    parameters: dict[str, Any]

    @abstractmethod
    async def call(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        if False:
            yield
        raise NotImplementedError


class ToolRegistry:
    """
    Registry for available tools.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str):
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry.")
        return self._tools[name]

    def all_tools(self) -> dict[str, Tool]:
        return self._tools.copy()

    def get_tool_schema(self) -> list[dict[str, Any]]:
        schema_list = []
        for tool_name, tool_instance in self._tools.items():
            if not hasattr(tool_instance, "description") or not hasattr(
                tool_instance, "parameters"
            ):
                continue

            schema = {
                "type": "function",
                "function": {
                    "name": tool_instance.name,
                    "description": tool_instance.description,
                    "parameters": tool_instance.parameters,
                },
            }
            schema_list.append(schema)
        return schema_list
