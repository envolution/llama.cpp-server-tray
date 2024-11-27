import os
import sys
import subprocess
import tempfile
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QTextEdit, QPushButton,
    QMessageBox, QWidget, QHBoxLayout, QLabel
)
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QIcon
from PySide6.QtCore import Qt, QRegularExpression, QTimer


class ShellSyntaxHighlighter(QSyntaxHighlighter):
    """Custom syntax highlighter for shell scripts."""

    def highlightBlock(self, text):
        # Keywords
        keywords = [
            "if", "then", "else", "fi", "for", "in", "do", "done", "while", "until",
            "case", "esac", "function"
        ]
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0077ff"))
        keyword_format.setFontWeight(QFont.Bold)

        for keyword in keywords:
            expression = QRegularExpression(rf"\b{keyword}\b")
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), keyword_format)

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#888888"))
        expression = QRegularExpression(r"#.*")
        iterator = expression.globalMatch(text)
        while iterator.hasNext():
            match = iterator.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), comment_format)

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#00aa00"))
        expression = QRegularExpression(r'"[^"]*"|\'[^\']*\'')
        iterator = expression.globalMatch(text)
        while iterator.hasNext():
            match = iterator.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), string_format)


class ShellEditor(QMainWindow):
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.original_content = ""
        self.setWindowTitle("Llama.cpp service config editor")
        self.setGeometry(300, 200, 800, 600)
        self.init_ui()

    def init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()


        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Courier", 12))
        ShellSyntaxHighlighter(self.text_edit.document())
        main_layout.addWidget(self.text_edit)

        # Button layout
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.close_button = QPushButton("Close")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.close_button)
        main_layout.addLayout(button_layout)

        # Connect buttons
        self.save_button.clicked.connect(self.save_file)
        self.close_button.clicked.connect(self.close_editor)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Load file
        self.load_file()

    def load_file(self):
        try:
            with open(self.file_path, "r") as file:
                content = file.read()
                self.text_edit.setPlainText(content)
                self.original_content = content
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

    def save_file(self):
        content = self.text_edit.toPlainText()
        if os.access(self.file_path, os.W_OK):
            try:
                with open(self.file_path, "w") as file:
                    file.write(content)
                self.original_content = content
                QMessageBox.information(self, "Saved", "File saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
        else:
            self.save_with_pkexec(content)

    def show_toast(self, code='info', message=''):
        if code == 'info':
            background_color = '#90EE90'  # Light Pastel Green
            text_color = '#000000'  # Black
        elif code == 'warning':
            background_color = '#FFFACD'  # Light Yellow
            text_color = '#000000'  # Black
        elif code == 'error':
            background_color = '#FF6347'  # Light Pastel Red
            text_color = '#000000'  # Black
        else:
            raise ValueError('Invalid code. Please choose from info, warning, or error.')        

        # Create the toast QLabel
        toast = QLabel(message, self)
        toast.setAlignment(Qt.AlignCenter)
        toast.setStyleSheet(f"background-color: {background_color} ; color: {text_color}; padding: 10px; border-radius: 5px;")
        
        # Set the position of the toast message at the bottom of the window
        toast.setGeometry(self.rect().adjusted(0, self.height() - 40, 0, 0))
        toast.show()

        # Timer to hide the toast after 3 seconds
        QTimer.singleShot(3000, toast.close)

    def save_with_pkexec(self, content):
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(content.encode())
            
            subprocess.run(
                ["pkexec", "cp", temp_file_path, self.file_path],
                check=True
            )
            self.original_content = content
            #QMessageBox.information(self, "Saved", "File saved successfully with elevated privileges.")
            self.show_toast("info", "File saved successfully.")
        except Exception as e:
            #QMessageBox.critical(self, "Error", f"Failed to save file with elevated privileges: {e}")
            self.show_toast("error", f"Failed: {e}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    def close_editor(self):
        if self.text_edit.toPlainText() != self.original_content:
            response = QMessageBox.warning(
                self, "Unsaved Changes",
                "You have unsaved changes. Do you want to save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if response == QMessageBox.Save:
                self.save_file()
            elif response == QMessageBox.Cancel:
                return
        self.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python editor.py <file-path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Error: {file_path} is not a valid file.")
        sys.exit(1)

    print (os.getcwd())
    app = QApplication(sys.argv)    

    editor = ShellEditor(file_path)
#    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'llama.cpp-server-tray_on.png')    
#    editor.setWindowIcon(QIcon(icon_path))
    editor.setWindowIcon(QIcon.fromTheme('folder'))
    editor.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
