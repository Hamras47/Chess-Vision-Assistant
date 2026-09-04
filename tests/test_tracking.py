import chess,pytest
from app.chess.coordinates import visual_index_to_square,square_to_visual_index
from app.chess.move_tracker import infer_move,expected_changed_squares,infer_move_from_scores

def test_orientation_round_trips():
 for white_bottom in (True,False):
  for sq in chess.SQUARES: assert visual_index_to_square(square_to_visual_index(sq,white_bottom),white_bottom)==sq
def test_white_bottom_corners():
 assert chess.square_name(visual_index_to_square(56,True))=='a1'
 assert chess.square_name(visual_index_to_square(0,True))=='a8'
def test_black_bottom_corners():
 assert chess.square_name(visual_index_to_square(56,False))=='h8'
 assert chess.square_name(visual_index_to_square(0,False))=='h1'
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
