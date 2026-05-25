import os
import sys
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QPushButton, QMenu, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon, QCursor, QPainter, QPixmap

from models import Config, FolderRecord
from storage import FolderStorage


def _get_icon_path():
    if hasattr(sys, '_MEIPASS'):
        p = os.path.join(sys._MEIPASS, 'app_icon.ico')
        if os.path.exists(p):
            return p
    local = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "FreqFolderManager", "app_icon.ico",
    )
    if os.path.exists(local):
        return local
    return None


FLOATING_STYLESHEET = """
QFrame#floatingRoot {
    background-color: #16213e;
    border: 2px solid #e94560;
    border-radius: 14px;
}
QFrame#titleBar {
    background-color: #1a1a2e;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    min-height: 44px;
    max-height: 44px;
}
QLabel#titleLabel {
    color: #e94560;
    font-size: 17px;
    font-weight: bold;
    padding-left: 6px;
}
QLabel#monitorDot {
    color: #4ecca3;
    font-size: 12px;
}
QPushButton#titleBtn {
    background-color: transparent;
    border: none;
    border-radius: 10px;
    color: #a0b0c0;
    font-size: 18px;
    padding: 2px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}
QPushButton#titleBtn:hover {
    background-color: rgba(233, 69, 96, 60);
    color: #e94560;
}
QPushButton#titleBtn#closeBtn:hover {
    background-color: #e94560;
    color: white;
}
QListWidget {
    background-color: #1a1a2e;
    border: none;
    outline: none;
    padding: 4px 8px;
}
QListWidget::item {
    color: #e0e0e0;
    padding: 8px 12px;
    border-radius: 8px;
    margin: 2px 0px;
    font-size: 15px;
}
QListWidget::item:hover {
    background-color: #0f3460;
}
QListWidget::item:selected {
    background-color: #e94560;
}
QFrame#bottomBar {
    background-color: #1a1a2e;
    border-bottom-left-radius: 14px;
    border-bottom-right-radius: 14px;
    min-height: 38px;
    max-height: 38px;
}
QPushButton#bottomBtn {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: #a0b0c0;
    font-size: 14px;
    padding: 4px 12px;
}
QPushButton#bottomBtn:hover {
    background-color: #0f3460;
    color: #e94560;
}
QLabel#countLabel {
    color: #6b7b8d;
    font-size: 13px;
    padding-right: 6px;
}
"""


