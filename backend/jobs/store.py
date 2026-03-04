
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from threading import Lock
from typing import Any, Dict, Optional
import time

class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"

@dataclass
class Job:
    job_id: str
    video_id: str
    platform: str
    export: bool
    status: JobStatus = JobStatus.queued
    stage: str = "queued"
    progress: float = 0.0
    error: Optional[str] = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    result: Optional[Dict[str, Any]] = None

    def to_public(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = str(self.status)
        return d

class InMemoryJobStore:
    def __init__(self):
        self._lock = Lock()
        self._jobs: Dict[str, Job] = {}

    def create(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.job_id] = job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in kwargs.items():
                setattr(job, k, v)
            job.updated_at = time.time()
