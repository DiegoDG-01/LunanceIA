from typing import Protocol, Any


class AIAgentInterface(Protocol):
    async def run(self, *args: Any, **kwargs: Any) -> Any: ...
