import sys
import os
import time
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QHeaderView
)
from PySide6.QtCore import Qt, QThread, Signal
from pathlib import Path


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


#actually load and run app
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioToolGUI()
    window.show()
    sys.exit(app.exec())