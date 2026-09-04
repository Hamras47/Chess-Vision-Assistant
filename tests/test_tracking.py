import chess,pytest
from app.chess.coordinates import Orientation,mapping_table,square_to_visual,square_to_visual_index,visual_index_to_square,visual_to_square
from app.chess.move_tracker import infer_move,expected_changed_squares,infer_move_from_scores,reconcile_reconstruction
from app.chess.session import TrackingSession

@pytest.mark.parametrize('color,orientation',[(chess.WHITE,Orientation.WHITE_BOTTOM),(chess.BLACK,Orientation.BLACK_BOTTOM)])
def test_player_color_controls_only_app_display_orientation(color,orientation):
 session=TrackingSession(); session.browser_orientation=Orientation.BLACK_BOTTOM if color==chess.WHITE else Orientation.WHITE_BOTTOM; session.select_player(color)
 assert session.player_color==color and session.app_display_orientation is orientation
 session.board.turn=not color
 assert session.board.turn!=session.player_color

def test_reconstruction_reconciliation_preserves_legal_turn_sequence():
 board=chess.Board(); reconstructed=board.copy(); reconstructed.push_uci('e2e4')
 recovered,move=reconcile_reconstruction(board,reconstructed)
 assert move.uci()=='e2e4' and recovered.turn==chess.BLACK and recovered.move_stack[-1]==move

def test_reconstruction_reconciliation_rejects_non_single_move_jump():
 board=chess.Board(); reconstructed=board.copy(); reconstructed.push_uci('e2e4'); reconstructed.push_uci('e7e5')
 assert reconcile_reconstruction(board,reconstructed)==(None,None)

@pytest.mark.parametrize('orientation',[Orientation.WHITE_BOTTOM,Orientation.BLACK_BOTTOM])
def test_orientation_round_trips_all_64_squares(orientation):
 for square in chess.SQUARES:
  row,col=square_to_visual(square,orientation)
  assert visual_to_square(row,col,orientation)==square
  assert visual_index_to_square(square_to_visual_index(square,orientation),orientation)==square

def test_white_bottom_exact_mapping_table():
 assert mapping_table(Orientation.WHITE_BOTTOM)==[
  ['a8','b8','c8','d8','e8','f8','g8','h8'],['a7','b7','c7','d7','e7','f7','g7','h7'],
  ['a6','b6','c6','d6','e6','f6','g6','h6'],['a5','b5','c5','d5','e5','f5','g5','h5'],
  ['a4','b4','c4','d4','e4','f4','g4','h4'],['a3','b3','c3','d3','e3','f3','g3','h3'],
  ['a2','b2','c2','d2','e2','f2','g2','h2'],['a1','b1','c1','d1','e1','f1','g1','h1']]

def test_black_bottom_exact_mapping_table():
 assert mapping_table(Orientation.BLACK_BOTTOM)==[
  ['h1','g1','f1','e1','d1','c1','b1','a1'],['h2','g2','f2','e2','d2','c2','b2','a2'],
  ['h3','g3','f3','e3','d3','c3','b3','a3'],['h4','g4','f4','e4','d4','c4','b4','a4'],
  ['h5','g5','f5','e5','d5','c5','b5','a5'],['h6','g6','f6','e6','d6','c6','b6','a6'],
  ['h7','g7','f7','e7','d7','c7','b7','a7'],['h8','g8','f8','e8','d8','c8','b8','a8']]

@pytest.mark.parametrize('orientation,square,cell',[
 (Orientation.WHITE_BOTTOM,'a8',(0,0)),(Orientation.WHITE_BOTTOM,'h1',(7,7)),
 (Orientation.WHITE_BOTTOM,'g8',(0,6)),(Orientation.WHITE_BOTTOM,'f6',(2,5)),
 (Orientation.BLACK_BOTTOM,'h1',(0,0)),(Orientation.BLACK_BOTTOM,'a8',(7,7)),
 (Orientation.BLACK_BOTTOM,'g8',(7,1)),(Orientation.BLACK_BOTTOM,'f6',(5,2)),
 (Orientation.BLACK_BOTTOM,'b8',(7,6)),(Orientation.BLACK_BOTTOM,'c6',(5,5))])
def test_exact_visual_cells(orientation,square,cell):
 assert square_to_visual(chess.parse_square(square),orientation)==cell
 assert visual_to_square(*cell,orientation)==chess.parse_square(square)

@pytest.mark.parametrize('uci',["g8f6","b8c6"])
def test_black_bottom_knight_move_maps_and_infers_correctly(uci):
 board=chess.Board(); board.push_uci('e2e4'); move=chess.Move.from_uci(uci)
 visual_cells={square_to_visual(square,Orientation.BLACK_BOTTOM) for square in expected_changed_squares(board,move)}
 canonical={visual_to_square(row,col,Orientation.BLACK_BOTTOM) for row,col in visual_cells}
 inferred,_,_=infer_move(board,canonical)
 assert inferred==move
 board.push(inferred)
 assert board.piece_at(move.to_square)==chess.Piece(chess.KNIGHT,chess.BLACK)
 assert square_to_visual(move.to_square,Orientation.BLACK_BOTTOM)==((5,2) if uci=='g8f6' else (5,5))

