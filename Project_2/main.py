import random
import sys
import time

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QLabel, QLineEdit, QStackedWidget, QMessageBox)


class WelcomeScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()

        self.label = QLabel("Witaj w testerze sprawności psychomotorycznej.\nPodaj swoje imię:")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("np. Jan Kowalski")
        self.name_input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_btn = QPushButton("Dalej")
        self.start_btn.clicked.connect(self.go_next)

        layout.addStretch()
        layout.addWidget(self.label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.start_btn)
        layout.addStretch()
        self.setLayout(layout)

    def go_next(self):
        if self.name_input.text().strip():
            self.main_window.user_name = self.name_input.text()
            self.main_window.goto_menu()
        else:
            # ZMIANA: self.main_window zamiast self
            QMessageBox.warning(self.main_window, "Błąd", "Proszę podać imię przed rozpoczęciem.")


class MenuScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()

        # Ustawiamy nieco mniejsze marginesy boczne, żeby przyciski były szersze
        layout.setContentsMargins(50, 20, 50, 20)

        self.label = QLabel("Wybierz test do przeprowadzenia:")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 26px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.label)

        self.btn_simple = QPushButton("1. Prosty czas reakcji (Optyczny)")
        self.btn_simple.clicked.connect(lambda: self.main_window.setup_test("simple"))

        self.btn_complex = QPushButton("2. Złożony czas reakcji (Optyczny)")
        self.btn_complex.clicked.connect(lambda: self.main_window.setup_test("complex"))

        self.btn_acoustic = QPushButton("3. Prosty czas reakcji (Akustyczny)")
        self.btn_acoustic.clicked.connect(lambda: self.main_window.setup_test("acoustic"))

        self.btn_results = QPushButton("Pokaż Podsumowanie Wyników")
        # Zamiast wpisywać style ręcznie, nadajemy mu unikalną nazwę (ID),
        # którą obsłużymy w globalnym arkuszu stylów na dole kodu
        self.btn_results.setObjectName("resultsBtn")
        self.btn_results.clicked.connect(self.main_window.goto_results)

        layout.addWidget(self.btn_simple)
        layout.addWidget(self.btn_complex)
        layout.addWidget(self.btn_acoustic)
        layout.addSpacing(20)  # Dodatkowa pusta przestrzeń
        layout.addWidget(self.btn_results)
        layout.addStretch()
        self.setLayout(layout)


class InstructionScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)

        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Usunąłem sztywny rozmiar, teraz czcionka dziedziczy z globalnych stylów

        self.start_btn = QPushButton("Rozpocznij Trening")
        # Wykorzystamy zielony styl z przycisku wyników
        self.start_btn.setObjectName("resultsBtn")
        self.start_btn.clicked.connect(self.start_test)

        layout.addStretch()
        layout.addWidget(self.label)
        layout.addSpacing(30)
        layout.addWidget(self.start_btn)
        layout.addStretch()
        self.setLayout(layout)

        self.current_test_key = None

    def set_instruction(self, test_key, instruction_text):
        self.current_test_key = test_key
        self.label.setText(
            f"<b>Instrukcja:</b><br><br>{instruction_text}<br><br><i>Najpierw odbędzie się krótki trening.</i>")

    def start_test(self):
        self.main_window.start_specific_test(self.current_test_key)


class BaseTestScreen(QWidget):
    def __init__(self, main_window, test_name):
        super().__init__()
        self.main_window = main_window
        self.test_name = test_name
        self.layout = QVBoxLayout()

        self.info_label = QLabel("Przygotuj się...")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Tu musimy zostawić styl inline, aby nadpisał globalny kolor na biały (na ciemnym tle)
        self.info_label.setStyleSheet("font-size: 30px; font-weight: bold; color: white;")

        self.layout.addWidget(self.info_label)
        self.setLayout(self.layout)

        self.is_training = True
        self.training_trials = 3
        self.actual_trials = 8
        self.current_trial = 0
        self.is_waiting_for_reaction = False
        self.start_time = 0

    def handle_reaction(self, reaction_time):
        self.current_trial += 1

        if self.is_training:
            # ZMIANA: self.main_window zamiast self
            QMessageBox.information(self.main_window, "Trening", f"Twój czas: {reaction_time:.3f} s")
            if self.current_trial >= self.training_trials:
                self.is_training = False
                self.current_trial = 0
                # ZMIANA: self.main_window zamiast self
                QMessageBox.information(self.main_window, "Koniec treningu",
                                        "Teraz rozpocznie się test właściwy. Wyniki będą zapisywane.")
        else:
            self.main_window.test_results[self.test_name].append(reaction_time)

        self.reset_screen()

        if not self.is_training and self.current_trial >= self.actual_trials:
            # ZMIANA: self.main_window zamiast self
            QMessageBox.information(self.main_window, "Koniec", "Test zakończony! Wracamy do menu.")
            self.is_training = True
            self.current_trial = 0
            self.main_window.goto_menu()
        else:
            self.start_test_sequence()

    def reset_screen(self):
        self.setStyleSheet("background-color: none;")
        self.info_label.setText("Przygotuj się...")
        self.update()


