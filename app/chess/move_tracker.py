"""Exact python-chess history reconciliation for authoritative AI board scans."""
import chess

def reconcile_reconstruction(board,reconstructed,max_plies=2):
    target=reconstructed.piece_map()
    if board.piece_map()==target:return board,()
    matches=[]
    def walk(position,moves,depth):
        if depth==0:return
        for move in position.legal_moves:
            candidate=position.copy(); candidate.push(move); sequence=moves+(move,)
            if candidate.piece_map()==target:matches.append((candidate,sequence))
            elif depth>1:walk(candidate,sequence,depth-1)
    walk(board,(),max_plies)
    return matches[0] if len(matches)==1 else (None,None)
