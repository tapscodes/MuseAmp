#utility functions for museamp

from pathlib import Path

def get_supported_filetypes():
    #return supported audio file extensions
    return {".flac", ".mp3"}

def is_supported_filetype(filepath):
    #check if the file has a supported extension
    return Path(filepath).suffix.lower() in get_supported_filetypes()

def get_file_extension(filepath):
    #return the file extension in lower case
    return Path(filepath).suffix.lower()

def is_audio_file(filepath):
    #check if the file is a supported audio file (exists and is supported type)
    path = Path(filepath)
    return path.is_file() and is_supported_filetype(filepath)

def filter_supported_files(filepaths):
    #return only supported audio files from a list of file paths
    return [f for f in filepaths if is_audio_file(f)]

def get_files_in_folder(folder):
    #recursively get all supported files in a folder
    folder = Path(folder)
    return [
        str(p) for p in folder.rglob("*")
        if p.is_file() and is_supported_filetype(p)
    ]

def find_supported_files(folder, supported_filetypes, recursive=True, already_listed=None):
    #find supported files in a folder, optionally recursively, skipping already_listed
    from pathlib import Path
    import os
    files = []
    already_listed = already_listed or set()
    if recursive:
        for path in Path(folder).rglob("*"):
            if path.is_file() and path.suffix.lower() in supported_filetypes and str(path) not in already_listed:
                files.append(str(path))
    else:
        for filename in os.listdir(folder):
            path = Path(folder) / filename
            if path.is_file() and path.suffix.lower() in supported_filetypes and str(path) not in already_listed:
                files.append(str(path))
    return files
