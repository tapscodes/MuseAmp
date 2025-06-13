import subprocess
from pathlib import Path
from PySide6.QtCore import QObject, Signal
import os 

#supported file types for processing
supported_filetypes = {".flac", ".mp3"}

class Worker(QObject):
    #background worker for analyzing/tagging files with replaygain
    finished = Signal(list, list)   #updates, error_logs
    progress = Signal(int)  #percent complete

    def __init__(self, files, lufs=None, create_modified=False):
        super().__init__()
        self.files = files
        self.lufs = lufs
        self.create_modified = create_modified

    def run(self):
        updates = []
        error_logs = []
        total = len(self.files)
        processed = 0

        def emit_progress():
            percent = int((processed / total) * 100) if total else 100
            if percent > 100:
                percent = 100
            self.progress.emit(percent)

        for row, file_path in enumerate(self.files):
            ext = Path(file_path).suffix.lower()
            if ext not in supported_filetypes:
                updates.append((row, "-", "-", "-"))
                processed += 1
                emit_progress()
                continue
            out_file = file_path
            if self.create_modified:
                p = Path(file_path)
                out_file = str(p.with_stem(p.stem + "_modified"))
            lufs_str = f"-{abs(int(self.lufs))}" if self.lufs is not None else "-18"
            loudness_val = "-"
            replaygain_val = "-"
            clipping_val = "-"
            rsgain_cmd = [
                "rsgain", "custom", "-s", "i", "-l", lufs_str, "-O", out_file
            ]
            if hasattr(self, "overwrite_rg") and not self.overwrite_rg:
                rsgain_cmd.insert(2, "-S")
            try:
                proc = subprocess.run(
                    rsgain_cmd,
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
        self.finished.emit(updates, error_logs)

class AddFilesWorker(QObject):
    #background worker for adding files/folders and analyzing them
    finished = Signal(list, list)   #updates, error_logs
    progress = Signal(int)  #percent complete

    def __init__(self, files):
        super().__init__()
        self.files = files

    def run(self):
        updates = []
        error_logs = []
        total = len(self.files)
        for idx, file_path in enumerate(self.files):
            path = Path(file_path)
            loudness_val = "-"
            replaygain_val = "-"
            clipping_val = "-"
            if not path.is_file():
                error_logs.append(f"{file_path}: Not a file")
                updates.append((idx, loudness_val, replaygain_val, clipping_val))
                self.progress.emit(int((idx + 1) / total * 100))
                continue
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

class ApplyGainWorker(QObject):
    #background worker for applying gain to files using ffmpeg
    finished = Signal(list, list)  #error_logs, analysis_results
    progress = Signal(int)   #percent

    def __init__(self, files, lufs, table, supported_filetypes, create_modified=False):
        super().__init__()
        self.files = files
        self.lufs = lufs
        self.table = table
        self.supported_filetypes = supported_filetypes
        self.create_modified = create_modified
        self.output_dir = None  # Will be set by GUI if needed

    def run(self):
        error_logs = []
        total = len(self.files)
        # Use output_dir from GUI if provided
        output_dir = None
        if self.create_modified and self.files:
            if hasattr(self, "output_dir") and self.output_dir:
                output_dir = Path(self.output_dir)
                try:
                    output_dir.mkdir(exist_ok=True)
                except Exception as e:
                    error_logs.append(f"Failed to create output directory '{output_dir}': {e}")
                    self.finished.emit(error_logs, [])
                    return
            else:
                # fallback: use default location if not set
                first_file = Path(self.files[0])
                output_dir = first_file.parent / "museamp_modified"
                try:
                    output_dir.mkdir(exist_ok=True)
                except Exception as e:
                    error_logs.append(f"Failed to create output directory '{output_dir}': {e}")
                    self.finished.emit(error_logs, [])
                    return

        for idx, file_path in enumerate(self.files):
            ext = Path(file_path).suffix.lower()
            if ext not in self.supported_filetypes:
                continue
            lufs_str = f"-{abs(self.lufs)}"
            tag_cmd = [
                "rsgain", "custom", "-s", "i", "-l", lufs_str, "-O", file_path
            ]
            gain_val = None
            try:
                proc_tag = subprocess.run(tag_cmd, capture_output=True, text=True, check=False)
                if proc_tag.returncode != 0:
                    error_logs.append(f"{file_path} (tag):\n{proc_tag.stderr or proc_tag.stdout}")
                    self.progress.emit(int((idx + 1) / total * 100))
                    continue
                output = proc_tag.stdout
                lines = output.strip().splitlines()
                if len(lines) >= 2:
                    header = lines[0].split('\t')
                    values = lines[1].split('\t')
                    colmap = {k: i for i, k in enumerate(header)}
                    gain_idx = colmap.get("Gain (dB)", -1)
                    if gain_idx != -1 and gain_idx < len(values):
                        gain_val = values[gain_idx]
                    else:
                        gain_val = None
            except Exception as e:
                error_logs.append(f"{file_path} (tag): {str(e)}")
                self.progress.emit(int((idx + 1) / total * 100))
                continue

            if gain_val is None or gain_val == "-":
                error_logs.append(f"{file_path}: Could not determine ReplayGain value.")
                self.progress.emit(int((idx + 1) / total * 100))
                continue

            try:
                gain_db = float(gain_val)
            except Exception:
                error_logs.append(f"{file_path}: Invalid gain value '{gain_val}'.")
                self.progress.emit(int((idx + 1) / total * 100))
                continue

            # Determine output file path
            out_file = file_path
            if self.create_modified and output_dir:
                p = Path(file_path)
                out_file = str(output_dir / p.name)

            tmp_file = str(Path(out_file).with_suffix(f".gain_tmp{ext}"))
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", file_path,
                "-map_metadata", "0", "-map", "0",
                "-af", f"volume={gain_db}dB",
                "-c:v", "copy"
            ]
            if ext == ".mp3":
                ffmpeg_cmd += ["-c:a", "libmp3lame"]
            elif ext == ".flac":
                ffmpeg_cmd += ["-c:a", "flac"]
                try:
                    probe = subprocess.run(
                        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=bits_per_raw_sample,bits_per_sample", "-of", "default=noprint_wrappers=1:nokey=1", file_path],
                        capture_output=True, text=True, check=False
                    )
                    bit_depths = [int(x) for x in probe.stdout.strip().splitlines() if x.isdigit()]
                    if bit_depths:
                        bit_depth = max(bit_depths)
                        if bit_depth == 16:
                            ffmpeg_cmd += ["-sample_fmt", "s16"]
                        elif bit_depth == 24:
                            ffmpeg_cmd += ["-sample_fmt", "s32"]
                        elif bit_depth == 32:
                            ffmpeg_cmd += ["-sample_fmt", "s32"]
                except Exception:
                    pass
            ffmpeg_cmd.append(tmp_file)
            try:
                proc_ffmpeg = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=False)
                if proc_ffmpeg.returncode != 0:
                    error_logs.append(f"{file_path} (ffmpeg):\n{proc_ffmpeg.stderr or proc_ffmpeg.stdout}")
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
                    self.progress.emit(int((idx + 1) / total * 100))
                    continue
                os.replace(tmp_file, out_file)
            except Exception as e:
                error_logs.append(f"{file_path} (ffmpeg): {str(e)}")
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
            self.progress.emit(int((idx + 1) / total * 100))

        analysis_results = []
        for idx, file_path in enumerate(self.files):
            loudness_val = "-"
            replaygain_val = "-"
            clipping_val = "-"
            ext = Path(file_path).suffix.lower()
            # For modified output, analyze the output file, not the original
            analyze_path = file_path
            if self.create_modified and output_dir:
                p = Path(file_path)
                analyze_path = str(output_dir / p.name)
            if ext not in self.supported_filetypes:
                analysis_results.append((idx, loudness_val, replaygain_val, clipping_val))
                continue
            try:
                proc = subprocess.run(
                    ["rsgain", "custom", "-s", "i", "-l", lufs_str, "-O", analyze_path],
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
                    error_logs.append(f"{analyze_path} (analyze):\n{proc.stderr or proc.stdout}")
            except Exception as e:
                error_logs.append(f"{analyze_path} (analyze): {str(e)}")
            analysis_results.append((idx, loudness_val, replaygain_val, clipping_val))
        self.finished.emit(error_logs, analysis_results)
