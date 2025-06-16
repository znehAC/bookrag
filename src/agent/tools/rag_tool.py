from typing import Any

from agent.tools.tool import Tool
from rag.db import PgVectorStore
from rag.retrieve import Retriever

_store = PgVectorStore()
_retriever = Retriever(_store)


class RagTool(Tool):
    name = "search_context"
    description = "Queries the book to obtain relevant passages."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The text to make a query to the database.",
            },
        },
        "required": ["query"],
    }

    async def call(self, arguments: dict[str, Any]) -> str:
        q = arguments.get("query", "")
        passages = _retriever.query(q)
        if not passages:
            return "não encontrei trechos relevantes."
        return "\n\n---\n\n".join(passages)
