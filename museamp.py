import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QProgressBar, QMessageBox, QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QHeaderView,
    QLineEdit, QLabel, QDialog, QTextEdit, QDialogButtonBox
)
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import Qt, QThread, Signal, QObject
from pathlib import Path
import subprocess

#supported file types
supported_filetypes = {".flac", ".mp3"}

#class to define gui
class ErrorLogDialog(QDialog):
    def __init__(self, log_text, parent=None):
        #basic window properties
        super().__init__(parent)
        self.setWindowTitle("Error Log")
        self.setMinimumSize(400, 300)
        #layout and text setup
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(log_text)
        layout.addWidget(self.text_edit)

        #button setup
        button_box = QDialogButtonBox()
        copy_btn = QPushButton("Copy Log")
        ok_btn = QPushButton("OK")
        button_box.addButton(copy_btn, QDialogButtonBox.ActionRole)
        button_box.addButton(ok_btn, QDialogButtonBox.AcceptRole)
        layout.addWidget(button_box)
        copy_btn.clicked.connect(self.copy_log)
        ok_btn.clicked.connect(self.accept)
    def copy_log(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_edit.toPlainText())

#worker for background operations
class Worker(QObject):
    finished = Signal(list, list)   #updates, error_logs
    progress = Signal(int)  #percent complete

    def __init__(self, files, mode, lufs=None):
        super().__init__()
        self.files = files
        self.mode = mode  # "analyze", "tag", or "delete" modes (TODO: replace "delete" with 'apply' once i'm sure things are working)
        self.lufs = lufs

    #runner for worker thread
    def run(self):
        updates = []
        error_logs = []
        total = len(self.files)
        processed = 0

        #helper to update progress bar
        def emit_progress():
            percent = int((processed / total) * 100) if total else 100
            if percent > 100:
                percent = 100
            self.progress.emit(percent)

        #helper to update table after each file
        def emit_partial_update():
            partial = []
            for i in range(total):
                if i < len(updates):
                    partial.append(updates[i])
                else:
                    partial.append((i, "-", "-", "-"))
            self.finished.emit(partial, [])

        #tag mode: apply ReplayGain tags to files
        if self.mode == "tag":
            for row, file_path in enumerate(self.files):
                ext = Path(file_path).suffix.lower()
                if ext not in supported_filetypes:
                    updates.append((row, "-", "-", "-"))
                    processed += 1
                    emit_progress()
                    emit_partial_update()
                    continue
                #build rsgain command to apply ReplayGain tag
                # self.lufs is expected to be an int between 5 and 30
                lufs_str = f"-{abs(int(self.lufs))}" if self.lufs is not None else "-18"
                cmd = [
                    "rsgain",
                    "custom",
                    "-s", "i",
                    "-l", lufs_str,
                    "-O",
                    f'"{file_path}"'  # add quotes around file path
                ]
                loudness_val = "-"
                replaygain_val = "-"
                clipping_val = "-"
                try:
                    proc = subprocess.run(
                        ["rsgain", "custom", "-s", "i", "-l", lufs_str, "-O", file_path],
                        capture_output=True, text=True, check=False
                    )
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
                    else:
                        error_logs.append(f"{file_path}:\n{proc.stderr or proc.stdout}")
                except Exception as e:
                    error_logs.append(f"{file_path}: {str(e)}")
                updates.append((row, loudness_val, replaygain_val, clipping_val))
                processed += 1
                emit_progress()
                emit_partial_update()
            # skip the analyze phase, just emit the updates
            self.finished.emit(updates, error_logs)
            return
        #delete mode: remove ReplayGain tags from files
        elif self.mode == "delete":
            for row, file_path in enumerate(self.files):
                ext = Path(file_path).suffix.lower()
                if ext not in supported_filetypes:
                    updates.append((row, "-", "-", "-"))
                    processed += 1
                    emit_progress()
                    emit_partial_update()
                    continue
                #build rsgain command to delete ReplayGain tags
                cmd = [
                    "rsgain",
                    "custom",
                    "-s", "d",
                    "-O",
                    f'"{file_path}"'  # add quotes around file path
                ]
                try:
                    proc = subprocess.run(
                        ["rsgain", "custom", "-s", "d", "-O", file_path],
                        capture_output=True, text=True, check=False
                    )
                    if proc.returncode != 0:
                        error_logs.append(f"{file_path}:\n{proc.stderr or proc.stdout}")
                except Exception as e:
                    error_logs.append(f"{file_path}: {str(e)}")
                processed += 1
                emit_progress()
                emit_partial_update()
            mode = "analyze"
        else:
            mode = "analyze"

        #analyze mode: scan files for ReplayGain/loudness/clipping info
        if mode == "analyze":
            processed = 0  #reset for analysis phase
            updates.clear()
            for row, file_path in enumerate(self.files):
                loudness_val = "-"
                replaygain_val = "-"
                clipping_val = "-"
                cmd = [
                    "rsgain",
                    "custom",
                    "-O",
                    f'"{file_path}"'  # add quotes around file path
                ]
                try:
                    proc = subprocess.run(
                        ["rsgain", "custom", "-O", file_path],
                        capture_output=True, text=True, check=False
                    )
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
                updates.append((row, loudness_val, replaygain_val, clipping_val))
                processed += 1
                emit_progress()
                emit_partial_update()
        self.finished.emit(updates, error_logs)

