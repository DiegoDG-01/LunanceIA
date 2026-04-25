import asyncio
from typing import Dict, List


class SSEManager:

    def __init__(self):
        self._connections: Dict[int, List[asyncio.Queue]] = {}

    async def connect(self, user_id: int) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()

        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(queue)

        return queue

    async def disconnect(self, user_id: int, queue: asyncio.Queue) -> None:
        if user_id in self._connections:
            self._connections[user_id].remove(queue)
            if not self._connections[user_id]:
                del self._connections[user_id]

    async def send_to_user(self, user_id: int, data: dict) -> bool:
        if user_id in self._connections:
            for queue in self._connections[user_id]:
                await queue.put(data)
            return True
        return False

sse_manager = SSEManager()
