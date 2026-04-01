import sys
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QListWidget, QGroupBox,
                             QComboBox, QMessageBox, QFileDialog, QGridLayout, QCheckBox)
from PyQt6.QtCore import Qt


class CPU:
    """Model logiczny naszego mikroprocesora."""

    def __init__(self):
        # Wewnętrzna reprezentacja rejestrów to zawsze 16-bitowe liczby całkowite (0-65535)
        self.registers = {'AX': 0, 'BX': 0, 'CX': 0, 'DX': 0}

    def get_val(self, reg_name):
        reg_name = reg_name.upper()
        if reg_name in self.registers:
            return self.registers[reg_name]

        # Obsługa rejestrów 8-bitowych (H - High, L - Low)
        base_reg = reg_name[0] + 'X'
        if reg_name[1] == 'H':
            return (self.registers[base_reg] >> 8) & 0xFF
        elif reg_name[1] == 'L':
            return self.registers[base_reg] & 0xFF
        raise ValueError(f"Nieznany rejestr: {reg_name}")

    def set_val(self, reg_name, value):
        reg_name = reg_name.upper()
        if reg_name in self.registers:
            self.registers[reg_name] = value & 0xFFFF  # Maskowanie do 16 bitów
        else:
            base_reg = reg_name[0] + 'X'
            current_val = self.registers[base_reg]
            if reg_name[1] == 'H':
                # Zmieniamy tylko starsze 8 bitów
                self.registers[base_reg] = (current_val & 0x00FF) | ((value & 0xFF) << 8)
            elif reg_name[1] == 'L':
                # Zmieniamy tylko młodsze 8 bitów
                self.registers[base_reg] = (current_val & 0xFF00) | (value & 0xFF)
            else:
                raise ValueError(f"Nieznany rejestr: {reg_name}")

    def is_16_bit(self, reg_name):
        return reg_name.upper().endswith('X')


