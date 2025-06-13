#!/usr/bin/env python3
import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFileDialog, QProgressBar, QMessageBox,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QHeaderView,
    QLineEdit, QLabel, QDialog, QTextEdit, QDialogButtonBox, QCheckBox,
    QApplication
)
from PySide6.QtGui import QIntValidator, QIcon
from PySide6.QtCore import Qt, QThread
from .workers import Worker, AddFilesWorker, ApplyGainWorker
from .utils import find_supported_files

#supported filetypes for museamp
supported_filetypes = {".flac", ".mp3"}

class ErrorLogDialog(QDialog):
    def __init__(self, log_text, parent=None):
        super().__init__(parent)
        #set error log dialog properties
        self.setWindowTitle("Error Log")
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(log_text)
        layout.addWidget(self.text_edit)
        button_box = QDialogButtonBox()
        copy_btn = QPushButton("Copy Log")
        ok_btn = QPushButton("OK")
        button_box.addButton(copy_btn, QDialogButtonBox.ActionRole)
        button_box.addButton(ok_btn, QDialogButtonBox.AcceptRole)
        layout.addWidget(button_box)
        copy_btn.clicked.connect(self.copy_log)
        ok_btn.clicked.connect(self.accept)
    def copy_log(self):
        #copy error log to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())

