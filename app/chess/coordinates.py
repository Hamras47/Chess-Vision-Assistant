import chess

def visual_index_to_square(index: int, white_bottom: bool) -> chess.Square:
    row, col = divmod(index, 8)
    return chess.square(col, 7-row) if white_bottom else chess.square(7-col, row)

def square_to_visual_index(square: chess.Square, white_bottom: bool) -> int:
    file, rank = chess.square_file(square), chess.square_rank(square)
    return (7-rank)*8+file if white_bottom else rank*8+(7-file)