class SimpleOpticalTest(BaseTestScreen):
    def __init__(self, main_window):
        super().__init__(main_window, "simple")

    def start_test_sequence(self):
        self.setFocus()
        self.setStyleSheet("background-color: #555555;")  # Ciemniejszy szary dla lepszego kontrastu napisu
        self.info_label.setText("Czekaj na zielony kolor...")
        self.is_waiting_for_reaction = False
        delay = random.uniform(1.5, 5.0)
        QTimer.singleShot(int(delay * 1000), self.show_stimulus)

    def show_stimulus(self):
        self.setStyleSheet("background-color: #27ae60;")  # Przyjemniejszy odcień zieleni
        self.info_label.setText("WCIŚNIJ SPACJĘ!")
        self.start_time = time.perf_counter()
        self.is_waiting_for_reaction = True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if self.is_waiting_for_reaction:
                reaction_time = time.perf_counter() - self.start_time
                self.is_waiting_for_reaction = False
                self.handle_reaction(reaction_time)
            else:
                self.info_label.setText("Falstart! Poczekaj na zielony kolor.")


class ComplexOpticalTest(BaseTestScreen):
    def __init__(self, main_window):
        super().__init__(main_window, "complex")
        self.stimulus_type = None

        self.shape_label = QLabel()
        self.shape_label.setFixedSize(150, 150)  # Powiększono kształt
        self.shape_label.hide()
        self.layout.addWidget(self.shape_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self.handle_timeout)
        self.max_wait_time = 1500  # Dałem 1.5 sekundy, żeby test był odrobinę trudniejszy

    def start_test_sequence(self):
        self.setFocus()
        self.setStyleSheet("background-color: black;")

        self.info_label.show()
        self.info_label.setText("Czekaj...")
        self.shape_label.hide()

        self.stimulus_type = None
        self.is_waiting_for_reaction = False
        delay = random.uniform(1.5, 4.0)
        QTimer.singleShot(int(delay * 1000), self.show_stimulus)

    def show_stimulus(self):
        if random.random() > 0.3:
            self.stimulus_type = 'target'
            self.shape_label.setStyleSheet("background-color: #e74c3c; border-radius: 0px;")  # Nowoczesna czerwień
        else:
            self.stimulus_type = 'distractor'
            self.shape_label.setStyleSheet(
                "background-color: #2ecc71; border-radius: 75px;")  # Nowoczesna zieleń, rogi na 75px (połowa z 150)

        self.info_label.hide()
        self.shape_label.show()

        self.start_time = time.perf_counter()
        self.is_waiting_for_reaction = True
        self.timeout_timer.start(self.max_wait_time)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space and self.is_waiting_for_reaction:
            self.timeout_timer.stop()
            reaction_time = time.perf_counter() - self.start_time
            self.is_waiting_for_reaction = False

            if self.stimulus_type == 'target':
                self.handle_reaction(reaction_time)
            else:
                self.shape_label.hide()
                self.info_label.show()
                self.info_label.setText("Błąd! Należało zignorować ten kształt.")
                self.stimulus_type = None
                QTimer.singleShot(1500, self.start_test_sequence)

    def handle_timeout(self):
        if not self.is_waiting_for_reaction:
            return

        self.is_waiting_for_reaction = False
        self.shape_label.hide()
        self.info_label.show()

        if self.stimulus_type == 'distractor':
            self.info_label.setText("Dobrze! Zignorowano.")
            self.current_trial += 1

            if self.is_training and self.current_trial >= self.training_trials:
                self.is_training = False
                self.current_trial = 0
                # ZMIANA: self.main_window zamiast self
                QMessageBox.information(self.main_window, "Koniec treningu",
                                        "Teraz rozpocznie się test właściwy. Wyniki będą zapisywane.")
            elif not self.is_training and self.current_trial >= self.actual_trials:
                # ZMIANA: self.main_window zamiast self
                QMessageBox.information(self.main_window, "Koniec", "Test zakończony! Wracamy do menu.")
                self.is_training = True
                self.current_trial = 0
                self.main_window.goto_menu()
                return

            QTimer.singleShot(1500, self.start_test_sequence)

        elif self.stimulus_type == 'target':
            self.info_label.setText("Zbyt wolno! Pominięto cel.")
            self.stimulus_type = None
            QTimer.singleShot(1500, self.start_test_sequence)

    def reset_screen(self):
        super().reset_screen()
        self.info_label.show()
        self.shape_label.hide()


