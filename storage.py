import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable

from models import FolderRecord, Config


class FolderStorage:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.get_instance()
        self._lock = threading.RLock()
        self._folders: Dict[str, FolderRecord] = {}
        self._on_change_callbacks: List[Callable] = []
        self._load()

    def _load(self):
        data_file = self.config.data_file
        if Path(data_file).exists():
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    record = FolderRecord.from_dict(item)
                    if record.path:
                        self._folders[record.path] = record
            except (json.JSONDecodeError, IOError):
                pass

    def save(self):
        with self._lock:
            data = [r.to_dict() for r in self._folders.values()]
        with open(self.config.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def on_change(self, callback: Callable):
        self._on_change_callbacks.append(callback)

    def _notify_change(self):
        for cb in self._on_change_callbacks:
            try:
                cb()
            except Exception:
                pass

    def record_access(self, path: str) -> FolderRecord:
        normalized = FolderRecord._normalize_path(path)
        with self._lock:
            if normalized in self._folders:
                self._folders[normalized].increment()
            else:
                self._folders[normalized] = FolderRecord(path=normalized)
            record = self._folders[normalized]
        self.save()
        self._notify_change()
        return record

    def get_all(self, sort_mode: Optional[str] = None) -> List[FolderRecord]:
        sort_mode = sort_mode or self.config.sort_mode
        with self._lock:
            records = list(self._folders.values())

        threshold = self.config.auto_collect_threshold
        filtered = [r for r in records if r.access_count >= threshold or r.is_locked]

        if sort_mode == "frequency":
            filtered.sort(key=lambda r: (-r.access_count, r.last_access_time), reverse=False)
            filtered.sort(key=lambda r: -r.access_count)
        elif sort_mode == "recent":
            filtered.sort(key=lambda r: r.last_access_time, reverse=True)
        elif sort_mode == "path":
            filtered.sort(key=lambda r: r.path.lower())

        return filtered

    def get_all_groups(self) -> Dict[str, List[FolderRecord]]:
        records = self.get_all()
        groups: Dict[str, List[FolderRecord]] = {}
        for r in records:
            groups.setdefault(r.group, []).append(r)
        return groups

    def remove(self, path: str) -> bool:
        normalized = FolderRecord._normalize_path(path)
        with self._lock:
            if normalized in self._folders:
                del self._folders[normalized]
                self.save()
                self._notify_change()
                return True
        return False

    def toggle_lock(self, path: str) -> bool:
        normalized = FolderRecord._normalize_path(path)
        with self._lock:
            if normalized in self._folders:
                self._folders[normalized].is_locked = not self._folders[normalized].is_locked
                self.save()
                self._notify_change()
                return self._folders[normalized].is_locked
        return False

    def set_group(self, path: str, group: str):
        normalized = FolderRecord._normalize_path(path)
        with self._lock:
            if normalized in self._folders:
                self._folders[normalized].group = group
                self.save()
                self._notify_change()

    def set_alias(self, path: str, alias: str):
        normalized = FolderRecord._normalize_path(path)
        with self._lock:
            if normalized in self._folders:
                self._folders[normalized].alias = alias
                self.save()
                self._notify_change()

    def cleanup(self) -> int:
        if not self.config.auto_cleanup_enabled:
            return 0
        days = self.config.cleanup_days
        min_count = self.config.cleanup_min_count
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        with self._lock:
            to_remove = []
            for path, record in self._folders.items():
                if record.is_locked:
                    continue
                try:
                    last = datetime.fromisoformat(record.last_access_time)
                    if last < cutoff and record.access_count <= min_count:
                        to_remove.append(path)
                except (ValueError, TypeError):
                    pass
            for path in to_remove:
                del self._folders[path]
                removed += 1
        if removed > 0:
            self.save()
            self._notify_change()
        return removed

    def is_whitelisted(self, path: str) -> bool:
        normalized = FolderRecord._normalize_path(path)
        whitelist = self.config.whitelist
        for wp in whitelist:
            wn = FolderRecord._normalize_path(wp)
            if normalized.lower().startswith(wn.lower()):
                return True
        return False

    def get_record(self, path: str) -> Optional[FolderRecord]:
        normalized = FolderRecord._normalize_path(path)
        with self._lock:
            return self._folders.get(normalized)

    def total_count(self) -> int:
        with self._lock:
            return len(self._folders)

    def get_invalid_paths(self) -> List[str]:
        """返回所有不存在的文件夹路径"""
        invalid = []
        with self._lock:
            for path in self._folders:
                if not Path(path).is_dir():
                    invalid.append(path)
        return invalid

    def remove_paths(self, paths: List[str]):
        """批量删除指定路径的记录"""
        with self._lock:
            for path in paths:
                normalized = FolderRecord._normalize_path(path)
                self._folders.pop(normalized, None)
            self.save()
            self._notify_change()
