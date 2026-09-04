from enum import Enum
import chess

class Orientation(str,Enum):
    WHITE_BOTTOM='white_bottom'
    BLACK_BOTTOM='black_bottom'

def as_orientation(value):
    if isinstance(value,Orientation):return value
    if value is True:return Orientation.WHITE_BOTTOM
    if value is False:return Orientation.BLACK_BOTTOM
    return Orientation(value)

def visual_to_square(row:int,col:int,orientation:Orientation)->chess.Square:
    if not 0<=row<8 or not 0<=col<8:raise ValueError(f'Visual cell out of range: row={row}, col={col}')
    orientation=as_orientation(orientation)
    file,rank=(col,7-row) if orientation is Orientation.WHITE_BOTTOM else (7-col,row)
    return chess.square(file,rank)

def square_to_visual(square:chess.Square,orientation:Orientation)->tuple[int,int]:
    orientation=as_orientation(orientation); file=chess.square_file(square); rank=chess.square_rank(square)
    return (7-rank,file) if orientation is Orientation.WHITE_BOTTOM else (rank,7-file)

def visual_index_to_square(index:int,orientation:Orientation)->chess.Square:
    row,col=divmod(index,8); return visual_to_square(row,col,orientation)

def square_to_visual_index(square:chess.Square,orientation:Orientation)->int:
    row,col=square_to_visual(square,orientation); return row*8+col

def user_color(orientation:Orientation)->chess.Color:return chess.WHITE if as_orientation(orientation) is Orientation.WHITE_BOTTOM else chess.BLACK

def mapping_table(orientation:Orientation):return [[chess.square_name(visual_to_square(row,col,orientation)) for col in range(8)] for row in range(8)]
