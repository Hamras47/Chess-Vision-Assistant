# Chess Vision User Guide

## Chess Vision 2.47

Use **Left Arrow** to undo and **Right Arrow** to redo. The actual chess position, turn, castling rights and en-passant state are restored. A new move after undo clears the redo branch. Arrow keys keep their normal behavior in text fields, dropdowns and modal dialogs. Ctrl+Z/Ctrl+Y remain available.

The evaluation bar sits beside the board. Positive values favor White and negative values favor Black, even when you play Black or flip the board. `M3` means White mates in three; `-M2` means Black mates in two. The smooth bounded bar is an advantage indicator, not a predicted win percentage.

In **Settings → AI Recognition**, choose **GPT-5.6 Terra** or **GPT-5.6 Luna**. Terra is the default for new configurations and balances intelligence and cost; Luna is the lighter, lower-cost option. Existing explicit Luna choices remain saved. Your chosen model is used for the next scan. API project permissions determine availability.

In **Settings → Chess Engine**, turn **Stockfish Suggestions** off to stop automatic analysis. Best moves show Off, arrows disappear, and the bar dims to neutral. Manual moves, undo/redo, and scans still work. Turning it on analyzes the current position.

Scanning validates the image before sending it. A blank or invalid screenshot gets one local recapture after the overlay closes; failed AI recognition asks you to Rescan and does not automatically repeat API requests.

## Installation and first launch

When available on the project's release page, download the **complete Windows distribution ZIP** and extract it. Open the extracted `ChessVision` folder and double-click `ChessVision.exe`. Keep its `_internal` folder and license files beside it; the EXE alone is not a standalone application. If no binary release is listed, follow the README's build instructions. Chess Vision opens with a normal starting position; manual play works without an OpenAI key or Stockfish.

![Main window](screenshots/01-main-window.png)

## Add your OpenAI API key

Open **Settings**, paste your own OpenAI API key, and select **Save**. The key is stored by the operating system's credential service—not in a project file or QSettings. **Show** reveals only text entered in the current session; an existing key remains represented by a masked placeholder. Select **Test Connection** for a non-blocking credential check.

![Settings](screenshots/05-settings.png)

If scanning says that a key is required, choose **Open Settings**. Invalid credentials, timeouts, and network failures are shown without echoing the key.

## Install Stockfish

Stockfish is the independent, open-source engine used for local analysis. Download it from [the official Stockfish website](https://stockfishchess.org/download/), extract the archive, then open **Settings** in Chess Vision. Select **Browse**, choose `stockfish.exe`, and select **Test Engine**. A successful check displays “Engine detected.” Stockfish is licensed under GPLv3 and is developed by the Stockfish community; it is not a 47 Lab product and is not bundled with Chess Vision.

## Scan and confirm a position

1. Put a chessboard on screen and select **Scan Board**.
2. Drag a square selection around all 64 squares. Only this selected image is sent to the configured OpenAI API.
3. Confirm whether you play White or Black and whose turn it is.
4. For a midgame position, enable only castling rights that still exist in the game.

![Board selection](screenshots/02-scan-board.png)

![Position confirmation](screenshots/03-confirm-position.png)

Exact starting positions automatically receive normal castling rights. For midgame scans, Chess Vision cannot infer move history from a still image. Castling is available only when both the king and corresponding rook are on their starting squares and you explicitly confirm that right. En-passant history also cannot be reconstructed from a still image, so imported positions start without an en-passant target.

## Manual analysis

After import, move pieces for both sides by clicking a source and destination or dragging. Illegal moves are rejected. The best-move arrow and evaluation come from local Stockfish. Promotions ask you to choose queen, rook, bishop, or knight. Castling and en passant work whenever the canonical position contains the required rights.

![Analysis](screenshots/04-analysis.png)

**Flip** changes orientation without changing the position. **New Game** creates a starting board. **Rescan** replaces the current position and clears its undo/redo history. Keyboard shortcuts include `F` to flip, `Ctrl+Z`/`Ctrl+Y` for undo/redo, `Ctrl+R` to rescan, and `Ctrl+N` for a new game.

![Split-screen companion layout](screenshots/06-split-screen.png)

## Troubleshooting and privacy

- **No best move:** configure and test Stockfish; manual moves still work without it.
- **Could not verify board:** select the board edges tightly, avoid overlays, and retry.
- **Wrong side or orientation:** use Rescan for metadata changes or Flip for display only.
- **Connection error:** verify internet access and test the key in Settings.

Scan Board sends the selected board screenshot to OpenAI for recognition. Normal manual moves are not continuously sent to OpenAI. Stockfish analysis runs locally. Chess Vision ships with no shared API key; credentials belong to each user and are stored with the OS credential service.
