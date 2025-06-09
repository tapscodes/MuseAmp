# Museamp
Museamp (Music + Amplifier) is an audio level normalizer/amplifier that makes your audio files play at the same normalized level. It can either directly alter your audio files (not advised as this can cause clipping to ruin audio quality) or simply apply a ReplayGain tag to your files so your audio player knows what level to play the audio at. It currently only supports MP3 and FLAC files as those are the most commonly used filetypes.

## How to Use
1. After installing the depenencies on your system that are listed below, load up the program ```MuseAmp.pyw``` if installing from source, or simply install the binaries from the release tab and load up the program that way (should get you the necessary dependencies automatically). For linux users this app will also be available on [Flathub](https://flathub.org/).
2. From here add your files with the 'Add Files' or 'Add Folder' button with the 'Remove Files' button being there to remove any files you've accidentally added in that you didn't mean to.
3. Once the files are loaded in, set your desired LUFS in the bottom right textbox
4. Once the LUFS have been set, you can hit the 'Analyze & Tag' button to analyze your songs and tag them with a ReplayGain tag at the desired LUFS so they can be used in your music player of choice. If you hit 'Apply Gain' instead, the files will be directly loudened or made quieter to be at the LUFS value you specified.
5. Once you're done simply close the application.

### What are common values for LUFS?
LUFS value can vary between -5 and -30 with the ReplayGain 2.0 standard being at -18 LUFS, which is also the default for this app.  

Some other commonly used values are -14 LUFS by Spotify, Amazon Music, and YouTube, -16 LUFS by Apple Music, -18 as a common Podcast value, and -20 LUFS for TV broadcasts. 

However lots of more modern music tracks are mastered as high as -8 to -10 LUFS to account for listeners who might listen to music at extremely loud volumes. I personally generally use around -16 LUFS.

## Where to submit bugs?
You can submit bugs to the [issues page](https://github.com/tapscodes/MuseAmp/issues) of this GitHub repository. However, I made this app primarily with the intent of it working as a linux FlatPak application so I can't guarantee that if the MacOS or Windows builds are buggy that i'll end up looking into fixing them unless the problem is actually with the way the program logic itself works (which is likely where most bugs are due to the simple UI). Feel free to submit a pull request with a fix if you know one or can figure one out though!

## How can I contribute?
To contribute all you need to do is fork the program, make your changes, and then submit them as a pull request and I'll add them or deny them based on wether or not they work and/or fit the program well.

## Remaining Bugs In Program
-Supports .mp3 and .flac files which are proper mp3s and flacs, still bad at handling improper flac files (poorly converted ones) and produce an error message if they are read which might be hard to decipher for users.

## Dependancies (for devs)
- FFmpeg [Download] (https://ffmpeg.org/) to apply gain to files
- RSGain [Download](https://github.com/complexlogic/rsgain) for audio analysis
- Python [Download](https://www.python.org/downloads/) for the libraries below
- Mutagen ```pip install mutagen``` to edit tags
- PySide6 ```pip install PySide6``` for the UI

## How to build flatpak (for devs)
1. Install flatpak and flatpak builder in your repository of choice.
2. Setup flatpak user with ```flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo``` 
3. Build with ```flatpak run org.flatpak.Builder builder-dir --user --ccache --force-clean --install io.github.tapscodes.MuseAmp.json``` and run it with ```flatpak run io.github.tapscodes.MuseAmp```

## How to check linter for flathub (for devs)
Run ```flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest io.github.tapscodes.MuseAmp.json``` to check manifest