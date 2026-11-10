from typing import Any, Protocol


class AIAgentInterface(Protocol):
    async def run(self, *args: Any, **kwargs: Any) -> Any: ...
