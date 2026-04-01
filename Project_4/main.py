import sys
import os
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QLabel, QTextEdit, QGroupBox, QMessageBox)
from PyQt6.QtCore import Qt


class RS232Simulator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Symulator Transmisji RS232")
        self.resize(1000, 600)

        # Inicjalizacja słownika i bufora transmisyjnego
        self.dictionary_file = "slownik.txt"
        self.ensure_dictionary_exists()
        self.bad_words = self.load_dictionary()
        self.transmission_buffer = ""  # Nasze "medium" transmisyjne

        self.setup_ui()

    def ensure_dictionary_exists(self):
        """Tworzy plik słownika z przykładowymi słowami, jeśli nie istnieje."""
        if not os.path.exists(self.dictionary_file):
            with open(self.dictionary_file, "w", encoding="utf-8") as f:
                f.write("cholera\nkurcze\nmotyla noga\npsia krew\n")

    def load_dictionary(self):
        """Wczytuje słowa ze słownika do listy."""
        try:
            with open(self.dictionary_file, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie udało się wczytać słownika: {e}")
            return []

    def filter_profanity(self, text):
        """Zamienia wulgaryzmy na gwiazdki."""
        filtered_text = text
        for word in self.bad_words:
            # Używamy wyrażeń regularnych do ignorowania wielkości liter (case-insensitive)
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            filtered_text = pattern.sub('*' * len(word), filtered_text)
        return filtered_text

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # ================= NADAJNIK (TX) =================
        tx_group = QGroupBox("Nadajnik (TX)")
        tx_layout = QVBoxLayout()

        self.tx_input = QTextEdit()
        self.tx_input.setPlaceholderText("Wpisz tekst do nadania...")

        self.btn_send = QPushButton("Zakoduj i Wyślij (RS232)")
        self.btn_send.clicked.connect(self.transmit_data)

        self.tx_binary_output = QTextEdit()
        self.tx_binary_output.setReadOnly(True)
        self.tx_binary_output.setPlaceholderText("Tutaj pojawi się zakodowany strumień bitów...")

        tx_layout.addWidget(QLabel("Tekst źródłowy:"))
        tx_layout.addWidget(self.tx_input)
        tx_layout.addWidget(self.btn_send)
        tx_layout.addWidget(QLabel("Strumień wyjściowy (Ramki RS232):"))
        tx_layout.addWidget(self.tx_binary_output)
        tx_group.setLayout(tx_layout)

        # ================= ODBIORNIK (RX) =================
        rx_group = QGroupBox("Odbiornik (RX)")
        rx_layout = QVBoxLayout()

        self.rx_binary_input = QTextEdit()
        self.rx_binary_input.setReadOnly(True)
        self.rx_binary_input.setPlaceholderText("Oczekiwany strumień bitów...")

        self.btn_receive = QPushButton("Odbierz i Zdekoduj")
        self.btn_receive.clicked.connect(self.receive_data)

        self.rx_decoded_output = QTextEdit()
        self.rx_decoded_output.setReadOnly(True)
        self.rx_decoded_output.setPlaceholderText("Zdekodowany i przefiltrowany tekst...")

        rx_layout.addWidget(QLabel("Odebrany strumień (Medium):"))
        rx_layout.addWidget(self.rx_binary_input)
        rx_layout.addWidget(self.btn_receive)
        rx_layout.addWidget(QLabel("Zdekodowany tekst ASCII:"))
        rx_layout.addWidget(self.rx_decoded_output)
        rx_group.setLayout(rx_layout)

        # Dodanie grup do głównego układu
        main_layout.addWidget(tx_group)
        main_layout.addWidget(rx_group)

    # --- LOGIKA KODOWANIA (NADAJNIK) ---
    def transmit_data(self):
        raw_text = self.tx_input.toPlainText()
        if not raw_text:
            return

        # Zgodnie z poleceniem, filtrujemy przed wysłaniem (lub po odbiorze, tutaj robimy przed)
        filtered_text = self.filter_profanity(raw_text)

        encoded_stream = ""
        byte_data = filtered_text.encode('windows-1250', errors='replace')

        for byte_val in byte_data:
            # byte_val to teraz liczba od 0 do 255. Zawsze da dokładnie 8 bitów!
            bin_str = format(byte_val, '08b')

            # Odwrócenie kolejności (LSB do MSB)
            lsb_first = bin_str[::-1]

            # Dodanie bitu startu ('0') i dwóch bitów stopu ('11')
            frame = '0' + lsb_first + '11'
            encoded_stream += frame

        self.tx_binary_output.setPlainText(encoded_stream)
        self.transmission_buffer = encoded_stream
        self.rx_binary_input.setPlainText(self.transmission_buffer)
        self.rx_decoded_output.clear()

    # --- LOGIKA DEKODOWANIA (ODBIORNIK) ---
    def receive_data(self):
        data_stream = self.transmission_buffer
        if not data_stream:
            QMessageBox.information(self, "Pusto", "Brak danych w buforze transmisji.")
            return

        # Długość jednej ramki to 11 bitów (1 start + 8 danych + 2 stop)
        frame_length = 11
        if len(data_stream) % frame_length != 0:
            QMessageBox.warning(self, "Błąd", "Uszkodzony strumień danych! Długość nie jest wielokrotnością 11 bitów.")
            return

        decoded_bytes = bytearray()  # Zbieramy surowe bajty

        for i in range(0, len(data_stream), frame_length):
            frame = data_stream[i:i + frame_length]

            start_bit = frame[0]
            data_bits_lsb = frame[1:9]
            stop_bits = frame[9:11]

            if start_bit != '0' or stop_bits != '11':
                # Znak zapytania w ASCII w razie błędu
                decoded_bytes.append(ord('?'))
                continue

            data_bits_msb = data_bits_lsb[::-1]

            # Zamiana 8 bitów na wartość dziesiętną bajtu (0-255)
            byte_val = int(data_bits_msb, 2)
            decoded_bytes.append(byte_val)

        # Odkodowanie zebranych bajtów z powrotem na tekst z polskimi znakami
        decoded_text = decoded_bytes.decode('windows-1250', errors='replace')

        final_text = self.filter_profanity(decoded_text)
        self.rx_decoded_output.setPlainText(final_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Prosty styl QSS dla lepszej czytelności
    app.setStyleSheet("""
        QGroupBox { font-weight: bold; border: 2px solid gray; border-radius: 5px; margin-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }
        QTextEdit { font-family: Consolas, monospace; font-size: 14px; }
        QPushButton { font-weight: bold; padding: 10px; background-color: #3498db; color: white; }
        QPushButton:hover { background-color: #2980b9; }
    """)

    window = RS232Simulator()
    window.show()
    sys.exit(app.exec())