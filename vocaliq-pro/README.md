# VocalIQ Pro — AI Singing Evaluation System

A full-stack Flask project with a distinctive responsive UI, account authentication, private score history, audio analysis, interactive graphs, and downloadable PDF reports.

## Features
- User registration, password hashing, login/logout, session-protected dashboard and per-user data separation.
- Upload audio or record from the browser microphone.
- Pitch contour / pitch stability estimate using Librosa YIN.
- Tempo estimate, audio-derived rhythm consistency estimate, duration and median detected pitch.
- Optional lyrics similarity when reference lyrics and Whisper transcription are available.
- Per-user evaluation history, score trend graph, result page, and PDF report download.
- Temporary uploaded audio is removed after analysis; persistent records store scores and transcript, not the source audio.
- Responsive editorial-style UI with dark ink, violet, peach and mint design system.

## Requirements
- Python 3.10–3.12 recommended.
- FFmpeg is recommended for Whisper support. Whisper is optional at runtime: if unavailable, pitch/rhythm analysis still runs and lyric similarity is skipped.
- Audio dependencies such as NumPy/Librosa may need build tools on some Windows/Python combinations. Python 3.11 is a safe choice for many environments.

## Windows / VS Code setup
1. Extract the ZIP and open `vocaliq-pro` in VS Code.
2. In the terminal:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Install FFmpeg and ensure `ffmpeg` is on PATH if you want Whisper transcription. Whisper downloads its selected model on first use; set `WHISPER_MODEL=base` for a more accurate but slower model. Default is `tiny`.
4. Start the app:
   ```powershell
   python app.py
   ```
5. Visit http://127.0.0.1:5000 and create an account.

If PowerShell blocks activation, use Command Prompt and run `.venv\Scripts\activate.bat` instead.

## Scoring caveat — read this
- Pitch score currently measures pitch stability from estimated notes; it is **not** exact note-by-note melody matching against an original reference song.
- Rhythm score is a heuristic based on onset-strength variation, not a trained rhythm classifier or precise singer-vs-reference alignment.
- Lyrics similarity uses Whisper's recognized transcript and a token-sequence similarity score. Whisper may not accurately transcribe singing, accompaniment, or noisy audio.
- These are practice-oriented estimates, not professional vocal judgments. For genuine reference-song evaluation, add a reference audio file and align pitch sequences with chroma / DTW, plus onset alignment.

## Security / deployment notes
- Change `SECRET_KEY` to a long random secret before deployment. Example PowerShell: `$env:SECRET_KEY='your-long-random-secret'`.
- The development server is for local use, not production. Use HTTPS, secure cookies, CSRF protection, rate limiting, upload scanning, and a production WSGI server before public deployment.
- SQLite database `vocaliq.db` is created automatically at first run. Keep it backed up if you need your history.
- Uploaded clips are capped at 25 MB and 3 minutes; temporary audio files are deleted after processing.


## Reference melody comparison (new)

On the Singing Studio page, optionally upload the original song/instrumental in **Reference song audio** along with your own singing take. VocalIQ extracts pitch contours from both files and uses dynamic time warping (DTW) to align them despite timing differences. The approximate melody-match score is shown on the result page, and the reference contour is overlaid on the pitch chart.

**Accuracy caveat:** this is an educational prototype. A mixed song contains vocals and instruments, so pitch extraction can follow accompaniment instead of the lead singer. For stronger results, use an instrumental/reference vocal stem, similar song sections, and relatively clean audio. This compares contours approximately; it is not professional source separation or a validated singing assessment. Existing SQLite databases are migrated automatically on startup.
