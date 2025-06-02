import sys
import os
import time
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal
from pathlib import Path

#supported file types
supported_filetypes = {".flac", ".mp3"}

#class to define GUI
class AudioToolGUI(QWidget):
    def __init__(self):
        super().__init__()
        #set basic window properties
        self.setWindowTitle("MuseAmp")
        self.setMinimumSize(700, 500)
        self.layout = QVBoxLayout(self)  # Main vertical layout

        #file info table setup
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["File Path", "Extension", "Real Codec", "ReplayGain", "Clipping"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)    #make cells read-only
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)   #select entire rows
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  #stretch first column

        #buttons
        self.add_files_btn = QPushButton("Add File(s)")
        self.add_folder_btn = QPushButton("Add Folder")
        self.remove_files_btn = QPushButton("Remove File(s)")
        self.gain_btn = QPushButton("Apply Gain")
        self.replaygain_btn = QPushButton("Apply ReplayGain")

        #progress bar defaulting to 100
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(100)         # Default to 100%
        self.progress_bar.setFormat("100%")

        #horizontal layout for buttons
        self.button_layout = QHBoxLayout()
        for btn in [
            self.add_files_btn, self.add_folder_btn,
            self.remove_files_btn, self.gain_btn, self.replaygain_btn
        ]:
            self.button_layout.addWidget(btn)

        #add widgets to the main layout
        self.layout.addWidget(self.table)
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.progress_bar)
        
        #connect buttons to functions
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.remove_files_btn.clicked.connect(self.remove_files)

    #add files to table/list
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files")
        unsupported = []
        #check each file to make sure it's supported
        for file_path in files:
            path = Path(file_path)
            if path.suffix.lower() not in supported_filetypes:
                unsupported.append(path.name)
            else:
                self.add_file_to_table(file_path)

        #let user know why files weren't added (if any unsupported)
        if unsupported:
            QMessageBox.warning(
                self,
                "Unsupported File Type",
                "These files are not supported file types and were not added:\n" + "\n".join(unsupported)
            )

    #add supported files from folder to table/list
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return

        #walk through the folder and add supported files
        for root, _, files in os.walk(folder):
            for filename in files:
                path = Path(root) / filename
                if path.suffix.lower() in supported_filetypes:
                    self.add_file_to_table(str(path))

    #actually add file to the table/list
    def add_file_to_table(self, file_path):
        path = Path(file_path)
        if not path.is_file():
            return
        if self.is_already_listed(str(path)):
            return

        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(str(path)))       #File Path
        self.table.setItem(row, 1, QTableWidgetItem(path.suffix.lower()))  #Extension
        self.table.setItem(row, 2, QTableWidgetItem("-"))              #Real Codec placeholder
        self.table.setItem(row, 3, QTableWidgetItem("-"))              #ReplayGain placeholder
        self.table.setItem(row, 4, QTableWidgetItem("-"))              #Clipping placeholder

    #check if file is already listed in the table/list
    def is_already_listed(self, filepath):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == filepath:
                return True
        return False

    #remove selected files from the table/list
    def remove_files(self):
        selected_rows = sorted({item.row() for item in self.table.selectedItems()}, reverse=True)
        for row in selected_rows:
            self.table.removeRow(row)


#actually load and run app
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioToolGUI()
    window.show()
    sys.exit(app.exec())