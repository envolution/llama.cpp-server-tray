#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
from pathlib import Path
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QMessageBox, QMainWindow, QTextEdit, QVBoxLayout, QWidget, QInputDialog
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer, QProcess

# Paths to icons
ICON_RUNNING = "llama_service_running.png"
ICON_STOPPED = "llama_service.png"

SERVICE_NAME = "llama.cpp.service"
APP_NAME = "llama_tray_service"
AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / f"{APP_NAME}.desktop"

# Configuration file paths
CONFIG_FILE = Path("/etc/llama.cpp-service/llama-server.conf")
CONFIG_SAMPLE = Path("/etc/llama.cpp-service/llama-server.conf.sample")

def is_service_running():
    """Check if the systemd service is active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip() == "active"
    except Exception as e:
        print(f"Error checking service status: {e}")
        return False

def start_service(log_window=None):
    """Start the systemd service."""
    try:
        subprocess.run(
            ["systemctl", "start", SERVICE_NAME],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error starting service: {e.stderr}")
        # Open log window if provided
        if log_window:
            log_window.show()
        
        # Show error message
        QMessageBox.critical(
            None, 
            "Service Start Failed", 
            f"Could not start the service. Error:\n{e.stderr}"
        )
        return False
    return True

def stop_service():
    """Stop the systemd service."""
    try:
        subprocess.run(
            ["systemctl", "stop", SERVICE_NAME],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error stopping service: {e.stderr}")

def create_autostart_entry():
    """Create a .desktop file for autostart."""
    if not AUTOSTART_DIR.exists():
        AUTOSTART_DIR.mkdir(parents=True)
    with open(AUTOSTART_FILE, "w") as f:
        f.write(
            f"""[Desktop Entry]
Type=Application
Exec={sys.executable} {sys.argv[0]}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name={APP_NAME}
Comment=Tray application for llama.cpp.service
"""
        )

def remove_autostart_entry():
    """Remove the autostart .desktop file."""
    if AUTOSTART_FILE.exists():
        AUTOSTART_FILE.unlink()

def is_autostart_enabled():
    """Check if the autostart .desktop file exists."""
    return AUTOSTART_FILE.exists()

def open_config_file():
    """Open configuration file with elevated permissions."""
    # Ensure config file exists, copying from sample if needed
    if not CONFIG_FILE.exists():
        try:
            # Attempt to copy sample file to config file
            subprocess.run(
                ["qt-sudo", "cp", str(CONFIG_SAMPLE), str(CONFIG_FILE)],
                check=True
            )
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(
                None, 
                "Configuration Error", 
                f"Could not create config file: {e}"
            )
            return

    # Command to open the file with a text editor
    cmd = ["qt-sudo", "-d", "leafpad", str(CONFIG_FILE)]
    
    try:
        # Start the editor in the background, detached from the parent process
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,  # Detach from the parent session
        )
    except FileNotFoundError:
        QMessageBox.critical(
            None, 
            "Configuration Error", 
            "The specified editor (leafpad) could not be found."
        )
        return
    except Exception as e:
        QMessageBox.critical(
            None, 
            "Configuration Error", 
            f"An unexpected error occurred: {e}"
        )
        return
    
    return True

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
            "journalctl", ["-u", self.service_name, "-f", "-n", "50"]
        )

    def update_logs(self):
        """Update the text widget with new log data."""
        output = self.log_process.readAllStandardOutput().data().decode()
        self.log_viewer.append(output)

    def closeEvent(self, event):
        """Handle window close."""
        if self.log_process.state() == QProcess.Running:
            self.log_process.terminate()

class TrayIcon(QSystemTrayIcon):
    def __init__(self):
        super().__init__()
        self.menu = QMenu()

        # Actions
        self.start_action = QAction("Start Service")
        self.stop_action = QAction("Stop Service")
        self.autostart_action = QAction("Auto-Run at Startup")
        self.autostart_action.setCheckable(True)
        self.configure_action = QAction("Configure")  # New configuration action
        self.show_log_action = QAction("Show Log")
        self.quit_action = QAction("Quit")

        # Add actions to menu
        self.menu.addAction(self.start_action)
        self.menu.addAction(self.stop_action)
        self.menu.addSeparator()
        self.menu.addAction(self.autostart_action)
        self.menu.addAction(self.configure_action)  # Add configure action
        self.menu.addSeparator()
        self.menu.addAction(self.show_log_action)
        self.menu.addSeparator()
        self.menu.addAction(self.quit_action)

        # Connect actions
        self.start_action.triggered.connect(self.handle_start)
        self.stop_action.triggered.connect(self.handle_stop)
        self.autostart_action.triggered.connect(self.toggle_autostart)
        self.configure_action.triggered.connect(open_config_file)  # Connect configuration action
        self.show_log_action.triggered.connect(self.show_log)
        self.quit_action.triggered.connect(self.handle_quit)

        self.setContextMenu(self.menu)

        # Timer to periodically check service status
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_icon)
        self.timer.start(5000)  # Check every 5 seconds

        # Initialize icon state
        self.autostart_action.setChecked(is_autostart_enabled())
        self.update_icon()

        # Log window instance
        self.log_window = None

    def handle_start(self):
        # Create log window before starting service
        if not self.log_window:
            self.log_window = LogWindow(SERVICE_NAME)

        # Try to start service, passing log window to handle potential failure
        start_service(self.log_window)
        self.update_icon()

    def handle_stop(self):
        stop_service()
        self.update_icon()

    def show_log(self):
        if not self.log_window or not self.log_window.isVisible():
            self.log_window = LogWindow(SERVICE_NAME)
            self.log_window.show()

    def toggle_autostart(self):
        if self.autostart_action.isChecked():
            create_autostart_entry()
        else:
            remove_autostart_entry()

    def handle_quit(self):
        if is_service_running():
            response = QMessageBox.question(
                None,
                "Service Running",
                "Are you sure you want to quit without shutting down the service?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if response == QMessageBox.No:
                return
        self.timer.stop()
        QApplication.quit()

    def update_icon(self):
        if is_service_running():
            self.setIcon(QIcon.fromTheme(ICON_RUNNING))
        else:
            self.setIcon(QIcon.fromTheme(ICON_STOPPED))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Create the tray icon
    tray_icon = TrayIcon()
    tray_icon.setToolTip("Llama.cpp Service Control")
    tray_icon.show()

    # Start the event loop
    sys.exit(app.exec())
