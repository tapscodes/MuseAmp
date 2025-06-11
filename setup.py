from setuptools import setup, find_packages

setup(
    name="MuseAmp",
    version="1.0.0",
    description="Audio level normalizer/amplifier for MP3 and FLAC files",
    author="tapscodes",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "PySide6",
    ],
    entry_points={
        "gui_scripts": [
            "MuseAmp = museamp.main:main",
        ],
    },
)
