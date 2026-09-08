# Third-party notices

Chess Vision 1.6 uses the following third-party software and artwork. This summary does not replace the applicable license texts.

- **python-chess**, copyright Niklas Fiekas and contributors — GNU General Public License version 3 or later: <https://github.com/niklasf/python-chess>
- **Qt for Python / PySide6**, The Qt Company and contributors — GNU Lesser General Public License version 3, GNU GPLv3, or commercial terms: <https://doc.qt.io/qtforpython-6/licenses.html>
- **Cburnett chess pieces**, Colin M. L. Burnett — Creative Commons Attribution-ShareAlike 3.0 Unported. The local SVGs adapt fill/outline colors: <https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces>
- **OpenCV**, OpenCV team/contributors — Apache License 2.0: <https://opencv.org/license/>
- **MSS**, Pierre M. and contributors — MIT License: <https://github.com/BoboTiG/python-mss>
- **OpenAI Python library**, OpenAI — Apache License 2.0: <https://github.com/openai/openai-python>
- **keyring**, Python Packaging Authority contributors — MIT License: <https://github.com/jaraco/keyring>

Stockfish is supported as a separately installed user-selected program and is **not bundled**. Stockfish is developed by its independent community under GNU GPLv3: <https://stockfishchess.org/>.

The Windows distribution keeps Qt libraries as separate files in `_internal` rather than statically linking them. The build includes the project `LICENSE`, this notice, and dependency license texts in `licenses/`. Redistributors must also supply corresponding source for the distributed version. Piece artwork retains its attribution and CC BY-SA terms.
