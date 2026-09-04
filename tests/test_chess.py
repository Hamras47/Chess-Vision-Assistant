import chess
from app.chess_state import ChessState

def test_start_fen_and_legal_move():
    s=ChessState(); assert s.fen()==chess.STARTING_FEN; s.play('e2e4'); assert s.board.piece_at(chess.E4).symbol()=='P'
def test_invalid_move_rejected():
    s=ChessState()
    try: s.play('e2e5'); assert False
    except ValueError: pass
def test_fen_validation():
    s=ChessState('8/8/8/8/8/8/4K3/4k3 w - - 0 1'); assert s.validate()[0] is False
