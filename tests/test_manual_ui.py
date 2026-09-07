import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import chess
import numpy as np
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication, QPushButton

from app.chess.coordinates import Orientation, mapping_table, square_to_visual, visual_to_square
from app.ui.board_widget import ChessBoardWidget
from app.ui.dpi_coordinates import MonitorCoordinates
from app.ui.main_window import MainWindow
from app.ui.promotion_dialog import PromotionDialog
from app.ui.region_selector import RegionSelector


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def make_window(monkeypatch, app):
    monkeypatch.setattr(MainWindow, "_find_engine", lambda self: "")
    window = MainWindow()
    window.show()
    app.processEvents()
    return window


def test_64_square_mapping_and_orientations():
    for orientation in (Orientation.WHITE_BOTTOM, Orientation.BLACK_BOTTOM):
        mapped = [visual_to_square(row, col, orientation) for row in range(8) for col in range(8)]
        assert len(set(mapped)) == 64
        for square in chess.SQUARES:
            row, col = square_to_visual(square, orientation)
            assert visual_to_square(row, col, orientation) == square
    assert mapping_table(Orientation.WHITE_BOTTOM)[7] == ["a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1"]
    assert mapping_table(Orientation.BLACK_BOTTOM)[7] == ["h8", "g8", "f8", "e8", "d8", "c8", "b8", "a8"]


def test_click_click_legal_move_and_illegal_target(app):
    widget = ChessBoardWidget()
    widget.resize(640, 640)
    widget.show()
    app.processEvents()
    spy = QSignalSpy(widget.move_requested)
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, widget._rect_for(chess.E2).center().toPoint())
    assert widget.selected == chess.E2
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, widget._rect_for(chess.E5).center().toPoint())
    assert spy.count() == 0
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, widget._rect_for(chess.E2).center().toPoint())
    QTest.mouseClick(widget, Qt.LeftButton, Qt.NoModifier, widget._rect_for(chess.E4).center().toPoint())
    assert spy.count() == 1
    assert list(spy.at(0)) == [chess.E2, chess.E4]
    widget.close()


