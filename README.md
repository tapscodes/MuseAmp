# Museamp
Museamp (Music + Amplifier) is an audio level normalizer/amplifier that makes your audio files play at the same normalized level. It can either directly alter your audio files (not advised as this can cause clipping to ruin audio quality) or simply apply a ReplayGain tag to your files so your audio player knows what level to play the audio at.

## Dependancies
-RSGain [Download](https://github.com/complexlogic/rsgain) for audio analysis
-Python [Download](https://www.python.org/downloads/) for the libraries below
-Mutagen ```pip install mutagen``` to edit tags
-PySide6 ```pip install PySide6``` for the UI