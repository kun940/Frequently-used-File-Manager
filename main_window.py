import os
import sys
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QMenu, QAction, QLabel,
    QComboBox, QPushButton, QSystemTrayIcon, QFrame,
    QAbstractItemView, QSplitter, QToolBar, QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QPixmap, QPainter

from models import Config, FolderRecord
from storage import FolderStorage
from monitor import ExplorerMonitor, RecentFolderMonitor


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


STYLESHEET = """
QMainWindow {
    background-color: #1a1a2e;
}
QWidget {
    color: #e0e0e0;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
}
QFrame#topBar {
    background-color: #16213e;
    border-bottom: 1px solid #0f3460;
    border-radius: 0px;
}
QLineEdit#searchBox {
    background-color: #0f3460;
    border: 1px solid #1a1a5e;
    border-radius: 8px;
    padding: 8px 14px 8px 36px;
    color: #e0e0e0;
    font-size: 13px;
    min-height: 20px;
}
QLineEdit#searchBox:focus {
    border: 1px solid #e94560;
}
QLineEdit#searchBox::placeholder {
    color: #6b7b8d;
}
QComboBox {
    background-color: #0f3460;
    border: 1px solid #1a1a5e;
    border-radius: 6px;
    padding: 6px 12px;
    color: #e0e0e0;
    min-width: 100px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    color: #e0e0e0;
    selection-background-color: #e94560;
    border: 1px solid #0f3460;
}
QPushButton#iconBtn {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 6px;
    color: #a0b0c0;
}
QPushButton#iconBtn:hover {
    background-color: #0f3460;
    color: #e94560;
}
QTreeWidget {
    background-color: #1a1a2e;
    border: none;
    outline: none;
    alternate-background-color: #16213e;
}
QTreeWidget::item {
    padding: 6px 4px;
    border-bottom: 1px solid #0f3460;
}
QTreeWidget::item:hover {
    background-color: #16213e;
}
QTreeWidget::item:selected {
    background-color: #0f3460;
}
QTreeWidget::item:selected:active {
    background-color: #e94560;
}
QHeaderView::section {
    background-color: #16213e;
    color: #a0b0c0;
    padding: 8px 6px;
    border: none;
    border-bottom: 2px solid #e94560;
    font-size: 12px;
    font-weight: bold;
}
QHeaderView::section:hover {
    color: #e94560;
}
QMenu {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 4px;
}
QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #e94560;
}
QMenu::separator {
    height: 1px;
    background-color: #0f3460;
    margin: 4px 8px;
}
QLabel#statusLabel {
    color: #6b7b8d;
    font-size: 11px;
    padding: 4px 8px;
}
QLabel#titleLabel {
    color: #e94560;
    font-size: 16px;
    font-weight: bold;
}
QLabel#monitorDot {
    font-size: 10px;
}
QSplitter::handle {
    background-color: #0f3460;
    width: 1px;
}
QToolBar {
    background-color: #16213e;
    border: none;
    spacing: 4px;
    padding: 2px;
}
"""