def test_drag_drop_legal_move(app):
    widget = ChessBoardWidget()
    widget.resize(640, 640)
    widget.show()
    app.processEvents()
    spy = QSignalSpy(widget.move_requested)
    source = widget._rect_for(chess.G1).center().toPoint()
    target = widget._rect_for(chess.F3).center().toPoint()
    QTest.mousePress(widget, Qt.LeftButton, Qt.NoModifier, source)
    QTest.mouseMove(widget, QPoint((source.x() + target.x()) // 2, (source.y() + target.y()) // 2), 20)
    QTest.mouseMove(widget, target, 20)
    QTest.mouseRelease(widget, Qt.LeftButton, Qt.NoModifier, target)
    assert spy.count() == 1
    assert list(spy.at(0)) == [chess.G1, chess.F3]
    widget.close()


def test_main_window_smoke_responsive_and_pieces_render(monkeypatch, app):
    window = make_window(monkeypatch, app)
    assert window.board.board_fen() == chess.STARTING_BOARD_FEN
    assert len(window.view.piece_map()) == 32
    for width, height in ((1150, 800), (900, 650), (1400, 900)):
        window.resize(width, height)
        app.processEvents()
        _, _, square = window.view._layout()
        assert square > 45
        assert window.panel.isVisible()
    image = window.view.grab().toImage()
    assert not image.isNull()
    window.close()


@pytest.mark.parametrize(
    "width,height,expected_mode",
    [
        (1920, 1080, "wide"),
        (1200, 900, "wide"),
        (960, 1000, "wide"),
        (900, 900, "compact"),
        (800, 900, "compact"),
        (700, 800, "compact"),
        (600, 700, "compact"),
    ],
)
def test_real_window_resizes_and_reflows_without_clipping(monkeypatch, app, width, height, expected_mode):
    window = make_window(monkeypatch, app)
    window.resize(width, height)
    app.processEvents()
    assert (window.width(), window.height()) == (width, height)
    assert window.layout_mode == expected_mode
    assert window.view.width() == window.view.height()
    assert window.view.geometry().intersected(window.board_host.rect()) == window.view.geometry()
    assert window.view.width() >= 460
    for control in (window.panel.best_button, window.panel.evaluation_label, window.panel.scan_button, window.panel.new_button):
        assert control.isVisible()
        top_left = control.mapTo(window, QPoint(0, 0))
        assert 0 <= top_left.x() < window.width()
        assert 0 <= top_left.y() < window.height()
        assert top_left.x() + control.width() <= window.width()
        assert top_left.y() + control.height() <= window.height()
    if expected_mode == "wide":
        assert window.panel.width() <= 220
        assert window.panel.x() > window.board_host.x()
    else:
        assert window.panel.y() > window.board_host.y()
        assert window.panel.width() == window.body.geometry().width()
    window.close()


def test_resizing_back_to_large_restores_wide_layout(monkeypatch, app):
    window = make_window(monkeypatch, app)
    window.resize(700, 800)
    app.processEvents()
    assert window.layout_mode == "compact"
    window.resize(960, 1000)
    app.processEvents()
    assert window.layout_mode == "wide"
    assert window.panel.width() <= 220
    window.close()


def test_minimum_size_and_visible_ui_are_minimal(monkeypatch, app):
    window = make_window(monkeypatch, app)
    assert (window.minimumWidth(), window.minimumHeight()) == (560, 560)
    assert window.view.minimumWidth() <= 180
    assert window.panel.minimumWidth() <= 180
    assert not window.testAttribute(Qt.WA_TranslucentBackground)
    assert not window.windowFlags() & Qt.FramelessWindowHint
    visible_text = {label.text() for label in window.panel.findChildren(type(window.panel.turn_label))}
    assert "ALTERNATIVES" not in visible_text
    assert "MOVE HISTORY" not in visible_text
    assert not hasattr(window.panel, "undo_button")
    assert not hasattr(window.panel, "redo_button")
    window.close()


def test_piece_assets_use_one_consistent_palette():
    root = Path(__file__).parents[1] / "assets" / "pieces"
    for path in root.glob("black_*.svg"):
        source = path.read_text(encoding="utf-8").lower()
        assert "#24292f" in source, path.name
    for path in root.glob("white_*.svg"):
        source = path.read_text(encoding="utf-8").lower()
        assert "#f5f0e6" in source, path.name


def test_white_piece_on_light_and_black_piece_on_dark_have_contrast(app):
    widget = ChessBoardWidget()
    widget.resize(640, 640)
    widget.show()
    app.processEvents()
    image = widget.grab().toImage()

    def contrasting_pixels(square, background):
        rect = widget._rect_for(square).adjusted(10, 10, -10, -10).toRect()
        count = 0
        for x in range(rect.left(), rect.right() + 1, 2):
            for y in range(rect.top(), rect.bottom() + 1, 2):
                color = image.pixelColor(x, y)
                if sum(abs(component - base) for component, base in zip((color.red(), color.green(), color.blue()), background)) > 75:
                    count += 1
        return count

    assert contrasting_pixels(chess.B1, (216, 212, 197)) > 80
    assert contrasting_pixels(chess.B8, (111, 136, 116)) > 80
    widget.close()


def test_white_and_black_orientation_follow_player(monkeypatch, app):
    window = make_window(monkeypatch, app)
    window.load_position(chess.Board(), chess.BLACK, chess.WHITE)
    assert window.view.orientation == Orientation.BLACK_BOTTOM
    window.load_position(chess.Board(), chess.WHITE, chess.WHITE)
    assert window.view.orientation == Orientation.WHITE_BOTTOM
    window.flip_board()
    assert window.view.orientation == Orientation.BLACK_BOTTOM
    window.close()


def test_manual_moves_both_sides_trigger_analysis(monkeypatch, app):
    window = make_window(monkeypatch, app)
    calls = []
    monkeypatch.setattr(window, "analyze", lambda: calls.append(window.board.turn))
    assert window.commit_manual_move(chess.E2, chess.E4)
    assert window.commit_manual_move(chess.E7, chess.E5)
    assert calls == [chess.BLACK, chess.WHITE]
    assert window.game.history_text() == "1. e4    e5"
    assert not hasattr(window.panel, "history_label")
    window.close()


def test_stale_stockfish_result_is_ignored(monkeypatch, app):
    window = make_window(monkeypatch, app)
    window.analysis_token = 4
    rows = [("e4", "e2e4", 20, None, 12)]
    window.analysis_done(3, rows)
    assert window.view.arrow is None
    window.analysis_done(4, rows)
    assert window.view.arrow == (chess.E2, chess.E4)
    window.close()


def test_rescan_style_load_resets_history_undo_redo_and_arrow(monkeypatch, app):
    window = make_window(monkeypatch, app)
    monkeypatch.setattr(window, "analyze", lambda: None)
    window.commit_manual_move(chess.E2, chess.E4)
    window.undo()
    window.view.arrow = (chess.E7, chess.E5)
    imported = chess.Board(None)
    imported.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    imported.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    window.load_position(imported, chess.WHITE, chess.BLACK)
    assert not window.game.records and not window.game.can_undo and not window.game.can_redo
    assert window.view.arrow is None
    assert window.board.turn == chess.BLACK
    assert window.board.castling_rights == 0
    window.close()


def test_promotion_and_scan_overlays_construct(app):
    promotion = PromotionDialog(chess.WHITE)
    assert {button.text() for button in promotion.findChildren(QPushButton)} == {"Queen", "Rook", "Bishop", "Knight"}
    assert promotion.isModal()
    promotion.close()
    desktop = np.zeros((600, 800, 3), dtype=np.uint8)
    mapping = MonitorCoordinates(QRect(0, 0, 800, 600), {"left": 0, "top": 0, "width": 800, "height": 600}, 1.0)
    selector = RegionSelector(desktop, mapping)
    selector.show()
    app.processEvents()
    assert selector.cursor().shape() == Qt.CrossCursor
    selector.close()


def test_no_live_tracking_runtime_files_or_imports():
    root = Path(__file__).parents[1]
    forbidden_files = {"tracking_worker.py", "change_detector.py", "move_tracker.py", "session.py", "stabilizer.py"}
    assert not forbidden_files & {path.name for path in (root / "app").rglob("*.py")}
    source = "\n".join(path.read_text(encoding="utf-8") for path in (root / "app").rglob("*.py"))
    for forbidden in ("TrackingWorker", "start_tracking", "tracking_frame", "RECOVERING", "VERIFYING", "TRACKING_LOST", "frame_signature"):
        assert forbidden not in source
