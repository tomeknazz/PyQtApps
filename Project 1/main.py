import datetime
import sys

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QPixmap
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QPushButton, QLabel, QFileDialog, QGridLayout, QStackedWidget)


class CalculatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kalkulator i zegar")
        self.setFixedSize(400, 700)

        # Ustawienie globalnego stylu dla wszystkich przycisków w aplikacji
        self.setStyleSheet("""
            QPushButton { 
                background-color: white; 
                color: black; 
                border: 1px solid #999; 
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #eee;
            }
        """)

        self.current_bg_color = QColor(240, 240, 240)
        self.bg_pixmap = None
        self.show_analog = False

        self.main_layout = QVBoxLayout()

        self.init_clock_ui()
        self.init_calc_ui()
        self.init_settings_ui()

        self.setLayout(self.main_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

    def init_clock_ui(self):
        # Kontener na górną sekcję zegara
        clock_section = QVBoxLayout()

        # StackedWidget pozwala zachować ten sam rozmiar miejsca dla obu typów zegara
        self.clock_stack = QStackedWidget()
        self.clock_stack.setFixedHeight(120)

        # Widżet dla zegara cyfrowego
        self.digital_clock = QLabel()
        self.digital_clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.digital_clock.setStyleSheet(
            "font-size: 30px; font-weight: bold; color: black; background: rgba(255,255,255,100);")

        # Pusty widżet pełniący rolę "miejsca" dla zegara analogowego (rysowanego w paintEvent)
        self.analog_placeholder = QWidget()

        self.clock_stack.addWidget(self.digital_clock)
        self.clock_stack.addWidget(self.analog_placeholder)

        # Przycisk zmiany trybu pod zegarem, by nie pływał
        self.analog_toggle = QPushButton("Zmień tryb zegara")
        self.analog_toggle.setFixedWidth(150)
        self.analog_toggle.clicked.connect(self.toggle_clock_mode)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.analog_toggle)
        btn_layout.addStretch()

        clock_section.addWidget(self.clock_stack)
        clock_section.addLayout(btn_layout)

        self.main_layout.addLayout(clock_section)

    def init_calc_ui(self):
        self.display = QLineEdit()
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.display.setFixedHeight(100)
        self.display.setStyleSheet("font-size: 32px; background: white; color: black; border: 2px solid #ccc;")
        self.main_layout.addWidget(self.display)

        grid = QGridLayout()
        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            'C', '0', '=', '+'
        ]

        row, col = 0, 0
        for button_text in buttons:
            btn = QPushButton(button_text)
            btn.setFixedSize(70, 70)
            btn.setStyleSheet("font-size: 20px; font-weight: bold;")
            btn.clicked.connect(self.on_button_click)
            grid.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1
        self.main_layout.addLayout(grid)

    def init_settings_ui(self):
        settings_layout = QHBoxLayout()
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("HEX np. #ff0000")
        self.hex_input.setStyleSheet("background: white; color: black; height: 30px;")

        apply_btn = QPushButton("Ustaw kolor")
        apply_btn.clicked.connect(self.apply_hex_color)

        upload_btn = QPushButton("Wgraj zdjęcie")
        upload_btn.clicked.connect(self.upload_background)

        settings_layout.addWidget(self.hex_input)
        settings_layout.addWidget(apply_btn)
        settings_layout.addWidget(upload_btn)
        self.main_layout.addLayout(settings_layout)

    def on_button_click(self):
        sender = self.sender().text()
        current_text = self.display.text()

        if sender == 'C':
            self.display.clear()
        elif sender == '=':
            try:
                result = str(eval(current_text))
                self.display.setText(result)
            except:
                self.display.setText("Błąd")
        else:
            self.display.setText(current_text + sender)

    def toggle_clock_mode(self):
        self.show_analog = not self.show_analog
        if self.show_analog:
            self.clock_stack.setCurrentIndex(1)
        else:
            self.clock_stack.setCurrentIndex(0)
        self.update()

    def apply_hex_color(self):
        color_code = self.hex_input.text()
        if QColor.isValidColor(color_code):
            self.current_bg_color = QColor(color_code)
            self.bg_pixmap = None
            self.update()

    def upload_background(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz obraz", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.bg_pixmap = QPixmap(file_path).scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rysowanie tła
        if self.bg_pixmap:
            painter.drawPixmap(0, 0, self.bg_pixmap)
        else:
            painter.fillRect(self.rect(), self.current_bg_color)

        now = datetime.datetime.now()
        self.digital_clock.setText(now.strftime("%H:%M:%S"))

        if self.show_analog:
            painter.save()
            # Ustawienie środka zegara dokładnie tam, gdzie jest analog_placeholder
            center = self.clock_stack.geometry().center()
            painter.translate(center.x(), center.y())

            # Tarcza
            painter.setBrush(QColor(255, 255, 255, 220))
            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.drawEllipse(-55, -55, 110, 110)

            # Wskazówki
            self.draw_hand(painter, (now.hour % 12 + now.minute / 60) * 30, 30, 4)
            self.draw_hand(painter, (now.minute + now.second / 60) * 6, 45, 2)
            self.draw_hand(painter, now.second * 6, 50, 1, Qt.GlobalColor.red)
            painter.restore()

    def draw_hand(self, painter, angle, length, width, color=Qt.GlobalColor.black):
        painter.save()
        painter.rotate(angle)
        painter.setPen(QPen(color, width))
        painter.drawLine(0, 0, 0, -length)
        painter.restore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CalculatorApp()
    window.show()
    sys.exit(app.exec())
