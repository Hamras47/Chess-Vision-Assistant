import chess
import chess.engine

from app.engine.stockfish import parse_analysis


def test_multipv_rows_use_san_uci_and_side_to_move_score():
    board = chess.Board()
    infos = [
        {
            "score": chess.engine.PovScore(chess.engine.Cp(score), board.turn),
            "pv": [chess.Move.from_uci(uci)],
            "depth": 12,
        }
        for score, uci in ((63, "e2e4"), (41, "d2d4"), (22, "g1f3"))
    ]
    rows = parse_analysis(board, infos)
    assert rows == [
        ("e4", "e2e4", 63, None, 12),
        ("d4", "d2d4", 41, None, 12),
        ("Nf3", "g1f3", 22, None, 12),
    ]


def test_analysis_parses_black_side_to_move():
    board = chess.Board()
    board.push_uci("e2e4")
    info = {
        "score": chess.engine.PovScore(chess.engine.Cp(35), chess.BLACK),
        "pv": [chess.Move.from_uci("e7e5")],
    }
    assert parse_analysis(board, info)[0][:4] == ("e5", "e7e5", 35, None)
