from typing import Protocol, Any


class AIAgentInterface(Protocol):
    async def run(self, prompt: Any) -> Any: ...