class FloatingWidget(QFrame):
    open_main_window = pyqtSignal()
    open_settings = pyqtSignal()

    def __init__(self, storage: FolderStorage, config: Config, parent=None):
        super().__init__(parent)
        self.storage = storage
        self.config = config
        self._drag_pos = QPoint()
        self._pinned = config.get("floating_always_on_top", True)
        self._max_items = config.get("floating_max_items", 15)
        self._pending_refresh = True
        self._setup_ui()
        self._apply_window_flags()
        self._load_position()
        self._set_window_icon()
        self._refresh_list()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_list)
        self._refresh_timer.start(5000)
        self.storage.on_change(self._request_refresh)

    def _setup_ui(self):
        self.setObjectName("floatingRoot")
        self.setStyleSheet(FLOATING_STYLESHEET)
        self.setFixedWidth(400)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(0)

        title_bar = QFrame()
        title_bar.setObjectName("titleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 4, 6, 4)
        title_layout.setSpacing(6)

        title_label = QLabel("📁 高频文件夹")
        title_label.setObjectName("titleLabel")
        title_layout.addWidget(title_label)

        monitor_dot = QLabel("●")
        monitor_dot.setObjectName("monitorDot")
        title_layout.addWidget(monitor_dot)
        title_layout.addStretch()

        self._pin_btn = QPushButton("📌" if self._pinned else "📍")
        self._pin_btn.setObjectName("titleBtn")
        self._pin_btn.setToolTip("切换置顶")
        self._pin_btn.clicked.connect(self._toggle_pin)
        title_layout.addWidget(self._pin_btn)

        min_btn = QPushButton("─")
        min_btn.setObjectName("titleBtn")
        min_btn.setToolTip("最小化")
        min_btn.clicked.connect(self.hide)
        title_layout.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("titleBtn")
        close_btn.setToolTip("关闭浮窗")
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)

        layout.addWidget(title_bar)

        self._list = QListWidget()
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._show_context_menu)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setMaximumHeight(self._max_items * 40)
        layout.addWidget(self._list, 1)

        bottom_bar = QFrame()
        bottom_bar.setObjectName("bottomBar")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(12, 4, 12, 4)
        bottom_layout.setSpacing(6)

        settings_btn = QPushButton("⚙ 设置")
        settings_btn.setObjectName("bottomBtn")
        settings_btn.clicked.connect(self.open_settings.emit)
        bottom_layout.addWidget(settings_btn)

        main_btn = QPushButton("📋 主窗口")
        main_btn.setObjectName("bottomBtn")
        main_btn.clicked.connect(self.open_main_window.emit)
        bottom_layout.addWidget(main_btn)

        bottom_layout.addStretch()

        self._count_label = QLabel("")
        self._count_label.setObjectName("countLabel")
        bottom_layout.addWidget(self._count_label)

        layout.addWidget(bottom_bar)

    def _apply_window_flags(self):
        flags = Qt.FramelessWindowHint | Qt.Tool
        if self._pinned:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _set_window_icon(self):
        icon_path = _get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

    def _load_position(self):
        pos_data = self.config.get("floating_position", None)
        if pos_data and isinstance(pos_data, dict):
            x = pos_data.get("x")
            y = pos_data.get("y")
            if x is not None and y is not None:
                self.move(int(x), int(y))
                return
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.right() - 400, geo.top() + 60)

    def _save_position(self):
        pos = self.pos()
        self.config.set("floating_position", {"x": pos.x(), "y": pos.y()})

    def _toggle_pin(self):
        self._pinned = not self._pinned
        self._pin_btn.setText("📌" if self._pinned else "📍")
        self.config.set("floating_always_on_top", self._pinned)
        self._apply_window_flags()
        self.show()

    def _request_refresh(self):
        self._pending_refresh = True

    def _refresh_list(self):
        if not self._pending_refresh:
            return
        self._pending_refresh = False
        records = self.storage.get_all("frequency")
        max_items = self.config.get("floating_max_items", 15)
        records = records[:max_items]

        self._list.setUpdatesEnabled(False)
        self._list.clear()
        for r in records:
            folder_name = Path(r.path).name or r.path
            if r.access_count >= 10:
                count_str = f"🔥 {r.access_count}"
            elif r.access_count >= 5:
                count_str = f"  {r.access_count}"
            else:
                count_str = f"  {r.access_count}"

            display = f"📂 {folder_name}    {count_str}"
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, r.path)

            if r.access_count >= 10:
                item.setForeground(QColor("#e94560"))
            elif r.access_count >= 5:
                item.setForeground(QColor("#ffa500"))

            if r.is_locked:
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            self._list.addItem(item)

        self._list.setUpdatesEnabled(True)

        total = self.storage.total_count()
        shown = len(records)
        self._count_label.setText(f"{shown}/{total}")

        content_height = min(len(records), max_items) * 40
        total_height = 44 + content_height + 38 + 24
        self.setFixedHeight(total_height)

    def _on_item_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            try:
                os.startfile(path)
            except (OSError, FileNotFoundError):
                pass

    def _show_context_menu(self, pos):
        item = self._list.itemAt(pos)
        if not item:
            return
        path = item.data(Qt.UserRole)
        if not path:
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #16213e; border: 1px solid #0f3460; border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 8px 24px; border-radius: 4px; color: #e0e0e0; font-size: 13px; }
            QMenu::item:selected { background-color: #e94560; }
        """)

        open_action = menu.addAction("📂 打开文件夹")
        open_action.triggered.connect(lambda: self._open_folder(path))

        copy_action = menu.addAction("📋 复制路径")
        copy_action.triggered.connect(lambda: self._copy_path(path))

        parent_action = menu.addAction("⬆ 打开上级目录")
        parent_action.triggered.connect(lambda: self._open_parent(path))

        menu.addSeparator()

        record = self.storage.get_record(path)
        if record:
            lock_text = "🔓 取消锁定" if record.is_locked else "🔒 锁定保留"
            lock_action = menu.addAction(lock_text)
            lock_action.triggered.connect(lambda: self.storage.toggle_lock(path))

        menu.addSeparator()

        delete_action = menu.addAction("🗑 删除记录")
        delete_action.triggered.connect(lambda: self.storage.remove(path))

        menu.exec_(self._list.viewport().mapToGlobal(pos))

    def _open_folder(self, path: str):
        try:
            os.startfile(path)
        except (OSError, FileNotFoundError):
            pass

    def _copy_path(self, path: str):
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(path)

    def _open_parent(self, path: str):
        parent = str(Path(path).parent)
        if parent and parent != path:
            self._open_folder(parent)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            title_bar = self.findChild(QFrame, "titleBar")
            if title_bar and title_bar.geometry().contains(event.pos()):
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._save_position()
            self._drag_pos = QPoint()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        title_bar = self.findChild(QFrame, "titleBar")
        if title_bar and title_bar.geometry().contains(event.pos()):
            self._toggle_pin()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def showEvent(self, event):
        self._pending_refresh = True
        self._refresh_list()
        super().showEvent(event)