class FolderTreeWidget(QTreeWidget):
    folder_double_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["文件夹路径", "访问次数", "最近访问", "分组", "状态"])
        self.setColumnWidth(0, 380)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 160)
        self.setColumnWidth(3, 80)
        self.setColumnWidth(4, 60)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(False)
        self.setSortingEnabled(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setIndentation(0)
        self.itemDoubleClicked.connect(self._on_double_click)

    def _on_double_click(self, item: QTreeWidgetItem, column: int):
        path = item.data(0, Qt.UserRole)
        if path:
            self.folder_double_clicked.emit(path)


class MainWindow(QMainWindow):
    def __init__(self, storage: FolderStorage, config: Config):
        super().__init__()
        self.storage = storage
        self.config = config
        self.monitor: ExplorerMonitor = None
        self.recent_monitor: RecentFolderMonitor = None
        self._tray_icon: QSystemTrayIcon = None
        self._floating_widget = None
        self._pending_refresh = True
        self._setup_ui()
        self._setup_tray()
        self._setup_monitors()
        self._refresh_list()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_list)
        self._refresh_timer.start(5000)
        self.storage.on_change(self._request_refresh)

    def _setup_ui(self):
        self.setWindowTitle("高频文件夹管理器")
        self.setMinimumSize(820, 560)
        self.resize(900, 640)
        self.setStyleSheet(STYLESHEET)

        icon_path = _get_icon_path()
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar_layout = QVBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(16, 12, 16, 8)
        top_bar_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_label = QLabel("📁 高频文件夹管理器")
        title_label.setObjectName("titleLabel")
        self._monitor_status = QLabel("● 监控中")
        self._monitor_status.setObjectName("monitorDot")
        self._monitor_status.setStyleSheet("color: #4ecca3;")
        title_row.addWidget(title_label)
        title_row.addStretch()
        title_row.addWidget(self._monitor_status)
        top_bar_layout.addLayout(title_row)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self._search_box = QLineEdit()
        self._search_box.setObjectName("searchBox")
        self._search_box.setPlaceholderText("🔍 搜索文件夹路径...")
        self._search_box.textChanged.connect(self._on_search)
        search_row.addWidget(self._search_box)

        self._sort_combo = QComboBox()
        self._sort_combo.addItems(["按频次排序", "按最近访问排序", "按路径排序"])
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        search_row.addWidget(self._sort_combo)

        self._group_btn = QPushButton("☰")
        self._group_btn.setObjectName("iconBtn")
        self._group_btn.setToolTip("分组显示")
        self._group_btn.setCheckable(True)
        self._group_btn.clicked.connect(self._toggle_group)
        self._group_btn.setFixedSize(36, 36)
        search_row.addWidget(self._group_btn)

        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setObjectName("iconBtn")
        self._settings_btn.setToolTip("设置")
        self._settings_btn.setFixedSize(36, 36)
        self._settings_btn.clicked.connect(self._open_settings)
        search_row.addWidget(self._settings_btn)

        self._add_btn = QPushButton("+")
        self._add_btn.setObjectName("iconBtn")
        self._add_btn.setToolTip("手动添加文件夹")
        self._add_btn.setFixedSize(36, 36)
        self._add_btn.clicked.connect(self._manual_add)
        search_row.addWidget(self._add_btn)

        self._clean_invalid_btn = QPushButton("!")
        self._clean_invalid_btn.setObjectName("iconBtn")
        self._clean_invalid_btn.setToolTip("清理失效路径")
        self._clean_invalid_btn.setFixedSize(36, 36)
        self._clean_invalid_btn.setStyleSheet("QPushButton#iconBtn { color: #ffa500; }")
        self._clean_invalid_btn.clicked.connect(self._clean_invalid_paths)
        self._clean_invalid_btn.hide()
        search_row.addWidget(self._clean_invalid_btn)

        top_bar_layout.addLayout(search_row)
        main_layout.addWidget(top_bar)

        self._tree = FolderTreeWidget()
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.folder_double_clicked.connect(self._open_folder)
        main_layout.addWidget(self._tree, 1)

        status_bar = QHBoxLayout()
        status_bar.setContentsMargins(16, 4, 16, 8)
        self._status_label = QLabel("就绪")
        self._status_label.setObjectName("statusLabel")
        status_bar.addWidget(self._status_label)
        status_bar.addStretch()
        self._count_label = QLabel("")
        self._count_label.setObjectName("statusLabel")
        status_bar.addWidget(self._count_label)
        main_layout.addLayout(status_bar)

    def _setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon_path = _get_icon_path()
        if icon_path:
            icon = QIcon(icon_path)
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(0, 0, 0, 0))
            painter = QPainter(pixmap)
            painter.setBrush(QColor("#e94560"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
            painter.setPen(QColor("white"))
            font = QFont("Arial", 16, QFont.Bold)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "F")
            painter.end()
            icon = QIcon(pixmap)

        self._tray_icon = QSystemTrayIcon(icon, self)
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示主窗口")
        show_action.triggered.connect(self._show_window)

        self._toggle_floating_action = tray_menu.addAction("显示浮窗")
        self._toggle_floating_action.triggered.connect(self._toggle_floating)

        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self._quit_app)
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._tray_activated)
        self._tray_icon.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()

    def set_floating_widget(self, widget):
        self._floating_widget = widget
        self._update_floating_action_text()

    def _toggle_floating(self):
        if self._floating_widget:
            if self._floating_widget.isVisible():
                self._floating_widget.hide()
            else:
                self._floating_widget.show()
            self._update_floating_action_text()

    def _update_floating_action_text(self):
        if self._floating_widget:
            if self._floating_widget.isVisible():
                self._toggle_floating_action.setText("隐藏浮窗")
            else:
                self._toggle_floating_action.setText("显示浮窗")

    def _setup_monitors(self):
        self.monitor = ExplorerMonitor(self.storage, self.config)
        self.recent_monitor = RecentFolderMonitor(self.storage, self.config)
        self.monitor.start()
        self.recent_monitor.start()

    def _request_refresh(self):
        self._pending_refresh = True

    def _refresh_list(self):
        if not self._pending_refresh:
            return
        self._pending_refresh = False
        search_text = self._search_box.text().strip().lower()
        sort_mode = self._get_sort_mode()
        records = self.storage.get_all(sort_mode)

        if search_text:
            records = [r for r in records if search_text in r.path.lower() or (r.alias and search_text in r.alias.lower())]

        invalid_paths = self.storage.get_invalid_paths()
        invalid_set = set(invalid_paths)
        if invalid_paths:
            self._clean_invalid_btn.show()
            self._clean_invalid_btn.setToolTip(f"清理 {len(invalid_paths)} 个失效路径")
        else:
            self._clean_invalid_btn.hide()

        self._tree.setUpdatesEnabled(False)
        self._tree.clear()

        if self._group_btn.isChecked():
            groups = {}
            for r in records:
                groups.setdefault(r.group, []).append(r)
            for group_name, group_records in sorted(groups.items()):
                group_item = QTreeWidgetItem(self._tree, [f"📂 {group_name}", "", "", "", ""])
                group_item.setExpanded(True)
                font = group_item.font(0)
                font.setBold(True)
                group_item.setFont(0, font)
                group_item.setForeground(0, QColor("#e94560"))
                for r in group_records:
                    self._add_record_item(group_item, r, invalid_set)
        else:
            for r in records:
                self._add_record_item(None, r, invalid_set)

        self._tree.setUpdatesEnabled(True)
        total = self.storage.total_count()
        shown = len(records)
        self._count_label.setText(f"显示 {shown} / 总计 {total}")
        self._status_label.setText(
            f"监控运行中 · 阈值 ≥{self.config.auto_collect_threshold}次"
        )

    def _add_record_item(self, parent, record: FolderRecord, invalid_set: set = None):
        item = QTreeWidgetItem(parent or self._tree)
        item.setData(0, Qt.UserRole, record.path)

        is_invalid = invalid_set and record.path in invalid_set
        display_path = record.alias if record.alias else record.path
        if is_invalid:
            item.setText(0, f"⚠ {display_path}")
            item.setForeground(0, QColor("#6b7b8d"))
        else:
            item.setText(0, display_path)
            if record.alias:
                item.setToolTip(0, record.path)

        count_text = f"🔥 {record.access_count}" if record.access_count >= 10 else str(record.access_count)
        item.setText(1, count_text)
        if record.access_count >= 10:
            item.setForeground(1, QColor("#e94560"))
        elif record.access_count >= 5:
            item.setForeground(1, QColor("#ffa500"))

        try:
            dt = datetime.fromisoformat(record.last_access_time)
            item.setText(2, dt.strftime("%Y-%m-%d %H:%M"))
        except (ValueError, TypeError):
            item.setText(2, record.last_access_time)

        item.setText(3, record.group)

        status_parts = []
        if record.is_locked:
            status_parts.append("🔒")
        item.setText(4, " ".join(status_parts) if status_parts else "-")

    def _get_sort_mode(self) -> str:
        idx = self._sort_combo.currentIndex()
        return ["frequency", "recent", "path"][idx]

    def _on_search(self, text: str):
        self._pending_refresh = True
        self._refresh_list()

    def _on_sort_changed(self, index: int):
        self._pending_refresh = True
        self._refresh_list()

    def _toggle_group(self, checked: bool):
        self._pending_refresh = True
        self._refresh_list()

    def _show_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        path = item.data(0, Qt.UserRole)
        if not path:
            return

        menu = QMenu(self)
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
            lock_action.triggered.connect(lambda: self._toggle_lock(path))

            alias_text = "✏ 修改别名" if record.alias else "🏷 设置别名"
            alias_action = menu.addAction(alias_text)
            alias_action.triggered.connect(lambda: self._set_alias(path))

            if record.alias:
                clear_alias_action = menu.addAction("✕ 清除别名")
                clear_alias_action.triggered.connect(lambda: self._set_alias(path, clear=True))

        menu.addSeparator()

        delete_action = menu.addAction("🗑 删除记录")
        delete_action.triggered.connect(lambda: self._delete_record(path))

        menu.exec_(self._tree.viewport().mapToGlobal(pos))

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

    def _toggle_lock(self, path: str):
        self.storage.toggle_lock(path)

    def _set_alias(self, path: str, clear: bool = False):
        if clear:
            self.storage.set_alias(path, "")
            return
        from PyQt5.QtWidgets import QInputDialog
        record = self.storage.get_record(path)
        current_alias = record.alias if record else ""
        alias, ok = QInputDialog.getText(
            self, "设置别名",
            f"为文件夹设置简短别名：\n{path}",
            text=current_alias,
        )
        if ok:
            self.storage.set_alias(path, alias.strip())

    def _delete_record(self, path: str):
        self.storage.remove(path)

    def _manual_add(self):
        from PyQt5.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            if not self.storage.is_whitelisted(folder):
                self.storage.record_access(folder)

    def _clean_invalid_paths(self):
        invalid = self.storage.get_invalid_paths()
        if not invalid:
            return
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "清理失效路径",
            f"检测到 {len(invalid)} 个文件夹路径已失效（目录不存在）。\n\n是否删除这些记录？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self.storage.remove_paths(invalid)

    def _open_settings(self):
        from settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self.storage, self)
        if dialog.exec_() == SettingsDialog.Accepted:
            self._pending_refresh = True
            self._refresh_list()
            if self._floating_widget:
                self._floating_widget._apply_opacity()

    def _quit_app(self):
        if self.monitor:
            self.monitor.stop()
        if self.recent_monitor:
            self.recent_monitor.stop()
        if self._tray_icon:
            self._tray_icon.hide()
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().quit()

    def closeEvent(self, event):
        if self.config.minimize_to_tray:
            event.ignore()
            self.hide()
        else:
            self._quit_app()
            event.accept()
