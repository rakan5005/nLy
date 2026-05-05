"""In-memory LRU cache with optional disk persistence."""

import json
import os
import threading
from collections import OrderedDict


class Cache:
    def __init__(self, max_size: int = 10000, disk_path: str | None = None):
        self.max_size = max_size
        self.disk_path = disk_path
        self._lock = threading.Lock()
        self._store: OrderedDict[str, str] = OrderedDict()
        self.hits = 0
        self.misses = 0
        if disk_path:
            self._load_disk()

    def get(self, key: str) -> str | None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self.hits += 1
                return self._store[key]
            self.misses += 1
            return None

    def set(self, key: str, value: str) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            else:
                if len(self._store) >= self.max_size:
                    self._store.popitem(last=False)
            self._store[key] = value

    def save_to_disk(self) -> None:
        if not self.disk_path:
            return
        with self._lock:
            os.makedirs(os.path.dirname(self.disk_path) or ".", exist_ok=True)
            with open(self.disk_path, "w", encoding="utf-8") as f:
                json.dump(list(self._store.items()), f)

    def _load_disk(self) -> None:
        if not self.disk_path or not os.path.exists(self.disk_path):
            return
        try:
            with open(self.disk_path, "r", encoding="utf-8") as f:
                items = json.load(f)
            with self._lock:
                for k, v in items[-self.max_size :]:
                    self._store[k] = v
        except (json.JSONDecodeError, OSError):
            pass

    @property
    def size(self) -> int:
        return len(self._store)
