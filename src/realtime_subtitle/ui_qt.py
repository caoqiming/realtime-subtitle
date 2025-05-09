from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QCheckBox, QTextEdit, QVBoxLayout,
    QHBoxLayout, QWidget, QDialog, QLabel, QLineEdit, QComboBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from realtime_subtitle.subtitle import RealtimeSubtitle
from realtime_subtitle import app_config

rs = RealtimeSubtitle()
cfg = app_config.get()

# Constants
SUBTITLE_LENGTH = cfg.SubtitleLength
SUBTITLE_HIGH = cfg.SubtitleHight
TRANSLATION_SUBTITLE_LENGTH = cfg.TranslationSubtitleLength
TRANSLATION_SUBTITLE_HIGH = cfg.TranslationSubtitleHight
MODLE_OUTPUT_ADD_THRESHOLD = 80
MODLE_OUTPUT_SUB_THRESHOLD = 3
MODLE_REFUSE_THRESHOLD = cfg.ModelRefuseThreshold


class MainWindow(QMainWindow):
    update_text_signal = pyqtSignal(str, str)  # 定义信号，用于更新文本框内容

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Realtime Subtitle")
        self.model_thrashing_count = 0
        self.last_all_text_length = 0

        # Main layout
        main_layout = QVBoxLayout()

        # Buttons
        button_layout = QHBoxLayout()
        self.start_stop_button = QPushButton("Start")
        self.start_stop_button.clicked.connect(self.start_stop_button_onclick)
        button_layout.addWidget(self.start_stop_button)

        self.floating_check_button = QCheckBox("Subtitle Floating Window")
        self.floating_check_button.stateChanged.connect(
            self.floating_check_button_onclick)
        button_layout.addWidget(self.floating_check_button)

        self.translation_floating_check_button = QCheckBox(
            "Translation Floating Window")
        self.translation_floating_check_button.stateChanged.connect(
            self.translation_floating_check_button_onclick)
        button_layout.addWidget(self.translation_floating_check_button)

        self.setting_button = QPushButton("Settings")
        self.setting_button.clicked.connect(self.setting_button_onclick)
        button_layout.addWidget(self.setting_button)

        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self.export_button_onclick)
        button_layout.addWidget(self.export_button)

        main_layout.addLayout(button_layout)

        # Text areas
        self.all_text = QTextEdit()
        self.all_text.setReadOnly(True)
        main_layout.addWidget(self.all_text)

        self.all_translation_text = QTextEdit()
        self.all_translation_text.setReadOnly(True)
        main_layout.addWidget(self.all_translation_text)

        # Central widget
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Floating windows
        self.floating_window = None
        self.translation_floating_window = None

        # Connect signal to slot
        self.update_text_signal.connect(self.update_text_slot)

        # Update hook
        rs.set_update_hook(self.update_hook)

    def start_stop_button_onclick(self):
        if rs.running:
            rs.stop()
            self.start_stop_button.setText("Start")
        else:
            rs.start()
            self.start_stop_button.setText("Stop")

    def floating_check_button_onclick(self):
        if self.floating_check_button.isChecked():
            self.floating_window = FloatingWindow(
                cfg, "original")
            self.floating_window.show()
        elif self.floating_window:
            self.floating_window.close()
            self.floating_window = None

    def translation_floating_check_button_onclick(self):
        if self.translation_floating_check_button.isChecked():
            self.translation_floating_window = FloatingWindow(
                cfg, "translation")
            self.translation_floating_window.show()
        elif self.translation_floating_window:
            self.translation_floating_window.close()
            self.translation_floating_window = None

    def setting_button_onclick(self):
        dialog = SettingsDialog(cfg, rs)
        dialog.exec()

    def export_button_onclick(self):
        if rs.running:
            rs.stop()
        rs.export()

    def update_hook(self):
        archived_text = "".join([one.text for one in rs.archived_data])
        temp_text = "".join([one.text for one in rs.temp_data])
        archived_translation = "".join(
            [one.translated_text for one in rs.archived_data])
        temp_translation = "".join([one.translated_text for one in rs.temp_data[:len(
            rs.temp_data) - cfg.TranslationPresantDelay]])

        all_text = archived_text + temp_text
        all_translation = archived_translation + temp_translation

        # Handle model thrashing
        if len(all_text) > self.last_all_text_length + MODLE_OUTPUT_ADD_THRESHOLD or len(all_text) < self.last_all_text_length - MODLE_OUTPUT_SUB_THRESHOLD:
            self.model_thrashing_count += 1
            if self.model_thrashing_count < MODLE_REFUSE_THRESHOLD:
                return
            else:
                self.model_thrashing_count = 0

        self.last_all_text_length = len(all_text)

        # Emit signal to update GUI
        self.update_text_signal.emit(all_text, all_translation)

    def update_text_slot(self, all_text, all_translation):
        """Slot function to update GUI elements."""
        self.all_text.setPlainText(all_text)
        self.all_translation_text.setPlainText(all_translation)

        if self.floating_window:
            self.floating_window.update_content(
                all_text, SUBTITLE_LENGTH, SUBTITLE_HIGH)
        if self.translation_floating_window:
            self.translation_floating_window.update_content(
                all_translation, TRANSLATION_SUBTITLE_LENGTH, TRANSLATION_SUBTITLE_HIGH)