class AcousticTest(BaseTestScreen):
    def __init__(self, main_window):
        super().__init__(main_window, "acoustic")
        self.sound = QSoundEffect()
        self.sound.setSource(QUrl.fromLocalFile("beep.wav"))
        self.sound.setVolume(1.0)  # Głośniej, by bodziec był wyraźniejszy

    def start_test_sequence(self):
        self.setFocus()
        self.setStyleSheet("background-color: #2c3e50;")  # Ciemny granat
        self.info_label.setText("Skup się na dźwięku...")
        self.is_waiting_for_reaction = False
        delay = random.uniform(2.0, 5.0)
        QTimer.singleShot(int(delay * 1000), self.show_stimulus)

    def show_stimulus(self):
        self.sound.stop()
        self.sound.play()

        self.start_time = time.perf_counter()
        self.is_waiting_for_reaction = True
        self.info_label.setText("REAGUJ!")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            if self.is_waiting_for_reaction:
                reaction_time = time.perf_counter() - self.start_time
                self.is_waiting_for_reaction = False
                self.handle_reaction(reaction_time)
            else:
                self.info_label.setText("Falstart!")


class ResultsScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)

        self.label = QLabel("Podsumowanie Wyników")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")

        self.stats_label = QLabel()
        self.stats_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.stats_label.setStyleSheet("font-size: 16px; margin-bottom: 10px;")

        self.figure = Figure(figsize=(6, 4), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.add_subplot(111)

        self.exit_btn = QPushButton("Powrót do Menu")
        self.exit_btn.clicked.connect(self.main_window.goto_menu)

        layout.addWidget(self.label)
        layout.addWidget(self.stats_label)
        layout.addWidget(self.canvas)
        layout.addWidget(self.exit_btn)
        self.setLayout(layout)

    def display_results(self):
        text = f"<b>Badany:</b> {self.main_window.user_name}<br><br>"
        has_any_data = False

        tests_info = [
            ("simple", "Prosty Optyczny", "#3498db"),
            ("complex", "Złożony Optyczny", "#e74c3c"),
            ("acoustic", "Akustyczny", "#27ae60")
        ]

        for test_key, test_name, color in tests_info:
            results = self.main_window.test_results[test_key]
            if results:
                has_any_data = True
                avg = sum(results) / len(results)
                text += f"<b>{test_name}:</b> Średni czas: {avg:.3f} s (prób: {len(results)})<br>"
            else:
                text += f"<b>{test_name}:</b> Brak danych<br>"

        self.stats_label.setText(text)
        self.axes.clear()

        if has_any_data:
            for test_key, test_name, color in tests_info:
                results = self.main_window.test_results[test_key]
                if results:
                    trials = list(range(1, len(results) + 1))
                    self.axes.plot(trials, results, marker='o', linestyle='-', color=color, linewidth=2, markersize=6,
                                   label=test_name)

            self.axes.set_title("Krzywa czasu reakcji")
            self.axes.set_xlabel("Numer próby")
            self.axes.set_ylabel("Czas (s)")
            self.axes.grid(True, linestyle='--', alpha=0.5)
            self.axes.legend()

            from matplotlib.ticker import MaxNLocator
            self.axes.xaxis.set_major_locator(MaxNLocator(integer=True))
            self.figure.tight_layout()
        else:
            self.axes.text(0.5, 0.5, "Brak danych do wyświetlenia",
                           horizontalalignment='center', verticalalignment='center', fontsize=14, color='gray')
            self.axes.set_axis_off()

        self.canvas.draw()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tester Sprawności Psychomotorycznej")
        self.resize(800, 700)  # Nieco szersze okno, by pomieścić ładnie duży tekst

        self.user_name = ""
        self.test_results = {
            "simple": [],
            "complex": [],
            "acoustic": []
        }

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.welcome_screen = WelcomeScreen(self)
        self.menu_screen = MenuScreen(self)
        self.instruction_screen = InstructionScreen(self)
        self.simple_test = SimpleOpticalTest(self)
        self.complex_test = ComplexOpticalTest(self)
        self.acoustic_test = AcousticTest(self)
        self.results_screen = ResultsScreen(self)

        self.stacked_widget.addWidget(self.welcome_screen)
        self.stacked_widget.addWidget(self.menu_screen)
        self.stacked_widget.addWidget(self.instruction_screen)
        self.stacked_widget.addWidget(self.simple_test)
        self.stacked_widget.addWidget(self.complex_test)
        self.stacked_widget.addWidget(self.acoustic_test)
        self.stacked_widget.addWidget(self.results_screen)

    def goto_menu(self):
        self.stacked_widget.setCurrentWidget(self.menu_screen)

    def setup_test(self, test_key):
        instructions = {
            "simple": "Gdy ekran zmieni kolor na <b>ZIELONY</b>,<br>jak najszybciej naciśnij klawisz <b>SPACJA</b>.",
            "complex": "Naciśnij <b>SPACJĘ</b> tylko wtedy, gdy zobaczysz<br><span style='color:red;'><b>CZERWONY KWADRAT</b></span>.<br>Ignoruj zielone koła.",
            "acoustic": "Skup się na dźwięku.<br>Gdy usłyszysz sygnał, jak najszybciej naciśnij <b>SPACJĘ</b>."
        }
        self.instruction_screen.set_instruction(test_key, instructions[test_key])
        self.stacked_widget.setCurrentWidget(self.instruction_screen)

    def start_specific_test(self, test_key):
        if test_key == "simple":
            self.stacked_widget.setCurrentWidget(self.simple_test)
            self.simple_test.start_test_sequence()
        elif test_key == "complex":
            self.stacked_widget.setCurrentWidget(self.complex_test)
            self.complex_test.start_test_sequence()
        elif test_key == "acoustic":
            self.stacked_widget.setCurrentWidget(self.acoustic_test)
            self.acoustic_test.start_test_sequence()

    def goto_results(self):
        self.results_screen.display_results()
        self.stacked_widget.setCurrentWidget(self.results_screen)


# === GLOBALNY ARKUSZ STYLÓW (QSS) ===
STYLE_SHEET = """
QMainWindow {
    background-color: #f4f6f9;
}

/* Wymuszamy jasne tło i jasne krawędzie dla okienek dialogowych */
QMessageBox {
    background-color: #f4f6f9;
}

/* Zabezpieczamy tekst wewnątrz MessageBoxa */
QMessageBox QLabel {
    color: #2c3e50;
    font-size: 18px;
}

QLabel {
    color: #2c3e50;
    font-size: 20px;
}

QLineEdit {
    font-size: 20px;
    padding: 12px;
    border: 2px solid #bdc3c7;
    border-radius: 8px;
    background-color: #ffffff;
    color: #2c3e50;
}

QLineEdit:focus {
    border: 2px solid #3498db;
}

QPushButton {
    background-color: #3498db;
    color: white;
    font-size: 18px;
    font-weight: bold;
    padding: 15px;
    border-radius: 8px;
    border: none;
    margin-bottom: 5px;
}

QPushButton:hover {
    background-color: #2980b9;
}

QPushButton:pressed {
    background-color: #1a5276;
}

QPushButton#resultsBtn {
    background-color: #27ae60;
}

QPushButton#resultsBtn:hover {
    background-color: #2ecc71;
}

QPushButton#resultsBtn:pressed {
    background-color: #1e8449;
}
"""

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # APLIKACJA ŁADUJE GLOBALNY STYL
    app.setStyleSheet(STYLE_SHEET)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())