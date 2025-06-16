from .rag_tool import RagTool
from .tool import ToolRegistry

registry = ToolRegistry()
registry.register(RagTool())