class FloatingWindow(QMainWindow):
    def __init__(self, cfg: app_config.AppConfig, type: str):
        super().__init__()
        screen = QApplication.primaryScreen()
        screen_size = screen.geometry()  # 返回屏幕的 QRect 对象
        self.screen_width = screen_size.width()
        self.screen_height = screen_size.height()
        if type == "original":
            self.setWindowTitle("Original Floating Window")
            self.setGeometry(
                int(cfg.FloatingWindowXOffset * self.screen_width),
                int(cfg.FloatingWindowYOffset * self.screen_height),
                int(cfg.FloatingWindowX * self.screen_width),
                int(cfg.FloatingWindowY * self.screen_height))
        elif type == "translation":
            self.setGeometry(
                int(cfg.TranslationFloatingWindowXOffset * self.screen_width),
                int(cfg.TranslationFloatingWindowYOffset * self.screen_height),
                int(cfg.FloatingWindowX * self.screen_width),
                int(cfg.FloatingWindowY * self.screen_height))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet(
            f"background-color: {cfg.FloatingWindowBackgroundColor}; "
            f"color: {cfg.FloatingWindowTextColor}; "
            f"font-size: {cfg.FloatingWindowFontSize}px;"
        )
        self.setCentralWidget(self.text_edit)

    def update_content(self, text, length, height):
        show_length = len(text) % length + (height - 1) * length
        show_text = text[-show_length:]
        formatted_text = "\n".join([show_text[i:i + length]
                                   for i in range(0, len(show_text), length)])
        self.text_edit.setPlainText(formatted_text)


class SettingsDialog(QDialog):
    def __init__(self, cfg, rs):
        super().__init__()
        self.setWindowTitle("Settings")
        self.setGeometry(100, 100, 600, 600)

        layout = QVBoxLayout()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        self.field_widgets = {}

        for field_name, field_type in cfg.__annotations__.items():
            if field_name == "AllModelName":
                continue

            label = QLabel(field_name)
            scroll_layout.addWidget(label)

            if field_name == "ModelName":
                combo_box = QComboBox()
                combo_box.addItems([cfg.ModelName] + cfg.AllModelName)
                combo_box.setCurrentText(cfg.ModelName)
                self.field_widgets[field_name] = combo_box
                scroll_layout.addWidget(combo_box)
            elif field_name == "InputDevice":
                combo_box = QComboBox()
                combo_box.addItems([cfg.InputDevice] + rs.get_input_devices())
                combo_box.setCurrentText(cfg.InputDevice)
                self.field_widgets[field_name] = combo_box
                scroll_layout.addWidget(combo_box)
            elif field_type == bool:
                checkbox = QCheckBox()
                checkbox.setChecked(cfg.__dict__[field_name])
                self.field_widgets[field_name] = checkbox
                scroll_layout.addWidget(checkbox)
            elif field_type in [int, float, str]:
                line_edit = QLineEdit(str(cfg.__dict__[field_name]))
                self.field_widgets[field_name] = line_edit
                scroll_layout.addWidget(line_edit)

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        scroll_layout.addWidget(save_button)

        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        self.setLayout(layout)

    def save_settings(self):
        for field_name, widget in self.field_widgets.items():
            if isinstance(widget, QComboBox):
                value = widget.currentText()
            elif isinstance(widget, QCheckBox):
                value = widget.isChecked()
            elif isinstance(widget, QLineEdit):
                value = widget.text()
                if isinstance(cfg.__dict__[field_name], int):
                    value = int(value)
                elif isinstance(cfg.__dict__[field_name], float):
                    value = float(value)
            cfg.__dict__[field_name] = value
        app_config.save(cfg)
        self.accept()


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
