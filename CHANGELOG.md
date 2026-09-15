# Changelog and Development Journey

## 2.5 — Game modes

### Added
- Analysis, local Player vs Player, and Player vs Computer modes.
- Native Stockfish opponent Elo, bounded by the installed engine's supported range.
- Per-game evaluation, full-strength suggestions, and undo/redo options.
- Exact turn-pair undo/redo in computer games and natural, non-blocking computer timing.

### Improved
- Compact New Game setup with live Elo controls and restrained visual polish.

## 2.47

### Added
- Left/Right keyboard move navigation using canonical chess history.
- Animated vertical evaluation bar with consistent White perspective.
- Saved Terra/Luna recognition selector; Terra default for new configurations.
- Persistent Stockfish Suggestions toggle.

### Improved
- Screenshot validation and one local recapture after invalid images; one AI request per scan.
- Refined compact styling, Settings groups and secondary evaluation typography.
- Rapid move/undo animation cleanup and stale engine-result protection.

### Windows
- Suppress Stockfish console windows for analysis and engine testing.
- Updated ONEDIR application metadata to Chess Vision 2.47.

## 1.6.0 — Stable architecture

- Prioritized reliable, predictable analysis over experimental live tracking.
- Uses AI visual recognition only for initialization and rescan.
- Uses deterministic `python-chess` state, manual legal moves, and local Stockfish analysis.
- Added responsive split-screen layout, castling confirmation, secure per-user credentials, Windows packaging, and release documentation.

## Early prototype

- Explored DPI-aware screen capture, board reconstruction, visualization, and initial Stockfish integration.
- Established legal position handling and move analysis.

## Computer vision and ML exploration

- Built a MobileNetV3-Small square classifier with 13 classes, generated datasets, confidence scoring, ONNX export, and local inference experiments.
- Controlled validation/test results were strong where recorded in the research project, but did not imply equivalent accuracy across real websites, themes, scaling, or overlays.

## Hybrid tracking research

- Evaluated local ML recognition, OpenAI vision, change detection, legal-move inference, stabilization, synchronization states, and confidence-aware recovery.
- These experiments informed the product but are not production features in 1.6.

## Future research

- Automatic live tracking and faster synchronization.
- Stronger real-world, multi-theme Chess.com/Lichess datasets.
- Hybrid local and AI verification with confidence-aware recovery.

Future items are exploratory and are not present in the stable release.
