import chess

class ChessState:
    def __init__(self, fen=chess.STARTING_FEN): self.board = chess.Board(fen)
    def set_fen(self, fen): self.board = chess.Board(fen)
    def fen(self): return self.board.fen()
    def play(self, move):
        m = chess.Move.from_uci(move) if isinstance(move, str) else move
        if m not in self.board.legal_moves: raise ValueError("Illegal move")
        self.board.push(m)
    def reset(self): self.board.reset()
    def validate(self): return self.board.is_valid(), self.board.status()
