# Licensing review

Chess Vision Assistant is released under GNU GPL version 3 or, at your option, any later version. Copyright 2026 47 Lab and contributors. See the complete text in the root `LICENSE`.

The project license is compatible with the runtime's `python-chess` dependency, which is GPL-3.0-or-later.

Important components:

- `python-chess`: GPL-3.0-or-later.
- PySide6 / Qt for Python: LGPLv3/GPLv3/commercial options; a frozen build must preserve applicable Qt notices and LGPL relinking/replacement rights.
- Cburnett chess piece SVGs: CC BY-SA 3.0; attribution and share-alike terms apply to adaptations in `assets/pieces`.
- Stockfish: GPLv3. Chess Vision does not bundle it; users select a separately downloaded executable.
- Generated Chess Vision icon: generated specifically for this project; no third-party logo was incorporated.

Redistributed binaries must include the license and notices and provide the complete corresponding source for that exact version, including build scripts. The build script collects installed dependency license texts. Qt DLLs remain replaceable in `_internal`; modifications and reverse engineering for debugging those modifications are permitted under the applicable license. Stockfish remains a separate user download.
