# Chess Vision Assistant

Chess Vision is a Windows desktop chess companion for analysis, local two-player games, and play against Stockfish. Capture a position once with AI in Analysis mode, or start a timed game with player names and captured-piece displays.

![Chess Vision 3.5 analysis](docs/screenshots/analysis.png)

> Chess Vision 3.5 adds game clocks, player bars, smooth movement, and approximate 600–2800 ChessAI difficulty. No Python installation is needed for the Windows download.

## Overview

The `python-chess` board is the source of truth. OpenAI vision reconstructs a selected image only during Scan Board or Rescan in Analysis mode. Stockfish runs locally for analysis and computer moves. There is no continuous screen tracking.

## Features

- Analysis, local Player vs Player, and Player vs Computer modes
- Approximate 600–2800 ChessAI strength; White, Black, or Random human color
- 1 / 5 / 10 / 20-minute clocks, no increment, with timeout adjudication
- Player names and captured-piece SVGs beside the correctly oriented player
- Smooth piece motion, synchronized castling, and natural computer thinking time
- Per-game evaluation, full-strength suggestions, and undo/redo options
- DPI-aware one-time capture and OpenAI reconstruction
- Player, turn, and midgame castling confirmation
- Legal click/drag moves, promotion, castling, en passant, undo/redo
- Local asynchronous Stockfish best move, evaluation, and arrow
- Left/Right arrow-key undo/redo with exact chess-state restoration
- Animated White-perspective evaluation bar beside the board
- Terra/Luna recognition selection and a persistent Stockfish Suggestions toggle
- Responsive wide and split-screen layouts with board flipping
- Windows Credential Manager storage for each user's API key
- No bundled API key, Stockfish binary, ML runtime, or browser tracking

## Screenshots

| New Game | Player vs Computer | Player vs Player |
|---|---|---|
| ![New Game](docs/screenshots/new-game.png) | ![ChessAI game](docs/screenshots/pvc.png) | ![Local game](docs/screenshots/pvp.png) |

See the [user guide](docs/USER_GUIDE.md) for setup and controls.

## Quick start and game modes

Choose **New Game**:

- **Analysis:** move both colors freely, scan/rescan positions, and use your saved Stockfish Suggestions preference. No clocks or required names.
- **Player vs Player:** enter White/Black names, choose a time control, and move each side locally.
- **Player vs Computer:** enter your name, choose White/Black/Random, difficulty and time. ChessAI makes the other side's moves automatically; choosing Black starts its White opening.

PvP/PvC offer separate **Evaluation Bar**, **Best Move Suggestions**, and **Allow Undo / Redo** switches. Learning tools always use full-strength analysis, independent of opponent difficulty. Captured icons show pieces captured **by** that player.

