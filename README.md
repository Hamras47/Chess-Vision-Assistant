# Chess Vision Assistant V1.6

V1.6 is a manual chess analysis board with one-time OpenAI position import. The internal `python-chess` board is authoritative: the user enters moves for both sides, legality is enforced locally, and Stockfish analyzes whichever side is to move.

There is no live browser monitoring, automatic move detection, background capture, recovery state machine, or ML runtime.

## Install and run

```powershell
python -m pip install -e ".[dev]"
python -m app.main
```

Add `OPENAI_API_KEY` to `.env` to enable Scan Board. The configured OpenAI model takes precedence, then `OPENAI_VISION_MODEL`, then the default `gpt-5.6-luna`. Configure a Stockfish executable in Settings to enable asynchronous MultiPV analysis.

## Workflow

1. Start from the normal initial board or click **Scan Board**.
2. For a scan, select the board once and confirm player color and whose turn it is.
3. Click-click or drag-drop a legal move for the side to move.
4. Review Stockfish's top move, two alternatives, evaluation, arrow, and SAN history.
5. Use Undo/Redo for corrections, Rescan for a fresh import, or New Game for the starting position.

Imported midgame positions default to no castling or en-passant rights. During confirmation, the user may explicitly enable castling rights only where the king and matching rook occupy their starting squares. A recognized exact starting layout receives normal starting-position castling rights automatically.
