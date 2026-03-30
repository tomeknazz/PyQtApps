import sys
import random
import psutil
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QLineEdit, QStackedWidget, QMessageBox,
                             QProgressBar, QTextEdit, QGroupBox)
from PyQt6.QtCore import Qt, QTimer, QTime


class LoginScreen(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        layout = QVBoxLayout()
        layout.setContentsMargins(100, 100, 100, 100)

        self.label = QLabel("System SCADA - Logowanie Operatora")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Nazwa użytkownika (wpisz: admin)")
        self.user_input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Hasło (wpisz: admin)")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.login_btn = QPushButton("Zaloguj")
        self.login_btn.clicked.connect(self.attempt_login)

        layout.addStretch()
        layout.addWidget(self.label)
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)
        layout.addWidget(self.login_btn)
        layout.addStretch()
        self.setLayout(layout)

    def attempt_login(self):
        # Prosta autoryzacja
        if self.user_input.text() == "admin" and self.pass_input.text() == "admin":
            self.user_input.clear()
            self.pass_input.clear()
            self.main_window.login_success()
        else:
            QMessageBox.warning(self, "Błąd", "Nieprawidłowe dane logowania!")


class DispatcherPanel(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

        # --- Zmienne Procesowe ---
        self.cpu_usage = 0.0
        self.simulated_temp = 40.0
        self.fan_active = False
        self.production_speed = 100

        # --- Zmienne Autodiagnostyki (Czuwak) ---
        self.is_checking_presence = False
        self.presence_time_left = 30

        self.setup_ui()
        self.setup_timers()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)

        # --- SEKCJA 1: Pasek statusu i ostrzeżeń ---
        self.warning_banner = QLabel("SYSTEM PRACUJE NORMALNIE")
        self.warning_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.warning_banner.setStyleSheet(
            "background-color: #27ae60; color: white; font-size: 20px; font-weight: bold; padding: 10px;")
        self.layout.addWidget(self.warning_banner)

        # --- SEKCJA 2: Parametry procesowe ---
        params_group = QGroupBox("Parametry Procesu (Zależne od sprzętu PC)")
        params_layout = QVBoxLayout()

        # Zużycie CPU (Odczyt z PC)
        cpu_layout = QHBoxLayout()
        cpu_layout.addWidget(QLabel("Obciążenie Głównego Rdzenia (CPU PC):"))
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        cpu_layout.addWidget(self.cpu_bar)
        params_layout.addLayout(cpu_layout)

        # Temperatura (Symulowana na bazie CPU)
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Temperatura Silnika Linii (°C):"))
        self.temp_bar = QProgressBar()
        self.temp_bar.setRange(20, 120)
        self.temp_bar.setFormat("%v °C")
        temp_layout.addWidget(self.temp_bar)
        params_layout.addLayout(temp_layout)

        # Prędkość i Wentylatory
        status_layout = QHBoxLayout()
        self.speed_label = QLabel(f"Prędkość Linii: {self.production_speed}%")
        self.speed_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.fan_label = QLabel("Dodatkowy Wentylator: WYŁĄCZONY")
        self.fan_label.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")

        status_layout.addWidget(self.speed_label)
        status_layout.addWidget(self.fan_label)
        params_layout.addLayout(status_layout)

        params_group.setLayout(params_layout)
        self.layout.addWidget(params_group)

        # --- SEKCJA 3: Logi Zdarzeń ---
        logs_group = QGroupBox("Dziennik Zdarzeń i Awarii")
        logs_layout = QVBoxLayout()
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet("background-color: #2c3e50; color: #ecf0f1; font-family: Consolas;")
        logs_layout.addWidget(self.log_console)
        logs_group.setLayout(logs_layout)
        self.layout.addWidget(logs_group)

        # Wymuszenie łapania zdarzeń klawiatury dla Czuwaka
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setup_timers(self):
        # 1. Timer odświeżający parametry (co 1 sekundę)
        self.process_timer = QTimer(self)
        self.process_timer.timeout.connect(self.update_process_parameters)

        # 2. Timer generujący losowe awarie (co 5 sekund sprawdzamy szansę)
        self.failure_timer = QTimer(self)
        self.failure_timer.timeout.connect(self.simulate_random_failure)

        # 3. Timer wyzwalający kontrolę obecności (np. co 20-40 sekund)
        self.presence_trigger_timer = QTimer(self)
        self.presence_trigger_timer.setSingleShot(True)
        self.presence_trigger_timer.timeout.connect(self.start_presence_check)

        # 4. Timer odliczający 30 sekund na reakcję operatora
        self.presence_countdown_timer = QTimer(self)
        self.presence_countdown_timer.timeout.connect(self.update_presence_countdown)

    def start_simulation(self):
        self.log_event("Zalogowano pomyślnie. Start symulacji linii produkcyjnej.")
        self.process_timer.start(1000)
        self.failure_timer.start(5000)
        self.schedule_next_presence_check()
        self.setFocus()  # Ważne dla łapania klawisza spacji

    def stop_simulation(self):
        self.process_timer.stop()
        self.failure_timer.stop()
        self.presence_trigger_timer.stop()
        self.presence_countdown_timer.stop()
        self.log_console.clear()

    def log_event(self, message):
        time_str = QTime.currentTime().toString("HH:mm:ss")
        self.log_console.append(f"[{time_str}] {message}")

    # --- LOGIKA PROCESU ---
    def update_process_parameters(self):
        # Odczyt rzeczywistego użycia procesora (nieblokujący)
        self.cpu_usage = psutil.cpu_percent(interval=None)
        self.cpu_bar.setValue(int(self.cpu_usage))

        # Symulacja temperatury: Rośnie gdy CPU wysokie, spada gdy działa wentylator
        heat_factor = (self.cpu_usage - 30) * 0.1  # Jeśli CPU > 30%, generuje ciepło
        cooling_factor = 5.0 if self.fan_active else 0.0

        self.simulated_temp += heat_factor - cooling_factor

        # Szum losowy i limity
        self.simulated_temp += random.uniform(-1.0, 1.0)
        self.simulated_temp = max(20.0, min(self.simulated_temp, 120.0))
        self.temp_bar.setValue(int(self.simulated_temp))

        # Reagowanie na przekroczenia wartości granicznych
        self.check_limits()

    def check_limits(self):
        if self.simulated_temp > 85.0 and not self.fan_active:
            self.fan_active = True
            self.fan_label.setText("Dodatkowy Wentylator: WŁĄCZONY")
            self.fan_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #3498db;")
            self.log_event("UWAGA: Przekroczono 85°C. Automatyczne załączenie wentylatora chłodzącego.")

        elif self.simulated_temp < 60.0 and self.fan_active:
            self.fan_active = False
            self.fan_label.setText("Dodatkowy Wentylator: WYŁĄCZONY")
            self.fan_label.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
            self.log_event("INFO: Temperatura ustabilizowana. Wyłączenie wentylatora.")

        if self.simulated_temp > 100.0 and self.production_speed == 100:
            self.production_speed = 50
            self.speed_label.setText(f"Prędkość Linii: {self.production_speed}%")
            self.speed_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
            self.log_event("KRYTYCZNE: Temperatura > 100°C! Dławienie prędkości produkcji do 50%.")

        elif self.simulated_temp < 80.0 and self.production_speed == 50:
            self.production_speed = 100
            self.speed_label.setText(f"Prędkość Linii: {self.production_speed}%")
            self.speed_label.setStyleSheet("font-size: 16px; font-weight: bold; color: black;")
            self.log_event("INFO: Parametry w normie. Przywrócenie prędkości produkcji do 100%.")

    def simulate_random_failure(self):
        if random.random() < 0.1:  # 10% szansy na awarię co 5 sekund
            events = [
                "Zacięcie materiału na podajniku taśmowym nr 3.",
                "Spadek ciśnienia w układzie pneumatycznym.",
                "Błąd odczytu z czujnika zbliżeniowego."
            ]
            self.log_event(f"AWARIA: {random.choice(events)}")

    # --- AUTODIAGNOSTYKA (CZUWAK) ---
    def schedule_next_presence_check(self):
        # Losowy czas do kolejnego sprawdzenia (np. od 15 do 35 sekund)
        delay = random.randint(15000, 35000)
        self.presence_trigger_timer.start(delay)

    def start_presence_check(self):
        self.is_checking_presence = True
        self.presence_time_left = 30
        self.log_event("ALARM AUTODIAGNOSTYKI: Wymagane potwierdzenie obecności operatora!")
        self.warning_banner.setStyleSheet(
            "background-color: #e74c3c; color: white; font-size: 20px; font-weight: bold; padding: 10px;")
        self.update_warning_banner()

        # Uruchamiamy odliczanie co 1 sekundę
        self.presence_countdown_timer.start(1000)

    def update_presence_countdown(self):
        self.presence_time_left -= 1
        self.update_warning_banner()

        if self.presence_time_left <= 0:
            self.presence_countdown_timer.stop()
            self.log_event("KRYTYCZNE: Brak reakcji operatora! Wylogowanie awaryjne.")
            QMessageBox.critical(self, "ALARM",
                                 "Brak potwierdzenia obecności! Ze względów bezpieczeństwa nastąpi wylogowanie.")
            self.main_window.logout()

    def update_warning_banner(self):
        if self.is_checking_presence:
            # Migający efekt na zmianę (parzyste/nieparzyste sekundy)
            if self.presence_time_left % 2 == 0:
                self.warning_banner.setStyleSheet(
                    "background-color: #e74c3c; color: white; font-size: 20px; font-weight: bold;")
            else:
                self.warning_banner.setStyleSheet(
                    "background-color: #c0392b; color: yellow; font-size: 20px; font-weight: bold;")

            self.warning_banner.setText(f"POTWIERDŹ OBECNOŚĆ (SPACJA)! Pozostało: {self.presence_time_left} s")
        else:
            self.warning_banner.setStyleSheet(
                "background-color: #27ae60; color: white; font-size: 20px; font-weight: bold;")
            self.warning_banner.setText("SYSTEM PRACUJE NORMALNIE")

    def keyPressEvent(self, event):
        # Oczekujemy na wciśnięcie Spacji
        if event.key() == Qt.Key.Key_Space and self.is_checking_presence:
            self.is_checking_presence = False
            self.presence_countdown_timer.stop()
            self.update_warning_banner()
            self.log_event("INFO: Obecność operatora potwierdzona.")
            self.schedule_next_presence_check()  # Zaplanuj kolejne sprawdzenie


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Symulator Stanowiska Dyspozytorskiego")
        self.resize(800, 600)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.login_screen = LoginScreen(self)
        self.dispatcher_panel = DispatcherPanel(self)

        self.stacked_widget.addWidget(self.login_screen)
        self.stacked_widget.addWidget(self.dispatcher_panel)

    def login_success(self):
        self.stacked_widget.setCurrentWidget(self.dispatcher_panel)
        self.dispatcher_panel.start_simulation()

    def logout(self):
        self.dispatcher_panel.stop_simulation()
        self.stacked_widget.setCurrentWidget(self.login_screen)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Globalny Arkusz Stylów dla technicznego wyglądu
    app.setStyleSheet("""
            QMainWindow { background-color: #f4f6f9; }
            QLabel { color: #2c3e50; font-size: 14px; }
            QLineEdit { padding: 10px; font-size: 16px; border: 2px solid #bdc3c7; border-radius: 5px; }
            QPushButton { background-color: #3498db; color: white; font-size: 16px; font-weight: bold; padding: 12px; border-radius: 5px; }
            QPushButton:hover { background-color: #2980b9; }
            QGroupBox { font-weight: bold; border: 2px solid #bdc3c7; border-radius: 5px; margin-top: 10px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }
            QProgressBar { border: 2px solid grey; border-radius: 5px; text-align: center; font-weight: bold; }
            QProgressBar::chunk { background-color: #e67e22; width: 20px; }

            /* --- NAPRAWA OKIENEK DIALOGOWYCH --- */
            QMessageBox {
                background-color: #f4f6f9;
            }
            QMessageBox QLabel {
                color: #2c3e50;
                font-size: 14px;
                font-weight: normal;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                font-size: 14px;
            }
        """)

    # Inicjalizacja psutil (pierwsze wywołanie czesto zwraca 0.0, wiec wywolujemy w tle)
    psutil.cpu_percent(interval=None)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())