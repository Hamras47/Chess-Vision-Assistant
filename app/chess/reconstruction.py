import logging,chess
PIECE_TYPES={'pawn':chess.PAWN,'knight':chess.KNIGHT,'bishop':chess.BISHOP,'rook':chess.ROOK,'queen':chess.QUEEN,'king':chess.KING}
def build_board(result):
    board=chess.Board(None)
    for name,value in result.squares.items():
        if value=='empty': continue
        color_name,piece_name=value.split('_',1)
        board.set_piece_at(chess.parse_square(name),chess.Piece(PIECE_TYPES[piece_name],color_name=='white'))
    board.turn=result.side_to_move!='black'; board.castling_rights=chess.BB_EMPTY; board.ep_square=None; board.clear_stack()
    white_kings=len(board.pieces(chess.KING,chess.WHITE)); black_kings=len(board.pieces(chess.KING,chess.BLACK)); status=board.status()
    logging.info('Reconstruction FEN placement=%s turn=%s kings white=%d black=%d board.status=%s valid=%s',board.board_fen(),result.side_to_move,white_kings,black_kings,status,board.is_valid())
    if white_kings!=1 or black_kings!=1: raise ValueError(f'king count invalid: white={white_kings} black={black_kings}')
    for color, name in ((chess.WHITE, 'white'), (chess.BLACK, 'black')):
        pawns=board.pieces(chess.PAWN,color)
        if len(pawns)>8: raise ValueError(f'too many {name} pawns')
        if pawns & (chess.BB_RANK_1 | chess.BB_RANK_8): raise ValueError(f'{name} pawn on first or eighth rank')
    wk=board.king(chess.WHITE); bk=board.king(chess.BLACK)
    if chess.square_distance(wk,bk)<=1: raise ValueError('kings are adjacent')
    if not board.is_valid(): raise ValueError(f'python-chess rejected piece placement: status={status}')
    return board
