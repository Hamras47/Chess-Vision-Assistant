"""Canonical, manually edited chess state."""
from __future__ import annotations

from dataclasses import dataclass

import chess

WHITE_KINGSIDE = "white_kingside"
WHITE_QUEENSIDE = "white_queenside"
BLACK_KINGSIDE = "black_kingside"
BLACK_QUEENSIDE = "black_queenside"

CASTLING_REQUIREMENTS = {
    WHITE_KINGSIDE: (chess.E1, chess.H1, chess.WHITE),
    WHITE_QUEENSIDE: (chess.E1, chess.A1, chess.WHITE),
    BLACK_KINGSIDE: (chess.E8, chess.H8, chess.BLACK),
    BLACK_QUEENSIDE: (chess.E8, chess.A8, chess.BLACK),
}


def is_new_game_placement(board: chess.Board) -> bool:
    """A scan is a new game only when all 64 squares match the initial layout."""
    return board.board_fen() == chess.STARTING_BOARD_FEN


def available_castling_options(board: chess.Board) -> tuple[str, ...]:
    """Return rights that are physically possible, without assuming history."""
    available = []
    for option, (king_square, rook_square, color) in CASTLING_REQUIREMENTS.items():
        if (
            board.piece_at(king_square) == chess.Piece(chess.KING, color)
            and board.piece_at(rook_square) == chess.Piece(chess.ROOK, color)
        ):
            available.append(option)
    return tuple(available)


def apply_castling_rights(board: chess.Board, selected: set[str] | tuple[str, ...]) -> None:
    """Apply only selected rights whose king and rook still occupy home squares."""
    possible = set(available_castling_options(board))
    board.castling_rights = chess.BB_EMPTY
    for option in set(selected) & possible:
        rook_square = CASTLING_REQUIREMENTS[option][1]
        board.castling_rights |= chess.BB_SQUARES[rook_square]


@dataclass(frozen=True)
class MoveRecord:
    move: chess.Move
    san: str
    move_number: int
    color: chess.Color


class ManualGameState:
    """Own the only authoritative board and its undo/redo history."""

    def __init__(self, board: chess.Board | None = None, player_color: chess.Color = chess.WHITE):
        self.player_color = player_color
        self.version = 0
        self._records: list[MoveRecord] = []
        self._redo: list[chess.Move] = []
        self.load(board or chess.Board(), player_color)

    @property
    def board(self) -> chess.Board:
        return self._board

    @property
    def records(self) -> tuple[MoveRecord, ...]:
        return tuple(self._records)

    @property
    def can_undo(self) -> bool:
        return bool(self._records and self._board.move_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def load(self, board: chess.Board, player_color: chess.Color) -> None:
        loaded = board.copy(stack=False)
        loaded.clear_stack()
        self._board = loaded
        self.player_color = player_color
        self._records = []
        self._redo = []
        self.version += 1

    def new_game(self, player_color: chess.Color) -> None:
        self.load(chess.Board(), player_color)

    def legal_moves_from(self, square: chess.Square) -> list[chess.Move]:
        piece = self._board.piece_at(square)
        if piece is None or piece.color != self._board.turn:
            return []
        return [move for move in self._board.legal_moves if move.from_square == square]

    def promotion_options(self, source: chess.Square, target: chess.Square) -> list[int]:
        return [
            move.promotion
            for move in self.legal_moves_from(source)
            if move.to_square == target and move.promotion is not None
        ]

    def make_move(
        self,
        source: chess.Square,
        target: chess.Square,
        promotion: int | None = None,
    ) -> MoveRecord:
        move = chess.Move(source, target, promotion=promotion)
        if move not in self._board.legal_moves:
            raise ValueError(f"Illegal move: {move.uci()}")
        record = MoveRecord(move, self._board.san(move), self._board.fullmove_number, self._board.turn)
        self._board.push(move)
        self._records.append(record)
        self._redo.clear()
        self.version += 1
        return record

    def undo(self) -> MoveRecord | None:
        if not self.can_undo:
            return None
        move = self._board.pop()
        record = self._records.pop()
        self._redo.append(move)
        self.version += 1
        return record

    def redo(self) -> MoveRecord | None:
        if not self._redo:
            return None
        move = self._redo.pop()
        if move not in self._board.legal_moves:
            self._redo.clear()
            return None
        record = MoveRecord(move, self._board.san(move), self._board.fullmove_number, self._board.turn)
        self._board.push(move)
        self._records.append(record)
        self.version += 1
        return record

    def history_text(self) -> str:
        lines: list[str] = []
        for record in self._records:
            if record.color == chess.WHITE:
                lines.append(f"{record.move_number}. {record.san}")
            elif lines and lines[-1].startswith(f"{record.move_number}. "):
                lines[-1] += f"    {record.san}"
            else:
                lines.append(f"{record.move_number}... {record.san}")
        return "\n".join(lines)

    def turn_labels(self) -> tuple[str, str]:
        side = "White to move" if self._board.turn == chess.WHITE else "Black to move"
        owner = "Your turn" if self._board.turn == self.player_color else "Opponent turn"
        return owner, side

    def outcome_status(self) -> str:
        if self._board.is_checkmate():
            winner = "Black" if self._board.turn == chess.WHITE else "White"
            return f"CHECKMATE · {winner} wins"
        if self._board.is_stalemate():
            return "STALEMATE"
        if self._board.is_insufficient_material():
            return "DRAW · Insufficient material"
        if self._board.is_seventyfive_moves():
            return "DRAW · 75-move rule"
        if self._board.is_fivefold_repetition():
            return "DRAW · Fivefold repetition"
        if self._board.is_check():
            return "CHECK"
        return ""


def turn_from_selection(player_color: chess.Color, my_turn: bool) -> chess.Color:
    return player_color if my_turn else not player_color
