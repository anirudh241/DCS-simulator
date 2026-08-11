"""
Entry point for the DCS Simulator (boiler drum module, phase 1).

Run with:
    python main.py
"""

import sys

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DCS Simulator")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
