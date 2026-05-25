import os
import threading
import time
import logging
from pathlib import Path
from typing import Optional, Set, Callable
from urllib.parse import unquote

from models import Config, FolderRecord
from storage import FolderStorage

logger = logging.getLogger(__name__)


class ExplorerMonitor:
    def __init__(self, storage: FolderStorage, config: Optional[Config] = None):
        self.storage = storage
        self.config = config or Config.get_instance()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._known_paths: Set[str] = set()
        self._on_new_folder: Optional[Callable] = None
        self._cleanup_counter = 0

    def on_new_folder(self, callback: Callable):
        self._on_new_folder = callback

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("文件夹监控已启动")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("文件夹监控已停止")

    def _get_explorer_paths(self) -> Set[str]:
        paths = set()
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            windows = shell.Windows()
            for i in range(windows.Count):
                try:
                    item = windows.Item(i)
                    url = item.LocationURL
                    if url and url.startswith("file:///"):
                        folder_path = self._url_to_path(url)
                        if folder_path and Path(folder_path).is_dir():
                            paths.add(folder_path)
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"获取Explorer窗口失败: {e}")
        return paths

    @staticmethod
    def _url_to_path(url: str) -> str:
        path = url.replace("file:///", "")
        path = unquote(path)
        path = path.replace("/", "\\")
        if path and path[0].isalpha() and path[1:3] == ":\\":
            return path.rstrip("\\")
        return ""

    def _monitor_loop(self):
        while self._running:
            try:
                current_paths = self._get_explorer_paths()
                new_paths = current_paths - self._known_paths
                for p in new_paths:
                    if not self.storage.is_whitelisted(p):
                        self.storage.record_access(p)
                        logger.info(f"检测到文件夹访问: {p}")
                        if self._on_new_folder:
                            try:
                                self._on_new_folder(p)
                            except Exception:
                                pass
                self._known_paths = current_paths
            except Exception as e:
                logger.error(f"监控循环异常: {e}")

            self._cleanup_counter += 1
            if self._cleanup_counter >= 100:
                self._cleanup_counter = 0
                try:
                    removed = self.storage.cleanup()
                    if removed > 0:
                        logger.info(f"自动清理了 {removed} 个低活跃目录")
                except Exception as e:
                    logger.error(f"自动清理异常: {e}")

            interval = self.config.monitor_interval_seconds
            for _ in range(interval * 10):
                if not self._running:
                    break
                time.sleep(0.1)


class RecentFolderMonitor:
    def __init__(self, storage: FolderStorage, config: Optional[Config] = None):
        self.storage = storage
        self.config = config or Config.get_instance()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._recent_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft\\Windows\\Recent"
        self._known_recent: Set[str] = set()

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("最近文件监控已启动")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        while self._running:
            try:
                self._scan_recent()
            except Exception as e:
                logger.error(f"最近文件监控异常: {e}")
            for _ in range(50):
                if not self._running:
                    break
                time.sleep(0.1)

    def _scan_recent(self):
        if not self._recent_dir.exists():
            return
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            for lnk_file in self._recent_dir.glob("*.lnk"):
                try:
                    shortcut = shell.CreateShortCut(str(lnk_file))
                    target = shortcut.TargetPath
                    if target and Path(target).is_dir():
                        normalized = FolderRecord._normalize_path(target)
                        if normalized not in self._known_recent:
                            self._known_recent.add(normalized)
                            if not self.storage.is_whitelisted(target):
                                self.storage.record_access(target)
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"扫描最近文件失败: {e}")
