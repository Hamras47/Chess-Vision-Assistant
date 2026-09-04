from dataclasses import dataclass
from typing import Literal
FILES='abcdefgh'; RANKS='12345678'
SQUARES=[f+r for r in RANKS[::-1] for f in FILES]
PIECES=['empty']+[f'{color}_{piece}' for color in ('white','black') for piece in ('pawn','knight','bishop','rook','queen','king')]
@dataclass
class BoardRecognitionResult:
    orientation: Literal['white_bottom','black_bottom','unknown']
    side_to_move: Literal['white','black','unknown']
    squares: dict[str,str]
    confidence: float
    warnings: list[str]
SQUARE_SCHEMA={'type':'object','additionalProperties':False,'required':SQUARES,'properties':{sq:{'type':'string','enum':PIECES} for sq in SQUARES}}
SCHEMA={'type':'object','additionalProperties':False,'required':['orientation','side_to_move','squares','confidence','warnings'],'properties':{'orientation':{'type':'string','enum':['white_bottom','black_bottom','unknown']},'side_to_move':{'type':'string','enum':['white','black','unknown']},'squares':SQUARE_SCHEMA,'confidence':{'type':'number','minimum':0,'maximum':1},'warnings':{'type':'array','items':{'type':'string'}}}}
def parse(data):
    if not isinstance(data,dict): raise ValueError('root must be an object')
    squares=data.get('squares')
    if not isinstance(squares,dict): raise ValueError('squares must be an object')
    missing=set(SQUARES)-set(squares); extra=set(squares)-set(SQUARES)
    if missing or extra: raise ValueError(f'64-square coverage failed: missing={sorted(missing)} extra={sorted(extra)}')
    invalid={sq:value for sq,value in squares.items() if value not in PIECES}
    if invalid: raise ValueError(f'invalid square values: {invalid}')
    orientation=data.get('orientation'); side=data.get('side_to_move')
    if orientation not in ('white_bottom','black_bottom','unknown'): raise ValueError('invalid orientation')
    if side not in ('white','black','unknown'): raise ValueError('invalid side_to_move')
    confidence=float(data.get('confidence')); warnings=data.get('warnings',[])
    if not 0<=confidence<=1 or not isinstance(warnings,list): raise ValueError('invalid confidence or warnings')
    return BoardRecognitionResult(orientation,side,dict(squares),confidence,list(warnings))
def piece_count(result): return sum(value!='empty' for value in result.squares.values())
