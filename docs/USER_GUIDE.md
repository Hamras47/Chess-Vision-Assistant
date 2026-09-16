# Chess Vision User Guide

## Chess Vision 3.5

### Choose a game

Open **New Game** and select **Analysis**, **Player vs Player**, or **Player vs Computer**.

- Analysis preserves the unrestricted manual board and one-time AI scan/rescan workflow. There are no clocks or forced names.
- PvP asks for White and Black names (blank defaults to White/Black).
- PvC asks for your name (blank defaults to Player), color, and approximate 600–2800 difficulty. The opponent is **ChessAI**. Random resolves once; your side is placed at the bottom. Playing Black automatically starts ChessAI's White move.

In PvP/PvC, choose exactly **1, 5, 10, or 20 minutes** per side, with no increment. Independently enable evaluation, best-move suggestions, and undo/redo. Evaluation and suggestions remain full strength regardless of opponent difficulty.

![New Game setup](screenshots/new-game.png)

### Difficulty, clocks, and captures

The difficulty is an approximate playing-strength target, not a Chess.com/FIDE rating. Below Stockfish's native Elo range, the app selects among engine-evaluated candidate moves using bounded score-loss preferences; higher settings use native limiting. ChessAI has a small variable presentation delay, overlapping calculation time rather than adding to it.

Only the active side loses time, including ChessAI's thinking/presentation time. A flag fall loses unless python-chess determines that the opponent lacks sufficient mating material. Clocks pause in New Game setup and stop at game end. Undo/redo does not refund or restore time.

Player bars follow board orientation. Icons show pieces **captured by** the named player, including en passant and promotion captures. Undo removes a capture and redo restores it.

Analysis shows captured pieces too, but no clocks. Only captures recorded after the current starting/imported position are shown; a scan cannot reconstruct prior capture history. Click **Built by 47 Lab** to open https://fortysevenlab.com in your browser.

![Player vs Computer](screenshots/pvc.png)

![Player vs Player](screenshots/pvp.png)

### History and analysis controls

Use **Left Arrow** to undo and **Right Arrow** to redo, or Ctrl+Z/Ctrl+Y. Analysis/PvP navigate one ply; PvC normally restores a complete human/computer pair using the exact recorded moves, not a new engine reply. The per-game history switch can disable navigation. If an incomplete turn is redone to ChessAI's turn, history pauses without recomputing a reply; redo further if available or start a new game. Position, turn, castling and en-passant rights are restored, but elapsed clock time is not. A new move clears the redo branch. Arrow keys retain normal behavior in text fields, dropdowns and dialogs.

The evaluation bar sits beside the board. Positive values favor White and negative values favor Black, even when you play Black or flip the board. `M3` means White mates in three; `-M2` means Black mates in two. The smooth bounded bar is an advantage indicator, not a predicted win percentage.

In **Settings → AI Recognition**, choose **GPT-5.6 Terra** or **GPT-5.6 Luna**. Terra is the default for new configurations and balances intelligence and cost; Luna is the lighter, lower-cost option. Existing explicit Luna choices remain saved. Your chosen model is used for the next scan. API project permissions determine availability.

In Analysis mode, **Settings → Chess Engine → Stockfish Suggestions** controls automatic analysis. Off removes arrows and dims the bar; manual moves and scanning still work. PvP/PvC use the learning-tool switches in New Game instead.

Scanning validates the image before sending it. A blank or invalid screenshot gets one local recapture after the overlay closes; failed AI recognition asks you to Rescan and does not automatically repeat API requests.

## Installation and first launch

When available on the project's release page, download the **complete Windows distribution ZIP** and extract it. Open the extracted `ChessVision` folder and double-click `ChessVision.exe`. Keep its `_internal` folder and license files beside it; the EXE alone is not a standalone application. If no binary release is listed, follow the README's build instructions. Chess Vision opens with a normal starting position; manual play works without an OpenAI key or Stockfish.

![Main window](screenshots/analysis.png)

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

![Analysis](screenshots/analysis.png)

**Flip** changes orientation without changing the position. **New Game** creates a starting board. **Rescan** replaces the current position and clears its undo/redo history. Keyboard shortcuts include `F` to flip, `Ctrl+Z`/`Ctrl+Y` for undo/redo, `Ctrl+R` to rescan, and `Ctrl+N` for a new game.

![Split-screen companion layout](screenshots/06-split-screen.png)

## Troubleshooting and privacy

- **No best move:** configure and test Stockfish; manual moves still work without it.
- **Could not verify board:** select the board edges tightly, avoid overlays, and retry.
- **Wrong side or orientation:** use Rescan for metadata changes or Flip for display only.
- **Connection error:** verify internet access and test the key in Settings.

Scan Board sends the selected board screenshot to OpenAI for recognition. Normal manual moves are not continuously sent to OpenAI. Stockfish analysis runs locally. Chess Vision ships with no shared API key; credentials belong to each user and are stored with the OS credential service.