class RegisterWidget(QGroupBox):
    """Wizualny komponent reprezentujący jeden 16-bitowy rejestr."""

    def __init__(self, name, cpu_ref, update_callback):
        super().__init__(f"Rejestr {name}")
        self.name = name
        self.cpu = cpu_ref
        self.update_callback = update_callback

        layout = QVBoxLayout()

        # Wyświetlacze szesnastkowe dla H i L
        hex_layout = QHBoxLayout()
        self.hex_label = QLabel("0000")
        self.hex_label.setStyleSheet("font-family: Consolas; font-size: 20px; font-weight: bold; color: #3498db;")
        self.hex_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hex_layout.addWidget(QLabel(f"{name[0]}H : {name[0]}L  => "))
        hex_layout.addWidget(self.hex_label)
        layout.addLayout(hex_layout)

        # Diody (bity)
        bits_layout = QHBoxLayout()
        bits_layout.setSpacing(2)
        self.bit_checkboxes = []

        for i in range(15, -1, -1):
            cb = QCheckBox()
            # Stylizacja na okrągłe diody w QSS zajmie się wyglądem
            cb.setToolTip(f"Bit {i}")
            cb.clicked.connect(self.on_bit_toggled)
            self.bit_checkboxes.append(cb)
            bits_layout.addWidget(cb)

            # Przerwa między połówkami (H i L)
            if i == 8:
                bits_layout.addSpacing(15)

        layout.addLayout(bits_layout)

        # Etykiety bitów
        labels_layout = QHBoxLayout()
        labels_layout.addWidget(QLabel("15 (MSB)"), alignment=Qt.AlignmentFlag.AlignLeft)
        labels_layout.addWidget(QLabel("8"), alignment=Qt.AlignmentFlag.AlignRight)
        labels_layout.addSpacing(15)
        labels_layout.addWidget(QLabel("7"), alignment=Qt.AlignmentFlag.AlignLeft)
        labels_layout.addWidget(QLabel("0 (LSB)"), alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(labels_layout)

        self.setLayout(layout)
        self.refresh_ui()

    def on_bit_toggled(self):
        # Przeliczenie zaznaczonych checkboxów na wartość liczbową
        val = 0
        for i, cb in enumerate(self.bit_checkboxes):
            bit_index = 15 - i
            if cb.isChecked():
                val |= (1 << bit_index)
        self.cpu.set_val(self.name, val)
        self.update_callback()  # Poinformuj główne okno o zmianie

    def refresh_ui(self):
        val = self.cpu.get_val(self.name)
        # Aktualizacja Labela Hex
        self.hex_label.setText(f"{val:04X}")

        # Aktualizacja Checkboxów bez wyzwalania sygnałów kliknięcia
        for i, cb in enumerate(self.bit_checkboxes):
            bit_index = 15 - i
            cb.blockSignals(True)
            cb.setChecked(bool(val & (1 << bit_index)))
            cb.blockSignals(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Symulator Mikroprocesora 16-bit")
        self.resize(1000, 700)

        self.cpu = CPU()
        self.current_line = -1

        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # ================= LEWA STRONA (REJESTRY I BUILDER) =================
        left_layout = QVBoxLayout()

        # Słownik przechowujący widgety rejestrów do ich łatwego odświeżania
        self.reg_widgets = {}
        for reg in ['AX', 'BX', 'CX', 'DX']:
            rw = RegisterWidget(reg, self.cpu, self.refresh_all_registers)
            self.reg_widgets[reg] = rw
            left_layout.addWidget(rw)

        # Konstruktor poleceń
        builder_group = QGroupBox("Kreator Rozkazów")
        builder_layout = QHBoxLayout()

        self.op_combo = QComboBox()
        self.op_combo.addItems(["MOV", "ADD", "SUB"])

        self.dest_combo = QComboBox()
        self.dest_combo.addItems(["AX", "AH", "AL", "BX", "BH", "BL", "CX", "CH", "CL", "DX", "DH", "DL"])

        self.src_combo = QComboBox()
        self.src_combo.addItems(["AX", "AH", "AL", "BX", "BH", "BL", "CX", "CH", "CL", "DX", "DH", "DL"])
        self.src_combo.setEditable(True)
        self.src_combo.lineEdit().setPlaceholderText("Rejestr lub Liczba")

        add_btn = QPushButton("Dodaj do kodu")
        add_btn.clicked.connect(self.add_instruction_from_builder)

        builder_layout.addWidget(self.op_combo)
        builder_layout.addWidget(self.dest_combo)
        builder_layout.addWidget(QLabel(","))
        builder_layout.addWidget(self.src_combo)
        builder_layout.addWidget(add_btn)
        builder_group.setLayout(builder_layout)

        left_layout.addWidget(builder_group)
        main_layout.addLayout(left_layout, stretch=1)

        # ================= PRAWA STRONA (KOD I KONTROLA) =================
        right_layout = QVBoxLayout()

        right_layout.addWidget(QLabel("<b>PAMIĘĆ PROGRAMU (Asembler)</b>"))

        self.code_list = QListWidget()
        self.code_list.setStyleSheet("font-family: Consolas; font-size: 16px;")
        right_layout.addWidget(self.code_list)

        # Przyciski sterujące
        controls_layout = QGridLayout()

        btn_step = QPushButton("Wykonaj KROK")
        btn_step.clicked.connect(self.execute_step)

        btn_run = QPushButton("Wykonaj PROGRAM")
        btn_run.clicked.connect(self.execute_all)

        btn_reset = QPushButton("Resetuj Procesor")
        btn_reset.clicked.connect(self.reset_cpu)

        btn_clear = QPushButton("Wyczyść Kod")
        btn_clear.clicked.connect(self.code_list.clear)

        btn_save = QPushButton("Zapisz Program")
        btn_save.clicked.connect(self.save_program)

        btn_load = QPushButton("Wczytaj Program")
        btn_load.clicked.connect(self.load_program)

        controls_layout.addWidget(btn_step, 0, 0)
        controls_layout.addWidget(btn_run, 0, 1)
        controls_layout.addWidget(btn_reset, 0, 2)
        controls_layout.addWidget(btn_clear, 1, 0)
        controls_layout.addWidget(btn_save, 1, 1)
        controls_layout.addWidget(btn_load, 1, 2)

        right_layout.addLayout(controls_layout)
        main_layout.addLayout(right_layout, stretch=1)

    def refresh_all_registers(self):
        for rw in self.reg_widgets.values():
            rw.refresh_ui()

    def add_instruction_from_builder(self):
        op = self.op_combo.currentText()
        dest = self.dest_combo.currentText()
        src = self.src_combo.currentText().strip()

        if not src:
            QMessageBox.warning(self, "Błąd", "Brak argumentu źródłowego!")
            return

        instruction = f"{op} {dest}, {src}"
        self.code_list.addItem(instruction)

    # --- LOGIKA WYKONYWANIA ROZKAZÓW ---
    def parse_and_execute(self, line):
        # Usuwamy komentarze i białe znaki
        line = line.split(';')[0].strip().upper()
        if not line:
            return True  # Pusta linia, idziemy dalej

        # Wyrażenie regularne do parsowania: OP DEST, SRC (przecinek opcjonalny)
        match = re.match(r'^([A-Z]+)\s+([A-Z]{2})\s*,?\s*(.+)$', line)
        if not match:
            raise SyntaxError(f"Nieprawidłowa składnia: {line}")

        op, dest, src = match.groups()

        if op not in ['MOV', 'ADD', 'SUB']:
            raise SyntaxError(f"Nieobsługiwana operacja: {op}")

        # Pobranie wartości źródłowej (Tryb Rejestrowy lub Natychmiastowy)
        src_val = 0
        if re.match(r'^[A-D][XLH]$', src):
            # Tryb rejestrowy
            # Zabezpieczenie przed mieszaniem 8 i 16 bitów
            if self.cpu.is_16_bit(dest) != self.cpu.is_16_bit(src):
                raise ValueError("Niezgodność rozmiarów operandów (8-bit vs 16-bit)!")
            src_val = self.cpu.get_val(src)
        else:
            # Tryb natychmiastowy (liczba dziesiętna lub hex np. 0xFF)
            try:
                src_val = int(src, 0)
                # Zabezpieczenie przed wpisaniem za dużej liczby
                max_val = 0xFFFF if self.cpu.is_16_bit(dest) else 0xFF
                if src_val > max_val or src_val < -max_val:
                    raise ValueError(f"Wartość {src} przekracza rozmiar rejestru {dest}!")
            except ValueError as e:
                raise ValueError(f"Nieprawidłowa wartość natychmiastowa: {src}. Szczegóły: {e}")

        # Wykonanie operacji na ALU
        dest_val = self.cpu.get_val(dest)

        if op == 'MOV':
            result = src_val
        elif op == 'ADD':
            result = dest_val + src_val
        elif op == 'SUB':
            result = dest_val - src_val

        # Zapis do rejestru (CPU zajmuje się maskowaniem do 8/16 bitów)
        self.cpu.set_val(dest, result)
        self.refresh_all_registers()
        return True

    def execute_step(self):
        if self.code_list.count() == 0:
            return

        # Odznaczenie poprzedniej linii
        if self.current_line >= 0 and self.current_line < self.code_list.count():
            self.code_list.item(self.current_line).setBackground(Qt.GlobalColor.transparent)
            self.code_list.item(self.current_line).setForeground(Qt.GlobalColor.white)  # Dla Dark Mode

        self.current_line += 1

        if self.current_line >= self.code_list.count():
            self.current_line = -1
            QMessageBox.information(self, "Koniec", "Program zakończył działanie.")
            return

        # Podświetlenie aktualnej linii na żółto (i ciemny tekst dla czytelności)
        item = self.code_list.item(self.current_line)
        item.setBackground(QColor("#f1c40f"))
        item.setForeground(QColor("black"))
        self.code_list.setCurrentItem(item)

        line_text = item.text()
        try:
            self.parse_and_execute(line_text)
        except Exception as e:
            QMessageBox.critical(self, "Błąd Wykonania", f"Błąd w linii {self.current_line + 1}:\n{str(e)}")
            self.current_line = -1  # Przerwanie działania

    def execute_all(self):
        self.reset_cpu()  # Czysty start
        while self.current_line < self.code_list.count() - 1:
            self.execute_step()
            # Jeśli wystąpił błąd, current_line zostanie zresetowany na -1
            if self.current_line == -1:
                break

    def reset_cpu(self):
        for reg in ['AX', 'BX', 'CX', 'DX']:
            self.cpu.set_val(reg, 0)
        self.refresh_all_registers()

        if self.current_line >= 0 and self.current_line < self.code_list.count():
            self.code_list.item(self.current_line).setBackground(Qt.GlobalColor.transparent)
            self.code_list.item(self.current_line).setForeground(Qt.GlobalColor.white)
        self.current_line = -1

    # --- ZAPIS I ODCZYT ---
    def save_program(self):
        path, _ = QFileDialog.getSaveFileName(self, "Zapisz Program", "",
                                              "Pliki Asemblera (*.asm);;Wszystkie Pliki (*)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                for i in range(self.code_list.count()):
                    f.write(self.code_list.item(i).text() + "\n")
            QMessageBox.information(self, "Sukces", "Program zapisany.")

    def load_program(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wczytaj Program", "",
                                              "Pliki Asemblera (*.asm);;Wszystkie Pliki (*)")
        if path:
            self.code_list.clear()
            self.reset_cpu()
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        self.code_list.addItem(line.strip())


# === GLOBALNY ARKUSZ STYLÓW (DARK MODE) ===
STYLE_SHEET = """
QMainWindow { background-color: #2c3e50; }
QLabel { color: #ecf0f1; }
QGroupBox { font-weight: bold; border: 2px solid #7f8c8d; border-radius: 6px; margin-top: 12px; color: #ecf0f1; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }

/* Stylowanie CheckBoxow na kropki (Dioda off) */
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 8px; border: 2px solid #7f8c8d; background-color: #34495e; }
/* Dioda on */
QCheckBox::indicator:checked { background-color: #e74c3c; border: 2px solid #c0392b; }

QComboBox, QLineEdit { padding: 5px; font-size: 14px; background-color: #34495e; color: white; border: 1px solid #7f8c8d; border-radius: 4px; }
QListWidget { background-color: #1e2b3c; color: white; border: 2px solid #7f8c8d; }
QListWidget::item { padding: 5px; border-bottom: 1px solid #2c3e50; }

QPushButton { background-color: #2980b9; color: white; font-weight: bold; padding: 10px; border-radius: 5px; border: none; }
QPushButton:hover { background-color: #3498db; }
QPushButton:pressed { background-color: #1c5980; }

QMessageBox { background-color: #2c3e50; }
QMessageBox QLabel { color: white; }
"""

if __name__ == "__main__":
    from PyQt6.QtGui import QColor

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())