#worker for adding files/folders
class AddFilesWorker(QObject):
    finished = Signal(list, list)   #updates, error_logs
    progress = Signal(int)  #percent complete

    def __init__(self, files):
        super().__init__()
        self.files = files

    #runner for add files/folder worker
    def run(self):
        updates = []
        error_logs = []
        total = len(self.files)
        for idx, file_path in enumerate(self.files):
            path = Path(file_path)
            loudness_val = "-"
            replaygain_val = "-"
            clipping_val = "-"
            #check if file exists
            if not path.is_file():
                error_logs.append(f"{file_path}: Not a file")
                updates.append((idx, loudness_val, replaygain_val, clipping_val))
                self.progress.emit(int((idx + 1) / total * 100))
                continue
            #check if file type is supported (taken from top supported_filetypes var)
            if path.suffix.lower() not in supported_filetypes:
                error_logs.append(f"{file_path}: Unsupported file type")
                updates.append((idx, loudness_val, replaygain_val, clipping_val))
                self.progress.emit(int((idx + 1) / total * 100))
                continue
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
                        #clipping: check "Clipping" or "Clipping Adjustment?" column in rsgain
                        clip_idx = colmap.get("Clipping", colmap.get("Clipping Adjustment?", -1))
                        if clip_idx != -1:
                            clip_val = values[clip_idx]
                            if clip_val.strip().upper() in ("Y", "YES"):
                                clipping_val = "Yes"
                            elif clip_val.strip().upper() in ("N", "NO"):
                                clipping_val = "No"
                            else:
                                clipping_val = clip_val
                else:
                    error_logs.append(f"{file_path}: rsgain failed\n{proc.stderr or proc.stdout}")
            except Exception as e:
                error_logs.append(f"{file_path}: {str(e)}")
            updates.append((idx, loudness_val, replaygain_val, clipping_val))
            self.progress.emit(int((idx + 1) / total * 100))
        self.finished.emit(updates, error_logs)

class AudioToolGUI(QWidget):
    def __init__(self):
        super().__init__()
        #set basic window properties
        self.setWindowTitle("MuseAmp")
        self.setMinimumSize(700, 500)
        self.layout = QVBoxLayout(self)  #main vertical layout

        #file info table setup
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["File Path", "Extension", "File Loudness", "ReplayGain", "Clipping"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)    #make cells read-only
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)   #select entire rows
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  #stretch first column

        #buttons
        self.add_files_btn = QPushButton("Add File(s)")
        self.add_folder_btn = QPushButton("Add Folder")
        self.remove_files_btn = QPushButton("Remove File(s)")
        self.gain_btn = QPushButton("Apply Gain")
        self.replaygain_btn = QPushButton("Analyze && Tag")

        #textbox for replaygain value input
        self.replaygain_input = QLineEdit()
        self.replaygain_input.setFixedWidth(50)           #fix width for neatness
        self.replaygain_input.setText("18")               #default ReplayGain 2.0 LUFS value (positive version)
        self.replaygain_input.setValidator(QIntValidator(5, 30, self))  #allow only 5 to 30

        #label for replaygain input
        self.replaygain_label = QLabel("Target LUFS: -")

        #layout for replaygain label + input
        self.replaygain_layout = QHBoxLayout()
        self.replaygain_layout.addWidget(self.replaygain_label)
        self.replaygain_layout.addWidget(self.replaygain_input)

        #progress bar defaulting to 100
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(100)         #default to 100%
        self.progress_bar.setFormat("100%")

        #horizontal layout for buttons and input
        self.button_layout = QHBoxLayout()
        for btn in [
            self.add_files_btn, self.add_folder_btn,
            self.remove_files_btn, self.gain_btn, self.replaygain_btn
        ]:
            self.button_layout.addWidget(btn)

        #add replaygain input layout to the right of replaygain button
        self.button_layout.addLayout(self.replaygain_layout)

        #add widgets to the main layout
        self.layout.addWidget(self.table)
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.progress_bar)
        
        #connect buttons to functions
        self.add_files_btn.clicked.connect(self.add_files)
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.remove_files_btn.clicked.connect(self.remove_files)
        self.replaygain_btn.clicked.connect(self.analyze_and_tag)

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
        files_to_add = []
        #check to see if supported file type
        for root, _, files in os.walk(folder):
            for filename in files:
                path = Path(root) / filename
                if path.suffix.lower() in supported_filetypes and not self.is_already_listed(str(path)):
                    files_to_add.append(str(path))
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

        #scan for existing ReplayGain tags
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

    #analyze and tag files (ReplayGain)
    def analyze_and_tag(self):
        files = []
        has_existing_rg = False
        for row in range(self.table.rowCount()):
            files.append(self.table.item(row, 0).text())
            rg_val = self.table.item(row, 3)
            if rg_val and rg_val.text() != "-":
                has_existing_rg = True
        if not files:
            QMessageBox.information(self, "No Files", "No files to analyze.")
            return
        if has_existing_rg:
            QMessageBox.warning(self, "WARNING", "WARNING: ReplayGain tag will be overwritten")
        #get user input for LUFS from textbox
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
        #pass user input LUFS to Worker
        self.worker = Worker(files, "tag", lufs)
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
            self.set_ui_enabled(True)
            self.set_progress(100)
            if error_logs:
                dlg = ErrorLogDialog("\n\n".join(error_logs), self)
                dlg.exec()
            QMessageBox.information(self, "Operation Complete", "Analysis and tagging have been completed.")

#actually load and run app
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AudioToolGUI()
    window.show()
    sys.exit(app.exec())