Analysis also shows captures made in the current move history, without clocks. Captures before a scanned position cannot be inferred. **Built by 47 Lab** opens [fortysevenlab.com](https://fortysevenlab.com) in your browser.

Computer difficulty is an **approximate playing-strength target**, not a Chess.com or FIDE rating. Below the installed engine's native Elo range, controlled selection among evaluated Stockfish candidates creates weaker play; higher settings use native Elo limiting. The UI shows your requested difficulty.

Only the side to move loses time. ChessAI's presentation delay counts against its clock. Clocks stop at game end and pause while New Game setup is open. Undo/redo changes the board only: spent time is not restored. A flag fall loses unless the opponent has insufficient mating material according to python-chess.

## How It Works

1. Select **Scan Board** and capture all 64 squares.
2. The selected image is sent to the configured OpenAI API.
3. Confirm player color, turn, and valid castling rights.
4. Enter moves manually for both sides; `python-chess` enforces rules.
5. Stockfish evaluates the canonical position locally. Use **Rescan** for a new import.

See [Architecture](docs/ARCHITECTURE.md) for the real component flow.

## Download for Windows

Go to [Chess Vision 3.5](https://github.com/Hamras47/Chess-Vision-Assistant/releases/tag/v3.5) and download `ChessVision-Windows-x64.zip`.

Extract the ZIP, open the `ChessVision` folder, and run `ChessVision.exe`. No Python installation or command prompt is required. In **Settings**, add your own OpenAI API key for board scanning and select your separately installed Stockfish executable for analysis.

### Windows App

Download and extract the **complete distribution ZIP**, then double-click `ChessVision.exe` inside the extracted `ChessVision` folder. Keep `_internal`, licenses, and the executable together; copying only the EXE will not work. It opens without a command prompt. Manual board/PvP play needs no API key or engine. PvC requires Stockfish. The unsigned build may trigger Windows SmartScreen.

### OpenAI Setup

Open **Settings**, enter your own key, select **Test Connection**, then **Save**. Saved credentials use Windows Credential Manager through `keyring`. Precedence is secure credential store, `OPENAI_API_KEY`, then no key. No developer key is included. Without a key, Scan Board directs you to Settings rather than crashing.

### Stockfish Setup

Stockfish is an independent open-source UCI engine. Download Windows Stockfish from the [official download page](https://stockfishchess.org/download/), extract it, then choose `stockfish.exe` with **Settings → Browse → Test Engine**. Analysis remains local. Stockfish is GPLv3 and is not bundled.

## User Guide

The [full user guide](docs/USER_GUIDE.md) covers installation, first launch, scanning, confirmation, manual moves, playing Black, castling, en passant, promotion, flip, rescanning, settings, and troubleshooting.

## Midgame Scanning

A still image cannot prove move history. Midgame imports therefore start without en-passant state and without castling rights unless explicitly confirmed.

## Castling

The confirmation dialog offers rights only when the king and matching rook occupy starting squares. Exact starting layouts receive normal rights automatically.

## En Passant

Imported images have no inferred en-passant target. During subsequent manual play, `python-chess` handles en passant normally.

## Promotion

Moving a pawn to the final rank opens a queen, rook, bishop, or knight chooser.

## Board Orientation / Flip

Confirmed player color sets initial orientation. **Flip** or `F` rotates display only.

## Rescanning

**Rescan** performs another one-time visual import and replaces current position/history after confirmation.

## Settings

Settings groups AI recognition, the chess engine, and application information. Select **GPT-5.6 Terra** (default) or **GPT-5.6 Luna**. Terra balances intelligence and cost; Luna is the lighter, lower-cost option. The saved model takes precedence over `OPENAI_VISION_MODEL`, then the Terra default. Unsupported saved values fall back to the environment/default. Exact API IDs: `gpt-5.6-terra`, `gpt-5.6-luna` ([official model catalog](https://developers.openai.com/api/docs/models)). Account access still depends on your API project.

In Analysis mode, **Stockfish Suggestions** defaults to On. Off stops automatic analysis and hides arrows, with a neutral dimmed evaluation bar. PvP/PvC use their independent New Game learning-tool options. API keys stay in the OS credential store; they are never written to QSettings or packaged files.

## Keyboard navigation and evaluation

**Left Arrow / Ctrl+Z** undo; **Right Arrow / Ctrl+Y** redo. Analysis/PvP navigate one ply; PvC normally navigates a human/computer turn pair and restores the exact saved reply. **Allow Undo / Redo** can disable navigation in a game. After undoing an incomplete computer turn, history may pause at ChessAI's turn; use redo when available or start a new game. Navigation restores turn, castling and en-passant state, not elapsed clock time. A new move clears incompatible redo history. Text fields, dropdowns and dialogs retain normal arrow behavior. **F** flips, **Ctrl+N** opens New Game, and **Ctrl+R** scans in Analysis mode.

The vertical bar grows White's region for positive evaluation and Black's for negative evaluation. Flipping the board moves the regions to match the displayed sides without changing the score. `M3` means White has mate in three; `-M2` means Black has mate in two. Finite scores use a bounded curve, not a win-probability estimate.

## Building From Source

Use 64-bit Windows and Python 3.11–3.14 (release build tested with Python 3.14):

```powershell
git clone <repository-url>
cd chess-vision
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m app.main
```

Verify and build:

```powershell
python -m compileall app
pytest -v
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The maintained [PyInstaller specification](ChessVision.spec) creates `dist/ChessVision/ChessVision.exe`, includes UI assets, and excludes unused ML stacks. The adjacent `_internal` directory is part of the application and must be distributed with the executable.

## Privacy & Security

Only the board image explicitly selected during Scan Board/Rescan is sent to OpenAI. Manual moves are not continuously streamed. Stockfish runs locally. Users own their credentials; Chess Vision ships without a shared 47 Lab key.

## Troubleshooting

- **API key required:** save and test a key in Settings.
- **Network unavailable/timeout:** check connectivity and retry.
- **Stockfish not configured:** browse to and test `stockfish.exe`.
- **Recognition fails:** tightly select all squares without overlays.
- **No castling:** confirm the pieces and castling right during import.

## Development Journey

[CHANGELOG.md](CHANGELOG.md) records the progression from capture prototypes through ML and hybrid-tracking research to the stable architecture.

## Roadmap

Possible research includes live tracking, stronger real-world multi-theme recognition, hybrid verification, and confidence-aware recovery. These are not current features.

## Contributing

Open an issue before large architectural changes. Preserve deterministic canonical state, add tests, run `pytest -v`, and never commit credentials or private captures.

## License

Chess Vision Assistant is licensed under [GNU GPL version 3 or later](LICENSE). Third-party software and artwork retain their own licenses; see [licensing details](docs/LICENSING.md) and [notices](THIRD_PARTY_NOTICES.md).

## Credits

- [Stockfish](https://stockfishchess.org/) community — engine, GPLv3 (not bundled)
- [python-chess](https://python-chess.readthedocs.io/) — rules/UCI, GPL-3.0-or-later
- Qt for Python / PySide6 — UI, LGPLv3/GPLv3/commercial
- Cburnett pieces — CC BY-SA 3.0, adapted palette; see `assets/pieces/README.md`

## Built by 47 Lab

Chess Vision is built by 47 Lab with restrained in-app attribution.