@pytest.mark.parametrize('orientation',[Orientation.WHITE_BOTTOM,Orientation.BLACK_BOTTOM])
def test_white_e2e4_maps_to_same_canonical_move_and_render_cell(orientation):
 board=chess.Board(); move=chess.Move.from_uci('e2e4')
 visual={square_to_visual(square,orientation) for square in expected_changed_squares(board,move)}
 canonical={visual_to_square(row,col,orientation) for row,col in visual}; inferred,_,_=infer_move(board,canonical); board.push(inferred)
 assert inferred==move and board.piece_at(chess.E4)==chess.Piece(chess.PAWN,chess.WHITE)
 assert square_to_visual(chess.E4,orientation)==((4,4) if orientation is Orientation.WHITE_BOTTOM else (3,3))

@pytest.mark.parametrize('orientation',[Orientation.WHITE_BOTTOM,Orientation.BLACK_BOTTOM])
def test_multiple_developed_knights_keep_files_and_render_cells(orientation):
 board=chess.Board()
 for uci in ('g1f3','g8f6','b1c3','b8c6'):
  board.push_uci(uci)
 expected={'f3':(5,5),'f6':(2,5),'c3':(5,2),'c6':(2,2)} if orientation is Orientation.WHITE_BOTTOM else {'f3':(2,2),'f6':(5,2),'c3':(2,5),'c6':(5,5)}
 for name,cell in expected.items():
  square=chess.parse_square(name)
  assert board.piece_at(square).piece_type==chess.KNIGHT
  assert square_to_visual(square,orientation)==cell

@pytest.mark.parametrize('orientation',[Orientation.WHITE_BOTTOM,Orientation.BLACK_BOTTOM])
@pytest.mark.parametrize('fen,uci',[
 ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1','e1g1'),
 ('r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1','e8g8'),
 ('r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1','e8c8'),
 ('rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2','e4d5')])
def test_capture_and_castling_mapping_both_orientations(orientation,fen,uci):
 board=chess.Board(fen); move=chess.Move.from_uci(uci)
 visual={square_to_visual(square,orientation) for square in expected_changed_squares(board,move)}
 canonical={visual_to_square(row,col,orientation) for row,col in visual}
 inferred,_,_=infer_move(board,canonical)
 assert inferred==move
def test_normal_move_inference():
 b=chess.Board(); m,c,_=infer_move(b,{chess.E2,chess.E4}); assert m.uci()=='e2e4' and c==1
def test_capture_inference():
 b=chess.Board(); [b.push_uci(x) for x in ['e2e4','d7d5']]; m,c,_=infer_move(b,{chess.E4,chess.D5}); assert m.uci()=='e4d5'
def test_castling_squares_and_inference():
 b=chess.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1'); m=chess.Move.from_uci('e1g1'); assert expected_changed_squares(b,m)=={chess.E1,chess.G1,chess.H1,chess.F1}; got,_,_=infer_move(b,expected_changed_squares(b,m)); assert got==m
@pytest.mark.parametrize('fen,uci',[
 ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1','e1c1'),('r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1','e8g8'),('r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1','e8c8')])
def test_other_castling_directions(fen,uci):
 b=chess.Board(fen); expected=expected_changed_squares(b,chess.Move.from_uci(uci)); move,_,_=infer_move(b,expected); assert move.uci()==uci
def test_en_passant_squares_and_inference():
 b=chess.Board(); [b.push_uci(x) for x in ['e2e4','a7a6','e4e5','d7d5']]; m=chess.Move.from_uci('e5d6'); got,_,_=infer_move(b,expected_changed_squares(b,m)); assert got==m
def test_promotion_inference():
 b=chess.Board('8/P7/8/8/8/8/7p/4K2k w - - 0 1'); m=chess.Move.from_uci('a7a8q'); got,_,_=infer_move(b,expected_changed_squares(b,m)); assert got is None # promotion image needs local classifier to disambiguate piece choice
def test_extra_highlight_square_is_tolerated():
 b=chess.Board(); move,score,_=infer_move(b,{chess.E2,chess.E4,chess.E5}); assert move.uci()=='e2e4' and score>.8
def test_weak_destination_signal_fallback():
 b=chess.Board(); scores={sq:0.0 for sq in chess.SQUARES}; scores[chess.E2]=.12; scores[chess.E4]=.05
 move,score,_=infer_move_from_scores(b,scores,.065); assert move.uci()=='e2e4'
def test_realistic_sequence_keeps_piece_state():
 b=chess.Board()
 for uci in ['e2e4','e7e5','g1f3','b8c6','f1b5']:
  expected=b.copy(); expected.push_uci(uci); move,_,_=infer_move(b,expected_changed_squares(b,chess.Move.from_uci(uci))); assert move.uci()==uci; b.push(move); assert b.piece_map()==expected.piece_map()
 assert len(b.piece_map())==32
def test_capture_sequence_piece_count():
 b=chess.Board()
 for uci in ['e2e4','d7d5','e4d5']:
  move,_,_=infer_move(b,expected_changed_squares(b,chess.Move.from_uci(uci))); b.push(move)
 assert len(b.piece_map())==31 and b.piece_at(chess.D5).symbol()=='P'
