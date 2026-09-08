import chess,pytest,numpy as np
from app.ai.schemas import parse,SCHEMA,SQUARES
from app.chess.reconstruction import build_board
from app.ai.openai_client import OpenAIClient,AIError,normalize_model
from app.ai.board_recognizer import recognize_image,RecognitionFailure
def empty_squares(): return {sq:'empty' for sq in SQUARES}
def payload(squares=None,side='white'):
 data=empty_squares(); data.update(squares or {})
 return {'orientation':'white_bottom','side_to_move':side,'squares':data,'confidence':.96,'warnings':[]}
def test_structured_ai_result_reconstructs_board():
 b=build_board(parse(payload({'e1':'white_king','e8':'black_king','e4':'white_pawn'}))); assert b.piece_at(chess.E4).symbol()=='P' and b.is_valid()
def test_missing_square_is_rejected():
 data=payload(); del data['squares']['a1']
 with pytest.raises(ValueError,match='64-square coverage'):parse(data)
def test_unknown_square_key_is_rejected():
 data=payload(); data['squares']['unknown']='white_pawn'
 with pytest.raises(ValueError,match='64-square coverage'):parse(data)
def test_unknown_piece_value_is_rejected():
 data=payload(); data['squares']['e4']='unknown'
 with pytest.raises(ValueError,match='invalid square values'):parse(data)
def test_missing_king_is_rejected():
 with pytest.raises(ValueError,match='king count'):build_board(parse(payload({'e1':'white_king'})))
def test_ai_key_missing_is_safe(monkeypatch):
 monkeypatch.delenv('OPENAI_API_KEY',raising=False); c=OpenAIClient(client=object()); assert not c.ready()
 with pytest.raises(AIError,match='key required'):c.client()
def test_schema_has_all_64_fixed_square_keys():
 squares=SCHEMA['properties']['squares']; assert len(squares['required'])==64 and squares['additionalProperties'] is False and 'unknown' not in squares['properties']['e4']['enum']
def test_luna_model_is_passed_to_api_unchanged(): assert normalize_model('gpt-5.6-luna')=='gpt-5.6-luna'
def test_exact_e4_e5_position_reconstruction():
 placement={}; back='rnbqkbnr'; names={'r':'rook','n':'knight','b':'bishop','q':'queen','k':'king'}
 for file,symbol in zip('abcdefgh',back): placement[file+'8']='black_'+names[symbol]; placement[file+'1']='white_'+names[symbol]
 for file in 'abcdfgh': placement[file+'7']='black_pawn'; placement[file+'2']='white_pawn'
 placement['e5']='black_pawn'; placement['e4']='white_pawn'; board=build_board(parse(payload(placement)))
 assert board.board_fen()=='rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR'
 assert board.piece_at(chess.E4).symbol()=='P' and board.piece_at(chess.E5).symbol()=='p' and board.piece_at(chess.E2) is None and board.piece_at(chess.E7) is None
def test_absolute_ai_square_keys_produce_same_fen_in_both_orientations():
 positions=[]
 for orientation in ('white_bottom','black_bottom'):
  data=payload({'e1':'white_king','e8':'black_king','g8':'black_knight','e4':'white_pawn'})
  data['orientation']=orientation
  positions.append(build_board(parse(data)).fen())
 assert positions[0]==positions[1]
def test_recognition_pipeline_with_mock_api(tmp_path,monkeypatch):
 data=payload({'e1':'white_king','e8':'black_king'}); monkeypatch.chdir(tmp_path)
 class Client:
  def recognize(self,png,schema,prompt): return data,.12,{'api_success':True,'status':'completed','model':'mock'}
 board,result,latency,api=recognize_image(np.zeros((64,64,3),dtype=np.uint8),'mock',True,Client())
 assert board.is_valid() and api['api_success'] and (tmp_path/'debug/ai_input.png').exists() and (tmp_path/'debug/ai_result.json').exists()
def test_recognition_reports_schema_stage():
 class Client:
  def recognize(self,png,schema,prompt): return {'bad':'response'},.1,{}
 with pytest.raises(RecognitionFailure) as error:recognize_image(np.zeros((8,8,3),dtype=np.uint8),'mock',False,Client())
 assert error.value.stage=='schema_validation'
