# Museamp
Museamp (Music + Amplifier) is an audio level normalizer/amplifier that makes your audio files play at the same normalized level. It can either directly alter your audio files (not advised as this can cause clipping to ruin audio quality) or simply apply a ReplayGain tag to your files so your audio player knows what level to play the audio at.

## How to Use
1. After installing the depenencies on your system that are listed below, load up the program.
2. From here add your files with the 'Add Files' or 'Add Folder' button with the 'Remove Files' button being there to remove any files you've accidentally added in that you didn't mean to.
3. Once the files are loaded in, set your desired LUFS in the bottom right textbox
4. Once the LUFS have been set, you can hit the 'Analyze & Tag' button to analyze your songs and tag them with a ReplayGain tag at the desired LUFS so they can be used in your music player of choice. If you hit 'Apply Gain' instead, the files will be directly loudened or made quieter to be at the LUFS value you specified.
5. Once you're done simply close the application.

### What are common values for LUFS?
LUFS value can vary between -5 and -30 with the ReplayGain 2.0 standard being at -18 LUFS, which is also the default for this app.  
Some other commonly used values are -14 LUFS by Spotify, Amazon Music, and YouTube, -16 LUFS by Apple Music, -18 as a common Podcast value, and -23/-24 LUFS for TV broadcasts. However lots of more modern music tracks are mastered as high as -8 to -10 LUFS to account for listeners who might listen to music at extremely loud volumes.

## Project Status
-Supports .mp3 and .flac files which are proper mp3s and flacs, still bad at handling improper flac files (poorly converted ones), will look into that further later

## Dependancies
- FFmpeg [Download] (https://ffmpeg.org/) to apply gain to files
- RSGain [Download](https://github.com/complexlogic/rsgain) for audio analysis
- Python [Download](https://www.python.org/downloads/) for the libraries below
- Mutagen ```pip install mutagen``` to edit tags
- PySide6 ```pip install PySide6``` for the UI

## How to build flatpak
1. Install flatpak and flatpak builder in your repository of choice.
2. Setup flatpak user with ```flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo``` 
3. Build with ```flatpak run org.flatpak.Builder builder-dir --user --ccache --force-clean --install io.github.tapscodes.museamp.json``` and run it with ```flatpak run io.github.tapscodes.museamp```
4. Optionally export it into a .flatpak file with ```flatpak build-export repo-dir builder-dir```
5. Install elsewhere with ```flatpak install --user museamp.flatpak``` and use ```flatpak run io.github.tapscodes.museamp``` to run it.