import sys,logging,cv2
from pathlib import Path
from dotenv import load_dotenv
from .openai_client import OpenAIClient
from .board_recognizer import recognize_image
from .schemas import piece_count

def main():
    load_dotenv(); logging.basicConfig(level=logging.INFO,format='%(levelname)s %(message)s')
    if len(sys.argv)!=2: raise SystemExit('Usage: python -m app.ai.debug_scan path/to/board.png')
    path=Path(sys.argv[1]); image=cv2.imread(str(path))
    if image is None: raise SystemExit(f'Could not load image: {path}')
    model=OpenAIClient().model; print('MODEL',model); print('IMAGE DIMENSIONS',f'{image.shape[1]}x{image.shape[0]}')
    try:
        board,result,latency,api=recognize_image(image,model,True)
        print('API SUCCESS',api['api_success']); print('API STATUS',api['status']); print('ORIENTATION',result.orientation); print('SIDE TO MOVE',result.side_to_move); print('PIECE COUNT',piece_count(result)); print('RECOGNIZED POSITION'); print(board); print('FEN PIECE PLACEMENT',board.board_fen()); print('VALIDATION RESULT',board.is_valid(),board.status()); print('WARNINGS',result.warnings); print('LATENCY',f'{latency:.2f}s')
    except Exception as e:
        print('API/PIPELINE SUCCESS',False); print('FAILURE STAGE',getattr(e,'stage','unknown')); print('FAILURE REASON',getattr(e,'reason',e)); raise SystemExit(1)
if __name__=='__main__':main()
