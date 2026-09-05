import cv2,json,logging,os
from pathlib import Path
from PySide6.QtCore import QThread,Signal
from .openai_client import OpenAIClient
from .schemas import SCHEMA,parse,piece_count
from .prompts import BOARD_PROMPT
from app.chess.reconstruction import build_board

class RecognitionFailure(RuntimeError):
    def __init__(self,stage,reason): self.stage=stage; self.reason=str(reason); super().__init__(f'{stage}: {reason}')

def recognize_image(image,model,debug=False,client=None):
    log=logging.getLogger(__name__); h,w=image.shape[:2]; log.info('Recognition begin model=%s image=%dx%d',model,w,h)
    ok,buf=cv2.imencode('.png',image)
    if not ok: raise RecognitionFailure('image_encoding','OpenCV PNG encoding failed')
    png=buf.tobytes()
    if debug:
        Path('debug').mkdir(exist_ok=True); Path('debug/ai_input.png').write_bytes(png)
        log.info('Debug AI input saved dimensions=%dx%d bytes=%d',w,h,len(png))
    try:data,latency,api= (client or OpenAIClient(model)).recognize(png,SCHEMA,BOARD_PROMPT)
    except Exception as e: raise RecognitionFailure('api_request',e) from e
    log.info('OPENAI_RAW_RESULT result=%s',json.dumps(data,sort_keys=True))
    if debug: Path('debug/ai_result.json').write_text(json.dumps(data,indent=2,sort_keys=True),encoding='utf-8')
    try:result=parse(data)
    except Exception as e:
        log.exception('Schema validation result=failed reason=%s',e); raise RecognitionFailure('schema_validation',e) from e
    log.info('Schema validation result=passed orientation=%s side_to_move=%s confidence=%.3f piece_count=%d warnings=%s',result.orientation,result.side_to_move,result.confidence,piece_count(result),result.warnings)
    if result.confidence < .90: raise RecognitionFailure('confidence',f'confidence {result.confidence:.3f} is below 0.90')
    try:board=build_board(result)
    except Exception as e:
        log.exception('Reconstruction result=failed reason=%s',e); raise RecognitionFailure('reconstruction',e) from e
    log.info('BOARD_RECONSTRUCTION_FEN board_fen=%s full_fen=%s',board.board_fen(),board.fen()); log.info('BOARD_VALIDATION_RESULT valid=%s status=%s',board.is_valid(),board.status())
    return board,result,latency,api

class RecognitionWorker(QThread):
    result=Signal(object,object,float); error=Signal(str)
    def __init__(self,image,model,debug=False,client=None): super().__init__(); self.image=image; self.model=model; self.debug=debug; self.client=client
    def run(self):
        last=None
        for attempt in range(1,3):
            try:
                logging.info('Recognition attempt=%d/2',attempt); board,result,latency,_=recognize_image(self.image,self.model,self.debug,self.client); self.result.emit(board,result,latency); return
            except Exception as e: last=e; logging.exception('Recognition attempt=%d failed stage=%s reason=%s',attempt,getattr(e,'stage','unknown'),getattr(e,'reason',e))
        self.error.emit(str(last))
