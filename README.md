# Synthy

Turn a scanned piano score (an IMSLP PDF, or photos of the pages) into
falling notes: watch and hear the piece in the browser, export it as an
MP4, or download a MIDI file for Synthesia. Right hand and left hand land
on separate tracks, at a tempo you choose.

Synthy runs [Audiveris](https://github.com/Audiveris/audiveris) to read
the score, then snaps every measure to its time signature before writing
MIDI, because optical music recognition gets pitches mostly right on
dense Romantic writing but drifts on rhythm. Measures that had to be
stretched or squeezed a lot are listed so you know where to check.

## Install

Python 3.11 or newer.

```bash
pip install -e ".[dev]"
```

Audiveris 5.11 on Linux, without root:

```bash
mkdir -p ~/.local/opt && cd ~/.local/opt
curl -sL -o audiveris.deb https://github.com/Audiveris/audiveris/releases/download/5.11.0/Audiveris-5.11.0-ubuntu22.04-x86_64.deb
dpkg-deb -x audiveris.deb extract && mv extract/opt/audiveris audiveris && rm -rf extract audiveris.deb
```

On macOS (Apple silicon; use the x86_64 dmg on Intel):

```bash
curl -sL -o /tmp/audiveris.dmg https://github.com/Audiveris/audiveris/releases/download/5.11.0/Audiveris-5.11.0-macosx-arm64.dmg
echo Y | hdiutil attach -nobrowse -readonly /tmp/audiveris.dmg
mkdir -p ~/Applications && cp -R /Volumes/Audiveris/Audiveris.app ~/Applications/
hdiutil detach /Volumes/Audiveris
```

Then the OCR data, on either platform:

```bash
mkdir -p ~/.local/share/AudiverisLtd/audiveris/tessdata
curl -sL -o ~/.local/share/AudiverisLtd/audiveris/tessdata/eng.traineddata https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
```

The Linux build needs a Java 21 runtime on the path; the macOS app bundles
its own. Synthy looks for the binary at `~/.local/opt/audiveris/bin/Audiveris`,
`~/Applications/Audiveris.app` and `/Applications/Audiveris.app`; set
`SYNTHY_AUDIVERIS` to use a different install, and `TESSDATA_PREFIX` for
a different OCR data folder.

## Use

Web app:

```bash
synthy serve
```

Then open http://127.0.0.1:8000, drop a PDF, set the tempo, and either
play the piece in the browser or download the MIDI. Uploads and
intermediate files live under `~/.cache/synthy/jobs`.

The player draws the notes falling onto an 88-key keyboard, right hand
green and left hand blue, with piano sound. Space plays and pauses, the
arrow keys skip four beats. Sliders set the playback speed, the scale
(pixels per beat, so notes can be tall and fast or short and dense) and
the note width; settings are remembered. A style menu switches the bar
look (matte, bevel, strike edge, capsule), and "Compare styles" shows
all four side by side on the same clock. Measure lines and the suspect
measure shading can be toggled. When a key is struck again while its
note is still held, the earlier bar is cut at the new onset. "Export MP4" renders the same view with
audio to an H.264/AAC file, faster than real time, in Chrome or Edge.

Command line:

```bash
synthy convert score.pdf -o score.mid --tempo 80 --pages 1-3,5
```

Both print the measures that look suspect: their expected length in
beats and what each hand actually read as.

## How it works

```
PDF / image -> page PNGs (2550 px wide, grayscale)
            -> Audiveris batch export, one MusicXML per page
            -> RawScore: notes per staff with raw onsets and durations
            -> normalize: scale each hand of each measure to the time signature,
                          infer a missing time signature, merge ties, flag outliers
            -> MIDI: track 1 right hand (channel 0), track 2 left hand (channel 1)
            -> player: the same note list as JSON, drawn on a canvas and played
                       through the FluidR3 piano soundfont; MP4 export encodes
                       that canvas and an offline audio render with WebCodecs
```

Measures before the first recognised time signature use the most common
measured length (from the shorter staff of each measure, since engine
mistakes mostly add duration); a time signature found later is only used
from where it appears, because it may be a meter change.

The engine sits behind `synthy.engine.Engine`, so another recognizer
can be plugged in by writing MusicXML per page.

## Develop

```bash
pytest            # unit tests, no Audiveris needed
pytest tests/test_integration.py   # runs Audiveris on a real scan if both exist
```

Design notes and the implementation plan are in `docs/superpowers/`.
