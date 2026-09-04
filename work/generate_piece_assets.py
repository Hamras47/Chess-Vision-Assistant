from pathlib import Path
import chess,chess.svg
out=Path('assets/pieces'); out.mkdir(parents=True,exist_ok=True)
names={chess.PAWN:'pawn',chess.KNIGHT:'knight',chess.BISHOP:'bishop',chess.ROOK:'rook',chess.QUEEN:'queen',chess.KING:'king'}
for color,label in ((chess.WHITE,'white'),(chess.BLACK,'black')):
    for piece_type,name in names.items():
        svg=chess.svg.piece(chess.Piece(piece_type,color))
        if color: svg=svg.replace('fill="#fff"','fill="#f5f0e6"').replace('stroke="#000"','stroke="#252a30"')
        else: svg=svg.replace('fill="#000"','fill="#24292f"').replace('stroke="#000"','stroke="#c7ccd1"')
        (out/f'{label}_{name}.svg').write_text(svg,encoding='utf-8')
