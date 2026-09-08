# Architecture

Chess Vision 1.6 deliberately separates probabilistic visual import from deterministic chess state.

```mermaid
flowchart LR
    A[One-time screen capture] --> B[OpenAI vision recognition]
    B --> C[Structured board reconstruction]
    C --> D[python-chess canonical state]
    D --> E[Manual legal move interaction]
    E --> D
    D --> F[Local Stockfish analysis]
    F --> G[Best move and evaluation UI]
```

## Authority and data flow

`ManualGameState` and its `python-chess.Board` are authoritative after a position is accepted. OpenAI is used only for Scan Board and Rescan. It reconstructs piece placement; the confirmation dialog supplies player color, side to move, and valid castling rights. Subsequent moves are entered by the user and checked locally by `python-chess`. Stockfish receives FEN positions through a long-lived background worker and returns MultiPV analysis.

The capture layer takes a frozen desktop snapshot and converts logical Qt coordinates to physical monitor coordinates for DPI-safe cropping. `OpenAIClient` sends only the selected board image. The responsive Qt view renders from canonical state and never changes chess rules.

## Configuration and security

The OpenAI key is resolved from the OS credential store first, then `OPENAI_API_KEY`. On Windows, the `keyring` backend uses Windows Credential Manager. QSettings stores only non-secret preferences: model, analysis duration, debug mode, and Stockfish path. Stockfish is an external UCI executable and is not included in the application build.

Packaged resources are located through `app.core.resources`, which supports source checkouts and PyInstaller's frozen resource directory.
