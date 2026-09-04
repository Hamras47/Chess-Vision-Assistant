from dataclasses import dataclass,field
from typing import Any
import chess

from .coordinates import Orientation


@dataclass
class TrackingSession:
    player_color: chess.Color|None=None
    browser_orientation: Orientation|None=None
    app_display_orientation: Orientation=Orientation.WHITE_BOTTOM
    board: chess.Board=field(default_factory=chess.Board)
    board_version: int=0
    tracking_session_id: int=0
    board_region: dict[str,int]|None=None
    last_accepted_frame: Any=None
    latest_frame: Any=None
    last_capture_signature: Any=None
    last_accepted_signature: Any=None
    frame_sequence: int=0
    tracking_state: str='WATCHING'
    local_recoveries: int=0
    two_ply_recoveries: int=0
    ai_recoveries: int=0
    failed_ai_recoveries: int=0

    @property
    def opponent_color(self):
        return None if self.player_color is None else not self.player_color

    def select_player(self,color:chess.Color):
        self.player_color=color
        self.app_display_orientation=Orientation.WHITE_BOTTOM if color==chess.WHITE else Orientation.BLACK_BOTTOM
