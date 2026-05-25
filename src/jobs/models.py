from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class ProgressEvent:
    message: str
    step: int | None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class Job:
    id: str
    url: str
    status: JobStatus = JobStatus.PENDING
    progress: list[ProgressEvent] = field(default_factory=list)
    result: dict | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat()
