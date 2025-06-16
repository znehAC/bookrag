import json
import logging
from enum import Enum
from typing import Any, AsyncGenerator, TypedDict, cast

from litellm import acompletion
from litellm.cost_calculator import completion_cost
from litellm.types.completion import ChatCompletionMessageParam
from litellm.types.utils import ModelResponseStream

from agent.memory import ChatMemory
from agent.tools.tool import ToolRegistry
from config import settings

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


class ChunkType(Enum):
    TOOL_CALL = "TOOL_CALL"
    COMPLETION = "COMPLETION"


class Chunk(TypedDict):
    type: ChunkType
    content: str | dict[str, Any]


class ChatSession:
    def __init__(self, chat_id: str, tool_registry: ToolRegistry):
        self.chat_id = chat_id
        self.tool_registry = tool_registry
        self.model = settings.MODEL
        self.api_key = settings.API_KEY.get_secret_value()
        self.memory = ChatMemory(5)

    async def _completion(
        self, messages: list[ChatCompletionMessageParam]
    ) -> AsyncGenerator[Chunk, None]:
        completion = await acompletion(
            model=self.model,
            api_key=self.api_key,
            stream=True,
            tool_choice="auto",
            tools=self.tool_registry.get_tool_schema(),
            messages=messages,
            stream_options={"include_usage": True},
        )
        current_tool_calls: list[dict[str, Any]] = []
        price = 0
        async for chunk in completion:  # type: ignore
            if not isinstance(chunk, ModelResponseStream) or not hasattr(
                chunk, "choices"
            ):
                continue

            usage_info = getattr(chunk, "usage", None)
            try:
                price += completion_cost(chunk, model=self.model)
            except Exception as e:
                logger.debug(f"Could not calculate completion cost: {e}")

            delta = chunk.choices[0].delta

            if delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    index = tool_call_delta.index
                    if index >= len(current_tool_calls):
                        current_tool_calls.extend(
                            cast(
                                list[dict[str, Any]],
                                [
                                    {
                                        "id": None,
                                        "type": "function",
                                        "function": {"name": None, "arguments": ""},
                                    }
                                ]
                                * (index - len(current_tool_calls) + 1),
                            )
                        )
                    if tool_call_delta.id:
                        current_tool_calls[index]["id"] = tool_call_delta.id
                    func_delta = tool_call_delta.function
                    if func_delta:
                        if func_delta.name:
                            current_tool_calls[index]["function"]["name"] = (
                                func_delta.name
                            )
                        if func_delta.arguments:
                            current_tool_calls[index]["function"]["arguments"] += (
                                func_delta.arguments
                            )

            content_value = getattr(delta, "content", None)
            if content_value is not None:
                content = str(cast(str, content_value))
                yield Chunk(type=ChunkType.COMPLETION, content=content)

        if current_tool_calls:
            for i, tc in enumerate(current_tool_calls):
                if tc.get("id") and tc.get("function", {}).get("name"):
                    yield Chunk(type=ChunkType.TOOL_CALL, content={**tc})
                else:
                    logger.error(
                        f"Incomplete tool call data post-stream at index {i}: {tc}. Skipping."
                    )

        logger.info(f"Completion costed: {price}")

    async def run(self, user_message="") -> AsyncGenerator[str, None]:
        iterations = 0
        self.memory.add_user_message(user_message)
        while True:
            if iterations > 5:
                logger.debug(
                    f"Exiting loop for chat {self.chat_id}: max iterations reached"
                )
                break

            messages = self.memory.get()
            tool_calls: list[dict[str, Any]] = []
            final_content = ""

            async for chunk in self._completion(messages):
                content = chunk["content"]
                if chunk["type"] == ChunkType.COMPLETION:
                    if not isinstance(content, str):
                        continue
                    yield content
                    final_content += content if isinstance(content, str) else ""
                    continue

                if not isinstance(content, dict):
                    continue

                tool_calls.append(content)

            self.memory.add_assistant_message(final_content, tool_calls)
            if not final_content.strip() and not tool_calls:
                logger.debug(
                    f"Exiting loop for chat {self.chat_id}: model responded with empty message."
                )
                break

            iterations += 1
            if not tool_calls:
                logger.debug(
                    f"Exiting loop for chat {self.chat_id}: no tool calls or empty reply."
                )
                break

            for tool_call in tool_calls:
                call_id = tool_call.get("id")
                func = tool_call.get("function")
                if not func or not call_id:
                    continue

                arg_str = func.get("arguments", "")

                try:
                    arguments = json.loads(arg_str)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse arguments : {arg_str}")
                    self.memory.add(
                        {
                            "role": "tool",
                            "content": "Failed to parse arguments",
                            "tool_call_id": call_id,
                        }
                    )
                    continue

                logger.debug(f"Calling tool: {func.get('name')} with args: {arguments}")
                try:
                    tool = self.tool_registry.get(func["name"])
                    result = await tool.call(arguments)
                    logger.info(f"result found: {result}")
                    self.memory.add(
                        {
                            "role": "tool",
                            "content": str(result),
                            "tool_call_id": call_id,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to execute tool {func.get('name')} - {arguments}"
                    )
                    self.memory.add(
                        {
                            "role": "tool",
                            "content": f"Failed to execute tool: {e}",
                            "tool_call_id": call_id,
                        }
                    )
