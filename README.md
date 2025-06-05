# Museamp
Museamp (Music + Amplifier) is an audio level normalizer/amplifier that makes your audio files play at the same normalized level. It can either directly alter your audio files (not advised as this can cause clipping to ruin audio quality) or simply apply a ReplayGain tag to your files so your audio player knows what level to play the audio at.

## How to Use
TODO: write this later

### What are common values for LUFS?
TODO: write this later

## Project Status
-Apply Gain button is attempting to delete replaygain tags atm to help with testing, will be applying actual gain to files later.
-Supports .mp3 and .flac files which are proper mp3s and flacs, still bad at handling improper flac files (poorly converted ones), will look into that further later

## Dependancies
-RSGain [Download](https://github.com/complexlogic/rsgain) for audio analysis
-Python [Download](https://www.python.org/downloads/) for the libraries below
-Mutagen ```pip install mutagen``` to edit tags
-PySide6 ```pip install PySide6``` for the UI