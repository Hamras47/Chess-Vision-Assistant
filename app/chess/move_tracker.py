import chess

def reconcile_reconstruction(board,reconstructed,max_plies=2):
    """Find a unique 0/1/2-ply legal path to a vision-reconstructed placement."""
    target=reconstructed.piece_map()
    if board.piece_map()==target:return board,()
    matches=[]
    def walk(position,moves,depth):
        if depth==0:return
        for move in position.legal_moves:
            candidate=position.copy(); candidate.push(move); sequence=moves+(move,)
            if candidate.piece_map()==target: matches.append((candidate,sequence))
            elif depth>1: walk(candidate,sequence,depth-1)
    walk(board,(),max_plies)
    return matches[0] if len(matches)==1 else (None,None)

def expected_changed_squares(board,move):
    changed={move.from_square,move.to_square}
    if board.is_castling(move):
        rank=chess.square_rank(move.from_square); changed.update([chess.square(7,rank),chess.square(5,rank)] if chess.square_file(move.to_square)==6 else [chess.square(0,rank),chess.square(3,rank)])
    if board.is_en_passant(move):changed.add(chess.square(chess.square_file(move.to_square),chess.square_rank(move.from_square)))
    return changed
def _candidate_score(expected,observed):
    """Missing a piece transition matters far more than highlight-only extras."""
    coverage=len(expected&observed)/max(1,len(expected)); missing=len(expected-observed); extra=len(observed-expected)
    return max(0.,coverage-.82*missing-.012*extra)
def infer_move(board,observed,relaxed=False,prior_uci=None):
    candidates=sorted([(_candidate_score(expected_changed_squares(board,m),observed)+(.04 if prior_uci==m.uci() else 0.),m,expected_changed_squares(board,m)) for m in board.legal_moves],key=lambda x:x[0],reverse=True)
    minimum=.50 if relaxed else .72
    margin=.08 if relaxed else (.03 if prior_uci else (.05 if candidates and candidates[0][0]>=.90 else .14))
    if not candidates or candidates[0][0]<minimum:return None,(candidates[0][0] if candidates else 0.),candidates[:8]
    if len(candidates)>1 and candidates[0][2]==candidates[1][2] and candidates[0][1].promotion:return None,candidates[0][0],candidates[:8]
    if candidates[0][2]==observed:return candidates[0][1],candidates[0][0],candidates[:8]
    if len(candidates)>1 and candidates[0][0]-candidates[1][0]<margin:return None,candidates[0][0],candidates[:8]
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

def visual_plausibility(board,move,observed,scores,threshold):
    expected=expected_changed_squares(board,move); coverage=len(expected&observed)/len(expected)
    strength=sum(min(1.,scores.get(square,0.)/max(threshold,.001)) for square in expected)/len(expected)
    return .65*coverage+.35*strength

def transition_squares(before,after):
    a,b=before.piece_map(),after.piece_map(); return {square for square in chess.SQUARES if a.get(square)!=b.get(square)}

def infer_legal_sequence(board,observed,scores,threshold,max_depth=2):
    candidates=[]
    def add(sequence,position):
        expected=transition_squares(board,position); missing=len(expected-observed); extra=len(observed-expected); coverage=len(expected&observed)/max(1,len(expected)); strength=sum(min(1.,scores.get(square,0.)/max(threshold,.001)) for square in expected)/max(1,len(expected)); score=.62*coverage+.38*strength-.32*missing-.035*extra
        candidates.append((max(0.,score),tuple(sequence),expected))
    for first in board.legal_moves:
        after_first=board.copy(); after_first.push(first); add([first],after_first)
        if max_depth>=2:
            for reply in after_first.legal_moves:
                after_reply=after_first.copy(); after_reply.push(reply); add([first,reply],after_reply)
    candidates.sort(key=lambda item:item[0],reverse=True)
    if not candidates:return None,0.,[]
    best=candidates[0]; margin=best[0]-(candidates[1][0] if len(candidates)>1 else 0.)
    return (best[1] if best[0]>=.82 and margin>=.065 else None),best[0],candidates[:8]
