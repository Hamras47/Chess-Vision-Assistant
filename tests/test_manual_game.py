import chess
import pytest

from app.chess.game_state import ManualGameState, turn_from_selection


def play(state, uci):
    move = chess.Move.from_uci(uci)
    return state.make_move(move.from_square, move.to_square, move.promotion)


def test_initial_starting_board_and_turn_mapping():
    state = ManualGameState()
    assert state.board.fen() == chess.STARTING_FEN
    assert turn_from_selection(chess.WHITE, True) == chess.WHITE
    assert turn_from_selection(chess.WHITE, False) == chess.BLACK
    assert turn_from_selection(chess.BLACK, True) == chess.BLACK
    assert turn_from_selection(chess.BLACK, False) == chess.WHITE


def test_legal_moves_follow_side_to_move_and_illegal_move_is_blocked():
    state = ManualGameState()
    assert chess.E4 in {move.to_square for move in state.legal_moves_from(chess.E2)}
    assert not state.legal_moves_from(chess.E7)
    with pytest.raises(ValueError, match="Illegal move"):
        state.make_move(chess.E2, chess.E5)
    play(state, "e2e4")
    assert state.board.turn == chess.BLACK
    assert state.legal_moves_from(chess.E7)


def test_capture_and_real_san_history():
    state = ManualGameState()
    for uci in ("e2e4", "d7d5", "e4d5"):
        play(state, uci)
    assert state.records[-1].san == "exd5"
    assert state.history_text() == "1. e4    d5\n2. exd5"


def test_castling_when_rights_are_available():
    board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    state = ManualGameState(board)
    record = play(state, "e1g1")
    assert record.san == "O-O"
    assert state.board.king(chess.WHITE) == chess.G1
    assert state.board.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)


def test_promotion_choice_is_applied():
    state = ManualGameState(chess.Board("7k/P7/8/8/8/8/8/7K w - - 0 1"))
    assert set(state.promotion_options(chess.A7, chess.A8)) == {chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT}
    record = state.make_move(chess.A7, chess.A8, chess.KNIGHT)
    assert record.san.startswith("a8=N")
    assert state.board.piece_at(chess.A8).piece_type == chess.KNIGHT


def test_en_passant():
    state = ManualGameState(chess.Board("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1"))
    record = play(state, "e5d6")
    assert record.san == "exd6"
    assert state.board.piece_at(chess.D5) is None


def test_check_checkmate_stalemate_and_draw_status():
    check = ManualGameState(chess.Board("4k3/8/8/8/8/8/4R3/4K3 b - - 0 1"))
    assert check.outcome_status() == "CHECK"
    mate = ManualGameState()
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        play(mate, uci)
    assert mate.outcome_status() == "CHECKMATE · Black wins"
    stale = ManualGameState(chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"))
    assert stale.outcome_status() == "STALEMATE"
    draw = ManualGameState(chess.Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1"))
    assert draw.outcome_status() == "DRAW · Insufficient material"


def test_undo_redo_and_new_move_clears_redo():
    state = ManualGameState()
    play(state, "e2e4")
    play(state, "e7e5")
    assert state.undo().san == "e5"
    assert state.can_redo
    assert state.redo().san == "e5"
    state.undo()
    play(state, "c7c5")
    assert not state.can_redo
    assert "c5" in state.history_text()


def test_imported_midgame_clears_history_and_preserves_position():
    board = chess.Board()
    board.push_uci("e2e4")
    board.push_uci("e7e5")
    state = ManualGameState()
    state.load(board, chess.BLACK)
    assert state.board.board_fen() == board.board_fen()
    assert not state.board.move_stack
    assert not state.records
    assert state.turn_labels() == ("Opponent turn", "White to move")
