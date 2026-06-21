from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QCheckBox, QListWidget, QListWidgetItem, QPushButton,
    QGroupBox, QFormLayout, QLineEdit, QMessageBox, QFileDialog,
    QTabWidget, QWidget, QFrame, QSlider,
)
from PyQt5.QtCore import Qt

from models import Config
from storage import FolderStorage

SETTINGS_STYLESHEET = """
QDialog {
    background-color: #1a1a2e;
    font-size: 26px;
}
QLabel {
    color: #e0e0e0;
    font-size: 26px;
}
QGroupBox {
    color: #e94560;
    border: 1px solid #0f3460;
    border-radius: 10px;
    margin-top: 16px;
    padding-top: 20px;
    font-weight: bold;
    font-size: 26px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
}
QSpinBox {
    background-color: #0f3460;
    border: 1px solid #1a1a5e;
    border-radius: 8px;
    padding: 8px 14px;
    color: #e0e0e0;
    min-width: 120px;
    font-size: 26px;
}
QCheckBox {
    color: #e0e0e0;
    spacing: 10px;
    font-size: 26px;
}
QCheckBox::indicator {
    width: 24px;
    height: 24px;
    border-radius: 5px;
    border: 1px solid #0f3460;
    background-color: #16213e;
}
QCheckBox::indicator:checked {
    background-color: #e94560;
    border-color: #e94560;
}
QListWidget {
    background-color: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    color: #e0e0e0;
    padding: 6px;
    font-size: 26px;
}
QListWidget::item {
    padding: 12px;
    border-radius: 6px;
    font-size: 26px;
}
QListWidget::item:selected {
    background-color: #0f3460;
}
QLineEdit {
    background-color: #0f3460;
    border: 1px solid #1a1a5e;
    border-radius: 8px;
    padding: 10px 16px;
    color: #e0e0e0;
    font-size: 26px;
}
QLineEdit:focus {
    border: 1px solid #e94560;
}
QPushButton {
    background-color: #0f3460;
    border: 1px solid #1a1a5e;
    border-radius: 8px;
    padding: 14px 28px;
    color: #e0e0e0;
    font-size: 26px;
}
QPushButton:hover {
    background-color: #e94560;
    border-color: #e94560;
}
QPushButton#dangerBtn {
    background-color: #5e1a1a;
    border-color: #e94560;
}
QPushButton#dangerBtn:hover {
    background-color: #e94560;
}
QTabWidget::pane {
    border: 1px solid #0f3460;
    border-radius: 6px;
    background-color: #1a1a2e;
}
QTabBar::tab {
    background-color: #16213e;
    color: #a0b0c0;
    padding: 16px 36px;
    font-size: 26px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #0f3460;
    color: #e94560;
}
QSlider::groove:horizontal {
    background-color: #0f3460;
    height: 8px;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background-color: #e94560;
    width: 22px;
    height: 22px;
    margin: -7px 0;
    border-radius: 11px;
}
QSlider::sub-page:horizontal {
    background-color: #e94560;
    border-radius: 3px;
}
"""


