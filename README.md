# Speeches Helper

A desktop application built with PySide6 to practice speeches against visible and blind timers, record audio, transcribe with local `faster-whisper`, generate delivery and comic timing reports, and compare past sessions side by side.

## Key Features

1. **Dual Rehearsal Timers**:
   - **Global Speech Timer**: Counts up from speech start. Can be toggled visible or hidden (displays `••:••` for blind practice).
   - **Virtual Phone Timer**: Simulates a smartphone countdown timer (default 3:00, customizable). Rings a continuous alarm when it hits zero until silenced.
   - **Blind Peeking**: Hold `1` to temporarily peek the global timer; hold `2` to peek the phone timer.

2. **Hands-Free Keyboard Shortcuts**:
   - `Space` / `Enter`: Begin or Stop speech recording.
   - `T`: Start the virtual phone timer.
   - `S`: Silence the phone alarm chime.
   - Hold `1`: Peek global timer.
   - Hold `2`: Peek phone timer.

3. **Fail-Safe Session Logging**:
   - The moment you stop recording, both the `.mp3` audio and the session metadata `.json` are written immediately to `./sessions` before transcription begins.
   - Even if transcription is interrupted, your audio and timing logs are never lost.

4. **Speech Profiling & Comic Timing Analysis**:
   - Automatic silence and pause detection (default 1.5s threshold for audience response, laughs, and dramatic pauses).
   - Effective speech duration calculated up to the last spoken word.
   - Segment-by-segment timeline with word counts, speaking pace (WPM), and pause badges.
   - Interactive audio player with scrubber, volume control, and click-to-seek directly from any speech block or pause.

5. **Side-by-Side Comparison**:
   - Pick any two past sessions to compare duration, word count, speaking pace, and pause frequency.
   - Dual-column text view with fuzzy similarity matching:
     - **Soft Green**: Similar phrasing (>= 65% match).
     - **Neutral**: Modified phrasing (35% - 65% match).
     - **Soft Red**: Divergent or new delivery (<= 35% match).

6. **Whisper Model Flexibility**:
   - Default model: `medium.en`.
   - Selector includes `small.en`, `medium.en`, `large-v3`, and `base.en`.
   - Also accepts typing any arbitrary HuggingFace or faster-whisper model identifier.

## Setup & Running

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python src/main.py
   ```

3. Run the automated tests:
   ```bash
   python -m unittest discover tests
   ```
