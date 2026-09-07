import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess
import pytest
from PySide6.QtWidgets import QApplication, QCheckBox

from app.chess.game_state import (
    BLACK_KINGSIDE,
    BLACK_QUEENSIDE,
    WHITE_KINGSIDE,
    WHITE_QUEENSIDE,
    ManualGameState,
    apply_castling_rights,
    available_castling_options,
    is_new_game_placement,
)
from app.ui.setup_dialog import PositionSetupDialog
from app.ui.main_window import MainWindow

ALL_RIGHTS = {
    WHITE_KINGSIDE,
    WHITE_QUEENSIDE,
    BLACK_KINGSIDE,
    BLACK_QUEENSIDE,
}


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def castle_board(turn=chess.WHITE):
    board = chess.Board("r3k2r/8/8/8/8/8/8/R3K2R w - - 0 1")
    board.turn = turn
    return board


def test_exact_starting_placement_is_new_game_with_automatic_rights(app):
    scanned = chess.Board()
    scanned.castling_rights = chess.BB_EMPTY
    assert is_new_game_placement(scanned)
    canonical = chess.Board() if is_new_game_placement(scanned) else scanned
    assert canonical.castling_xfen() == "KQkq"
    dialog = PositionSetupDialog(castling_options=None)
    assert not dialog.castling_boxes
    assert not dialog.findChildren(QCheckBox)
    dialog.close()


def test_midgame_defaults_to_no_castling_rights():
    board = castle_board()
    assert not is_new_game_placement(board)
    apply_castling_rights(board, set())
    assert board.castling_rights == chess.BB_EMPTY
    assert chess.Move.from_uci("e1g1") not in board.legal_moves
    assert chess.Move.from_uci("e1c1") not in board.legal_moves


@pytest.mark.parametrize(
    "right,turn,legal,forbidden",
    [
        (WHITE_KINGSIDE, chess.WHITE, "e1g1", "e1c1"),
        (WHITE_QUEENSIDE, chess.WHITE, "e1c1", "e1g1"),
        (BLACK_KINGSIDE, chess.BLACK, "e8g8", "e8c8"),
        (BLACK_QUEENSIDE, chess.BLACK, "e8c8", "e8g8"),
    ],
)
def test_each_individual_castling_right(right, turn, legal, forbidden):
    board = castle_board(turn)
    apply_castling_rights(board, {right})
    assert chess.Move.from_uci(legal) in board.legal_moves
    assert chess.Move.from_uci(forbidden) not in board.legal_moves


def test_multiple_castling_rights_are_applied():
    board = castle_board(chess.WHITE)
    apply_castling_rights(board, ALL_RIGHTS)
    assert board.castling_xfen() == "KQkq"
    assert chess.Move.from_uci("e1g1") in board.legal_moves
    assert chess.Move.from_uci("e1c1") in board.legal_moves
    board.turn = chess.BLACK
    assert chess.Move.from_uci("e8g8") in board.legal_moves
    assert chess.Move.from_uci("e8c8") in board.legal_moves


@pytest.mark.parametrize("mask", range(16))
def test_every_castling_right_combination(mask):
    ordered = (WHITE_KINGSIDE, WHITE_QUEENSIDE, BLACK_KINGSIDE, BLACK_QUEENSIDE)
    selected = {right for index, right in enumerate(ordered) if mask & (1 << index)}
    board = castle_board()
    apply_castling_rights(board, selected)
    assert board.has_kingside_castling_rights(chess.WHITE) == (WHITE_KINGSIDE in selected)
    assert board.has_queenside_castling_rights(chess.WHITE) == (WHITE_QUEENSIDE in selected)
    assert board.has_kingside_castling_rights(chess.BLACK) == (BLACK_KINGSIDE in selected)
    assert board.has_queenside_castling_rights(chess.BLACK) == (BLACK_QUEENSIDE in selected)


def test_only_physically_possible_options_are_offered():
    board = castle_board()
    board.remove_piece_at(chess.A1)
    board.remove_piece_at(chess.H8)
    assert set(available_castling_options(board)) == {WHITE_KINGSIDE, BLACK_QUEENSIDE}
    apply_castling_rights(board, ALL_RIGHTS)
    assert board.has_kingside_castling_rights(chess.WHITE)
    assert not board.has_queenside_castling_rights(chess.WHITE)
    assert not board.has_kingside_castling_rights(chess.BLACK)
    assert board.has_queenside_castling_rights(chess.BLACK)


def test_midgame_confirmation_is_compact_filtered_and_unchecked(app):
    board = castle_board()
    board.remove_piece_at(chess.A1)
    options = available_castling_options(board)
    dialog = PositionSetupDialog(castling_options=options)
    assert set(dialog.castling_boxes) == {WHITE_KINGSIDE, BLACK_KINGSIDE, BLACK_QUEENSIDE}
    assert all(not checkbox.isChecked() for checkbox in dialog.castling_boxes.values())
    assert "K" not in {checkbox.text() for checkbox in dialog.castling_boxes.values()}
    assert {checkbox.text() for checkbox in dialog.castling_boxes.values()} == {"King side", "Queen side"}
    dialog.castling_boxes[WHITE_KINGSIDE].setChecked(True)
    dialog._accept_values()
    assert dialog.castling_rights == {WHITE_KINGSIDE}
    dialog.close()


def test_king_move_removes_both_rights_and_undo_restores_them():
    board = castle_board()
    apply_castling_rights(board, {WHITE_KINGSIDE, WHITE_QUEENSIDE})
    state = ManualGameState(board)
    state.make_move(chess.E1, chess.E2)
    assert not state.board.has_castling_rights(chess.WHITE)
    state.undo()
    assert state.board.has_kingside_castling_rights(chess.WHITE)
    assert state.board.has_queenside_castling_rights(chess.WHITE)


def test_rook_move_removes_corresponding_right_and_undo_restores_it():
    board = castle_board()
    apply_castling_rights(board, {WHITE_KINGSIDE, WHITE_QUEENSIDE})
    state = ManualGameState(board)
    state.make_move(chess.H1, chess.H2)
    assert not state.board.has_kingside_castling_rights(chess.WHITE)
    assert state.board.has_queenside_castling_rights(chess.WHITE)
    state.undo()
    assert state.board.has_kingside_castling_rights(chess.WHITE)


def test_castling_moves_king_and_rook_as_one_manual_move():
    board = castle_board()
    apply_castling_rights(board, {WHITE_KINGSIDE})
    state = ManualGameState(board)
    record = state.make_move(chess.E1, chess.G1)
    assert record.san == "O-O"
    assert state.board.piece_at(chess.G1) == chess.Piece(chess.KING, chess.WHITE)
    assert state.board.piece_at(chess.F1) == chess.Piece(chess.ROOK, chess.WHITE)
    assert state.board.piece_at(chess.H1) is None


def test_main_window_applies_confirmation_rights_to_canonical_board(app, monkeypatch):
    monkeypatch.setattr(MainWindow, "_find_engine", lambda self: "")
    window = MainWindow()
    window.load_position(
        castle_board(),
        chess.WHITE,
        chess.WHITE,
        imported=True,
        castling_rights={WHITE_KINGSIDE},
    )
    assert chess.Move.from_uci("e1g1") in window.board.legal_moves
    assert chess.Move.from_uci("e1c1") not in window.board.legal_moves
    window.close()
