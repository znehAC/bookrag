# src/agent/memory.py

from collections import deque

from litellm.types.completion import (
    ChatCompletionMessageParam,
)


class ChatMemory:
    def __init__(self, window_size: int = 5):
        self._messages = deque[ChatCompletionMessageParam](maxlen=window_size)

    def add_user_message(self, content: str, name: str | None = None) -> None:
        msg: ChatCompletionMessageParam = {"role": "user", "content": content}
        if name:
            msg["name"] = name
        self._messages.append(msg)

    def add_assistant_message(self, content: str | None = None, tool_calls=[]) -> None:
        msg: ChatCompletionMessageParam = {
            "role": "assistant",
            "tool_calls": tool_calls,
        }
        if content:
            msg["content"] = content
        self._messages.append(msg)

    def add(self, message: ChatCompletionMessageParam) -> None:
        self._messages.append(message)

    def get(self, system_message: bool = True) -> list[ChatCompletionMessageParam]:
        if system_message:
            with open("data/PROMPT.md", "r") as file:
                system_prompt = file.read()
            messages: list[ChatCompletionMessageParam] = [
                {"role": "system", "content": system_prompt}
            ]
            messages.extend(list(self._messages))
        else:
            messages = list(self._messages)

        return messages

    def clear(self) -> None:
        self._messages.clear()

    @property
    def has_messages(self) -> bool:
        return len(self._messages) > 0
