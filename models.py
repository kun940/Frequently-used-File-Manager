import os
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class FolderRecord:
    path: str
    access_count: int = 1
    first_access_time: str = field(default_factory=lambda: datetime.now().isoformat())
    last_access_time: str = field(default_factory=lambda: datetime.now().isoformat())
    is_locked: bool = False
    group: str = ""
    alias: str = ""

    def __post_init__(self):
        self.path = self._normalize_path(self.path)
        if not self.group:
            self.group = self._infer_group()

    @staticmethod
    def _normalize_path(p: str) -> str:
        try:
            return str(Path(p).resolve()).rstrip("\\")
        except (OSError, ValueError):
            return p.rstrip("\\")

    def _infer_group(self) -> str:
        p = Path(self.path)
        if p.drive:
            return f"磁盘 {p.drive[0]}"
        return "其他"

    def increment(self):
        self.access_count += 1
        self.last_access_time = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FolderRecord":
        return cls(
            path=data.get("path", ""),
            access_count=data.get("access_count", 1),
            first_access_time=data.get("first_access_time", datetime.now().isoformat()),
            last_access_time=data.get("last_access_time", datetime.now().isoformat()),
            is_locked=data.get("is_locked", False),
            group=data.get("group", ""),
            alias=data.get("alias", ""),
        )


DEFAULT_WHITELIST = [
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\ProgramData",
    "C:\\$Recycle.Bin",
    "C:\\System Volume Information",
    "C:\\Users\\Public",
    "C:\\Users\\Default",
]

DEFAULT_CONFIG = {
    "auto_collect_threshold": 2,
    "cleanup_days": 30,
    "cleanup_min_count": 2,
    "auto_cleanup_enabled": True,
    "monitor_interval_seconds": 3,
    "whitelist": DEFAULT_WHITELIST,
    "sort_mode": "frequency",
    "show_hidden": False,
    "minimize_to_tray": True,
    "start_with_system": False,
    "floating_opacity": 0.92,
    "floating_max_items": 15,
    "floating_always_on_top": True,
    "floating_position": None,
}


class Config:
    _instance: Optional["Config"] = None

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.join(
                os.environ.get("APPDATA", os.path.expanduser("~")),
                "FreqFolderManager",
            )
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "config.json")
        self.data_file = os.path.join(config_dir, "folders.json")
        os.makedirs(config_dir, exist_ok=True)
        self._data = dict(DEFAULT_CONFIG)
        self._load()

    @classmethod
    def get_instance(cls, config_dir: Optional[str] = None) -> "Config":
        if cls._instance is None:
            cls._instance = cls(config_dir)
        return cls._instance

    def _load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except (json.JSONDecodeError, IOError):
                pass

    def save(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    @property
    def auto_collect_threshold(self) -> int:
        return self._data.get("auto_collect_threshold", 2)

    @property
    def cleanup_days(self) -> int:
        return self._data.get("cleanup_days", 30)

    @property
    def cleanup_min_count(self) -> int:
        return self._data.get("cleanup_min_count", 2)

    @property
    def auto_cleanup_enabled(self) -> bool:
        return self._data.get("auto_cleanup_enabled", True)

    @property
    def monitor_interval_seconds(self) -> int:
        return self._data.get("monitor_interval_seconds", 3)

    @property
    def whitelist(self) -> list:
        return self._data.get("whitelist", list(DEFAULT_WHITELIST))

    @property
    def sort_mode(self) -> str:
        return self._data.get("sort_mode", "frequency")

    @property
    def minimize_to_tray(self) -> bool:
        return self._data.get("minimize_to_tray", True)

    @property
    def start_with_system(self) -> bool:
        return self._data.get("start_with_system", False)

    @staticmethod
    def set_auto_start(enable: bool):
        """写入或删除注册表开机自启项 (HKCU\\...\\Run)"""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "FreqFolderManager"
            if enable:
                exe_path = sys.executable if getattr(sys, 'frozen', False) else f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
            else:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
                winreg.CloseKey(key)
        except Exception:
            pass
