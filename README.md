# Chess Vision Assistant

A local Windows chess analysis and training tool. It provides a responsive PySide6 interactive board, python-chess legal-state handling, optional local Stockfish analysis, and a modular pixel-capture/vision pipeline. It never clicks, controls, injects into, or reads a chess website.

## Install and run (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app.main
```

Edit `.env` and set `OPENAI_API_KEY` before using **Scan Board**. `OPENAI_VISION_MODEL` is optional and defaults to `gpt-5`; change it in `.env` to any vision-capable model your account can use. The key is never stored in QSettings or source control.

Stockfish is detected from saved and common local paths. If it is missing, use the gear button to locate `stockfish.exe`. Run tests with `pytest`.

## Live capture workflow

1. Click **Scan Board**. The app hides, captures the virtual desktop, and displays that frozen screenshot as a snipping surface.
2. Drag around the visible chessboard. The loose selection is corrected to a square 8×8 crop and only that crop is sent to OpenAI.
3. The structured piece list is validated, converted to one canonical `python-chess` board, displayed, and analyzed by Stockfish.
4. Tracking starts automatically. A background worker captures only the corrected board region every 300 ms. Edge-weighted square differences suppress flat highlight changes; stable changed squares are matched against legal moves. Routine moves do not call OpenAI.
5. If inference is ambiguous, the app attempts an AI recovery scan at most twice and at least five seconds apart. Persistent failure stops tracking and presents **Rescan**.

## Current capabilities

The compact interface exposes Scan/Rescan, the synchronized board, current status, best move, evaluation, alternatives, and one settings gear. OpenAI recognition, local tracking, and Stockfish all feed from the same `python-chess` board.

## Architecture

`app/chess/` owns reconstruction, coordinates, and legal move matching; `app/ai/` performs structured visual transcription; `app/engine.py` runs Stockfish asynchronously; `app/vision/` owns frozen-desktop capture, crop correction, edge-weighted change detection, stabilization, and the tracking worker.

## Roadmap / limitation

A single screenshot cannot establish historical castling rights or an en-passant target. Arbitrary midgame scans therefore use conservative rights. Promotion choice may require AI recovery because all promotion moves affect the same two visual squares. Real-world recognition quality depends on the selected model and a clean board crop.

## AI recognition diagnostics

Set `CHESS_VISION_DEBUG=1` before launching. A scan then saves the exact uploaded PNG to `debug/ai_input.png`, the parsed response to `debug/ai_result.json`, the immediate physical recapture to `debug/post_selection_capture.png`, and the frozen selection to `debug/selected_frozen.png`. The log records request status, configured model, dimensions, raw structured data, piece count, FEN placement, `python-chess` status, and the exact failed stage.

Repeat the same recognition pipeline without the GUI:

```powershell
python -m app.ai.debug_scan debug/ai_input.png
```
