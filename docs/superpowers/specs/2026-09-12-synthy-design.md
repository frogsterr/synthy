# Synthy design: sheet music to Synthesia MIDI

Date: 2026-09-12. Follows the brainstorming and OMR spike of the same day
(see the spike memory: Audiveris chosen over the SMT model for v1).

## Goal

A local web app that turns a PDF (IMSLP scan) or page images of a piano
score into a MIDI file that plays correctly as Synthesia falling notes.

## Decisions carried over from brainstorming

- Web page UI, run locally. MIDI download only, no in-page player.
- Fully automatic v1. Suspect measures are reported alongside the download
  (the normalization step produces the flags for free).
- Right hand and left hand on separate MIDI tracks.
- Fixed tempo chosen by the user (BPM, default 80).
- Engine (Audiveris) sits behind one interface so SMT can be added later.

## Pipeline

```
input (pdf | png | jpg)
  -> render.py     : page images, grayscale PNG, width 2550 px (Audiveris rejects > 20 MP)
  -> engine/*.py   : OMR engine, one MusicXML file per page
  -> score.py      : MusicXML -> RawScore (measures with notes per staff, raw lengths, time sigs)
  -> normalize.py  : snap every measure to its time signature, flag outliers, infer missing TS
  -> midi.py       : NoteEvents -> 2-track MIDI at fixed tempo
```

`pipeline.py` wires these together and returns a `ConversionResult`
(midi path, flagged measures, per-page measure counts, engine log path).

## Data model (`synthy/model.py`)

```python
@dataclass
class RawNote:
    staff: int            # 1 = treble/right hand, 2 = bass/left hand
    onset: Fraction       # quarters from measure start, as the engine wrote it
    duration: Fraction    # quarters, as the engine wrote it
    pitch: int            # MIDI number
    tie_start: bool
    tie_stop: bool

@dataclass
class RawMeasure:
    index: int                        # 0-based across the whole piece
    page: int                         # 1-based page number
    time_signature: Fraction | None   # measure length in quarters if the engine saw a TS
    notes: list[RawNote]
    staff_lengths: dict[int, Fraction]  # raw measure length per staff

@dataclass
class RawScore:
    measures: list[RawMeasure]

@dataclass
class NoteEvent:
    staff: int
    onset: Fraction       # absolute quarters from piece start
    duration: Fraction
    pitch: int

@dataclass
class MeasureReport:
    index: int
    page: int
    expected: Fraction
    raw: dict[int, Fraction]
    scale: dict[int, Fraction]
    suspect: bool
```

## Normalization rules

1. Expected length per measure: the most recent time signature seen. If
   none has been seen yet, use the first TS that appears later in the piece.
   If the piece has no TS at all, use the mode of raw staff lengths rounded
   to the nearest half quarter.
2. Each staff of each measure is scaled independently so its raw length
   equals the expected length. A staff with zero notes is left alone.
3. A measure is suspect when any staff's scale factor is outside
   [0.8, 1.25] (raw length off by more than 25%).
4. Absolute onset = sum of expected lengths of all previous measures +
   scaled onset within the measure.
5. Tied notes are merged after absolute times are known: a note with
   tie_stop extends the nearest earlier note of the same staff and pitch
   whose end touches its onset (within 1/16 quarter).
6. Grace notes (duration 0) are dropped.

## MIDI output

- Format 1, 480 ticks per beat. Track 0: tempo + time signature meta.
  Track 1 "Right Hand" channel 0. Track 2 "Left Hand" channel 1.
- Velocity 80. Note-off before note-on at equal ticks. Minimum duration 1 tick.

## Engine interface (`synthy/engine/base.py`)

```python
class Engine(Protocol):
    name: str
    def transcribe(self, pages: list[Path], workdir: Path) -> list[Path | None]:
        """One MusicXML path per input page, None where the engine produced nothing."""
```

Audiveris engine: binary from `SYNTHY_AUDIVERIS` env or
`~/.local/opt/audiveris/bin/Audiveris`; sets `TESSDATA_PREFIX` to
`~/.local/share/AudiverisLtd/audiveris/tessdata` unless already set; one
batch invocation for all pages: `-batch -transcribe -export -output <dir> pages...`.
Output `.mxl` matched to input pages by stem.

## Web app (`synthy/web/`)

FastAPI. Endpoints:

- `GET /` static page: file input, tempo, optional page range, submit.
- `POST /jobs` multipart (file, tempo, pages) -> `{id}`; runs the pipeline
  in a background thread.
- `GET /jobs/{id}` -> `{status: queued|running|done|error, stage, message,
  pages_done, pages_total, report}`; report includes suspect measures.
- `GET /jobs/{id}/midi` -> the file as `<stem>.mid`.

Jobs live under `~/.cache/synthy/jobs/<id>/` and in a process-local dict.

## CLI

`synthy convert INPUT [-o OUT.mid] [--tempo 80] [--pages 1-3,5]` for
scripting and for the integration test.

## Testing

- Unit tests build MusicXML with music21 in `tmp_path`; no engine needed.
- `tests/test_integration.py` runs the real Audiveris on page 1 of the
  Bortkiewicz PDF when the binary and PDF exist; skipped otherwise.

## Out of scope for v1

Manual correction UI, in-page playback, SMT engine, pedal, dynamics.
