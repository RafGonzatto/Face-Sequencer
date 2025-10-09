"""File system cleanup & retention policy service (initial scaffold)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


@dataclass
class CleanupStats:
    scanned: int = 0
    deleted: int = 0
    reclaimed_bytes: int = 0


class FileCleanupService:
    """Periodically remove old or oversized temporary/uploaded files."""

    def __init__(self, base_dir: str, *, max_age_hours: int = 24, max_total_bytes: int = 5 * 1024 * 1024 * 1024):
        self.base_dir = Path(base_dir)
        self.max_age = timedelta(hours=max_age_hours)
        self.max_total_bytes = max_total_bytes
        self.include_extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".tmp"}

    def scan(self) -> List[Path]:
        if not self.base_dir.exists():
            return []
        files: List[Path] = []
        for p in self.base_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in self.include_extensions:
                files.append(p)
        return files

    def enforce(self) -> CleanupStats:
        stats = CleanupStats()
        cutoff = datetime.utcnow() - self.max_age
        files = self.scan()
        total_size = 0
        sized: List[tuple[int, Path]] = []

        for f in files:
            stats.scanned += 1
            try:
                st = f.stat()
                file_mtime = datetime.utcfromtimestamp(st.st_mtime)
                if file_mtime < cutoff:
                    stats.reclaimed_bytes += st.st_size
                    f.unlink(missing_ok=True)
                    stats.deleted += 1
                    continue
                total_size += st.st_size
                sized.append((st.st_size, f))
            except OSError:
                continue

        # If over quota, prune largest-first
        if total_size > self.max_total_bytes:
            sized.sort(reverse=True)  # largest first
            for size, path in sized:
                if total_size <= self.max_total_bytes:
                    break
                try:
                    path.unlink(missing_ok=True)
                    stats.deleted += 1
                    stats.reclaimed_bytes += size
                    total_size -= size
                except OSError:
                    pass

        return stats


__all__ = ["FileCleanupService", "CleanupStats"]
