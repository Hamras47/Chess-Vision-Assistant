import chess

def reconcile_reconstruction(board,reconstructed):
    """Preserve move history when a recovered position is the current or next legal state."""
    if board.piece_map()==reconstructed.piece_map():return board,None
    matches=[]
    for move in board.legal_moves:
        candidate=board.copy(); candidate.push(move)
        if candidate.piece_map()==reconstructed.piece_map():matches.append((candidate,move))
    return matches[0] if len(matches)==1 else (None,None)

def expected_changed_squares(board,move):
    changed={move.from_square,move.to_square}
    if board.is_castling(move):
        rank=chess.square_rank(move.from_square); changed.update([chess.square(7,rank),chess.square(5,rank)] if chess.square_file(move.to_square)==6 else [chess.square(0,rank),chess.square(3,rank)])
    if board.is_en_passant(move):changed.add(chess.square(chess.square_file(move.to_square),chess.square_rank(move.from_square)))
    return changed
def _candidate_score(expected,observed):
    return max(0.,len(expected&observed)/max(1,len(expected))-.58*len(expected-observed)-.08*len(observed-expected))
def infer_move(board,observed,relaxed=False):
    candidates=sorted([(_candidate_score(expected_changed_squares(board,m),observed),m,expected_changed_squares(board,m)) for m in board.legal_moves],key=lambda x:x[0],reverse=True)
    minimum=.50 if relaxed else .72; margin=.08 if relaxed else .14
    if not candidates or candidates[0][0]<minimum:return None,(candidates[0][0] if candidates else 0.),candidates[:8]
    if len(candidates)>1 and candidates[0][0]-candidates[1][0]<margin:return None,candidates[0][0],candidates[:8]
    if len(candidates)>1 and candidates[0][2]==candidates[1][2] and candidates[0][1].promotion:return None,candidates[0][0],candidates[:8]
    return candidates[0][1],candidates[0][0],candidates[:8]
def infer_move_from_scores(board,scores,threshold):
    candidates=[]
    for move in board.legal_moves:
        expected=expected_changed_squares(board,move); signal=sum(min(1.,scores.get(s,0)/max(threshold,.001)) for s in expected)/len(expected); outside=sorted((v for s,v in scores.items() if s not in expected),reverse=True)[:2]; noise=sum(outside)/(max(threshold,.001)*max(1,len(outside))); candidates.append((max(0.,signal-.10*noise),move,expected))
    candidates.sort(key=lambda x:x[0],reverse=True)
    if not candidates:return None,0.,[]
    if candidates[0][1].promotion and len(candidates)>1 and candidates[0][2]==candidates[1][2]:return None,candidates[0][0],candidates[:8]
    if candidates[0][0]>=.62 and (len(candidates)==1 or candidates[0][0]-candidates[1][0]>=.07):return candidates[0][1],candidates[0][0],candidates[:8]
    return None,candidates[0][0],candidates[:8]
