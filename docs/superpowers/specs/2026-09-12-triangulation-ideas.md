# Triangulation: correcting OMR with recordings and score videos

Date: 2026-09-12. Ideas only, nothing implemented yet. Follows the v1
player work of the same day.

## Problem

Audiveris gets pitches mostly right on dense Romantic scores but drifts
on rhythm. Normalization snaps each measure to its time signature and
flags outliers, but inside a flagged measure the note onsets are still
guesses (230 of 553 measures flagged on the Bortkiewicz Sonata No. 2).

## Idea 1: audio recordings

Use a performance recording as a second witness. Each source is good at
what the other is bad at: OMR gives structure (measures, hands, which
note is which) but drifts on rhythm; a recording gives timing and pitch
but no structure.

1. Transcribe the recording to notes-in-seconds with a piano
   transcription model. Candidate: ByteDance
   `piano_transcription_inference` (CRNN, 172 MB checkpoint from Zenodo
   record 4034264, note F1 0.968 on MAESTRO, needs PyTorch, runs on MPS).
   Lighter but weaker alternative: Spotify Basic Pitch.
2. DTW-align the OMR pitch sequence against the transcription
   (symbolic to symbolic; robust to rubato).
3. Where the alignment cost is low, anchor measure boundaries to
   seconds. Inside an anchored measure, replace OMR onsets with the
   recording's onsets rescaled to the measure and quantized to a simple
   grid. Add notes OMR missed and drop ones it hallucinated; keep OMR's
   hand assignment by pitch proximity.
4. Regions with high alignment cost stay flagged, same UI as today.

Trust the recording only for onsets (pedal blurs offsets) and only
inside low-cost regions (performers skip repeats, cut, play wrong
notes). The user supplies an audio file; the tool does not fetch from
YouTube.

Spike to run first: transcribe one recording, align against the current
3-page output, count how many of the 23 flagged measures it resolves.

## Idea 2: score videos

Many YouTube "score videos" show the sheet music page while the audio
plays, and the uploader has already synchronized them. That gives a
per-frame mapping from page position to audio time, which the
audio-only plan lacks.

- We already render each PDF page to PNG for Audiveris. Downscale those
  and each video frame to small grayscale thumbnails and match; a scan
  and a re-typeset edition of the same passage still share the same
  system layout (where staves and barlines fall), so crude matching
  finds which page is on screen.
- Many such videos draw a moving cursor or highlight over the current
  measure. Detecting its x-position within the system yields a
  measure-level timestamp directly, with no audio transcription needed
  for the alignment step.
- With measures anchored that way, the recording only has to repair
  rhythm inside known measures, which is the easy half of Idea 1.

Caveats: many videos are re-typeset (MuseScore style) rather than IMSLP
scans, so frame matching must tolerate layout differences; accept a
downloaded video file rather than a URL.
