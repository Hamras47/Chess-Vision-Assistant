# Chess Vision Assistant V1.6

V1.6 is a deliberately small, no-ML desktop assistant. Luna performs the initial 64-square board read and rare recovery only. Normal live play uses rapid local screen differences, python-chess legal-move matching, and Stockfish.

The default vision model is exactly `gpt-5.6-luna`. Settings override `OPENAI_VISION_MODEL`, which overrides that default. The selected model is passed to the OpenAI Responses API unchanged.

## Install and run

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
copy .env.example .env
# Add OPENAI_API_KEY to .env and optionally configure Stockfish in Settings.
python -m app.main
```

Use **Scan Board**, select the browser board, then choose your colour and whether it is your turn. Your selected colour controls the internal-board orientation. Canonical square names always remain standard chess coordinates.

## Tracking and recovery

The capture loop runs at 125 ms by default. A stable visual change is matched against legal moves; commits are atomic and reset the visual baseline. OpenAI recovery starts only after a persistent stable board change cannot be resolved locally. Recovery accepts an identical board, a unique 1/2-ply legal sequence, or a structurally valid high-confidence full resync.

There are no Torch, ONNX, MobileNet, scikit-learn, model files, or square classifiers in the V1.6 runtime.
