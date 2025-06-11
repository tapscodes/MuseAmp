#utility functions for MuseAmp

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
