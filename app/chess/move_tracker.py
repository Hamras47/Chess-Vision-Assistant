import chess

def expected_changed_squares(board: chess.Board, move: chess.Move) -> set[chess.Square]:
    changed={move.from_square, move.to_square}
    if board.is_castling(move):
        rank=chess.square_rank(move.from_square)
        changed.update([chess.square(7,rank),chess.square(5,rank)] if chess.square_file(move.to_square)==6 else [chess.square(0,rank),chess.square(3,rank)])
    if board.is_en_passant(move): changed.add(chess.square(chess.square_file(move.to_square),chess.square_rank(move.from_square)))
    return changed

def infer_move(board: chess.Board, observed: set[chess.Square]):
    candidates=[]
    for move in board.legal_moves:
        expected=expected_changed_squares(board,move)
        overlap=len(observed&expected); union=len(observed|expected)
        score=overlap/union if union else 0
        if expected==observed: score=1.0
        candidates.append((score,move,expected))
    candidates.sort(key=lambda x:x[0],reverse=True)
    if not candidates or candidates[0][0] < .75: return None, 0.0, candidates[:5]
    if len(candidates)>1 and candidates[0][0]-candidates[1][0] < .15: return None,candidates[0][0],candidates[:5]
    return candidates[0][1],candidates[0][0],candidates[:5]