class SettingsDialog(QDialog):
    def __init__(self, config: Config, storage: FolderStorage, parent=None):
        super().__init__(parent)
        self.config = config
        self.storage = storage
        self.setWindowTitle("设置")
        self.setMinimumSize(1800, 1125)
        self.resize(2376, 1485)
        self.setStyleSheet(SETTINGS_STYLESHEET)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._create_general_tab(), "通用")
        tabs.addTab(self._create_floating_tab(), "浮窗")
        tabs.addTab(self._create_whitelist_tab(), "白名单")
        tabs.addTab(self._create_cleanup_tab(), "清理")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _create_general_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        monitor_group = QGroupBox("监控设置")
        monitor_form = QFormLayout(monitor_group)
        self._threshold_spin = QSpinBox()
        self._threshold_spin.setRange(1, 100)
        self._threshold_spin.setValue(self.config.auto_collect_threshold)
        self._threshold_spin.setToolTip("访问次数达到此阈值后自动收录到列表")
        monitor_form.addRow("自动收录阈值（次）:", self._threshold_spin)

        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 60)
        self._interval_spin.setValue(self.config.monitor_interval_seconds)
        self._interval_spin.setToolTip("扫描Explorer窗口的间隔秒数")
        monitor_form.addRow("监控间隔（秒）:", self._interval_spin)
        layout.addWidget(monitor_group)

        behavior_group = QGroupBox("行为设置")
        behavior_form = QFormLayout(behavior_group)
        self._tray_check = QCheckBox("关闭窗口时最小化到托盘")
        self._tray_check.setChecked(self.config.minimize_to_tray)
        behavior_form.addRow(self._tray_check)

        self._startup_check = QCheckBox("开机自动启动")
        self._startup_check.setChecked(self.config.start_with_system)
        behavior_form.addRow(self._startup_check)
        layout.addWidget(behavior_group)

        layout.addStretch()
        return widget

    def _create_floating_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        display_group = QGroupBox("浮窗显示")
        display_form = QFormLayout(display_group)

        self._floating_top_check = QCheckBox("始终置顶")
        self._floating_top_check.setChecked(self.config.get("floating_always_on_top", True))
        display_form.addRow(self._floating_top_check)

        self._floating_max_spin = QSpinBox()
        self._floating_max_spin.setRange(3, 50)
        self._floating_max_spin.setValue(self.config.get("floating_max_items", 15))
        self._floating_max_spin.setToolTip("浮窗中最多显示的文件夹数量")
        display_form.addRow("最大显示条目数:", self._floating_max_spin)

        opacity_row = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Horizontal)
        self._opacity_slider.setRange(50, 100)
        self._opacity_slider.setValue(int(self.config.get("floating_opacity", 0.92) * 100))
        self._opacity_slider.setTickPosition(QSlider.TicksBelow)
        self._opacity_slider.setTickInterval(10)
        self._opacity_label = QLabel(f"{self._opacity_slider.value()}%")
        self._opacity_label.setMinimumWidth(40)
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v}%")
        )
        opacity_row.addWidget(self._opacity_slider)
        opacity_row.addWidget(self._opacity_label)
        display_form.addRow("透明度:", opacity_row)

        layout.addWidget(display_group)
        layout.addStretch()
        return widget

    def _create_whitelist_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)

        desc = QLabel("白名单中的目录不会被收录到高频列表中")
        desc.setStyleSheet("color: #6b7b8d; font-size: 12px;")
        layout.addWidget(desc)

        self._whitelist_widget = QListWidget()
        for path in self.config.whitelist:
            item = QListWidgetItem(path)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self._whitelist_widget.addItem(item)
        layout.addWidget(self._whitelist_widget)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ 添加")
        add_btn.clicked.connect(self._add_whitelist)
        btn_row.addWidget(add_btn)

        remove_btn = QPushButton("- 移除选中")
        remove_btn.setObjectName("dangerBtn")
        remove_btn.clicked.connect(self._remove_whitelist)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return widget

    def _create_cleanup_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)

        cleanup_group = QGroupBox("自动清理设置")
        cleanup_form = QFormLayout(cleanup_group)

        self._auto_cleanup_check = QCheckBox("启用自动清理")
        self._auto_cleanup_check.setChecked(self.config.auto_cleanup_enabled)
        cleanup_form.addRow(self._auto_cleanup_check)

        self._cleanup_days_spin = QSpinBox()
        self._cleanup_days_spin.setRange(1, 365)
        self._cleanup_days_spin.setValue(self.config.cleanup_days)
        self._cleanup_days_spin.setToolTip("超过此天数未访问的目录将被清理")
        cleanup_form.addRow("清理阈值（天）:", self._cleanup_days_spin)

        self._cleanup_min_spin = QSpinBox()
        self._cleanup_min_spin.setRange(1, 100)
        self._cleanup_min_spin.setValue(self.config.cleanup_min_count)
        self._cleanup_min_spin.setToolTip("访问次数低于此值的目录才可被清理")
        cleanup_form.addRow("最低频次阈值:", self._cleanup_min_spin)
        layout.addWidget(cleanup_group)

        manual_group = QGroupBox("手动操作")
        manual_layout = QVBoxLayout(manual_group)
        clean_now_btn = QPushButton("立即执行清理")
        clean_now_btn.setObjectName("dangerBtn")
        clean_now_btn.clicked.connect(self._cleanup_now)
        manual_layout.addWidget(clean_now_btn)
        layout.addWidget(manual_group)

        layout.addStretch()
        return widget

    def _add_whitelist(self):
        folder = QFileDialog.getExistingDirectory(self, "选择要排除的目录")
        if folder:
            item = QListWidgetItem(folder)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self._whitelist_widget.addItem(item)

    def _remove_whitelist(self):
        current = self._whitelist_widget.currentRow()
        if current >= 0:
            self._whitelist_widget.takeItem(current)

    def _cleanup_now(self):
        removed = self.storage.cleanup()
        QMessageBox.information(
            self, "清理完成", f"已清理 {removed} 个低活跃目录"
        )

    def _save(self):
        self.config.set("auto_collect_threshold", self._threshold_spin.value())
        self.config.set("monitor_interval_seconds", self._interval_spin.value())
        self.config.set("minimize_to_tray", self._tray_check.isChecked())
        self.config.set("start_with_system", self._startup_check.isChecked())
        Config.set_auto_start(self._startup_check.isChecked())
        self.config.set("auto_cleanup_enabled", self._auto_cleanup_check.isChecked())
        self.config.set("cleanup_days", self._cleanup_days_spin.value())
        self.config.set("cleanup_min_count", self._cleanup_min_spin.value())

        self.config.set("floating_always_on_top", self._floating_top_check.isChecked())
        self.config.set("floating_max_items", self._floating_max_spin.value())
        self.config.set("floating_opacity", self._opacity_slider.value() / 100.0)

        whitelist = []
        for i in range(self._whitelist_widget.count()):
            whitelist.append(self._whitelist_widget.item(i).text().strip())
        self.config.set("whitelist", whitelist)

        self.config.save()
        self.accept()
