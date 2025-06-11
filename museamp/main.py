import sys
from PySide6.QtWidgets import QApplication
from .gui import AudioToolGUI
from .utils import (
    get_supported_filetypes,
    is_supported_filetype,
    get_file_extension,
    is_audio_file,
    filter_supported_files,
    get_files_in_folder,
)

def main():
    #create the qt application
    app = QApplication(sys.argv)
    #create and show the main window
    window = AudioToolGUI()
    window.show()
    #start the event loop
    sys.exit(app.exec())