class AudioToolGUI(QWidget):
    def __init__(self):
        super().__init__()
        #set main window properties
        self.setWindowTitle("MuseAmp")
        self.setMinimumSize(700, 500)
        self.layout = QVBoxLayout(self)  #main vertical layout

        #file info table setup
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["File Path", "Extension", "File Loudness", "ReplayGain", "Clipping"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)    #make cells read-only
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)   #select entire rows
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive) #let user resize columns
        self.table.horizontalHeader().setStretchLastSection(True) #stretch last column to fill space

        #buttons
        self.add_files_btn = QPushButton("Add File(s)")
        self.add_folder_btn = QPushButton("Add Folder")
        self.remove_files_btn = QPushButton("Remove File(s)")
        self.gain_btn = QPushButton("Apply Gain")
        self.replaygain_btn = QPushButton("Analyze && Tag")

        #label for replaygain input
        self.replaygain_label = QLabel("Target LUFS: -")
        #textbox for replaygain value input
        self.replaygain_input = QLineEdit()
        self.replaygain_input.setFixedWidth(50) #fix width for neatness
        self.replaygain_input.setText("18") #default replaygain 2.0 lufs value (positive version)
        self.replaygain_input.setValidator(QIntValidator(5, 30, self))  #allow only 5 to 30

        #add checkbox for "create copy of file(s)"
        self.create_modified_checkbox = QCheckBox("Create copy of file(s) instead of modifying in-place")
        self.create_modified_checkbox.setChecked(False)
        self.create_modified_folder = None  #store user-selected folder

        #add checkbox for "search subfolders"
        self.search_subfolders_checkbox = QCheckBox("Search subfolders")
        self.search_subfolders_checkbox.setChecked(True)

        #layout for lufs label + input
        self.replaygain_layout = QHBoxLayout()
        self.replaygain_layout.addWidget(self.replaygain_label)
        self.replaygain_layout.addWidget(self.replaygain_input)

        #horizontal layout for buttons
        self.button_layout = QHBoxLayout()
        for btn in [
            self.add_files_btn, self.add_folder_btn,
            self.remove_files_btn, self.gain_btn, self.replaygain_btn
        ]:
            self.button_layout.addWidget(btn)

        #new layout for lufs + checkboxes (second row)
        self.options_layout = QHBoxLayout()
        self.options_layout.addLayout(self.replaygain_layout)
        self.options_layout.addWidget(self.create_modified_checkbox)
        self.options_layout.addWidget(self.search_subfolders_checkbox)
        self.options_layout.addStretch(1)

        #progress bar defaulting to 100
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(100)         #default to 100%
        self.progress_bar.setFormat("100%")

        #add widgets to the main layout
        self.layout.addWidget(self.table)
        self.layout.addLayout(self.button_layout)
        self.layout.addLayout(self.options_layout)
        self.layout.addWidget(self.progress_bar)
        
        #connect buttons to functions
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.remove_files_btn.clicked.connect(self.remove_files)
        self.replaygain_btn.clicked.connect(self.analyze_and_tag)
        self.gain_btn.clicked.connect(self.apply_gain_adjust)

    #add files to table/list
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files")
        if not files:
            return
        self.set_ui_enabled(False)
        self.set_progress(0)
        files_to_add = []
        for file_path in files:
            if not self.is_already_listed(file_path):
                files_to_add.append(file_path)
        #insert rows now, do not scan yet, just set "-" for columns
        for file_path in files_to_add:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(file_path)))
            self.table.setItem(row, 1, QTableWidgetItem(Path(file_path).suffix.lower()))
            self.table.setItem(row, 2, QTableWidgetItem("-"))
            self.table.setItem(row, 3, QTableWidgetItem("-"))
            self.table.setItem(row, 4, QTableWidgetItem("-"))
        self.set_ui_enabled(True)
        self.set_progress(100)

    #what to do when files are finished being added
    def _on_add_files_finished(self, updates, error_logs, start_row):
        for idx, loudness_val, replaygain_val, clipping_val in updates:
            row = start_row + idx
            self.table.setItem(row, 2, QTableWidgetItem(loudness_val))
            self.table.setItem(row, 3, QTableWidgetItem(replaygain_val))
            self.table.setItem(row, 4, QTableWidgetItem(clipping_val))
        self.set_ui_enabled(True)
        self.set_progress(100)
        if error_logs:
            dlg = ErrorLogDialog("\n\n".join(error_logs), self)
            dlg.exec()

    #add supported files from folder to table/list
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not folder:
            return
        self.set_ui_enabled(False)
        self.set_progress(0)
        already_listed = {self.table.item(row, 0).text() for row in range(self.table.rowCount())}
        #use utility to find supported files
        files_to_add = find_supported_files(
            folder,
            supported_filetypes,
            recursive=self.search_subfolders_checkbox.isChecked(),
            already_listed=already_listed
        )
        #insert items into rows now, do not scan yet, just set "-" for columns
        start_row = self.table.rowCount()
        for file_path in files_to_add:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(file_path)))
            self.table.setItem(row, 1, QTableWidgetItem(Path(file_path).suffix.lower()))
            self.table.setItem(row, 2, QTableWidgetItem("-"))
            self.table.setItem(row, 3, QTableWidgetItem("-"))
            self.table.setItem(row, 4, QTableWidgetItem("-"))
        self.set_ui_enabled(True)
        self.set_progress(100)

    #actually add file to the table/list (used for single file add)
    def add_file_to_table(self, file_path):
        path = Path(file_path)
        if not path.is_file():
            return
        if self.is_already_listed(str(path)):
            return

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(path))) #file path
        self.table.setItem(row, 1, QTableWidgetItem(path.suffix.lower()))   #extension

        #scan for existing replaygain tags
        loudness_val = "-"
        replaygain_val = "-"
        clipping_val = "-"
        try:
            cmd = [
                "rsgain", "custom",
                "-O",
                str(path)
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            output = proc.stdout
            if proc.returncode == 0:
                lines = output.strip().splitlines()
                if len(lines) >= 2:
                    header = lines[0].split('\t')
                    values = lines[1].split('\t')
                    colmap = {k: i for i, k in enumerate(header)}
                    lufs = values[colmap.get("Loudness (LUFS)", -1)] if "Loudness (LUFS)" in colmap else "-"
                    gain = values[colmap.get("Gain (dB)", -1)] if "Gain (dB)" in colmap else "-"
                    if lufs != "-":
                        loudness_val = f"{lufs} LUFS"
                    if gain != "-":
                        replaygain_val = gain
                    #clipping: check "Clipping" or "Clipping Adjustment?" column from rsgain
                    clip_idx = colmap.get("Clipping", colmap.get("Clipping Adjustment?", -1))
                    if clip_idx != -1:
                        clip_val = values[clip_idx]
                        if clip_val.strip().upper() in ("Y", "YES"):
                            clipping_val = "Yes"
                        elif clip_val.strip().upper() in ("N", "NO"):
                            clipping_val = "No"
                        else:
                            clipping_val = clip_val
        except Exception:
            pass

        #set values in table
        self.table.setItem(row, 2, QTableWidgetItem(loudness_val))
        self.table.setItem(row, 3, QTableWidgetItem(replaygain_val))
        self.table.setItem(row, 4, QTableWidgetItem(clipping_val))

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

    #disable/enable all ui elements except the progress bar
    def set_ui_enabled(self, enabled: bool):
        self.add_files_btn.setEnabled(enabled)
        self.add_folder_btn.setEnabled(enabled)
        self.remove_files_btn.setEnabled(enabled)
        self.gain_btn.setEnabled(enabled)
        self.replaygain_btn.setEnabled(enabled)
        self.replaygain_input.setEnabled(enabled)
        self.table.setEnabled(enabled)

    #update table with results from worker
    def update_table_with_worker(self, updates):
        for row, loudness_val, replaygain_val, clipping_val in updates:
            self.table.setItem(row, 2, QTableWidgetItem(loudness_val))
            self.table.setItem(row, 3, QTableWidgetItem(replaygain_val))
            self.table.setItem(row, 4, QTableWidgetItem(clipping_val))

    #set progress bar value and format
    def set_progress(self, percent):
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"{percent}%")

    #analyze and tag files (replaygain)
    def analyze_and_tag(self):
        files = []
        for row in range(self.table.rowCount()):
            files.append(self.table.item(row, 0).text())
        if not files:
            QMessageBox.information(self, "No Files", "No files to analyze.")
            return

        #only show warning if not creating modified copy
        if not self.create_modified_checkbox.isChecked():
            reply = QMessageBox.question(
                self,
                "ReplayGain Tagging",
                "Some files may already have ReplayGain tags. Overwrite existing tags?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply != QMessageBox.Yes:
                self.set_ui_enabled(True)
                self.set_progress(100)
                return

        #prompt for folder if creating modified copy
        if self.create_modified_checkbox.isChecked():
            QMessageBox.information(
                self,
                "Select Folder",
                "Please select where you'd like to create the folder called 'museamp modified' to store your modified music files."
            )
            folder = QFileDialog.getExistingDirectory(self, "Select folder to save modified files in")
            if not folder:
                QMessageBox.warning(self, "No Folder Selected", "Operation cancelled: No folder selected for modified files.")
                self.set_ui_enabled(True)
                self.set_progress(100)
                return
            #always use a subfolder 'museamp_modified' inside the selected folder
            self.create_modified_folder = str(Path(folder) / "museamp_modified")

        #get user input for lufs from textbox
        try:
            lufs = int(self.replaygain_input.text())
        except Exception:
            QMessageBox.warning(self, "Invalid LUFS", "Please enter a valid LUFS value.")
            return

        self.set_ui_enabled(False)
        self.set_progress(0)
        for row in range(self.table.rowCount()):
            self.table.setItem(row, 3, QTableWidgetItem("-"))
            self.table.setItem(row, 4, QTableWidgetItem("-"))

        self.worker_thread = QThread()
        self.worker = Worker(
            files, lufs,
            create_modified=self.create_modified_checkbox.isChecked()
        )
        if self.create_modified_checkbox.isChecked():
            self.worker.output_dir = self.create_modified_folder
        self.worker.overwrite_rg = True
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.set_progress)
        self.worker.finished.connect(self._on_worker_finished_tag)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    #handle completion of analyze & tag worker
    def _on_worker_finished_tag(self, updates, error_logs):
        #only handle the final update (not partials)
        if not updates or not all(isinstance(u, tuple) for u in updates):
            return
        #only show popup if all rows are updated (not "-")
        all_done = all(isinstance(u, tuple) and all(x != "-" for x in u[1:]) for u in updates)
        self.update_table_with_worker(updates)
        if all_done:
            if error_logs:
                dlg = ErrorLogDialog("\n\n".join(error_logs), self)
                dlg.exec()
            QMessageBox.information(self, "Operation Complete", "Analysis and tagging have been completed.")
            self.set_ui_enabled(True)
            self.set_progress(100)
            

    def apply_gain_adjust(self):
        files = [self.table.item(row, 0).text() for row in range(self.table.rowCount())]
        if not files:
            return

        #only show warning if not creating modified copy
        if not self.create_modified_checkbox.isChecked():
            reply = QMessageBox.question(
                self,
                "Warning: Apply Gain",
                "Applying gain to your files can irreparably damage them regardless of format. Do you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        #prompt for folder if creating modified copy
        if self.create_modified_checkbox.isChecked():
            QMessageBox.information(
                self,
                "Select Folder",
                "Please select where you'd like to create the folder called 'museamp modified' to store your modified music files."
            )
            folder = QFileDialog.getExistingDirectory(self, "Select folder to save modified files in")
            if not folder:
                QMessageBox.warning(self, "No Folder Selected", "Operation cancelled: No folder selected for modified files.")
                self.set_ui_enabled(True)
                self.set_progress(100)
                return
            #always use a subfolder 'museamp_modified' inside the selected folder
            self.create_modified_folder = str(Path(folder) / "museamp_modified")

        #get lufs value from user input
        try:
            lufs = int(self.replaygain_input.text())
        except Exception:
            QMessageBox.warning(self, "Invalid LUFS", "Please enter a valid LUFS value.")
            return

        self.set_ui_enabled(False)
        self.set_progress(0)
        for row in range(self.table.rowCount()):
            self.table.setItem(row, 3, QTableWidgetItem("-"))
            self.table.setItem(row, 4, QTableWidgetItem("-"))

        self.gain_worker_thread = QThread()
        self.gain_worker = ApplyGainWorker(
            files, lufs, self.table, supported_filetypes,
            create_modified=self.create_modified_checkbox.isChecked()
        )
        if self.create_modified_checkbox.isChecked():
            self.gain_worker.output_dir = self.create_modified_folder
        self.gain_worker.moveToThread(self.gain_worker_thread)
        self.gain_worker.progress.connect(self.set_progress)
        self.gain_worker.finished.connect(self._on_apply_gain_finished)
        self.gain_worker.finished.connect(self.gain_worker_thread.quit)
        self.gain_worker.finished.connect(self.gain_worker.deleteLater)
        self.gain_worker_thread.finished.connect(self.gain_worker_thread.deleteLater)
        self.gain_worker_thread.started.connect(self.gain_worker.run)
        self.gain_worker_thread.start()

    def _on_apply_gain_finished(self, error_logs, analysis_results):
        #update the table with new analysis results after gain is applied
        for idx, loudness_val, replaygain_val, clipping_val in analysis_results:
            self.table.setItem(idx, 2, QTableWidgetItem(loudness_val))
            self.table.setItem(idx, 3, QTableWidgetItem(replaygain_val))
            self.table.setItem(idx, 4, QTableWidgetItem(clipping_val))
        #re-enable ui and set progress to 100%
        self.set_ui_enabled(True)
        self.set_progress(100)
        #show error log dialog if there were any errors
        if error_logs:
            dlg = ErrorLogDialog("\n\n".join(error_logs), self)
            dlg.exec()
        #inform the user that the operation is complete
        QMessageBox.information(self, "Operation Complete", "Gain has been applied to all files.")