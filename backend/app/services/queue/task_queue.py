from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Optional


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    progress: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "progress": self.progress,
        }


class TaskQueue:
    def __init__(self, max_workers: int = 3):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: list[asyncio.Task] = []
        self._max_workers = max_workers
        self._tasks: Dict[str, TaskResult] = {}
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        for _ in range(self._max_workers):
            worker = asyncio.create_task(self._worker())
            self._workers.append(worker)

    async def stop(self) -> None:
        self._started = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()

    async def enqueue(
        self,
        func: Callable[..., Coroutine],
        *args: Any,
        **kwargs: Any,
    ) -> str:
        task_id = uuid.uuid4().hex[:12]
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.QUEUED,
            created_at=datetime.utcnow(),
        )
        self._tasks[task_id] = task_result
        await self._queue.put((task_id, func, args, kwargs))
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskResult]:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[Dict[str, Any]]:
        return [task.to_dict() for task in sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True,
        )]

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    async def _worker(self) -> None:
        while self._started:
            try:
                task_id, func, args, kwargs = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            task_result = self._tasks.get(task_id)
            if not task_result:
                continue

            task_result.status = TaskStatus.PROCESSING
            try:
                result = await func(*args, **kwargs)
                task_result.status = TaskStatus.COMPLETED
                task_result.result = result
                task_result.completed_at = datetime.utcnow()
            except Exception as exc:
                task_result.status = TaskStatus.FAILED
                task_result.error = str(exc)
                task_result.completed_at = datetime.utcnow()
                print(f"Task {task_id} failed: {exc}")
            finally:
                self._queue.task_done()


_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue


task_queue = None


def __getattr__(name: str):
    if name == "task_queue":
        return get_task_queue()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
