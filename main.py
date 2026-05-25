import sys
import logging
import os
import traceback

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)


def main():
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from PyQt5.QtCore import Qt

        from models import Config
        from storage import FolderStorage
        from main_window import MainWindow
        from floating_widget import FloatingWidget

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)
        app.setApplicationName("高频文件夹管理器")

        config = Config.get_instance()
        storage = FolderStorage(config)

        window = MainWindow(storage, config)

        floating = FloatingWidget(storage, config)
        floating.open_main_window.connect(window._show_window)
        floating.open_settings.connect(window._open_settings)
        window.set_floating_widget(floating)

        floating.show()

        sys.exit(app.exec_())
    except Exception as e:
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            app = QApplication.instance()
            if app is None:
                app = QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "程序错误",
                f"高频文件夹管理器启动失败：\n\n{traceback.format_exc()}",
            )
        except Exception:
            with open(os.path.join(os.path.expanduser("~"), "freq_folder_error.log"), "w", encoding="utf-8") as f:
                f.write(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
