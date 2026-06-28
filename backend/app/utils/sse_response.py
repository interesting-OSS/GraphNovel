"""SSE (Server-Sent Events) response utilities."""
import json
import asyncio
from typing import AsyncGenerator
from fastapi.responses import StreamingResponse


class SSEResponse:
    """Helper for building SSE-formatted messages."""

    @staticmethod
    def format(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    @staticmethod
    def progress(message: str, percent: float, status: str = "", **kwargs) -> str:
        payload = {"type": "progress", "message": message, "progress": percent, "status": status, **kwargs}
        return SSEResponse.format(payload)

    @staticmethod
    def chunk(text: str, **kwargs) -> str:
        return SSEResponse.format({"type": "chunk", "chunk": text, **kwargs})

    @staticmethod
    def result(data: dict) -> str:
        return SSEResponse.format({"type": "result", "data": data})

    @staticmethod
    def error(message: str, code: str = "") -> str:
        return SSEResponse.format({"type": "error", "message": message, "code": code})

    @staticmethod
    def done(message: str = "完成") -> str:
        return SSEResponse.format({"type": "done", "message": message})

    @staticmethod
    def event(event_type: str, data: dict) -> str:
        return SSEResponse.format({"type": event_type, **data})


async def create_sse_response(
    generator: AsyncGenerator[str, None],
    heartbeat_interval: float = 15.0,
) -> StreamingResponse:
    """Create a FastAPI StreamingResponse with SSE headers and heartbeat.

    Uses asyncio.wait with a timeout to inject heartbeat comments
    when the main generator is idle, preventing proxy timeout.
    Properly cancels timed-out __anext__() tasks.
    """
    async def event_stream():
        gen = generator.__aiter__()
        gen_done = False

        while not gen_done:
            task = asyncio.create_task(gen.__anext__())
            try:
                done, pending = await asyncio.wait([task], timeout=heartbeat_interval)
                if done:
                    for t in done:
                        try:
                            yield t.result()
                        except StopAsyncIteration:
                            gen_done = True
                else:
                    # Cancel the pending __anext__() to prevent orphaned tasks
                    for t in pending:
                        t.cancel()
                        try:
                            await t
                        except (asyncio.CancelledError, StopAsyncIteration):
                            pass
                    yield ": heartbeat\n\n"
            except Exception as e:
                # Cancel pending task and yield error to client before closing
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, StopAsyncIteration):
                        pass
                yield SSEResponse.error(str(e))
                gen_done = True

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
