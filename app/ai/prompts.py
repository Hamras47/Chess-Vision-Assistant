BOARD_PROMPT='''The image contains exactly one standard 8x8 chessboard. Your only task is visual transcription; do not analyze or recommend chess moves.

Determine orientation from coordinate labels when visible. Inspect all 64 squares systematically, rank by rank, and assign exactly one allowed value to every square: empty, white_pawn, white_knight, white_bishop, white_rook, white_queen, white_king, black_pawn, black_knight, black_bishop, black_rook, black_queen, or black_king.

Ignore red outlines, green highlights, last-move highlights, coordinate labels, arrows, and selection indicators. Return only actual pieces. A screenshot usually cannot prove side to move; use unknown instead of guessing. Populate warnings for visual uncertainty. Return the required structured data only.'''
