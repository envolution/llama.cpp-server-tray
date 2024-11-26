import os
import sys
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QAction
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer, QProcess

# Paths to icons
ICON_RUNNING = "/usr/share/icons/hicolor/48x48/apps/llama_service_running.png"
ICON_STOPPED = "/usr/share/icons/hicolor/48x48/apps/llama_service.png"

SERVICE_NAME = "llama.cpp.service"
APP_NAME = "llama_tray_service"

def is_service_running():
    """Check if the systemd service is active."""
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip() == "active"
    except Exception as e:
        print(f"Error checking service status: {e}")
        return False

def start_service():
    """Start the systemd service."""
    try:
        subprocess.run(
            ["systemctl", "--user", "start", SERVICE_NAME],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error starting service: {e.stderr}")

def stop_service():
    """Stop the systemd service."""
    try:
        subprocess.run(
            ["systemctl", "--user", "stop", SERVICE_NAME],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error stopping service: {e.stderr}")

class LogWindow(QMainWindow):
    """A popup window to display live logs."""
    def __init__(self, service_name):
        super().__init__()
        self.service_name = service_name
        self.setWindowTitle(f"Logs: {self.service_name}")
        self.resize(800, 600)

        # Set up the text widget
        self.log_viewer = QTextEdit(self)
        self.log_viewer.setReadOnly(True)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.log_viewer)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Start the log process
        self.log_process = QProcess(self)
        self.log_process.setProcessChannelMode(QProcess.MergedChannels)
        self.log_process.readyRead.connect(self.update_logs)
        self.start_log_stream()

    def start_log_stream(self):
        """Start streaming logs using journalctl."""
        self.log_process.start(
            "journalctl", ["--user", "-u", self.service_name, "-f", "-n", "50"]
        )

    def update_logs(self):
        """Update the text widget with new log data."""
        output = self.log_process.readAllStandardOutput().data().decode()
        self.log_viewer.append(output)

    def closeEvent(self, event):
        """Handle window close."""
        if self.log_process.state() == QProcess.Running:
            self.log_process.terminate()
        event.accept()

class TrayIcon(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        self.menu = QMenu()

        # Actions
        self.start_action = QAction("Start Service")
        self.stop_action = QAction("Stop Service")
        self.show_log_action = QAction("Show Log")
        self.quit_action = QAction("Quit")

        # Add actions to menu
        self.menu.addAction(self.start_action)
        self.menu.addAction(self.stop_action)
        self.menu.addAction(self.show_log_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        # Connect actions
        self.start_action.triggered.connect(self.handle_start)
        self.stop_action.triggered.connect(self.handle_stop)
        self.show_log_action.triggered.connect(self.show_log)
        self.quit_action.triggered.connect(self.handle_quit)

        self.setContextMenu(self.menu)

        # Timer to periodically check service status
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_icon)
        self.timer.start(5000)  # Check every 5 seconds

        # Initialize icon state
        self.update_icon()

        # Log window instance
        self.log_window = None

    def handle_start(self):
        start_service()
        self.update_icon()

    def handle_stop(self):
        stop_service()
        self.update_icon()

    def show_log(self):
        if not self.log_window or not self.log_window.isVisible():
            self.log_window = LogWindow(SERVICE_NAME)
            self.log_window.show()

    def handle_quit(self):
        self.timer.stop()
        QApplication.quit()

    def update_icon(self):
        if is_service_running():
            self.setIcon(QIcon(ICON_RUNNING))
        else:
            self.setIcon(QIcon(ICON_STOPPED))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Create the tray icon
    tray_icon = TrayIcon()
    tray_icon.setToolTip("Llama.cpp Service Control")
    tray_icon.show()

    # Start the event loop
    sys.exit(app.exec())
