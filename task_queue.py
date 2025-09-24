"""Lightweight in-process job queue with optional progress reporting."""
from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from typing import Any, Callable, Dict, Optional


class JobManager:
    """Simple asynchronous job manager backing API endpoints."""

    def __init__(self, max_workers: int = 4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def enqueue(self, job_type: str, target: Callable, *args, **kwargs) -> str:
        job_id = str(uuid.uuid4())
        job_payload = {
            "id": job_id,
            "type": job_type,
            "status": "queued",
            "progress": 0,
            "message": "Queued",
            "result": None,
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "finished_at": None,
        }
        with self._lock:
            self._jobs[job_id] = job_payload

        def progress_callback(progress: Optional[float] = None, message: Optional[str] = None):
            with self._lock:
                job = self._jobs.get(job_id)
                if not job:
                    return
                if progress is not None:
                    job["progress"] = max(0, min(100, int(progress)))
                if message:
                    job["message"] = message

        def runner():
            self._mark_job_running(job_id)
            try:
                result = target(progress_callback, *args, **kwargs)
                self._mark_job_completed(job_id, result)
            except Exception as exc:  # noqa: BLE001
                self._mark_job_failed(job_id, exc)

        self._executor.submit(runner)
        return job_id

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return deepcopy(job) if job else None

    def list(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return deepcopy(self._jobs)

    def _mark_job_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job["status"] = "running"
                job["progress"] = max(job.get("progress", 0), 5)
                job["message"] = "Running"
                job["started_at"] = datetime.utcnow().isoformat()

    def _mark_job_completed(self, job_id: str, result: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job["status"] = "completed"
                job["progress"] = 100
                job["message"] = "Completed"
                job["result"] = result
                job["finished_at"] = datetime.utcnow().isoformat()

    def _mark_job_failed(self, job_id: str, exc: Exception) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job["status"] = "failed"
                job["progress"] = 100
                job["message"] = f"Failed: {exc}"[:200]
                job["error"] = str(exc)
                job["finished_at"] = datetime.utcnow().isoformat()


job_manager = JobManager()

__all__ = ["job_manager", "JobManager"]
