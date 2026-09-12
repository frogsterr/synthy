# Synthy

Turn a scanned piano score (an IMSLP PDF, or photos of the pages) into a
MIDI file that plays as falling notes in Synthesia. Right hand and left
hand land on separate tracks, at a tempo you choose.

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

Audiveris 5.11, without root:

```bash
mkdir -p ~/.local/opt && cd ~/.local/opt
curl -sL -o audiveris.deb https://github.com/Audiveris/audiveris/releases/download/5.11.0/Audiveris-5.11.0-ubuntu22.04-x86_64.deb
dpkg-deb -x audiveris.deb extract && mv extract/opt/audiveris audiveris && rm -rf extract audiveris.deb
mkdir -p ~/.local/share/AudiverisLtd/audiveris/tessdata
curl -sL -o ~/.local/share/AudiverisLtd/audiveris/tessdata/eng.traineddata https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata
```

Audiveris needs a Java 21 runtime on the path. Synthy looks for the
binary at `~/.local/opt/audiveris/bin/Audiveris`; set `SYNTHY_AUDIVERIS`
to use a different install, and `TESSDATA_PREFIX` for a different OCR
data folder.

## Use

Web app:

```bash
synthy serve
```

Then open http://127.0.0.1:8000, drop a PDF, set the tempo, download the
MIDI. Uploads and intermediate files live under `~/.cache/synthy/jobs`.

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
```

The engine sits behind `synthy.engine.Engine`, so another recognizer
can be plugged in by writing MusicXML per page.

## Develop

```bash
pytest            # unit tests, no Audiveris needed
pytest tests/test_integration.py   # runs Audiveris on a real scan if both exist
```

Design notes and the implementation plan are in `docs/superpowers/`.
